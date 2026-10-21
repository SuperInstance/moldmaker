#!/usr/bin/env python3
"""Acceptance tests for the Moldmaker deposit pipeline (v0).

The matrix follows the adversarial review filed during the build
(ZAI lane, 2026-10-14): traceability, idempotency, malformed output,
approval gates, corrections, privacy (secrets), dirty-tree safety,
partial failure = no partial commit.
"""
import copy
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

    def test_retry_short_circuits_before_validation(self):
        # Regression: sixth live dispatch (2026-10-15) — the retry of an
        # already-filed message re-interpreted it, the fresh interpretation
        # failed validation, and the retry died even though its deposit
        # already existed. The deposit id never depends on the
        # interpretation, so the already-filed check must come first:
        # a retry carrying a garbage interpretation still answers
        # "already filed" instead of raising.
        moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")
        bad = load_json("bilge.interp.json")
        bad["intents"][0]["source_quote"] = "something the user never said"
        r = moldmaker.deposit(self.store, self.raw, bad, external_id="msg-1")
        self.assertFalse(r["created"])

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

    def test_action_owner_alias_normalized_and_unknown_coerced(self):
        # Regression: fourth live dispatch (2026-10-14) lost the whole
        # deposit because MiniMax called a software action's owner
        # "software-agent" on every retry. Owner vocabulary is a routing
        # hint, not a reason to refuse an otherwise traceable deposit.
        aliased = copy.deepcopy(self.interp)
        aliased["actions"][0]["owner"] = "software-agent"
        clean, notes = moldmaker.validate_interpretation(self.raw, aliased)
        self.assertEqual(clean["actions"][0]["owner"], "logic-agent")
        self.assertTrue(any("normalized to 'logic-agent'" in n for n in notes))

        unknown = copy.deepcopy(self.interp)
        unknown["actions"][0]["owner"] = "martian-agent"
        clean, notes = moldmaker.validate_interpretation(self.raw, unknown)
        self.assertEqual(clean["actions"][0]["owner"], "unspecified")
        self.assertTrue(any("coerced to 'unspecified'" in n for n in notes))

        # And the aliased interpretation still files end to end, with the
        # normalization visible in the twin rather than silently rewritten.
        r = moldmaker.deposit(self.store, self.raw, aliased, external_id="msg-owner")
        with open(os.path.join(self.store, "deposits", r["slug"] + ".a2a.json")) as f:
            twin = json.load(f)
        self.assertEqual(twin["actions"][0]["owner"], "logic-agent")
        self.assertTrue(any("normalized" in n for n in twin["validation_notes"]))

    def test_secret_refused(self):
        with self.assertRaises(moldmaker.MoldmakerError):
            moldmaker.deposit(self.store, "my api_key = sk-1234567890abcdefghij ok",
                              self.interp, external_id="msg-secret")

    def test_dirty_tree_refused(self):
        with open(os.path.join(self.store, "UNRELATED.md"), "w") as f:
            f.write("somebody else's work in progress\n")
        with self.assertRaises(moldmaker.MoldmakerError):
            moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-1")

    def test_subdir_store_in_parent_repo_deposits(self):
        # Regression: fifth live dispatch (2026-10-14) was refused with
        # "uncommitted changes outside the store (['dogfood/'])" — in a
        # fresh CI checkout the routed store is a NEW subdirectory of
        # the repo, and git collapsed it to one untracked-dir entry the
        # dirty-tree guard could not match against its allowed files.
        root = os.path.join(self.tmp, "parent")
        os.makedirs(root)
        subprocess.run(["git", "-C", root, "init", "-q", "-b", "main"], check=True)
        subprocess.run(["git", "-C", root, "config", "user.name", "t"], check=True)
        subprocess.run(["git", "-C", root, "config", "user.email", "t@t"], check=True)
        with open(os.path.join(root, "README.md"), "w") as f:
            f.write("parent repo\n")
        subprocess.run(["git", "-C", root, "add", "README.md"], check=True)
        subprocess.run(["git", "-C", root, "commit", "-q", "-m", "init"], check=True)
        store = os.path.join(root, "dogfood")
        moldmaker.init_store(store, "dogfood-project", commit=False)
        r = moldmaker.deposit(store, self.raw, self.interp, external_id="msg-sub")
        self.assertTrue(r["created"])
        self.assertTrue(os.path.exists(os.path.join(store, "deposits", r["slug"] + ".md")))
        # the deposit commit touched only the store's own paths
        names = subprocess.run(["git", "-C", root, "show", "--pretty=",
                                "--name-only", "HEAD"],
                               capture_output=True, text=True).stdout.split()
        self.assertTrue(names)
        self.assertTrue(all(n.startswith("dogfood/") for n in names))
        # ...and a genuinely foreign file still blocks the next deposit
        with open(os.path.join(root, "UNRELATED.md"), "w") as f:
            f.write("somebody else's work in progress\n")
        raw2 = load("correction.txt")
        interp2 = load_json("correction.interp.json")
        with self.assertRaises(moldmaker.MoldmakerError):
            moldmaker.deposit(store, raw2, interp2, external_id="msg-sub-2")

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


    def test_deposit_sets_identity_when_missing(self):
        # A fresh CI checkout has no git identity; a deposit must still
        # be able to commit (regression: first live dispatch, 2026-10-14,
        # filed nothing because the workflow configured git AFTER the
        # handler ran and the pipeline assumed an identity existed).
        subprocess.run(["git", "-C", self.store, "config", "--unset", "user.name"])
        subprocess.run(["git", "-C", self.store, "config", "--unset", "user.email"])
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = self.tmp  # no .gitconfig here: a bare CI checkout
        try:
            r = moldmaker.deposit(self.store, self.raw, self.interp, external_id="msg-ci")
        finally:
            if old_home is not None:
                os.environ["HOME"] = old_home
        self.assertTrue(r["created"])
        name = subprocess.run(["git", "-C", self.store, "config", "--local", "user.name"],
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(name, "moldmaker")


class InterpreterTests(unittest.TestCase):
    def test_vault_url_empty_env_falls_back(self):
        # Regression: second live dispatch (2026-10-14) failed with
        # "unknown url type: '/proxy'" because the workflow expanded an
        # unset repo variable to VAULT_URL="" and the code used it as-is.
        import interpreter
        old = os.environ.get("VAULT_URL")
        os.environ["VAULT_URL"] = ""
        try:
            self.assertEqual(interpreter.vault_base_url(), interpreter.DEFAULT_VAULT_URL)
            os.environ["VAULT_URL"] = "https://example.invalid/vault"
            self.assertEqual(interpreter.vault_base_url(), "https://example.invalid/vault")
        finally:
            if old is None:
                os.environ.pop("VAULT_URL", None)
            else:
                os.environ["VAULT_URL"] = old


class HandlerTests(unittest.TestCase):
    def test_voice_without_transcript_needs_transcription(self):
        import handle_telegram
        out = handle_telegram.handle({"chat_id": 1, "audio_ref": "file_123"},
                                     repo_root=self.tmp if hasattr(self, "tmp") else "/tmp")
        self.assertFalse(out["ok"])
        self.assertEqual(out["needs"], "transcription")

    def test_handler_retry_never_calls_interpreter(self):
        # The Telegram face of the same regression: a retry is answered
        # from the record. If the interpreter is called at all, it
        # raises — the handler must still return "Already filed".
        import handle_telegram
        tmp = tempfile.mkdtemp(prefix="moldmaker-handler-")
        raw = load("bilge.txt")
        interp = load_json("bilge.interp.json")
        payload = {"chat_id": 1, "text": raw, "message_id": 42}
        out1 = handle_telegram.handle(payload, repo_root=tmp, interpretation=interp)
        self.assertTrue(out1["ok"])
        self.assertTrue(out1["created"])
        orig = handle_telegram.interpreter.interpret

        def boom(*a, **k):
            raise AssertionError("interpreter called on a retry")

        handle_telegram.interpreter.interpret = boom
        try:
            out2 = handle_telegram.handle(payload, repo_root=tmp)
        finally:
            handle_telegram.interpreter.interpret = orig
        self.assertTrue(out2["ok"])
        self.assertFalse(out2["created"])
        self.assertIn("Already filed", out2["ack_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
