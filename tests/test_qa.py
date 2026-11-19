import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import qa  # noqa: E402

CAL = os.path.join(ROOT, "data", "close_calendar.csv")


def run(folder):
    return qa.run_checks(qa.load(os.path.join(ROOT, "data", folder), CAL))


class PartnerDraft(unittest.TestCase):
    def setUp(self):
        self.r = run("partner_draft")
        self.by = {c["id"]: c for c in self.r["checks"]}

    def test_sent_back(self):
        self.assertFalse(self.r["ready"])

    def test_every_planted_issue_found(self):
        expected = {"C1": 1, "C2": 2, "C3": 1, "C4": 1, "C5": 1, "C6": 1, "C7": 1, "C8": 1}
        self.assertEqual({k: len(v["issues"]) for k, v in self.by.items()}, expected)

    def test_coverage_names_missing_tasks(self):
        msg = self.by["C1"]["issues"][0]
        for tid in ("A05", "A06", "A07", "A13"):
            self.assertIn(tid, msg)
        self.assertEqual(self.r["coverage"]["Acquired unit"]["mapped"], 10)

    def test_overclaimed_savings_are_capped(self):
        f2 = next(f for f in self.r["ranked_fixes"] if f["fix_id"] == "F2")
        self.assertEqual(f2["claimed_hours"], 30)
        self.assertEqual(f2["counted_hours"], 23)


class AfterFixes(unittest.TestCase):
    def test_readout_ready(self):
        r = run("after_fixes")
        self.assertTrue(r["ready"])
        self.assertEqual(r["issue_count"], 0)

    def test_ranking_order(self):
        r = run("after_fixes")
        self.assertEqual([f["fix_id"] for f in r["ranked_fixes"]], ["F2", "F1", "F5", "F3", "F4"])

    def test_exit_codes(self):
        self.assertEqual(qa.main(["--data", os.path.join(ROOT, "data", "after_fixes")]), 0)
        self.assertEqual(qa.main([]), 1)


if __name__ == "__main__":
    unittest.main()
