#!/usr/bin/env python3
"""Acceptance tests for the Moldmaker deposit pipeline (v0).

The matrix follows the adversarial review filed during the build
(ZAI lane, 2026-10-14): traceability, idempotency, malformed output,
approval gates, corrections, privacy (secrets), dirty-tree safety,
partial failure = no partial commit.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import moldmaker  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    with open(os.path.join(FIX, name)) as f:
        return f.read()


def load_json(name):
    with open(os.path.join(FIX, name)) as f:
        return json.load(f)


def commits(store):
    out = subprocess.run(["git", "-C", store, "rev-list", "--count", "HEAD"],
                         capture_output=True, text=True)
    return int(out.stdout.strip())


class DepositTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="moldmaker-test-")
        self.store = os.path.join(self.tmp, "store")
        os.makedirs(self.store)
        moldmaker.init_store(self.store, "test-project")
        self.raw = load("bilge.txt")
        self.interp = load_json("bilge.interp.json")

    def test_deposit_creates_three_parts_and_one_commit(self):
        before = commits(self.store)
        r = moldmaker.deposit(self.store, self.raw, self.interp,
                              source="telegram", external_id="msg-1",
                              timestamp="2026-10-14T09:00:00-08:00")
        self.assertTrue(r["created"])
        self.assertEqual(commits(self.store), before + 1)
        slug = r["slug"]
        self.assertTrue(os.path.exists(os.path.join(self.store, "deposits", slug + ".md")))
        self.assertTrue(os.path.exists(os.path.join(self.store, "deposits", slug + ".a2a.json")))
        # the third part: commentary in the commit message
        msg = subprocess.run(["git", "-C", self.store, "log", "-1", "--pretty=%B"],
                             capture_output=True, text=True).stdout
        self.assertIn("Meaning:", msg)
        self.assertIn("Why this mattered:", msg)
        # no date in the deposit filename
        self.assertNotIn("2026", slug)

    def test_human_file_preserves_raw_verbatim(self):
        r = moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")
        with open(os.path.join(self.store, "deposits", r["slug"] + ".md")) as f:
            human = f.read()
        self.assertIn(self.raw.strip(), human)
        self.assertIn("▸", human)  # annotations present, distinct

    def test_twin_is_traceable(self):
        r = moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")
        with open(os.path.join(self.store, "deposits", r["slug"] + ".a2a.json")) as f:
            twin = json.load(f)
        for it in twin["intents"] + twin["actions"]:
            self.assertIn(it["source_quote"], twin["source"]["raw"])

    def test_idempotent_retry(self):
        moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")
        n = commits(self.store)
        r2 = moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")
        self.assertFalse(r2["created"])
        self.assertEqual(commits(self.store), n)

    def test_untraceable_quote_refused_without_commit(self):
        bad = load_json("bilge.interp.json")
        bad["intents"][0]["source_quote"] = "something the user never said"
        n = commits(self.store)
        with self.assertRaises(moldmaker.MoldmakerError):
            moldmaker.deposit(self.store, self.raw, bad, external_id="msg-bad")
        self.assertEqual(commits(self.store), n)
        self.assertEqual(os.listdir(os.path.join(self.store, "deposits")), [])

    def test_span_mismatch_refused(self):
        bad = load_json("bilge.interp.json")
        bad["sections"][0]["span"] = {"start": 0, "end": 5}
        with self.assertRaises(moldmaker.MoldmakerError):
            moldmaker.deposit(self.store, self.raw, bad, external_id="msg-span")

    def test_approval_gate_demotes_then_honours_human(self):
        # fixture marks action.sensor-options 'approved'; the human did not
        r = moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")
        with open(os.path.join(self.store, "deposits", r["slug"] + ".a2a.json")) as f:
            twin = json.load(f)
        a = next(x for x in twin["actions"] if x["id"] == "action.sensor-options")
        self.assertEqual(a["status"], "proposed")
        self.assertTrue(any("demoted" in n for n in twin["validation_notes"]))
        # a fresh store where the human explicitly approves it
        store2 = os.path.join(self.tmp, "store2")
        os.makedirs(store2)
        moldmaker.init_store(store2, "test-project-2")
        r2 = moldmaker.deposit(store2, self.raw, self.interp, external_id="msg-1",
                               approved_ids=frozenset({"action.sensor-options"}))
        with open(os.path.join(store2, "deposits", r2["slug"] + ".a2a.json")) as f:
            twin2 = json.load(f)
        a2 = next(x for x in twin2["actions"] if x["id"] == "action.sensor-options")
        self.assertEqual(a2["status"], "approved")

    def test_secret_refused(self):
        with self.assertRaises(moldmaker.MoldmakerError):
            moldmaker.deposit(self.store, "my api_key = sk-1234567890abcdefghij ok",
                              self.interp, external_id="msg-secret")

    def test_dirty_tree_refused(self):
        with open(os.path.join(self.store, "UNRELATED.md"), "w") as f:
            f.write("somebody else's work in progress\n")
        with self.assertRaises(moldmaker.MoldmakerError):
            moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")

    def test_correction_is_a_new_deposit_original_intact(self):
        r1 = moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")
        raw2 = load("correction.txt")
        interp2 = load_json("correction.interp.json")
        r2 = moldmaker.deposit(self.store, raw2, interp2, external_id="msg-2")
        self.assertTrue(r2["created"])
        with open(os.path.join(self.store, "deposits", r1["slug"] + ".md")) as f:
            self.assertIn("float switch sticking", f.read())

    def test_views_and_agenda(self):
        moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")
        st = moldmaker.status(self.store)
        self.assertEqual(st["deposits"], 1)
        self.assertEqual(st["open_questions"], 1)
        self.assertEqual(st["actions_proposed"], 2)  # one demoted, one proposed
        agenda = moldmaker.render_agenda(self.store)
        self.assertIn("occupied all season", agenda)
        self.assertIn("action.sensor-options", agenda)


class HandlerTests(unittest.TestCase):
    def test_voice_without_transcript_needs_transcription(self):
        import handle_telegram
        out = handle_telegram.handle({"chat_id": 1, "audio_ref": "file_123"},
                                     repo_root=self.tmp if hasattr(self, "tmp") else "/tmp")
        self.assertFalse(out["ok"])
        self.assertEqual(out["needs"], "transcription")


if __name__ == "__main__":
    unittest.main(verbosity=2)
