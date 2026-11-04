"""Calculator vs. FMEA's 2026 published bills, using the documented rate version for each month."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_history  # noqa: E402

KNOWN_MISMATCHES = {("duke_rs1", "2026-01"), ("duke_rs1", "2026-02")}  # explained in docs/BILL_VALIDATION.md


class History(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = validate_history.run()

    def test_at_least_100_documented_checks_match(self):
        doc = [r for r in self.rows if r["basis"] == "documented"]
        ok = [r for r in doc if r["result"] in ("exact", "within rounding")]
        self.assertGreaterEqual(len(ok), 100)

    def test_only_known_mismatches(self):
        bad = {(r["tariff"], r["edition"]) for r in self.rows if r["result"] == "mismatch"}
        self.assertEqual(bad - KNOWN_MISMATCHES, set())

    def test_rounding_differences_are_cents(self):
        for r in self.rows:
            if r["result"] == "within rounding":
                self.assertLessEqual(abs(r["difference"]), 0.02)

    def test_every_documented_month_has_a_version(self):
        self.assertFalse([r for r in self.rows if r["result"] == "not checked"])


if __name__ == "__main__":
    unittest.main()
