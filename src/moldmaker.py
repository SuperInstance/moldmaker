#!/usr/bin/env python3
"""
moldmaker.py — the Moldmaker deposit pipeline (v0).

One transmission -> one deposit -> one git commit carrying three parts:
  1. deposits/<slug>.md        human markdown: the said (verbatim) with
                               the meant (annotations) running through it
  2. deposits/<slug>.a2a.json  the A2A twin: structured intent for agents
  3. the commit message        commentary facing the other agents

Design rules enforced here (docs/ARTIFACT-SPEC.md, docs/PHILOSOPHY.md):
  - The user's words are never rewritten by this code. Layer A is the
    raw transmission, byte for byte.
  - Every interpreted element must trace to an exact quote (or span)
    of the raw transmission, or declare an external context source.
    Untraceable interpretations are refused, never filed.
  - Inferred actions are PROPOSED, never approved, unless the human
    explicitly passes their ids as approved. An inference is not an
    authorization.
  - Deposits are idempotent: the same source + external id (or the
    same raw text) never lands twice.
  - Corrections are new deposits. Nothing here edits an old deposit.
  - No date in filenames. The commit carries the date; git is the ledger.
  - Obvious credentials are refused: secrets never enter deposits.

Stdlib only. The interpretation itself is produced elsewhere
(src/interpreter.py, or any agent) and handed in as JSON; this module
is the deterministic, validating, filing half — the part that must
not hallucinate.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

SCHEMA_VERSION = 1

ANNOTATION_KINDS = {"note", "inference", "formalization", "context", "action", "question"}
ANNOTATION_BASES = {"said", "inferred", "context"}
INTENT_STATUSES = {"draft", "proposed", "approved"}
ACTION_OWNERS = {"logic-agent", "hardware-agent", "research-agent", "human", "unspecified"}
PRIORITIES = {"high", "normal", "low"}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*\S{8,}", re.I),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
]


class MoldmakerError(Exception):
    pass


# ---------------------------------------------------------------- git

def git(store, *args, check=True):
    return subprocess.run(
        ["git", "-C", store, *args], capture_output=True, text=True, check=check
    )


def is_git_repo(store):
    return os.path.isdir(store) and git(store, "rev-parse", "--git-dir", check=False).returncode == 0


def git_root(store):
    out = git(store, "rev-parse", "--show-toplevel")
    return out.stdout.strip()


def store_dirty(store):
    """True if the repo containing the store has uncommitted changes."""
    return bool(git(store, "status", "--porcelain").stdout.strip())


def foreign_dirty_paths(store):
    """Uncommitted paths that a deposit must not sweep into its commit.

    A deposit may carry its own store files (deposits/, specs/, the
    store config files — e.g. just created by init). Anything else
    dirty in the repo belongs to somebody else's work in progress and
    blocks the deposit.
    """
    root = git_root(store)
    prefix = os.path.relpath(os.path.abspath(store), os.path.abspath(root))
    prefix = "" if prefix == "." else prefix.rstrip("/") + "/"
    allowed = (prefix + "deposits/", prefix + "specs/",
               prefix + "moldmaker.json", prefix + "STORE.md")
    bad = []
    for line in git(store, "status", "--porcelain").stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"')
        if not any(path == a or path.startswith(a) for a in allowed):
            bad.append(path)
    return bad


def ensure_identity(store):
    """A deposit must be able to commit in any checkout — including a
    fresh CI checkout with no git identity configured. Set a local
    Moldmaker identity when (and only when) none exists."""
    if not git(store, "config", "user.name", check=False).stdout.strip():
        git(store, "config", "user.name", "moldmaker")
    if not git(store, "config", "user.email", check=False).stdout.strip():
        git(store, "config", "user.email", "moldmaker@local")


def commit_count(store):
    out = git(store, "rev-list", "--count", "HEAD", check=False)
    return int(out.stdout.strip()) if out.returncode == 0 else 0


# ---------------------------------------------------------------- utils

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slugify(text, fallback="deposit"):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:48].strip("-") or fallback)


def scan_secrets(text):
    hits = [p.pattern for p in SECRET_PATTERNS if p.search(text or "")]
    if hits:
        raise MoldmakerError(
            "transmission appears to contain a credential; secrets never enter "
            f"deposits (matched {len(hits)} pattern(s))"
        )


def _require(cond, msg):
    if not cond:
        raise MoldmakerError(msg)


def _check_quote(raw, item, label):
    """Validate that item['source_quote'] traces to the raw transmission.

    Accepts either an exact substring quote, or an explicit span
    {start, end} whose slice equals the quote. Context-based items must
    instead carry source_ref and are checked by the caller.
    """
    quote = item.get("source_quote")
    _require(isinstance(quote, str) and quote.strip(), f"{label}: missing source_quote")
    span = item.get("span")
    if span is not None:
        try:
            start, end = int(span["start"]), int(span["end"])
        except Exception:
            raise MoldmakerError(f"{label}: malformed span")
        _require(0 <= start <= end <= len(raw), f"{label}: span out of bounds")
        _require(raw[start:end] == quote, f"{label}: span does not match source_quote")
    else:
        _require(quote in raw, f"{label}: source_quote not found in transmission")


# ---------------------------------------------------------------- validation

def validate_interpretation(raw, interp, approved_ids=frozenset()):
    """Validate + normalize an interpretation. Returns (clean, notes).

    Coercions are recorded in notes, never silent: an element the model
    marked 'approved' that the human did not approve is demoted to
    'proposed' and the demotion is written into the twin.
    """
    notes = []
    _require(isinstance(interp, dict), "interpretation must be a JSON object")
    clean = {"schema_version": SCHEMA_VERSION}

    title = interp.get("title")
    _require(isinstance(title, str) and title.strip(), "interpretation: missing title")
    clean["title"] = title.strip()

    sections = interp.get("sections")
    _require(isinstance(sections, list) and sections, "interpretation: sections must be a non-empty list")
    clean_sections = []
    for i, sec in enumerate(sections):
        label = f"sections[{i}]"
        _require(isinstance(sec, dict), f"{label}: must be an object")
        heading = sec.get("heading")
        _require(isinstance(heading, str) and heading.strip(), f"{label}: missing heading")
        _check_quote(raw, sec, label)
        anns = []
        for j, ann in enumerate(sec.get("annotations", [])):
            alabel = f"{label}.annotations[{j}]"
            _require(isinstance(ann, dict), f"{alabel}: must be an object")
            kind = ann.get("kind", "note")
            _require(kind in ANNOTATION_KINDS, f"{alabel}: bad kind {kind!r}")
            basis = ann.get("basis", "inferred")
            _require(basis in ANNOTATION_BASES, f"{alabel}: bad basis {basis!r}")
            text = ann.get("text")
            _require(isinstance(text, str) and text.strip(), f"{alabel}: missing text")
            conf = ann.get("confidence")
            if conf is not None:
                _require(isinstance(conf, (int, float)) and 0 <= conf <= 1,
                         f"{alabel}: confidence must be 0..1")
            if basis == "context":
                _require(isinstance(ann.get("source_ref"), str) and ann["source_ref"].strip(),
                         f"{alabel}: context annotation needs source_ref")
            elif ann.get("source_quote"):
                _check_quote(raw, ann, alabel)
            anns.append({"kind": kind, "basis": basis, "text": text.strip(),
                         "confidence": conf,
                         "source_quote": ann.get("source_quote"),
                         "source_ref": ann.get("source_ref")})
        clean_sections.append({"heading": heading.strip(),
                               "source_quote": sec["source_quote"],
                               "span": sec.get("span"),
                               "annotations": anns})
    clean["sections"] = clean_sections

    def _ids(items, label):
        seen = set()
        for it in items:
            _require(isinstance(it, dict) and isinstance(it.get("id"), str) and it["id"].strip(),
                     f"{label}: every item needs a string id")
            _require(it["id"] not in seen, f"{label}: duplicate id {it['id']!r}")
            seen.add(it["id"])
        return seen

    intents = interp.get("intents", [])
    _require(isinstance(intents, list), "interpretation: intents must be a list")
    _ids(intents, "intents")
    clean_intents = []
    for it in intents:
        _check_quote(raw, it, f"intent {it['id']}")
        status = it.get("status", "proposed")
        _require(status in INTENT_STATUSES, f"intent {it['id']}: bad status {status!r}")
        if status == "approved" and it["id"] not in approved_ids:
            status = "proposed"
            notes.append(f"intent {it['id']}: 'approved' demoted to 'proposed' (not human-approved)")
        clean_intents.append({"id": it["id"], "kind": it.get("kind", "statement"),
                              "statement": it.get("statement", "").strip(),
                              "source_quote": it["source_quote"],
                              "confidence": it.get("confidence"),
                              "status": status})
    clean["intents"] = clean_intents

    actions = interp.get("actions", [])
    _require(isinstance(actions, list), "interpretation: actions must be a list")
    _ids(actions, "actions")
    clean_actions = []
    for a in actions:
        _check_quote(raw, a, f"action {a['id']}")
        owner = a.get("owner", "unspecified")
        _require(owner in ACTION_OWNERS, f"action {a['id']}: bad owner {owner!r}")
        status = a.get("status", "proposed")
        if status == "approved" and a["id"] not in approved_ids:
            status = "proposed"
            notes.append(f"action {a['id']}: 'approved' demoted to 'proposed' (not human-approved)")
        _require(status in {"proposed", "approved"}, f"action {a['id']}: bad status {status!r}")
        clean_actions.append({"id": a["id"], "title": a.get("title", "").strip(),
                              "owner": owner, "status": status,
                              "source_quote": a["source_quote"],
                              "confidence": a.get("confidence")})
    clean["actions"] = clean_actions

    questions = interp.get("questions", [])
    _require(isinstance(questions, list), "interpretation: questions must be a list")
    _ids(questions, "questions")
    clean_questions = []
    for q in questions:
        if q.get("source_quote"):
            _check_quote(raw, q, f"question {q['id']}")
        priority = q.get("priority", "normal")
        _require(priority in PRIORITIES, f"question {q['id']}: bad priority {priority!r}")
        clean_questions.append({"id": q["id"], "question": q.get("question", "").strip(),
                                "why": q.get("why", "").strip(), "priority": priority,
                                "source_quote": q.get("source_quote")})
    clean["questions"] = clean_questions

    commentary = interp.get("commentary", {})
    _require(isinstance(commentary, dict), "interpretation: commentary must be an object")
    clean["commentary"] = {
        "tone": commentary.get("tone", ""),
        "meaning": commentary.get("meaning", ""),
        "salience": commentary.get("salience", ""),
        "connections": commentary.get("connections", []),
    }
    clean["validation_notes"] = notes
    return clean, notes


# ---------------------------------------------------------------- store

def init_store(store, project="moldmaker-project", commit=True):
    os.makedirs(os.path.join(store, "deposits"), exist_ok=True)
    os.makedirs(os.path.join(store, "specs"), exist_ok=True)
    created = False
    cfg_path = os.path.join(store, "moldmaker.json")
    if not os.path.exists(cfg_path):
        with open(cfg_path, "w") as f:
            json.dump({"project": project, "schema_version": SCHEMA_VERSION,
                       "created_at": now_iso()}, f, indent=2)
            f.write("\n")
        created = True
    store_md = os.path.join(store, "STORE.md")
    if not os.path.exists(store_md):
        with open(store_md, "w") as f:
            f.write(f"# {project} — Moldmaker store\n\n"
                    "deposits/ holds one human markdown + one A2A twin per "
                    "transmission.\nspecs/ holds generated views (INDEX, "
                    "ACTIONS, OPEN-QUESTIONS, AGENDA).\nThe git log is the "
                    "ledger; commit messages are commentary to other agents.\n")
        created = True
    if not is_git_repo(store):
        git(store, "init", "-q", "-b", "main")
        git(store, "config", "user.name", "moldmaker")
        git(store, "config", "user.email", "moldmaker@local")
        created = True
    # Only auto-commit when the store is its own repo root; a store nested
    # in another repo must never sweep that repo's unrelated changes.
    own_root = is_git_repo(store) and os.path.abspath(git_root(store)) == os.path.abspath(store)
    if commit and own_root and store_dirty(store):
        git(store, "add", "-A")
        git(store, "commit", "-q", "-m", f"init: moldmaker store for {project}",
            "-m", "Commentary: store created by moldmaker.py init. Layout per docs/ARTIFACT-SPEC.md.")
    return created


def deposit_id_for(source, external_id, raw):
    key = external_id if external_id else hashlib.sha256(raw.encode()).hexdigest()
    return hashlib.sha256(f"{source}|{key}".encode()).hexdigest()[:16]


def _twin_paths(store):
    d = os.path.join(store, "deposits")
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, n) for n in os.listdir(d) if n.endswith(".a2a.json"))


def load_twins(store):
    twins = []
    for p in _twin_paths(store):
        with open(p) as f:
            twins.append(json.load(f))
    twins.sort(key=lambda t: t["meta"]["timestamp"])
    return twins


def find_existing(store, deposit_id):
    for t in load_twins(store):
        if t["meta"]["deposit_id"] == deposit_id:
            return t["meta"]["slug"]
    return None


# ---------------------------------------------------------------- rendering

def render_human_md(meta, raw, interp):
    lines = [f"# {interp['title']}", ""]
    lines.append(f"_Deposit {meta['deposit_id']} · source {meta['source']} · "
                 f"{meta['timestamp']} · Layer A is the user's exact words; "
                 f"Layer B annotations are marked ▸ and never alter Layer A._")
    if meta.get("audio_ref"):
        lines.append(f"_Audio: {meta['audio_ref']}_")
    lines += ["", "## Layer A — the said (verbatim)", "", raw.strip(), ""]
    lines += ["## Layer B — the meant (annotated reading)", ""]
    for sec in interp["sections"]:
        lines += [f"### {sec['heading']}", "", f"> {sec['source_quote']}", ""]
        for ann in sec["annotations"]:
            conf = f" (confidence {ann['confidence']})" if ann.get("confidence") is not None else ""
            ref = f" [source: {ann['source_ref']}]" if ann.get("source_ref") else ""
            lines.append(f"> ▸ **{ann['kind']}** ({ann['basis']}){conf}: {ann['text']}{ref}")
        lines.append("")
    if interp["intents"]:
        lines += ["## Formal intents", ""]
        for it in interp["intents"]:
            lines.append(f"- **{it['id']}** [{it['status']}] {it['statement']} "
                         f"— from: “{it['source_quote']}”")
        lines.append("")
    if interp["validation_notes"]:
        lines += ["## Validation notes", ""]
        for n in interp["validation_notes"]:
            lines.append(f"- {n}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_twin(meta, raw, interp):
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": meta,
        "source": {"raw": raw},
        "sections": interp["sections"],
        "intents": interp["intents"],
        "actions": interp["actions"],
        "questions": interp["questions"],
        "commentary": interp["commentary"],
        "validation_notes": interp["validation_notes"],
        "provenance_note": "Every intent/action/question traces to an exact "
                           "source_quote (or span) of source.raw, validated "
                           "at deposit time by src/moldmaker.py.",
    }


def regenerate_views(store):
    twins = load_twins(store)
    specs = os.path.join(store, "specs")
    os.makedirs(specs, exist_ok=True)

    idx = ["# Deposit index", ""]
    for t in twins:
        m = t["meta"]
        idx.append(f"- [{t['sections'] and t['meta']['title']}](../deposits/{m['slug']}.md) "
                   f"— {m['timestamp']} · {m['source']} · deposit {m['deposit_id']}")
    with open(os.path.join(specs, "INDEX.md"), "w") as f:
        f.write("\n".join(idx).rstrip() + "\n")

    acts = ["# Actions (generated from deposits)", "",
            "Status is proposed until a human approves the action id. "
            "An inference is not an authorization.", ""]
    for t in twins:
        for a in t["actions"]:
            acts.append(f"- **{a['id']}** [{a['status']}] ({a['owner']}) {a['title']} "
                        f"— deposit {t['meta']['deposit_id']}")
    with open(os.path.join(specs, "ACTIONS.md"), "w") as f:
        f.write("\n".join(acts).rstrip() + "\n")

    qs = ["# Open questions (generated from deposits)", "",
          "Only questions whose answers would change the build belong here.", ""]
    order = {"high": 0, "normal": 1, "low": 2}
    all_q = [(q, t) for t in twins for q in t["questions"]]
    for q, t in sorted(all_q, key=lambda x: order[x[0]["priority"]]):
        qs.append(f"- **{q['id']}** [{q['priority']}] {q['question']} "
                  f"— why: {q['why']} (deposit {t['meta']['deposit_id']})")
    with open(os.path.join(specs, "OPEN-QUESTIONS.md"), "w") as f:
        f.write("\n".join(qs).rstrip() + "\n")
    return twins


def render_agenda(store):
    twins = load_twins(store)
    lines = ["# Meeting agenda (generated)", ""]
    order = {"high": 0, "normal": 1, "low": 2}
    all_q = [(q, t) for t in twins for q in t["questions"]]
    lines.append("## Questions only the user can settle")
    if all_q:
        for q, t in sorted(all_q, key=lambda x: order[x[0]["priority"]]):
            lines.append(f"- [{q['priority']}] {q['question']} — {q['why']}")
    else:
        lines.append("- (none — question exhaustion for now)")
    lines += ["", "## Proposed actions awaiting approval"]
    pending = [a for t in twins for a in t["actions"] if a["status"] == "proposed"]
    if pending:
        for a in pending:
            lines.append(f"- {a['id']} ({a['owner']}): {a['title']}")
    else:
        lines.append("- (none)")
    lines += ["", "## Recent deposits"]
    for t in twins[-5:]:
        lines.append(f"- {t['meta']['timestamp']} — {t['meta']['title']}")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------- deposit

def deposit(store, raw, interp, source="text", timestamp=None, external_id=None,
            audio_ref=None, approved_ids=frozenset(), commit=True):
    _require(isinstance(raw, str) and raw.strip(), "transmission text is empty")
    scan_secrets(raw)
    timestamp = timestamp or now_iso()
    clean, _notes = validate_interpretation(raw, interp, approved_ids)
    dep_id = deposit_id_for(source, external_id, raw)

    existing = find_existing(store, dep_id)
    if existing:
        return {"deposit_id": dep_id, "slug": existing, "created": False, "commit": None}

    if commit:
        _require(is_git_repo(store), "store is not a git repo (run init first)")
        ensure_identity(store)
        foreign = foreign_dirty_paths(store)
        _require(not foreign,
                 f"repo has uncommitted changes outside the store ({foreign[:3]}); "
                 "refusing to mix a deposit into them")

    slug = f"{slugify(clean['title'])}-{dep_id[:8]}"
    meta = {"deposit_id": dep_id, "slug": slug, "title": clean["title"],
            "source": source, "timestamp": timestamp,
            "external_id": external_id, "audio_ref": audio_ref}

    os.makedirs(os.path.join(store, "deposits"), exist_ok=True)
    human = render_human_md(meta, raw, clean)
    twin = build_twin(meta, raw, clean)
    with open(os.path.join(store, "deposits", f"{slug}.md"), "w") as f:
        f.write(human)
    with open(os.path.join(store, "deposits", f"{slug}.a2a.json"), "w") as f:
        json.dump(twin, f, indent=2)
        f.write("\n")
    regenerate_views(store)
    with open(os.path.join(store, "specs", "AGENDA.md"), "w") as f:
        f.write(render_agenda(store))

    commit_hash = None
    if commit:
        add_paths = ["deposits", "specs"]
        for extra in ("moldmaker.json", "STORE.md"):
            if os.path.exists(os.path.join(store, extra)):
                add_paths.append(extra)
        git(store, "add", "--", *add_paths)
        c = clean["commentary"]
        body = []
        if c["meaning"]:
            body.append(f"Meaning: {c['meaning']}")
        if c["salience"]:
            body.append(f"Why this mattered: {c['salience']}")
        if c["tone"]:
            body.append(f"Tone: {c['tone']}")
        for conn in c["connections"]:
            body.append(f"Connects: {conn}")
        body.append(f"Deposit {dep_id} · {len(clean['actions'])} proposed action(s) · "
                    f"{len(clean['questions'])} open question(s). "
                    "Orientation for agents: read this commentary, then the deposit.")
        args = ["commit", "-q", "-m", f"deposit: {clean['title']}"]
        for b in body:
            args += ["-m", b]
        git(store, *args)
        commit_hash = git(store, "rev-parse", "--short", "HEAD").stdout.strip()
    return {"deposit_id": dep_id, "slug": slug, "created": True, "commit": commit_hash}


def status(store):
    twins = load_twins(store)
    return {
        "deposits": len(twins),
        "actions_proposed": sum(1 for t in twins for a in t["actions"] if a["status"] == "proposed"),
        "actions_approved": sum(1 for t in twins for a in t["actions"] if a["status"] == "approved"),
        "open_questions": sum(len(t["questions"]) for t in twins),
        "commits": commit_count(store) if is_git_repo(store) else 0,
    }


# ---------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description="Moldmaker deposit pipeline (v0)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init")
    pi.add_argument("store")
    pi.add_argument("--project", default="moldmaker-project")

    pd = sub.add_parser("deposit")
    pd.add_argument("store")
    pd.add_argument("--text")
    pd.add_argument("--text-file")
    pd.add_argument("--interpretation", required=True)
    pd.add_argument("--source", default="text")
    pd.add_argument("--external-id")
    pd.add_argument("--audio-ref")
    pd.add_argument("--timestamp")
    pd.add_argument("--approve", default="", help="comma-separated ids the human approves")
    pd.add_argument("--no-commit", action="store_true")

    pv = sub.add_parser("validate")
    pv.add_argument("--text-file", required=True)
    pv.add_argument("--interpretation", required=True)

    ps = sub.add_parser("status")
    ps.add_argument("store")
    pa = sub.add_parser("agenda")
    pa.add_argument("store")

    args = p.parse_args(argv)
    try:
        if args.cmd == "init":
            init_store(args.store, args.project)
            print(f"store ready: {args.store}")
        elif args.cmd == "deposit":
            raw = args.text
            if args.text_file:
                with open(args.text_file) as f:
                    raw = f.read()
            with open(args.interpretation) as f:
                interp = json.load(f)
            approved = frozenset(x.strip() for x in args.approve.split(",") if x.strip())
            result = deposit(args.store, raw, interp, source=args.source,
                             timestamp=args.timestamp, external_id=args.external_id,
                             audio_ref=args.audio_ref, approved_ids=approved,
                             commit=not args.no_commit)
            print(json.dumps(result, indent=2))
        elif args.cmd == "validate":
            with open(args.text_file) as f:
                raw = f.read()
            with open(args.interpretation) as f:
                interp = json.load(f)
            _clean, notes = validate_interpretation(raw, interp)
            print("VALID" + (f" (notes: {notes})" if notes else ""))
        elif args.cmd == "status":
            print(json.dumps(status(args.store), indent=2))
        elif args.cmd == "agenda":
            print(render_agenda(args.store), end="")
    except MoldmakerError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
