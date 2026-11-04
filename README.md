# Residential Rate and Tariff Comparison

Calculates typical monthly residential electric bills from published Florida rate schedules and compares them across utilities and usage levels. Python (standard library only), with the same calculator as a formula-driven Excel workbook (`excel/tariff_calculator.xlsx`); outputs a CSV for Power BI and a small HTML table.

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
- **Validation against published bills** ([docs/BILL_VALIDATION.md](docs/BILL_VALIDATION.md)): the calculator reproduces **111 of 117** residential bills published in the Florida Municipal Electric Association's 2026 monthly comparisons (January-September; 1,000, 1,200 and 2,500 kWh; all five investor-owned schedules), using the rate version documented for each month in `data/history/` (74 exact, 37 within 1-2 cents of FMEA's per-component rounding). The 6 mismatches are Duke's January and February 2026 bills, explained in the report. Current rates also match the PSC's October 2026 comparison ([docs/VALIDATION.md](docs/VALIDATION.md)): 8 of 9 checks to the cent, with Duke differing only in fuel. The municipal utilities have no published-bill check yet.
- **Excel**: `excel/tariff_calculator.xlsx` holds the rates as tables and computes every bill with formulas. Change usage, month, billing days, peak kW or the tax option on its Inputs sheet. It matches the Python calculator on all 208 bills compared (`scripts/verify_excel.py`).
- The calculator has not been checked against individual customer bills; the published bills above are typical-bill comparisons.
- **Power BI view**: `powerbi/TariffComparison.pbip` is a Power BI Project (text-based report and model) with a bill-comparison page and a sources/validation page; see [docs/POWERBI.md](docs/POWERBI.md). Its files validate against Microsoft's schemas and the model is cross-checked by tests, but it has not been opened in Power BI Desktop (Windows-only); manual build steps are included as a fallback. `powerbi/preview.html` is a browser version of the same report for viewing without Power BI (for example on a Mac).

## Usage
```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_outputs.py   # outputs/bill_comparison.csv and outputs/comparison.html
python3 scripts/validate.py        # docs/VALIDATION.md
python3 scripts/validate_history.py   # docs/BILL_VALIDATION.md (2026 published bills, by month)
python3 scripts/build_excel_calculator.py   # excel/tariff_calculator.xlsx (recalculate in Excel or LibreOffice, then: python3 scripts/verify_excel.py)
python3 scripts/build_powerbi_data.py && python3 scripts/build_powerbi_project.py   # powerbi/ (Power BI Project)
```
The Power BI tests need `pip install jsonschema`.

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
- `reference/external_bills.json`, `reference/fmea_2026.json` - published bills used for validation
- `data/history/` - 2026 rate versions by month, each with the sources that document it
- `tests/` - hand-computed bills and the external checks
- `docs/METHODOLOGY.md` - assumptions and limits; `docs/VALIDATION.md` - check results
- `powerbi/` - Power BI Project and the CSVs it loads; `reference/powerbi-schemas/` - Microsoft's schemas used to validate it
