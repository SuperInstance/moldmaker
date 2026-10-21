#!/usr/bin/env python3
"""Offline tests for the quality-harness scorer: the checks must be
able to fail, or the harness measures nothing."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import harness  # noqa: E402

GOOD_RAMP = {
    "sections": [{"heading": "Ramp", "source_quote": "x", "annotations": [
        {"kind": "formalization", "basis": "inferred",
         "text": "Angle = arctan(6/40) ≈ 8.53 degrees."}]}],
    "intents": [], "actions": [{"id": "a", "why": "w"}],
    "questions": [{"id": "q", "question": "Whoever checks the fuel dock is unresolved — who is it?"}],
}
BAD_RAMP = {
    "sections": [{"heading": "Ramp", "source_quote": "x", "annotations": [
        {"kind": "note", "basis": "inferred", "text": "The user gave ramp dimensions."}]}],
    "intents": [], "actions": [{"id": "a", "why": "w"}], "questions": [],
}


class ScorerTests(unittest.TestCase):
    def checks(self, name):
        return dict((n, s) for n, _, s in harness.load_cases())[name]["checks"]

    def test_good_ramp_passes(self):
        results = harness.score_case(GOOD_RAMP, self.checks("ramp"))
        self.assertTrue(all(ok for ok, _ in results), results)

    def test_lazy_ramp_fails_the_arithmetic(self):
        results = harness.score_case(BAD_RAMP, self.checks("ramp"))
        failed = [d for ok, d in results if not ok]
        self.assertTrue(any("arithmetic" in d for d in failed), failed)

    def test_cases_load(self):
        cases = harness.load_cases()
        self.assertEqual({n for n, _, _ in cases},
                         {"ramp", "contradiction", "ramble", "fueldock"})


if __name__ == "__main__":
    unittest.main()
