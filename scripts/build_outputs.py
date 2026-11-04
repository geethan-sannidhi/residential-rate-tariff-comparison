"""Generate comparison CSV (loadable in Power BI/Excel) and a self-contained HTML view.

Seasonal tariffs (Duke) are shown three ways: a non-winter month (July), a winter month
(January) and the 12-month average. Non-seasonal tariffs have the same value in all three.
OUC's demand-level charge assumes Tier 1 (peak under 8 kW).
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tariffcalc import load_all, monthly_bill, annual_average_bill  # noqa: E402

USAGE = list(range(250, 2001, 250))  # 250..2000 kWh
SUMMER, WINTER = 7, 1
tariffs = load_all()

rows = []
for t in tariffs:
    for k in USAGE:
        b = monthly_bill(t, k, month=SUMMER)
        winter = monthly_bill(t, k, month=WINTER).total
        avg = annual_average_bill(t, k)
        rows.append({
            "utility": t.utility, "schedule": t.schedule, "jurisdiction": t.jurisdiction,
            "effective": t.meta["effective"], "kwh": k,
            "customer_charge": float(b.customer_charge),
            "demand_level_charge": float(b.demand_level_charge),
            **{f"charge_{n}": round(float(v), 4) for n, v in b.lines.items()},
            "minimum_adjustment": float(b.minimum_adjustment),
            "bill_july": float(b.total), "bill_january": float(winter), "bill_annual_average": float(avg),
            "cents_per_kwh_annual_average": round(float(avg) / k * 100, 2),
        })

out = ROOT / "outputs"
out.mkdir(exist_ok=True)
lead = ["utility", "schedule", "jurisdiction", "effective", "kwh", "bill_annual_average", "bill_july",
        "bill_january", "cents_per_kwh_annual_average", "customer_charge", "demand_level_charge", "minimum_adjustment"]
fields = lead + sorted({f for r in rows for f in r} - set(lead))
with open(out / "bill_comparison.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, restval=0)
    w.writeheader()
    w.writerows(rows)

series = {t.utility: [float(annual_average_bill(t, k)) for k in USAGE] for t in tariffs}
meta = {t.utility: {"schedule": t.schedule, "effective": t.meta["effective"], "jurisdiction": t.jurisdiction,
                    "sources": t.meta["sources"], "notes": t.meta["notes"]} for t in tariffs}
html = f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Residential bill comparison</title>
<style>
body{{font:15px/1.45 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#1d1d1f;background:#fff}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}
td,th{{border-bottom:1px solid #ddd;padding:.4rem .6rem;text-align:right;white-space:nowrap}}
th{{font-weight:600;vertical-align:bottom;white-space:normal;min-width:6rem}} td:first-child,th:first-child{{text-align:left}}
td.lo{{background:#e6f4ea}} td.hi{{background:#fdecea}} small,.note{{color:#555}} li{{margin:.35rem 0}}
</style>
<h1>Typical monthly residential bill by usage</h1>
<p class=note>12-month average bill (Duke's winter rates apply December-February). Before gross receipts tax,
franchise fees and local taxes. OUC assumes peak demand under 8 kW. Lowest and highest in each row are shaded.
See docs/METHODOLOGY.md for what this does and does not show.</p>
<div class=wrap><table id=t></table></div>
<h2>Schedules and sources</h2><ul id=s></ul>
<script>
const U={json.dumps(USAGE)},S={json.dumps(series)},M={json.dumps(meta)};
const names=Object.keys(S);
let h='<tr><th>kWh</th>'+names.map(k=>'<th>'+k+'</th>').join('')+'<th>Spread</th></tr>';
U.forEach((u,i)=>{{const v=names.map(n=>S[n][i]),lo=Math.min(...v),hi=Math.max(...v);
h+='<tr><td>'+u.toLocaleString()+'</td>'+v.map(x=>'<td class="'+(x===lo?'lo':x===hi?'hi':'')+'">$'+x.toFixed(2)+'</td>').join('')+'<td>$'+(hi-lo).toFixed(2)+'</td></tr>'}});
document.getElementById('t').innerHTML=h;
const esc=s=>s.replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
document.getElementById('s').innerHTML=Object.entries(M).map(([k,m])=>'<li><b>'+esc(k)+'</b> - '+esc(m.schedule)+' ('+esc(m.effective)+'; '+esc(m.jurisdiction)+')<br><small>'+m.sources.map(esc).join('<br>')+'</small></li>').join('');
</script>"""
(out / "comparison.html").write_text(html)
print(f"wrote {len(rows)} rows for {len(tariffs)} schedules")
