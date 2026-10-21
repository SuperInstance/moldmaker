#!/usr/bin/env python3
"""Tests for the cold store audit (moldmaker.audit_store / `audit` CLI).

The audit is the referee's pass: it trusts nothing from deposit time
and re-derives every checkable claim from the filed record. These
tests file a clean store, then tamper with the record the way a
careless (or inventing) agent could, and require the audit to catch it.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import moldmaker  # noqa: E402
from test_moldmaker import load, load_json  # noqa: E402


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = os.path.join(self.tmp, "store")
        moldmaker.init_store(self.store, commit=False)
        self.dep = moldmaker.deposit(
            self.store, load("bilge.txt"), load_json("bilge.interp.json"),
            timestamp="2026-10-14T08:00:00", commit=False)

    def twin_path(self):
        return os.path.join(self.store, "deposits",
                            self.dep["slug"] + ".a2a.json")

    def test_clean_store_audits_clean(self):
        self.assertEqual(moldmaker.audit_store(self.store), [])

    def test_tampered_quote_is_caught(self):
        with open(self.twin_path()) as f:
            twin = json.load(f)
        twin["intents"][0]["source_quote"] = "words the user never said"
        with open(self.twin_path(), "w") as f:
            json.dump(twin, f)
        findings = moldmaker.audit_store(self.store)
        self.assertTrue(any(self.dep["deposit_id"] in f for f in findings),
                        findings)

    def test_tampered_layer_a_is_caught(self):
        md_path = os.path.join(self.store, "deposits", self.dep["slug"] + ".md")
        with open(md_path) as f:
            text = f.read()
        with open(md_path, "w") as f:
            f.write(text.replace("bilge", "BILGE", 1))
        findings = moldmaker.audit_store(self.store)
        self.assertTrue(any("Layer A differs" in f for f in findings), findings)

    def test_unearned_approval_is_caught(self):
        with open(self.twin_path()) as f:
            twin = json.load(f)
        twin["actions"][0]["status"] = "approved"  # forged: no note
        with open(self.twin_path(), "w") as f:
            json.dump(twin, f)
        findings = moldmaker.audit_store(self.store)
        self.assertTrue(any("no human-approval confirmation" in f
                            for f in findings), findings)

    def test_honest_approval_audits_clean(self):
        store2 = os.path.join(self.tmp, "store2")
        moldmaker.init_store(store2, commit=False)
        interp = load_json("bilge.interp.json")
        interp["actions"][0]["status"] = "approved"
        dep = moldmaker.deposit(store2, load("bilge.txt"), interp,
                                timestamp="2026-10-14T09:00:00",
                                approved_ids={interp["actions"][0]["id"]},
                                commit=False)
        twin = json.load(open(os.path.join(store2, "deposits",
                                            dep["slug"] + ".a2a.json")))
        self.assertEqual(twin["actions"][0]["status"], "approved")
        self.assertEqual(moldmaker.audit_store(store2), [])

    def test_cli_exit_codes(self):
        env = dict(os.environ, PYTHONPATH="")
        ok = subprocess.run(
            [sys.executable, os.path.join(ROOT, "src", "moldmaker.py"),
             "audit", self.store], capture_output=True, text=True, env=env)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("AUDIT CLEAN", ok.stdout)
        with open(self.twin_path()) as f:
            twin = json.load(f)
        twin["meta"]["deposit_id"] = "0" * 16  # no longer recomputes
        with open(self.twin_path(), "w") as f:
            json.dump(twin, f)
        bad = subprocess.run(
            [sys.executable, os.path.join(ROOT, "src", "moldmaker.py"),
             "audit", self.store], capture_output=True, text=True, env=env)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("FINDING", bad.stdout)


if __name__ == "__main__":
    unittest.main()
