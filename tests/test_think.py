#!/usr/bin/env python3
"""Offline tests for the completeness pass (src/think.py).

The LLM call is injected, so no network and no provider is needed:
these tests pin the prompt contents, the traceability validation, the
budgets, and the honesty of specs/THINK.md (agent inferences, labeled).
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
import think  # noqa: E402
from test_moldmaker import load, load_json  # noqa: E402


def deposit_bilge(store):
    return moldmaker.deposit(store, load("bilge.txt"),
                             load_json("bilge.interp.json"),
                             timestamp="2026-10-14T08:00:00")


def stub_result(deposit_id):
    return {
        "gaps": [{"title": "Season occupancy unsettled",
                  "detail": "Bilge-trust mitigations differ if the boat "
                            "sits unattended.",
                  "deposit_ids": [deposit_id]}],
        "contradictions": [],
        "proposed_questions": [
            {"question": "Should the alarm also reach someone ashore "
                         "when it fires, and who?",
             "why": "A shore contact changes the notification build.",
             "priority": "high", "deposit_ids": [deposit_id]}],
    }


class ThinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = os.path.join(self.tmp, "store")
        moldmaker.init_store(self.store, commit=False)
        self.dep = deposit_bilge(self.store)
        self.dep_id = self.dep["deposit_id"]

    def twins(self):
        return moldmaker.load_twins(self.store)

    def test_prompt_carries_the_spec_set(self):
        prompt = think.build_prompt(self.twins())
        self.assertIn(self.dep_id, prompt)
        self.assertIn("Bilge alarm trust failure", prompt)
        self.assertIn("Is the boat occupied all season", prompt)
        self.assertIn("at most 7", prompt)

    def test_unknown_deposit_id_is_refused(self):
        bad = {"gaps": [{"title": "x", "detail": "y",
                         "deposit_ids": ["dep-does-not-exist"]}]}
        with self.assertRaises(think.ThinkError):
            think.validate_think(bad, {self.dep_id})

    def test_bad_priority_is_refused(self):
        bad = {"proposed_questions": [
            {"question": "q", "why": "w", "priority": "whenever",
             "deposit_ids": [self.dep_id]}]}
        with self.assertRaises(think.ThinkError):
            think.validate_think(bad, {self.dep_id})

    def test_budget_truncates_and_reports(self):
        raw = {"proposed_questions": [
            {"question": f"Question {i}?", "why": "w", "priority": "normal",
             "deposit_ids": [self.dep_id]} for i in range(10)]}
        clean, cuts = think.validate_think(raw, {self.dep_id})
        self.assertEqual(len(clean["proposed_questions"]), think.MAX_USER_QUESTIONS)
        self.assertEqual(cuts["proposed_questions"], 3)

    def test_run_writes_labeled_think_md(self):
        seen = {}
        def stub(prompt):
            seen["prompt"] = prompt
            return stub_result(self.dep_id)
        summary = think.run_think(self.store, complete_fn=stub)
        self.assertEqual(summary["proposed_questions"], 1)
        self.assertIn(self.dep_id, seen["prompt"])
        md = open(os.path.join(self.store, "specs", "THINK.md")).read()
        self.assertIn("NOT user statements", md)
        self.assertIn("reach someone ashore", md)
        self.assertIn("Season occupancy unsettled", md)
        self.assertIn(self.dep_id, md)

    def test_empty_result_is_question_exhaustion_not_error(self):
        stub = lambda prompt: {"gaps": [], "contradictions": [],
                               "proposed_questions": []}  # noqa: E731
        summary = think.run_think(self.store, complete_fn=stub)
        self.assertEqual(summary["proposed_questions"], 0)
        md = open(os.path.join(self.store, "specs", "THINK.md")).read()
        self.assertIn("question exhaustion for now", md)

    def test_empty_store_never_calls_the_llm(self):
        empty = os.path.join(self.tmp, "empty")
        moldmaker.init_store(empty, commit=False)
        def boom(prompt):
            raise AssertionError("LLM must not be called on an empty store")
        summary = think.run_think(empty, complete_fn=boom)
        self.assertEqual(summary["deposits"], 0)
        md = open(os.path.join(empty, "specs", "THINK.md")).read()
        self.assertIn("No deposits in this store yet", md)

    def test_proposal_duplicating_an_open_question_is_filtered(self):
        # The bilge deposit already asks this, verbatim, as an open
        # question — the pass must not hand it back as a new proposal.
        stub = lambda prompt: {"proposed_questions": [  # noqa: E731
            {"question": "Is the boat occupied all season, or left "
                         "unattended for long stretches?",
             "why": "w", "priority": "high", "deposit_ids": [self.dep_id]}]}
        summary = think.run_think(self.store, complete_fn=stub)
        self.assertEqual(summary["proposed_questions"], 0)
        md = open(os.path.join(self.store, "specs", "THINK.md")).read()
        self.assertIn("already_open", md)

    def test_second_run_does_not_repropose(self):
        stub = lambda prompt: stub_result(self.dep_id)  # noqa: E731
        first = think.run_think(self.store, complete_fn=stub)
        self.assertEqual(first["proposed_questions"], 1)
        second = think.run_think(self.store, complete_fn=stub)
        self.assertEqual(second["proposed_questions"], 0)
        md = open(os.path.join(self.store, "specs", "THINK.md")).read()
        self.assertIn("previously_proposed", md)

    def test_cli_prompt_only(self):
        env = dict(os.environ, PYTHONPATH="")
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "src", "think.py"),
             self.store, "--prompt-only"],
            capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(self.dep_id, r.stdout)


if __name__ == "__main__":
    unittest.main()
