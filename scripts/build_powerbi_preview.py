"""Write powerbi/preview.html: a browser preview of the Power BI report for people without
Power BI Desktop (e.g. on a Mac). Same data (powerbi/data/*.csv), same pages, slicers and visuals,
and the same measure logic as the DAX in docs/POWERBI.md. It is an HTML page, not a Power BI rendering.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "powerbi" / "data"
KWH = list(range(0, 3001, 50))
COMPONENTS = ["Fixed charges", "Energy (non-fuel)", "Fuel", "Cost-recovery clauses"]

utils = list(csv.DictReader(open(D / "utilities.csv")))
order = {u["tariff_key"]: i for i, u in enumerate(utils)}
bills = {u["tariff_key"]: [[0.0] * len(KWH) for _ in range(12)] for u in utils}
comps = {u["tariff_key"]: {c: [[0.0] * len(KWH) for _ in range(12)] for c in COMPONENTS} for u in utils}
for r in csv.DictReader(open(D / "bills.csv")):
    bills[r["tariff_key"]][int(r["month"]) - 1][int(r["kwh"]) // 50] = float(r["total_bill"])
for r in csv.DictReader(open(D / "components.csv")):
    comps[r["tariff_key"]][r["component"]][int(r["month"]) - 1][int(r["kwh"]) // 50] = round(float(r["amount"]), 3)
validation = list(csv.DictReader(open(D / "validation.csv")))

# Series colors follow the entity (fixed by short name), from the validated reference palette.
SERIES_ORDER = ["FPL", "FPL NW Florida", "Duke", "Tampa Electric", "FPUC", "JEA", "Tallahassee", "OUC"]
data = {
    "kwh": KWH,
    "components": COMPONENTS,
    "utilities": [{
        "key": u["tariff_key"], "name": u["utility"], "short": u["short_name"], "schedule": u["schedule"],
        "type": u["type"], "jurisdiction": u["jurisdiction"], "effective": u["effective"], "source": u["source_1"],
        "seasonal": u["seasonal"] == "True", "color": SERIES_ORDER.index(u["short_name"]),
        "bills": bills[u["tariff_key"]], "comps": [comps[u["tariff_key"]][c] for c in COMPONENTS],
    } for u in utils],
    "validation": [{**v, "short": next(u["short_name"] for u in utils if u["tariff_key"] == v["tariff_key"])} for v in validation],
}

TEMPLATE = (ROOT / "scripts" / "preview_template.html").read_text()
out = TEMPLATE.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
# Standalone page (GitHub Pages, or double-click locally): needs its own doctype, charset and viewport.
standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              + out.replace("</style>", "</style>\n</head>\n<body>", 1) + "\n</body>\n</html>\n")
(ROOT / "powerbi" / "preview.html").write_text(standalone)
print(f"wrote powerbi/preview.html ({len(standalone) / 1024:.0f} KB)")
# Fragment for hosts that supply their own document skeleton (e.g. the claude.ai artifact).
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(out)
    print(f"wrote fragment to {sys.argv[1]}")
