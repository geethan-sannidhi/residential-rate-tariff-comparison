"""Write the tidy CSVs the Power BI project loads (powerbi/data/).

bills.csv       one row per schedule x usage (0-3,000 kWh, every 50) x month: total and components
components.csv  the same bills in long form (one row per component) for stacked charts
utilities.csv   one row per schedule: names, jurisdiction, effective date, structure, sources
validation.csv  calculator vs. independently published bills (reference/external_bills.json)
OUC's demand-level charge assumes Tier 1 (peak under 8 kW), as in the other outputs.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from tariffcalc import load_all, monthly_bill  # noqa: E402
import validate  # noqa: E402

OUT = ROOT / "powerbi" / "data"
OUT.mkdir(parents=True, exist_ok=True)
SHORT = {"fpl_rs1": "FPL", "fpl_nwfl_rs1": "FPL NW Florida", "duke_rs1": "Duke", "teco_rs": "Tampa Electric",
         "fpuc_rs": "FPUC", "jea_res": "JEA", "tallahassee_res": "Tallahassee", "ouc_res": "OUC"}
COMPONENT = {"base_energy": "Energy (non-fuel)", "fuel": "Fuel"}  # everything else is a cost-recovery clause
tariffs = load_all()

with open(OUT / "utilities.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["tariff_key", "utility", "short_name", "schedule", "type", "jurisdiction", "effective",
                "seasonal", "demand_level_charge", "tiered", "source_1"])
    for t in tariffs:
        tiered = any(c["tier1"] != c["tier2"] for c in t.charges.values())
        w.writerow([t.key, t.utility, SHORT[t.key], t.schedule,
                    "Investor-owned" if t.jurisdiction.startswith("investor") else "Municipal",
                    t.jurisdiction, t.meta["effective"], t.seasonal, bool(t.demand_levels), tiered, t.meta["sources"][0]])

with open(OUT / "bills.csv", "w", newline="") as fb, open(OUT / "components.csv", "w", newline="") as fc:
    wb, wc = csv.writer(fb), csv.writer(fc)
    wb.writerow(["tariff_key", "kwh", "month", "total_bill", "customer_charge", "demand_level_charge",
                 "energy_non_fuel", "fuel", "other_clauses", "minimum_adjustment"])
    wc.writerow(["tariff_key", "kwh", "month", "component", "amount"])
    for t in tariffs:
        for kwh in range(0, 3001, 50):
            for m in range(1, 13):
                b = monthly_bill(t, kwh, month=m)
                lines = {k: float(v) for k, v in b.lines.items()}
                energy, fuel = lines.get("base_energy", 0.0), lines.get("fuel", 0.0)
                other = sum(v for k, v in lines.items() if k not in COMPONENT)
                fixed = float(b.customer_charge + b.demand_level_charge + b.minimum_adjustment)
                wb.writerow([t.key, kwh, m, float(b.total), float(b.customer_charge), float(b.demand_level_charge),
                             round(energy, 4), round(fuel, 4), round(other, 4), float(b.minimum_adjustment)])
                # components sum to the unrounded subtotal; total_bill is rounded to the cent
                for comp, val in (("Fixed charges", fixed), ("Energy (non-fuel)", energy), ("Fuel", fuel),
                                  ("Cost-recovery clauses", other)):
                    wc.writerow([t.key, kwh, m, comp, round(val, 4)])

_, rows = validate.run()
with open(OUT / "validation.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["tariff_key", "kwh", "calculator", "published", "difference", "source", "note"])
    for r in rows:
        w.writerow([r["tariff"], r["kwh"], float(r["got"]), r["expected"], float(r["diff"]), r["source"],
                    r.get("known_difference") or r["note"]])
print("wrote", ", ".join(sorted(p.name for p in OUT.glob("*.csv"))))
