#!/usr/bin/env python3
"""Tests for the blackboard face: a deterministic, escaped, glanceable
rendering of a store — and nothing in it edited by hand."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import moldmaker  # noqa: E402
import blackboard  # noqa: E402
from test_moldmaker import load, load_json  # noqa: E402


class BlackboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = os.path.join(self.tmp, "store")
        moldmaker.init_store(self.store, commit=False)
        moldmaker.deposit(self.store, load("bilge.txt"),
                          load_json("bilge.interp.json"),
                          timestamp="2026-10-14T08:00:00", commit=False)

    def test_renders_state_questions_actions_ledger(self):
        page = blackboard.render_blackboard(self.store)
        self.assertIn("Bilge alarm trust failure", page)      # ledger
        self.assertIn("occupied all season", page)            # the question
        self.assertIn("why it matters", page)
        self.assertIn("Find current sensors", page)           # an action
        self.assertIn("cost:", page)

    def test_deterministic(self):
        self.assertEqual(blackboard.render_blackboard(self.store),
                         blackboard.render_blackboard(self.store))

    def test_escapes_html_in_record(self):
        store2 = os.path.join(self.tmp, "store2")
        moldmaker.init_store(store2, commit=False)
        interp = load_json("bilge.interp.json")
        interp["title"] = "Bilge <script>alert(1)</script>"
        moldmaker.deposit(store2, load("bilge.txt"), interp,
                          timestamp="2026-10-14T08:00:00", commit=False)
        page = blackboard.render_blackboard(store2)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_empty_store_renders_honestly(self):
        empty = os.path.join(self.tmp, "empty")
        moldmaker.init_store(empty, commit=False)
        page = blackboard.render_blackboard(empty)
        self.assertIn("No deposits yet", page)
        self.assertIn("No open questions", page)


if __name__ == "__main__":
    unittest.main()
