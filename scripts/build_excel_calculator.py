"""Build excel/tariff_calculator.xlsx: the bill calculator as a formula-driven Excel workbook.

Rates are inputs (blue) copied from data/*.json; every bill is an Excel formula. Change the usage,
month, billing days or peak kW on Inputs and every sheet recalculates. scripts/verify_excel.py
recalculates the workbook in LibreOffice and compares it with the Python calculator.
"""
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tariffcalc import load_all  # noqa: E402

OUT = ROOT / "excel" / "tariff_calculator.xlsx"
FONT = "Arial"
BLUE, BLACK, GREEN = "0000FF", "000000", "008000"
HEAD = PatternFill("solid", fgColor="DCE6F1")
KEY = PatternFill("solid", fgColor="FFFF00")
THIN = Border(bottom=Side(style="thin", color="BFBFBF"))
USD2 = '$#,##0.00;($#,##0.00);"-"'
CENTS = '0.000'
GRT = 0.025641

tariffs = load_all()
wb = Workbook()


def st(c, color=BLACK, bold=False, fmt=None, fill=None, wrap=False, italic=False, size=10):
    c.font = Font(name=FONT, size=size, color=color, bold=bold, italic=italic)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if wrap:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    return c


def header(ws, row, names, widths=None, freeze=True):
    for j, n in enumerate(names, 1):
        c = st(ws.cell(row=row, column=j, value=n), bold=True, fill=HEAD, wrap=True)
        c.border = THIN
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
    if freeze:
        ws.freeze_panes = ws.cell(row=row + 1, column=1)


def title(ws, text, sub=None):
    st(ws.cell(row=1, column=1, value=text), bold=True, size=13)
    if sub:
        st(ws.cell(row=2, column=1, value=sub), italic=True, color="595959")


# ---------------------------------------------------------------- README
ws = wb.active
ws.title = "README"
ws.column_dimensions["A"].width = 110
for i, (t, b) in enumerate([
    ("Florida residential electric bill calculator", True),
    ("Eight published residential rate schedules; bills before franchise fees and local taxes. Rates as of 2026-11-04.", False),
    ("", False),
    ("How to use", True),
    ("Enter usage, billing month, billing days and peak demand on the Inputs sheet (yellow cells). Calculator shows each "
     "utility's bill and its components; Comparison shows bills across usage levels; Checks compares the workbook with "
     "independently published bills.", False),
    ("", False),
    ("Sheets", True),
    ("Inputs - the four things that vary from bill to bill, plus an optional gross receipts tax.", False),
    ("Schedules - one row per rate schedule: customer charge, tier break, minimum bill, winter months, demand-level charge, sources.", False),
    ("Rates - one row per schedule and charge, in cents per kWh, with winter rates where they differ; formula columns pick the rate for the selected month.", False),
    ("Calculator - each utility's bill at the inputs, broken into components, with cents per kWh and rank.", False),
    ("Comparison - bills from 250 to 3,000 kWh for the selected month, and 12-month averages (which matter for Duke's winter rates).", False),
    ("Checks - workbook results vs. bills published by the Florida PSC and FMEA.", False),
    ("", False),
    ("Colour key", True),
    ("Blue text = input (a published rate or a value you choose). Black = formula. Green = formula that links to another sheet. Yellow fill = cell to edit.", False),
    ("", False),
    ("Method", True),
    ("Bill = customer charge (monthly, or daily x billing days) + demand-level charge (OUC only) + sum of each per-kWh charge on the first "
     "1,000 kWh at the tier-1 rate and on the rest at the tier-2 rate + any minimum-bill adjustment, rounded to the cent. "
     "Full methodology and sources: docs/METHODOLOGY.md and data/*.json in the repository.", False),
], 1):
    st(ws.cell(row=i, column=1, value=t), bold=b, wrap=True)

# ---------------------------------------------------------------- Inputs
ws = wb.create_sheet("Inputs")
title(ws, "Inputs", "Edit the yellow cells.")
header(ws, 3, ["Input", "Value", "Notes"], [34, 12, 90], freeze=False)
inputs = [
    ("Monthly usage (kWh)", 1000, "Any non-negative number.", "#,##0"),
    ("Billing month (1-12)", 7, "Only Duke's rates change by month (December-February winter rates).", "0"),
    ("Days in billing period", 30, "Only Tampa Electric's customer charge is per day.", "0"),
    ("Peak demand (kW)", 5, "Only OUC: under 8 kW = Tier 1, 8-12 kW = Tier 2, 12 kW and up = Tier 3.", "0.0"),
    ("Add gross receipts tax? (Yes/No)", "No", f"Adds {GRT:.4%}, the Florida gross receipts tax factor in Tampa Electric's tariff (Sheet 6.023).", None),
]
for i, (label, val, note, fmt) in enumerate(inputs, 4):
    st(ws.cell(row=i, column=1, value=label))
    st(ws.cell(row=i, column=2, value=val), color=BLUE, fill=KEY, fmt=fmt)
    st(ws.cell(row=i, column=3, value=note), wrap=True)
dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False)
ws.add_data_validation(dv)
dv.add("B8")
dvm = DataValidation(type="whole", operator="between", formula1="1", formula2="12")
ws.add_data_validation(dvm)
dvm.add("B5")
KWH, MONTH, DAYS, PEAK, TAX = "Inputs!$B$4", "Inputs!$B$5", "Inputs!$B$6", "Inputs!$B$7", "Inputs!$B$8"
st(ws.cell(row=10, column=1, value="Gross receipts tax factor"))
st(ws.cell(row=10, column=2, value=GRT), color=BLUE, fmt="0.0000%")
st(ws.cell(row=10, column=3, value="Source: Tampa Electric tariff Sheet No. 6.023 (Section 203.01, Florida Statutes)."))
GRTREF = "Inputs!$B$10"

# ---------------------------------------------------------------- Schedules
ws = wb.create_sheet("Schedules")
title(ws, "Rate schedules", "Columns A-P are inputs from the tariffs; Q-R are formulas.")
scols = ["Key", "Utility", "Short name", "Customer charge ($)", "Customer charge unit", "Tier break (kWh)",
         "Minimum base bill ($)", "Winter months", "Demand tier 1 below (kW)", "Demand tier 2 below (kW)",
         "Demand charge tier 1 ($)", "Demand charge tier 2 ($)", "Demand charge tier 3 ($)", "Type", "Effective", "Primary source",
         "Number of winter months", "Selected month is winter?"]
header(ws, 4, scols, [16, 40, 14, 11, 11, 9, 10, 9, 9, 9, 9, 9, 9, 13, 30, 60, 9, 10])
S = {}
for i, t in enumerate(tariffs, 5):
    S[t.key] = i
    dl = t.demand_levels
    vals = [t.key, t.utility, {"fpl_rs1": "FPL", "fpl_nwfl_rs1": "FPL NW Florida", "duke_rs1": "Duke", "teco_rs": "Tampa Electric",
                               "fpuc_rs": "FPUC", "jea_res": "JEA", "tallahassee_res": "Tallahassee", "ouc_res": "OUC"}[t.key],
            float(t.customer_charge), t.customer_charge_unit, float(t.tier_break_kwh),
            None if t.minimum_base_bill is None else float(t.minimum_base_bill),
            ",".join(str(m) for m in t.winter_months) or None,
            float(dl[0][1]) if dl else None, float(dl[1][1]) if dl else None,
            float(dl[0][2]) if dl else None, float(dl[1][2]) if dl else None, float(dl[2][2]) if dl else None,
            "Investor-owned" if t.jurisdiction.startswith("investor") else "Municipal", t.meta["effective"], t.meta["sources"][0]]
    fmts = [None, None, None, USD2, None, "#,##0", USD2, None, "0.0", "0.0", USD2, USD2, USD2, None, None, None]
    for j, (v, f) in enumerate(zip(vals, fmts), 1):
        st(ws.cell(row=i, column=j, value=v), color=BLUE, fmt=f)
    R = str(i)
    st(ws[f"Q{R}"]).value = f'=IF(H{R}="",0,LEN(H{R})-LEN(SUBSTITUTE(H{R},",",""))+1)'
    st(ws[f"R{R}"], color=GREEN).value = f'=IF(H{R}="",FALSE,ISNUMBER(SEARCH(","&{MONTH}&",",","&H{R}&",")))'
SR = (5, 4 + len(tariffs))

# ---------------------------------------------------------------- Rates
ws = wb.create_sheet("Rates")
title(ws, "Per-kWh charges (cents per kWh)", "Columns A-H are inputs from the tariffs; I-N are formulas.")
rcols = ["Key", "Charge", "Group", "Tier 1 rate (first 1,000 kWh)", "Tier 2 rate (over 1,000 kWh)", "Winter tier 1", "Winter tier 2",
         "Utility", "Winter-or-normal tier 1", "Winter-or-normal tier 2", "Selected month is winter?", "Rate in use: tier 1",
         "Rate in use: tier 2", "Charge at the input usage ($)"]
header(ws, 4, rcols, [16, 22, 8, 11, 11, 9, 9, 34, 10, 10, 10, 10, 10, 13])
r = 5
for t in tariffs:
    for name, c in t.charges.items():
        w = c.get("winter")
        vals = [t.key, name.replace("_", " "), c["group"], float(c["tier1"]), float(c["tier2"]),
                float(w["tier1"]) if w else None, float(w["tier2"]) if w else None, t.utility]
        for j, v in enumerate(vals, 1):
            st(ws.cell(row=r, column=j, value=v), color=BLUE, fmt=CENTS if j in (4, 5, 6, 7) else None)
        R = str(r)
        m = f"MATCH(A{R},Schedules!$A${SR[0]}:$A${SR[1]},0)"
        st(ws[f"I{R}"], fmt=CENTS).value = f'=IF(F{R}="",D{R},F{R})'
        st(ws[f"J{R}"], fmt=CENTS).value = f'=IF(G{R}="",E{R},G{R})'
        st(ws[f"K{R}"], color=GREEN).value = f"=INDEX(Schedules!$R${SR[0]}:$R${SR[1]},{m})"
        st(ws[f"L{R}"], fmt=CENTS).value = f"=IF(K{R},I{R},D{R})"
        st(ws[f"M{R}"], fmt=CENTS).value = f"=IF(K{R},J{R},E{R})"
        brk = f"INDEX(Schedules!$F${SR[0]}:$F${SR[1]},{m})"
        st(ws[f"N{R}"], color=GREEN, fmt=USD2).value = f"=(MIN({KWH},{brk})*L{R}+MAX(0,{KWH}-{brk})*M{R})/100"
        r += 1
RR = (5, r - 1)
ws["F4"].comment = Comment("Only Duke has winter rates (base energy, December-February). Blank = same as the normal rate.", "analyst")


def rng(col):
    return f"Rates!${col}${RR[0]}:${col}${RR[1]}"


def bill_expr(s, k, t1col, t2col, with_tax=True):
    """Excel expression for one month's bill for schedule row s at usage k, using rate columns t1col/t2col."""
    key, brk = f"Schedules!$A${s}", f"Schedules!$F${s}"
    cc = f'Schedules!$D${s}*IF(Schedules!$E${s}="per_day",{DAYS},1)'
    dl = (f'IF(Schedules!$I${s}="",0,IF({PEAK}<Schedules!$I${s},Schedules!$K${s},'
          f'IF({PEAK}<Schedules!$J${s},Schedules!$L${s},Schedules!$M${s})))')
    per_kwh = f"SUMPRODUCT(({rng('A')}={key})*({rng(t1col)}*MIN({k},{brk})+{rng(t2col)}*MAX(0,{k}-{brk})))/100"
    base = f'SUMPRODUCT(({rng("A")}={key})*({rng("C")}="base")*({rng(t1col)}*MIN({k},{brk})+{rng(t2col)}*MAX(0,{k}-{brk})))/100'
    minadj = f'IF(Schedules!$G${s}="",0,MAX(0,Schedules!$G${s}-({cc}+{base})))'
    sub = f"({cc}+{dl}+{per_kwh}+{minadj})"
    if with_tax:
        sub = f'{sub}*(1+IF({TAX}="Yes",{GRTREF},0))'
    return f"ROUND({sub},2)"


def annual_expr(s, k):
    """12-month average: non-winter months at the normal rates, winter months at the winter rates (each rounded)."""
    n = f"Schedules!$Q${s}"
    return f"ROUND(((12-{n})*{bill_expr(s, k, 'D', 'E')}+{n}*{bill_expr(s, k, 'I', 'J')})/12,2)"


# ---------------------------------------------------------------- Calculator
ws = wb.create_sheet("Calculator")
title(ws, "Bill at the inputs", "All formulas. Change the yellow cells on Inputs.")
st(ws.cell(row=3, column=1), color=GREEN, italic=True).value = (
    f'="Usage: "&TEXT({KWH},"#,##0")&" kWh   Month: "&{MONTH}&"   Billing days: "&{DAYS}&"   Peak: "&{PEAK}&" kW   Gross receipts tax: "&{TAX}')
ccols = ["Utility", "Type", "Customer charge ($)", "Demand-level charge ($)", "Energy, non-fuel ($)", "Fuel ($)",
         "Other clauses ($)", "Minimum-bill adjustment ($)", "Gross receipts tax ($)", "Total bill ($)", "Cents per kWh",
         "Rank (1 = lowest)", "12-month average at this usage ($)"]
header(ws, 5, ccols, [40, 14, 11, 11, 11, 11, 11, 11, 11, 12, 9, 8, 13])
for i, t in enumerate(tariffs, 6):
    s, R = S[t.key], str(i)
    key = f"Schedules!$A${s}"
    st(ws[f"A{R}"], color=GREEN).value = f"=Schedules!B{s}"
    st(ws[f"B{R}"], color=GREEN).value = f"=Schedules!N{s}"
    st(ws[f"C{R}"], color=GREEN, fmt=USD2).value = f'=Schedules!$D${s}*IF(Schedules!$E${s}="per_day",{DAYS},1)'
    st(ws[f"D{R}"], color=GREEN, fmt=USD2).value = (f'=IF(Schedules!$I${s}="",0,IF({PEAK}<Schedules!$I${s},Schedules!$K${s},'
                                                    f'IF({PEAK}<Schedules!$J${s},Schedules!$L${s},Schedules!$M${s})))')
    st(ws[f"E{R}"], color=GREEN, fmt=USD2).value = f'=SUMIFS({rng("N")},{rng("A")},{key},{rng("B")},"base energy")'
    st(ws[f"F{R}"], color=GREEN, fmt=USD2).value = f'=SUMIFS({rng("N")},{rng("A")},{key},{rng("B")},"fuel")'
    st(ws[f"G{R}"], color=GREEN, fmt=USD2).value = f'=SUMIFS({rng("N")},{rng("A")},{key})-E{R}-F{R}'
    base = f'SUMIFS({rng("N")},{rng("A")},{key},{rng("C")},"base")'
    st(ws[f"H{R}"], color=GREEN, fmt=USD2).value = f'=IF(Schedules!$G${s}="",0,MAX(0,Schedules!$G${s}-(C{R}+{base})))'
    st(ws[f"I{R}"], color=GREEN, fmt=USD2).value = f'=IF({TAX}="Yes",SUM(C{R}:H{R})*{GRTREF},0)'
    st(ws[f"J{R}"], fmt=USD2, bold=True).value = f"=ROUND(SUM(C{R}:I{R}),2)"
    st(ws[f"K{R}"], color=GREEN, fmt="0.00").value = f'=IF({KWH}>0,J{R}/{KWH}*100,"")'
    st(ws[f"L{R}"]).value = f"=RANK(J{R},$J$6:$J${5 + len(tariffs)},1)"
    st(ws[f"M{R}"], color=GREEN, fmt=USD2).value = "=" + annual_expr(s, KWH)
ws["D5"].comment = Comment("OUC only: depends on the month's highest 15-minute demand (Inputs, peak kW).", "analyst")
ws["H5"].comment = Comment("FPL only: base bill (customer charge + non-fuel energy) is raised to $30 if lower.", "analyst")
ws["M5"].comment = Comment("Average of the 12 monthly bills at this usage. Differs from the total only for Duke.", "analyst")

# ---------------------------------------------------------------- Comparison
ws = wb.create_sheet("Comparison")
title(ws, "Bills by usage level", "Same billing days, peak kW and tax setting as Inputs.")
levels = list(range(250, 3001, 250))
shorts = [ws_name for ws_name in []]
for block, (label, fn) in enumerate((
        ("Selected month (Inputs, billing month)", lambda s, k: bill_expr(s, k, "L", "M")),
        ("12-month average", annual_expr))):
    top = 4 + block * (len(levels) + 4)
    st(ws.cell(row=top, column=1, value=label), bold=True)
    hdr = top + 1
    st(ws.cell(row=hdr, column=1, value="kWh"), bold=True, fill=HEAD)
    for j, t in enumerate(tariffs, 2):
        st(ws.cell(row=hdr, column=j), bold=True, fill=HEAD, color=GREEN, wrap=True).value = f"=Schedules!C{S[t.key]}"
    for i, k in enumerate(levels, hdr + 1):
        st(ws.cell(row=i, column=1, value=k), color=BLUE, fmt="#,##0")
        for j, t in enumerate(tariffs, 2):
            st(ws.cell(row=i, column=j), fmt=USD2).value = "=" + fn(S[t.key], f"$A{i}")
ws.column_dimensions["A"].width = 10
for j in range(2, 2 + len(tariffs)):
    ws.column_dimensions[get_column_letter(j)].width = 13

# ---------------------------------------------------------------- Checks
ref = json.loads((ROOT / "reference" / "external_bills.json").read_text())
ws = wb.create_sheet("Checks")
title(ws, "Workbook vs. independently published bills",
      "Published values exclude gross receipts tax and franchise fees; set Inputs to 30 billing days, peak under 8 kW and no tax for a like-for-like check.")
header(ws, 4, ["Utility", "kWh", "Workbook ($)", "Published ($)", "Difference ($)", "Source", "Note"], [40, 8, 12, 12, 12, 16, 90])
for i, c in enumerate(ref["checks"], 5):
    s, R = S[c["tariff"]], str(i)
    st(ws[f"A{R}"], color=GREEN).value = f"=Schedules!B{s}"
    st(ws[f"B{R}"], color=BLUE, fmt="#,##0").value = c["kwh"]
    st(ws[f"C{R}"], fmt=USD2).value = "=" + (annual_expr(s, f"B{R}") if c.get("annual_average") else bill_expr(s, f"B{R}", "D", "E"))
    st(ws[f"D{R}"], color=BLUE, fmt=USD2).value = c["expected"]
    st(ws[f"E{R}"], fmt='+$#,##0.00;-$#,##0.00;$0.00').value = f"=C{R}-D{R}"
    st(ws[f"F{R}"], color=BLUE).value = c["source"]
    st(ws[f"G{R}"], color=BLUE, wrap=True).value = c.get("known_difference") or c["note"]
n0 = 5 + len(ref["checks"]) + 1
for j, (k, v) in enumerate(ref["sources"].items()):
    st(ws.cell(row=n0 + j, column=1, value=f"{k}: {v}"), italic=True, color="595959")

OUT.parent.mkdir(exist_ok=True)
wb.save(OUT)
print(f"wrote {OUT.relative_to(ROOT)} ({len(tariffs)} schedules, {RR[1] - RR[0] + 1} rate rows)")
