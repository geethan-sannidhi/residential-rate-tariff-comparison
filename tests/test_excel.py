"""The Excel calculator must reproduce the Python calculator (scripts/verify_excel.py)."""
import sys
import unittest
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_excel  # noqa: E402


class ExcelCalculator(unittest.TestCase):
    def test_matches_python_calculator(self):
        problems, n = verify_excel.check()
        self.assertEqual(problems, [])
        self.assertGreaterEqual(n, 200)

    def test_bills_are_formulas_not_values(self):
        wb = load_workbook(verify_excel.XLSX)
        self.assertTrue(str(wb["Calculator"]["J6"].value).startswith("="))
        self.assertTrue(str(wb["Comparison"]["B6"].value).startswith("="))
        self.assertTrue(str(wb["Checks"]["C5"].value).startswith("="))


if __name__ == "__main__":
    unittest.main()
