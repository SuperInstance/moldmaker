#!/usr/bin/env python3
"""
blackboard.py — the blackboard face of a Moldmaker store.

Casey's surface law (2026-10-13): each surface gets a rendering native
to what it innately is — a port or a resize doesn't count. The laptop
surface is the repo (granular, clickable, diffable). The blackboard
is the opposite pole: the whole project at a glance, from across the
room — state first, the questions that need the human big and in
order, the work queue under them, the ledger at the bottom.

This renders ONE self-contained HTML file from a store: no external
assets, no JavaScript, no wall-clock (the stamp is the newest
deposit's timestamp, so the output is a deterministic function of the
record — re-rendering an unchanged record changes nothing).
"""

import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moldmaker  # noqa: E402

CSS = """
body { background:#101418; color:#e8e4da; font-family: Georgia, 'Times New Roman', serif;
       margin:0; padding:2.2rem 3rem; }
h1 { font-size:2.6rem; margin:0 0 .2rem; font-weight:normal; }
h2 { font-size:1.5rem; margin:2rem 0 .6rem; font-weight:normal; color:#9fd8c9;
     border-bottom:1px solid #2c353d; padding-bottom:.3rem; }
.stamp { color:#8a94a0; font-size:1rem; margin-bottom:1.5rem; }
.state { display:flex; gap:2.5rem; flex-wrap:wrap; margin:1rem 0; }
.stat b { font-size:2.2rem; display:block; font-weight:normal; color:#ffd98a; }
.stat span { color:#8a94a0; font-size:.95rem; text-transform:uppercase; letter-spacing:.08em; }
.q { font-size:1.35rem; line-height:1.45; margin:.55rem 0; }
.q .prio { color:#ff9d7a; font-size:1rem; text-transform:uppercase; letter-spacing:.06em; }
.q .why { color:#8a94a0; font-size:1.05rem; }
.a { font-size:1.15rem; line-height:1.5; margin:.5rem 0; }
.a .st { color:#9fd8c9; } .a .why, .a .cost { color:#8a94a0; font-size:1rem; }
.dep { color:#c9cfd6; font-size:1.05rem; margin:.35rem 0; }
.dep .when { color:#8a94a0; }
.empty { color:#8a94a0; font-size:1.15rem; }
footer { margin-top:2.5rem; color:#5c6670; font-size:.9rem; }
"""

ORDER = {"high": 0, "normal": 1, "low": 2}


def _think_questions(store):
    """Proposed questions from specs/THINK.md, as displayed lines."""
    path = os.path.join(store, "specs", "THINK.md")
    if not os.path.exists(path):
        return []
    out, in_section = [], False
    with open(path) as f:
        for line in f:
            if line.startswith("## "):
                in_section = line.startswith("## Proposed questions")
                continue
            if in_section and line.startswith("- ["):
                out.append(line.strip()[2:])
    return out


def _project_name(store):
    try:
        with open(os.path.join(store, "moldmaker.json")) as f:
            return json.load(f).get("project") or os.path.basename(
                os.path.abspath(store))
    except (OSError, ValueError):
        return os.path.basename(os.path.abspath(store))


def render_blackboard(store):
    twins = moldmaker.load_twins(store)
    st = moldmaker.status(store)
    st["project"] = _project_name(store)
    e = html.escape
    questions = [(q, t) for t in twins for q in t["questions"]]
    questions.sort(key=lambda x: ORDER[x[0]["priority"]])
    actions = [(a, t) for t in twins for a in t["actions"]]
    stamp = max((t["meta"]["timestamp"] for t in twins), default="—")
    think_qs = _think_questions(store)

    out = ["<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
           f"<title>{e(st['project'])} — blackboard</title>",
           f"<style>{CSS}</style></head><body>",
           f"<h1>{e(st['project'])}</h1>",
           f'<div class="stamp">The whole project, at a glance · '
           f"record as of {e(stamp)} · rendered from the deposits, "
           "nothing here is edited by hand</div>",
           '<div class="state">',
           f'<div class="stat"><b>{st["deposits"]}</b><span>deposits</span></div>',
           f'<div class="stat"><b>{len(questions)}</b><span>open questions</span></div>',
           f'<div class="stat"><b>{st["actions_proposed"]}</b><span>actions proposed</span></div>',
           f'<div class="stat"><b>{st["actions_approved"]}</b><span>actions approved</span></div>',
           "</div>"]

    out.append("<h2>For the human — in order</h2>")
    if questions:
        for q, t in questions:
            out.append(f'<div class="q"><span class="prio">{e(q["priority"])}</span> '
                       f'{e(q["question"])}<br><span class="why">why it matters: '
                       f'{e(q["why"])} (deposit {e(t["meta"]["deposit_id"])})</span></div>')
    else:
        out.append('<div class="empty">No open questions. The spec set is '
                   "waiting on work, not on you.</div>")

    if think_qs:
        out.append("<h2>What the completeness pass is asking</h2>")
        out.append('<div class="empty" style="margin-bottom:.5rem">Agent '
                   "inferences from specs/THINK.md — not yet on the agenda; "
                   "the meeting decides.</div>")
        for line in think_qs:
            out.append(f'<div class="q">{e(line)}</div>')

    out.append("<h2>The work queue</h2>")
    if actions:
        for a, t in actions:
            why = a.get("why") or "(why not recorded — predates the why/cost contract)"
            out.append(f'<div class="a"><span class="st">[{e(a["status"])}]</span> '
                       f'{e(a["title"])} <span class="why">— why: {e(why)} · '
                       f'cost: {e(a.get("cost") or "unknown")} · owner: '
                       f'{e(a["owner"])}</span></div>')
    else:
        out.append('<div class="empty">No actions proposed yet.</div>')

    out.append("<h2>The ledger</h2>")
    if twins:
        for t in reversed(twins):
            m = t["meta"]
            out.append(f'<div class="dep">{e(m["title"])} <span class="when">· '
                       f'{e(m["timestamp"])} · {e(m["source"])} · deposit '
                       f'{e(m["deposit_id"])}</span></div>')
    else:
        out.append('<div class="empty">No deposits yet.</div>')

    out.append("<footer>Generated by Moldmaker's blackboard face from the "
               "project store. The deposits are the record; this page is "
               "only a rendering of them.</footer>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description="Render a store's blackboard face")
    p.add_argument("store")
    p.add_argument("--out", help="output file (default: <store>/blackboard.html)")
    args = p.parse_args(argv)
    out_path = args.out or os.path.join(args.store, "blackboard.html")
    with open(out_path, "w") as f:
        f.write(render_blackboard(args.store))
    print(f"blackboard: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
