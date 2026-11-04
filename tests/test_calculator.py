"""Expected values below are worked out by hand from the tariff sheets
(see docs/METHODOLOGY.md), independent of the calculator code."""
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tariffcalc import load_tariff, monthly_bill  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"
FPL = load_tariff(DATA / "fpl_rs1.json")
TECO = load_tariff(DATA / "teco_rs.json")


class FPL_RS1(unittest.TestCase):
    def test_1000_kwh(self):
        # 10.52 + 1000 * (7.865+2.893+.148+.052+.345+.995-.040)/100 = 10.52 + 122.58
        self.assertEqual(monthly_bill(FPL, 1000).total, Decimal("133.10"))

    def test_1500_kwh_crosses_tier(self):
        # 10.52 + 122.58 + 500 * (8.865+3.893+1.500)/100 = 10.52+122.58+71.29
        self.assertEqual(monthly_bill(FPL, 1500).total, Decimal("204.39"))

    def test_minimum_bill_applies_at_zero_usage(self):
        # base bill 10.52 < 30 -> raised to 30; clauses are 0 at 0 kWh
        b = monthly_bill(FPL, 0)
        self.assertEqual(b.minimum_adjustment, Decimal("19.48"))
        self.assertEqual(b.total, Decimal("30.00"))

    def test_minimum_not_applied_when_base_exceeds_30(self):
        # 500 kWh base = 10.52 + 39.325 = 49.845 > 30
        self.assertEqual(monthly_bill(FPL, 500).minimum_adjustment, 0)


class TECO_RS(unittest.TestCase):
    def test_1000_kwh_30_days(self):
        # 13.50 + 1000*(8.948+3.210+.270+.264+.087+.717+.406)/100 = 13.50+139.02
        self.assertEqual(monthly_bill(TECO, 1000, days=30).total, Decimal("152.52"))

    def test_1200_kwh_crosses_tier(self):
        # 13.50 + 139.02 + 200*(9.948+4.210+1.744)/100 = 13.50+139.02+31.804
        self.assertEqual(monthly_bill(TECO, 1200, days=30).total, Decimal("184.32"))

    def test_basic_charge_scales_with_days(self):
        self.assertEqual(monthly_bill(TECO, 0, days=31).total, Decimal("13.95"))

    def test_gross_receipts_tax_option(self):
        plain = monthly_bill(TECO, 1000).total
        taxed = monthly_bill(TECO, 1000, include_gross_receipts_tax=True).total
        self.assertEqual(taxed, (plain * Decimal("1.025641")).quantize(Decimal("0.01")))


class General(unittest.TestCase):
    def test_negative_usage_rejected(self):
        with self.assertRaises(ValueError):
            monthly_bill(FPL, -1)

    def test_bill_monotonic_in_usage(self):
        from tariffcalc import load_all
        for t in load_all():
            for month in ((1, 7) if t.seasonal else (None,)):
                totals = [monthly_bill(t, k, month=month).total for k in range(0, 3001, 50)]
                self.assertEqual(totals, sorted(totals), t.key)


if __name__ == "__main__":
    unittest.main()
