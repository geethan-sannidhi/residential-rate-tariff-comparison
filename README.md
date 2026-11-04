# Residential Rate and Tariff Comparison

Calculates typical monthly residential electric bills from published Florida tariff sheets and compares them across utilities and usage levels. Python (standard library only); outputs a CSV for Excel/Power BI and a small HTML table.

## Scope (read this first)
- **Utilities covered: 2** - FPL (RS-1) and Tampa Electric (RS), from official tariff documents retrieved 2026-11-04.
- Both schedules have tiered energy charges (break at 1,000 kWh), a fixed customer charge (FPL monthly, TECO daily), and several per-kWh cost-recovery clauses. Neither has a seasonal rate on the sheets used.
- Not yet covered: Duke Energy Florida, Florida Public Utilities, Gulf (now part of FPL), municipal utilities. Duke's site blocked automated retrieval; adding a utility only requires a new JSON file in `data/` with its source URLs.
- Validation is by unit tests against hand-computed bills (`tests/`). It has **not** been checked against real customer bills.
- No Power BI `.pbix` is included; `outputs/bill_comparison.csv` is shaped for loading into Power BI.

## Usage
```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_outputs.py   # writes outputs/bill_comparison.csv and outputs/comparison.html
```

```python
from tariffcalc import load_tariff, monthly_bill
t = load_tariff("data/fpl_rs1.json")
monthly_bill(t, 1000).total          # Decimal('133.10')
```

## Layout
- `data/` - one JSON per tariff: every rate, effective date, source URL, notes
- `src/tariffcalc/` - calculator (holds no rates)
- `tests/` - hand-computed expected bills
- `docs/METHODOLOGY.md` - assumptions and limits
