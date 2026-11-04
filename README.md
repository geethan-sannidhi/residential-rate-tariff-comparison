# Residential Rate and Tariff Comparison

Calculates typical monthly residential electric bills from published Florida rate schedules and compares them across utilities and usage levels. Python (standard library only); outputs a CSV for Excel/Power BI and a small HTML table.

## Scope (read this first)
**8 residential schedules**, retrieved 2026-11-04:

| Utility | Schedule | Type | Structure |
|---|---|---|---|
| Florida Power & Light | RS-1 | investor-owned | tiered at 1,000 kWh; $30 minimum base bill |
| FPL Northwest Florida (former Gulf) | RS-1 + transition rider | investor-owned | as FPL plus rider |
| Duke Energy Florida | RS-1 | investor-owned | tiered **and seasonal** (Dec-Feb winter rates) |
| Tampa Electric | RS | investor-owned | tiered; daily customer charge |
| Florida Public Utilities | RS | investor-owned | tiered base and fuel |
| JEA (Jacksonville) | Residential | municipal | tiered base; monthly fuel |
| City of Tallahassee | Residential Standard | municipal | flat per kWh |
| OUC (Orlando) | Residential | municipal | tiered base; **demand-level charge** by peak kW |

- All four investor-owned utilities are covered. Rates come from tariff sheets and PSC filings; municipal rates come from each utility's own published rate page or sheet. Every data file lists its sources and caveats.
- **Validation** ([docs/VALIDATION.md](docs/VALIDATION.md)): 8 of 9 checks against independently published bills (Florida PSC's October 2026 1,000 kWh comparison and the Florida Municipal Electric Association's monthly comparison) match to the cent. The ninth, Duke, differs only by the fuel line: the PSC table uses Duke's January-May fuel factor while Duke's tariff sheet effective September 1, 2026 shows a lower one. JEA, Tallahassee and OUC have no independent check yet because the latest FMEA edition predates their fall 2026 rate changes.
- The calculator has not been checked against actual customer bills.
- No Power BI `.pbix` is included; `outputs/bill_comparison.csv` is shaped for loading into Power BI.

## Usage
```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_outputs.py   # outputs/bill_comparison.csv and outputs/comparison.html
python3 scripts/validate.py        # docs/VALIDATION.md
```

```python
from tariffcalc import load_tariff, monthly_bill, annual_average_bill
duke = load_tariff("data/duke_rs1.json")
monthly_bill(duke, 1000, month=1).total     # Decimal('154.46')  winter
monthly_bill(duke, 1000, month=7).total     # Decimal('143.72')
annual_average_bill(duke, 1000)             # Decimal('146.41')
ouc = load_tariff("data/ouc_res.json")
monthly_bill(ouc, 1000, peak_kw=9).total    # demand-level Tier 2
```

## Layout
- `data/` - one JSON per schedule: every rate, effective date, source URLs, notes
- `src/tariffcalc/` - calculator (holds no rates)
- `reference/external_bills.json` - published bills used for validation
- `tests/` - hand-computed bills and the external checks
- `docs/METHODOLOGY.md` - assumptions and limits; `docs/VALIDATION.md` - check results
