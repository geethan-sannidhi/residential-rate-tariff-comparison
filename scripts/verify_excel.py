"""Compare the Excel calculator's computed values with the Python calculator.

Reads cached (recalculated) values from excel/tariff_calculator.xlsx, using the input values saved in
the workbook. Recalculate after rebuilding (opening and saving in Excel does this; so does LibreOffice).
Exits non-zero on any mismatch; also used by tests/test_excel.py.
"""
import sys
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tariffcalc import load_all, monthly_bill, annual_average_bill  # noqa: E402

XLSX = ROOT / "excel" / "tariff_calculator.xlsx"


def check(path=XLSX):
    wb = load_workbook(path, data_only=True)
    inp = wb["Inputs"]
    kwh, month, days, peak, tax = (inp[f"B{r}"].value for r in range(4, 9))
    tax = tax == "Yes"
    tariffs = {t.utility: t for t in load_all()}
    problems, n = [], 0
    calc = wb["Calculator"]
    if calc["J6"].value is None:
        return ["workbook has no computed values: recalculate it first"], 0
    for r in range(6, 6 + len(tariffs)):
        t = tariffs[calc[f"A{r}"].value]
        exp = monthly_bill(t, kwh, month=month, days=days, peak_kw=peak, include_gross_receipts_tax=tax).total
        exp_avg = annual_average_bill(t, kwh, days=days, peak_kw=peak, include_gross_receipts_tax=tax)
        for got, e, what in ((calc[f"J{r}"].value, exp, "total"), (calc[f"M{r}"].value, exp_avg, "12-month avg")):
            n += 1
            if Decimal(str(round(got, 2))) != e:
                problems.append(f"Calculator {t.key} {what}: {got} vs {e}")
    comp = wb["Comparison"]
    by_short = {}
    sched = wb["Schedules"]
    for r in range(5, 5 + len(tariffs)):
        by_short[sched[f"C{r}"].value] = tariffs[sched[f"B{r}"].value]
    for block, avg in ((0, False), (1, True)):
        hdr = 5 + block * 16
        names = [comp.cell(row=hdr, column=j).value for j in range(2, 2 + len(tariffs))]
        for i in range(hdr + 1, hdr + 13):
            k = comp.cell(row=i, column=1).value
            for j, nm in enumerate(names, 2):
                t = by_short[nm]
                e = (annual_average_bill(t, k, days=days, peak_kw=peak, include_gross_receipts_tax=tax) if avg else
                     monthly_bill(t, k, month=month, days=days, peak_kw=peak, include_gross_receipts_tax=tax).total)
                got = comp.cell(row=i, column=j).value
                n += 1
                if Decimal(str(round(got, 2))) != e:
                    problems.append(f"Comparison {'avg' if avg else 'month'} {nm} {k} kWh: {got} vs {e}")
    return problems, n


if __name__ == "__main__":
    probs, n = check(Path(sys.argv[1]) if len(sys.argv) > 1 else XLSX)
    if probs:
        print("MISMATCHES:\n" + "\n".join(probs[:40]))
        sys.exit(1)
    print(f"Excel calculator matches the Python calculator on all {n} bills compared.")
