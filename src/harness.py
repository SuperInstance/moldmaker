#!/usr/bin/env python3
"""
harness.py — the interpretation-quality harness.

Validation guarantees traceability, not wisdom (docs/IMPLEMENTATION.md).
This harness measures the wisdom, mechanically, against a fixture set
of hard memos — a calculation the memo asks for outright, a rule the
memo kills in the same breath, three topics in one ramble, an owner
nobody can name. Each case carries expectations; each expectation is a
check that can fail. The scorer is pure and offline; the runner calls
the live interpreter (vault or OpenAI-compatible) per case.

A red harness is a finding, not an embarrassment: it names exactly
which quality the current prompt/model combination does not have yet.
Run it whenever the interpreter prompt or the model changes.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interpreter  # noqa: E402

CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "tests", "quality")


def _blob(interp, where):
    if where == "all":
        return json.dumps(interp)
    if where == "intents":
        return json.dumps(interp.get("intents", []))
    if where == "questions":
        return json.dumps(interp.get("questions", []))
    if where == "annotations":
        return json.dumps([s.get("annotations", [])
                           for s in interp.get("sections", [])])
    if where == "questions+annotations":
        return _blob(interp, "questions") + _blob(interp, "annotations")
    raise ValueError(f"unknown where {where!r}")


def _numbers(text):
    return [float(x) for x in re.findall(r"\d+\.\d+|\d+", text)]


def score_case(interp, checks):
    """Run expectation checks against one interpretation.
    Returns a list of (passed, description) — pure, offline."""
    results = []
    for c in checks:
        t = c["type"]
        if t == "regex_present":
            ok = re.search(c["pattern"], _blob(interp, c.get("where", "all")),
                           re.I) is not None
            desc = f"text matching /{c['pattern']}/ present in {c.get('where', 'all')}"
        elif t == "regex_absent":
            ok = re.search(c["pattern"], _blob(interp, c.get("where", "all")),
                           re.I) is None
            desc = f"text matching /{c['pattern']}/ absent from {c.get('where', 'all')}"
        elif t == "number_near":
            nums = _numbers(_blob(interp, "all"))
            ok = any(abs(n - c["value"]) <= c["tolerance"] for n in nums)
            desc = f"a number within {c['tolerance']} of {c['value']} (the memo's own arithmetic, done)"
        elif t == "min_sections":
            ok = len(interp.get("sections", [])) >= c["n"]
            desc = f"at least {c['n']} sections"
        elif t == "min_actions":
            ok = len(interp.get("actions", [])) >= c["n"]
            desc = f"at least {c['n']} action(s)"
        elif t == "min_questions":
            ok = len(interp.get("questions", [])) >= c["n"]
            desc = f"at least {c['n']} question(s)"
        elif t == "max_questions":
            ok = len(interp.get("questions", [])) <= c["n"]
            desc = f"at most {c['n']} question(s) (the user's attention is a budget)"
        elif t == "all_actions_have_why":
            acts = interp.get("actions", [])
            ok = bool(acts) and all((a.get("why") or "").strip() for a in acts)
            desc = "every action carries a why"
        else:
            raise ValueError(f"unknown check type {t!r}")
        results.append((ok, desc))
    return results


def load_cases(cases_dir=CASES_DIR):
    with open(os.path.join(cases_dir, "expectations.json")) as f:
        expectations = json.load(f)
    cases = []
    for name, spec in sorted(expectations.items()):
        with open(os.path.join(cases_dir, name + ".txt")) as f:
            cases.append((name, f.read(), spec))
    return cases


def run(provider="vault", model=None, cases_dir=CASES_DIR):
    cases = load_cases(cases_dir)
    lines, total, passed = [], 0, 0
    for name, text, spec in cases:
        interp = interpreter.interpret(text, provider=provider, model=model)
        results = score_case(interp, spec["checks"])
        good = sum(1 for ok, _ in results if ok)
        total += len(results)
        passed += good
        lines.append(f"## {name}: {good}/{len(results)}")
        lines.append(f"_{spec['about']}_")
        for ok, desc in results:
            lines.append(f"- {'PASS' if ok else 'FAIL'}: {desc}")
        lines.append("")
    header = (f"# Interpretation quality harness\n\n"
              f"Provider: {provider} · score: **{passed}/{total}** "
              f"across {len(cases)} hard memos.\n")
    return header + "\n" + "\n".join(lines), passed, total


def main(argv=None):
    p = argparse.ArgumentParser(description="Moldmaker interpretation-quality harness")
    p.add_argument("--provider", default="vault", choices=["vault", "openai"])
    p.add_argument("--model")
    p.add_argument("--out", help="write the report here (always printed too)")
    args = p.parse_args(argv)
    report, passed, total = run(args.provider, args.model)
    print(report)
    if args.out:
        with open(args.out, "w") as f:
            f.write(report)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
