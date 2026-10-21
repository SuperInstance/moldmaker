#!/usr/bin/env python3
"""
think.py — the Moldmaker completeness pass (PROCESS.md §4).

The deterministic half of the think cycle (agenda/view regeneration)
lives in moldmaker.py. This module is the other half: an LLM reads the
whole spec set — every deposit's intents, actions, open questions and
commentary — and attacks it with one question: *what's missing?*

Output discipline, same as everywhere in Moldmaker:

  - The output is a generated VIEW (specs/THINK.md), never a deposit.
    It contains agent inferences, labeled as agent inferences. It is
    not the user's words and never enters OPEN-QUESTIONS.md as if it
    were user-derived; the meeting agenda decides what gets asked.
  - Every gap, contradiction and proposed question must trace to the
    deposit ids that motivate it. A proposal that cannot name its
    deposits is refused — traceability is the point, here too.
  - Questions for the user are a budget (MAX_USER_QUESTIONS): only
    questions whose answers would change the build survive. Gaps the
    fleet can settle itself are listed separately, as fleet work.
  - Convergence signal: an empty result is a valid, reportable
    outcome — "question exhaustion for now" — not an error.

Providers match interpreter.py: "vault" (OIDC + the SuperInstance
vault proxy) or "openai" (any OpenAI-compatible endpoint). The LLM
call itself is injected (`complete_fn`) so tests run offline.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moldmaker  # noqa: E402
import interpreter  # noqa: E402

MAX_USER_QUESTIONS = 7
MAX_GAPS = 10
MAX_CONTRADICTIONS = 5
PRIORITIES = moldmaker.PRIORITIES

SYSTEM_PROMPT = """You are the completeness pass of Moldmaker. You are \
given the current spec set of a project — every deposit's intents, \
actions, open questions and commentary — and your one job is to attack \
it: what is missing? You are not the author of the specs and you must \
not rewrite them. Most gaps you find, the fleet should settle itself \
from the record or by research; only gaps that ONLY the user can \
settle become proposed questions, and only when the answer would \
change the build. Trivia dies unasked."""

SCHEMA_DESCRIPTION = """Return ONE JSON object, no prose around it:
{
  "gaps": [
    {"title": "short name of the gap",
     "detail": "what is unsettled and why it matters",
     "deposit_ids": ["deposit ids from the spec set that motivate this"]}
  ],
  "contradictions": [
    {"title": "short name of the tension",
     "detail": "which deposits pull against each other, and how",
     "deposit_ids": ["the deposit ids in tension"]}
  ],
  "proposed_questions": [
    {"question": "a question only the user can settle",
     "why": "why the answer would change the build",
     "priority": "high|normal|low",
     "deposit_ids": ["deposit ids that motivate asking"]}
  ]
}
Rules:
- deposit_ids must be copied exactly from the spec set below. A claim
  that cannot name its deposits will be rejected mechanically.
- proposed_questions is a budget of at most 7: the survivors only.
- Do not propose a question the spec set already answers, and do not
  re-ask a question that is already open verbatim — extend it or drop it.
- An empty result is a valid answer: if nothing is missing that would
  change the build, return three empty lists."""


class ThinkError(Exception):
    pass


def _require(cond, msg):
    if not cond:
        raise ThinkError(msg)


# ---------------------------------------------------------------- prompt

def build_context(twins):
    """The spec set, condensed to what the completeness pass reasons over."""
    lines = []
    for t in twins:
        m = t["meta"]
        lines.append(f"## deposit {m['deposit_id']} — {m['title']} "
                     f"({m['timestamp']}, source {m['source']})")
        for it in t["intents"]:
            lines.append(f"- intent {it['id']} [{it['status']}]: {it['statement']}")
        for a in t["actions"]:
            lines.append(f"- action {a['id']} [{a['status']}] ({a['owner']}): {a['title']}")
        for q in t["questions"]:
            lines.append(f"- open question {q['id']} [{q['priority']}]: {q['question']}")
        meaning = t["commentary"].get("meaning")
        if meaning:
            lines.append(f"- commentary: {meaning}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_prompt(twins):
    return "\n".join([SCHEMA_DESCRIPTION, "", "SPEC SET:", build_context(twins)])


# ---------------------------------------------------------------- validation

def _check_items(items, label, known_ids, fields):
    _require(isinstance(items, list), f"think output: {label} must be a list")
    clean = []
    for i, it in enumerate(items):
        ilabel = f"{label}[{i}]"
        _require(isinstance(it, dict), f"{ilabel}: must be an object")
        out = {}
        for f in fields:
            v = it.get(f)
            _require(isinstance(v, str) and v.strip(), f"{ilabel}: missing {f}")
            out[f] = v.strip()
        ids = it.get("deposit_ids")
        _require(isinstance(ids, list) and ids,
                 f"{ilabel}: deposit_ids must be a non-empty list")
        for d in ids:
            _require(d in known_ids,
                     f"{ilabel}: unknown deposit_id {d!r} — proposals must "
                     "trace to deposits in the spec set")
        out["deposit_ids"] = list(ids)
        clean.append(out)
    return clean


def validate_think(raw, known_ids):
    """Validate + normalize a completeness result. Returns (clean, cuts).

    Traceability failures refuse the whole output. Budget overflows are
    truncated and counted in `cuts` — the budget is a budget, and the
    render reports what it cut rather than hiding it.
    """
    _require(isinstance(raw, dict), "think output must be a JSON object")
    gaps = _check_items(raw.get("gaps", []), "gaps", known_ids, ("title", "detail"))
    contra = _check_items(raw.get("contradictions", []), "contradictions",
                          known_ids, ("title", "detail"))
    raw_questions = raw.get("proposed_questions", [])
    questions = _check_items(raw_questions, "proposed_questions",
                             known_ids, ("question", "why"))
    # priority is not part of _check_items' field copy — validate it
    # against the raw items, by index, so a bad value is refused rather
    # than silently defaulted.
    for i, q in enumerate(questions):
        prio = raw_questions[i].get("priority", "normal")
        _require(prio in PRIORITIES,
                 f"proposed_questions[{i}]: bad priority {prio!r}")
        q["priority"] = prio
    cuts = {}
    for label, items, cap in (("gaps", gaps, MAX_GAPS),
                              ("contradictions", contra, MAX_CONTRADICTIONS),
                              ("proposed_questions", questions, MAX_USER_QUESTIONS)):
        if len(items) > cap:
            cuts[label] = len(items) - cap
    clean = {
        "gaps": gaps[:MAX_GAPS],
        "contradictions": contra[:MAX_CONTRADICTIONS],
        "proposed_questions": questions[:MAX_USER_QUESTIONS],
    }
    return clean, cuts


# ---------------------------------------------------------------- rendering

def render_think_md(clean, cuts, n_deposits):
    lines = ["# Completeness pass (generated)", "",
             "_Agent-generated inferences from the completeness pass "
             "(PROCESS.md §4). These are NOT user statements and NOT "
             "deposits; they never enter OPEN-QUESTIONS.md as if "
             "user-derived. The meeting agenda decides what gets "
             "asked. Every item traces to the deposits that motivated "
             f"it. Spec set considered: {n_deposits} deposit(s)._", ""]
    qs = clean["proposed_questions"]
    lines.append("## Proposed questions for the user (survivors only)")
    if qs:
        order = {"high": 0, "normal": 1, "low": 2}
        for q in sorted(qs, key=lambda x: order[x["priority"]]):
            lines.append(f"- [{q['priority']}] {q['question']} — why: {q['why']} "
                         f"(from deposit(s): {', '.join(q['deposit_ids'])})")
    else:
        lines.append("- (none — question exhaustion for now)")
    lines += ["", "## Gaps the fleet should settle itself", ""]
    if clean["gaps"]:
        for g in clean["gaps"]:
            lines.append(f"- **{g['title']}** — {g['detail']} "
                         f"(from deposit(s): {', '.join(g['deposit_ids'])})")
    else:
        lines.append("- (none found)")
    lines += ["", "## Contradictions to surface", ""]
    if clean["contradictions"]:
        for c in clean["contradictions"]:
            lines.append(f"- **{c['title']}** — {c['detail']} "
                         f"(deposits in tension: {', '.join(c['deposit_ids'])})")
    else:
        lines.append("- (none found)")
    if cuts:
        lines += ["", "_Budget cuts applied: " +
                  ", ".join(f"{k} −{v}" for k, v in sorted(cuts.items())) + "._"]
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------- providers

def complete_vault(prompt, model=None):
    vault_url = interpreter.vault_base_url()
    oidc = os.environ.get("OIDC_TOKEN", "")
    if not oidc:
        raise ThinkError("OIDC_TOKEN not set (vault provider needs it)")
    data = interpreter._post_json(f"{vault_url}/proxy", {
        "oidc_token": oidc,
        "service": "llm",
        "action": "complete",
        "params": {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            **({"model": model} if model else {}),
        },
    })
    r = data.get("result", data)
    text = r.get("content") or r.get("text") or ""
    if not text and isinstance(r, str):
        text = r
    return interpreter.extract_json(text)


def complete_openai(prompt, model=None):
    url = os.environ.get("LLM_API_URL", "")
    if not url:
        raise ThinkError("LLM_API_URL not set (openai provider needs it)")
    headers = {}
    key = os.environ.get("LLM_API_KEY", "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = interpreter._post_json(url, {
        "model": model or os.environ.get("LLM_MODEL", "default"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }, headers=headers)
    return interpreter.extract_json(data["choices"][0]["message"]["content"])


def complete(prompt, provider="vault", model=None):
    if provider == "vault":
        return complete_vault(prompt, model)
    if provider == "openai":
        return complete_openai(prompt, model)
    raise ThinkError(f"unknown provider {provider!r}")


# ---------------------------------------------------------------- run

def run_think(store, provider="vault", model=None, complete_fn=None):
    """Run the completeness pass over a store; write specs/THINK.md.

    Returns a summary dict. With no deposits there is nothing to reason
    over: THINK.md says so and no LLM call is made.
    """
    twins = moldmaker.load_twins(store)
    specs = os.path.join(store, "specs")
    os.makedirs(specs, exist_ok=True)
    out_path = os.path.join(specs, "THINK.md")
    if not twins:
        with open(out_path, "w") as f:
            f.write("# Completeness pass (generated)\n\n"
                    "_No deposits in this store yet — nothing to reason "
                    "over. The pass runs once the spec set has deposits._\n")
        return {"deposits": 0, "gaps": 0, "contradictions": 0,
                "proposed_questions": 0, "path": out_path}
    prompt = build_prompt(twins)
    fn = complete_fn or (lambda p: complete(p, provider, model))
    raw = fn(prompt)
    known = {t["meta"]["deposit_id"] for t in twins}
    clean, cuts = validate_think(raw, known)
    with open(out_path, "w") as f:
        f.write(render_think_md(clean, cuts, len(twins)))
    return {"deposits": len(twins), "gaps": len(clean["gaps"]),
            "contradictions": len(clean["contradictions"]),
            "proposed_questions": len(clean["proposed_questions"]),
            "cuts": cuts, "path": out_path}


def main(argv=None):
    p = argparse.ArgumentParser(description="Moldmaker completeness pass")
    p.add_argument("store")
    p.add_argument("--provider", default="vault", choices=["vault", "openai"])
    p.add_argument("--model")
    p.add_argument("--prompt-only", action="store_true",
                   help="print the prompt and exit (no LLM call)")
    args = p.parse_args(argv)
    try:
        if args.prompt_only:
            twins = moldmaker.load_twins(args.store)
            print(build_prompt(twins), end="")
            return 0
        summary = run_think(args.store, args.provider, args.model)
    except (ThinkError, moldmaker.MoldmakerError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
