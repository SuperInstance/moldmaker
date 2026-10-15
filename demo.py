#!/usr/bin/env python3
"""
demo.py — end-to-end Moldmaker v0 demo (no LLM, no network).

Creates a throwaway project store, deposits two fixture transmissions
(the second is a correction of the first) through the real pipeline,
and prints the store tree, the generated views, the status, and the
git log — the ledger, commentary included.

Run: python3 demo.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import moldmaker  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "tests", "fixtures")


def show(store):
    for root, dirs, files in os.walk(store):
        if ".git" in root:
            continue
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in sorted(files):
            print("  " + os.path.relpath(os.path.join(root, name), store))


def main():
    tmp = tempfile.mkdtemp(prefix="moldmaker-demo-")
    store = os.path.join(tmp, "harbour-project")
    os.makedirs(store)
    try:
        moldmaker.init_store(store, "harbour-project")
        for text_name, interp_name, ext in [
            ("bilge.txt", "bilge.interp.json", "msg-1"),
            ("correction.txt", "correction.interp.json", "msg-2"),
        ]:
            with open(os.path.join(FIX, text_name)) as f:
                raw = f.read()
            with open(os.path.join(FIX, interp_name)) as f:
                interp = json.load(f)
            r = moldmaker.deposit(store, raw, interp, source="telegram",
                                  external_id=ext)
            print(f"deposit {ext}: created={r['created']} slug={r['slug']} commit={r['commit']}")
        # retry of the first deposit must not duplicate
        with open(os.path.join(FIX, "bilge.txt")) as f:
            raw = f.read()
        with open(os.path.join(FIX, "bilge.interp.json")) as f:
            interp = json.load(f)
        r = moldmaker.deposit(store, raw, interp, source="telegram", external_id="msg-1")
        print(f"retry msg-1: created={r['created']} (idempotent)")
        print("\nstore tree:")
        show(store)
        print("\nstatus:", json.dumps(moldmaker.status(store)))
        print("\nagenda:\n" + moldmaker.render_agenda(store))
        print("git log (the ledger — commentary is in the commit bodies):")
        out = subprocess.run(["git", "-C", store, "log", "--pretty=%h %s"],
                             capture_output=True, text=True)
        print(out.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
