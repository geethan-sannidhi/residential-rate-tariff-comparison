"""Generate comparison CSV (loadable in Power BI/Excel) and a self-contained HTML view."""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tariffcalc import load_all, monthly_bill  # noqa: E402

USAGE = list(range(250, 2001, 250))  # 250..2000 kWh
tariffs = load_all()
rows = []
for t in tariffs:
    for k in USAGE:
        b = monthly_bill(t, k)
        rows.append({
            "utility": t.utility, "schedule": t.schedule, "kwh": k,
            "customer_charge": float(b.customer_charge),
            **{f"charge_{n}": float(v) for n, v in b.lines.items()},
            "minimum_adjustment": float(b.minimum_adjustment),
            "total_bill": float(b.total),
            "cents_per_kwh": round(float(b.total) / k * 100, 2),
        })
out = ROOT / "outputs"; out.mkdir(exist_ok=True)
fields = sorted({f for r in rows for f in r}, key=lambda f: (f.startswith("charge_"), f))
with open(out / "bill_comparison.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, restval=0); w.writeheader(); w.writerows(rows)

series = {t.utility: [float(monthly_bill(t, k).total) for k in USAGE] for t in tariffs}
meta = {t.utility: {"schedule": t.schedule, "effective": t.meta["effective"], "sources": t.meta["sources"]} for t in tariffs}
html = f"""<!doctype html><meta charset=utf-8><title>Residential bill comparison</title>
<style>body{{font:15px system-ui;max-width:860px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ccc;padding:.35rem .6rem;text-align:right}}th:first-child,td:first-child{{text-align:left}}
small{{color:#555}}</style>
<h1>Typical monthly bill by usage</h1>
<p><small>Before franchise fees and taxes. 30-day billing period. See docs/METHODOLOGY.md for what this does and does not show.</small></p>
<table id=t></table><h3>Sources</h3><ul id=s></ul>
<script>
const U={json.dumps(USAGE)},S={json.dumps(series)},M={json.dumps(meta)};
let h='<tr><th>kWh</th>'+Object.keys(S).map(k=>'<th>'+k+'</th>').join('')+'<th>Difference</th></tr>';
U.forEach((u,i)=>{{const v=Object.values(S).map(a=>a[i]);h+='<tr><td>'+u+'</td>'+v.map(x=>'<td>$'+x.toFixed(2)+'</td>').join('')+'<td>$'+(Math.max(...v)-Math.min(...v)).toFixed(2)+'</td></tr>'}});
document.getElementById('t').innerHTML=h;
document.getElementById('s').innerHTML=Object.entries(M).map(([k,m])=>'<li>'+k+' - '+m.schedule+' ('+m.effective+'): '+m.sources.join(', ')+'</li>').join('');
</script>"""
(out / "comparison.html").write_text(html)
print(f"wrote {len(rows)} rows")
