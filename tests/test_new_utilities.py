"""Hand-computed expectations for the schedules added after FPL/TECO, plus external checks."""
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from tariffcalc import load_tariff, monthly_bill, annual_average_bill  # noqa: E402
import validate  # noqa: E402

T = lambda k: load_tariff(ROOT / "data" / f"{k}.json")
DUKE, OUC, JEA, TAL, FPUC = T("duke_rs1"), T("ouc_res"), T("jea_res"), T("tallahassee_res"), T("fpuc_rs")


class DukeRS1(unittest.TestCase):
    CLAUSES = Decimal("3.465") + Decimal("0.386") + Decimal("0.133") + Decimal("0.040") + Decimal("0.238") + Decimal("0.936")

    def test_summer_1000(self):
        # 14.43 + 1000 * (7.731 + 5.198) / 100 = 14.43 + 129.29
        self.assertEqual(monthly_bill(DUKE, 1000, month=7).total, Decimal("143.72"))

    def test_winter_1000(self):
        # 14.43 + 1000 * (8.805 + 5.198) / 100 = 154.46
        self.assertEqual(monthly_bill(DUKE, 1000, month=1).total, Decimal("154.46"))

    def test_winter_months_are_dec_to_feb(self):
        bills = {m: monthly_bill(DUKE, 1000, month=m).total for m in range(1, 13)}
        self.assertEqual({m for m, b in bills.items() if b == Decimal("154.46")}, {12, 1, 2})

    def test_summer_1500_second_tier_fuel(self):
        # 143.72 + 500 * (8.503 + 4.535 + 1.733) / 100 = 143.72 + 73.855
        self.assertEqual(monthly_bill(DUKE, 1500, month=7).total, Decimal("217.58"))

    def test_annual_average_weights_three_winter_months(self):
        # (3 * 154.46 + 9 * 143.72) / 12 = 146.405 -> 146.41
        self.assertEqual(annual_average_bill(DUKE, 1000), Decimal("146.41"))

    def test_month_required(self):
        with self.assertRaises(ValueError):
            monthly_bill(DUKE, 1000)


class OUCResidential(unittest.TestCase):
    def test_tier1_1000(self):
        # 18.50 + 5.00 + 1000 * (5.935 + 4.767) / 100 = 130.52
        self.assertEqual(monthly_bill(OUC, 1000, peak_kw=5).total, Decimal("130.52"))

    def test_demand_level_boundaries(self):
        self.assertEqual(monthly_bill(OUC, 0, peak_kw=7.99).total, Decimal("23.50"))
        self.assertEqual(monthly_bill(OUC, 0, peak_kw=8).total, Decimal("28.50"))
        self.assertEqual(monthly_bill(OUC, 0, peak_kw=12).total, Decimal("33.50"))


class Others(unittest.TestCase):
    def test_jea_1200(self):
        # 21 + 1000*(7.815+4.975)/100 + 200*(9.705+4.975)/100 = 21 + 127.90 + 29.36
        self.assertEqual(monthly_bill(JEA, 1200).total, Decimal("178.26"))

    def test_tallahassee_flat(self):
        # 10.29 + 2000 * 13.583 / 100 = 281.95
        self.assertEqual(monthly_bill(TAL, 2000).total, Decimal("281.95"))

    def test_fpuc_minimum_is_customer_charge(self):
        self.assertEqual(monthly_bill(FPUC, 0).total, Decimal("24.40"))


class ExternalChecks(unittest.TestCase):
    def test_published_bills(self):
        _, rows = validate.run()
        for r in rows:
            with self.subTest(tariff=r["tariff"], kwh=r["kwh"]):
                if r.get("known_difference"):
                    # Duke: only the fuel line differs (34.65 vs 41.27 per 1,000 kWh)
                    self.assertEqual(r["diff"], Decimal("-6.62"))
                else:
                    self.assertEqual(r["diff"], 0)


if __name__ == "__main__":
    unittest.main()
