"""Monthly residential bill calculator driven by sourced tariff data files.

Every rate lives in data/*.json together with its source URL. The code holds
no rates, so a reviewer can check numbers against the tariff sheet directly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CENT = Decimal("0.01")
GROSS_RECEIPTS_TAX = Decimal("0.025641")  # TECO sheet 6.023; FL Stat. 203.01


def _d(x) -> Decimal:
    return Decimal(str(x))


@dataclass(frozen=True)
class Tariff:
    key: str
    utility: str
    schedule: str
    jurisdiction: str
    customer_charge: Decimal
    customer_charge_unit: str  # per_month | per_day
    tier_break_kwh: Decimal
    minimum_base_bill: Decimal | None
    charges: dict  # name -> {tier1, tier2, group, [winter: {tier1, tier2}]} in cents/kWh
    winter_months: tuple = ()
    demand_levels: tuple = ()  # ((min_kw, max_kw|None, amount), ...)
    meta: dict = field(default_factory=dict)

    @property
    def seasonal(self) -> bool:
        return bool(self.winter_months)


@dataclass(frozen=True)
class Bill:
    utility: str
    kwh: Decimal
    customer_charge: Decimal
    demand_level_charge: Decimal
    lines: dict  # charge name -> dollars (unrounded Decimal)
    minimum_adjustment: Decimal
    tax: Decimal
    total: Decimal

    def rounded_lines(self) -> dict:
        return {k: v.quantize(CENT, ROUND_HALF_UP) for k, v in self.lines.items()}


def load_tariff(path: Path) -> Tariff:
    d = json.loads(Path(path).read_text())
    cc = d["customer_charge"]
    mb = d.get("minimum_base_bill")
    charges = {}
    for k, v in d["energy_charges_cents_per_kwh"].items():
        c = {"tier1": _d(v["tier1"]), "tier2": _d(v["tier2"]), "group": v["group"]}
        if "winter" in v:
            c["winter"] = {"tier1": _d(v["winter"]["tier1"]), "tier2": _d(v["winter"]["tier2"])}
        charges[k] = c
    levels = tuple(
        (_d(x["min_kw"]), None if x["max_kw"] is None else _d(x["max_kw"]), _d(x["amount"]))
        for x in d.get("demand_level_charges", [])
    )
    return Tariff(
        key=Path(path).stem,
        utility=d["utility"],
        schedule=d["schedule"],
        jurisdiction=d.get("jurisdiction", ""),
        customer_charge=_d(cc["amount"]),
        customer_charge_unit=cc["unit"],
        tier_break_kwh=_d(d["tier_break_kwh"]),
        minimum_base_bill=None if mb is None else _d(mb),
        charges=charges,
        winter_months=tuple(d.get("winter_months", ())),
        demand_levels=levels,
        meta={k: d[k] for k in ("effective", "retrieved", "sources", "notes")},
    )


def load_all(data_dir: Path = DATA_DIR) -> list[Tariff]:
    return [load_tariff(p) for p in sorted(Path(data_dir).glob("*.json"))]


def _demand_level_charge(t: Tariff, peak_kw) -> Decimal:
    if not t.demand_levels:
        return Decimal(0)
    kw = _d(peak_kw)
    for lo, hi, amount in t.demand_levels:
        if kw >= lo and (hi is None or kw < hi):
            return amount
    raise ValueError(f"peak_kw {peak_kw} outside demand levels for {t.key}")


def monthly_bill(t: Tariff, kwh, month: int | None = None, days: int = 30,
                 peak_kw=5, include_gross_receipts_tax: bool = False) -> Bill:
    """Bill for one month, before franchise fees and local taxes.

    month: 1-12. Required for seasonal tariffs (use annual_average_bill otherwise).
    peak_kw: monthly maximum 15-minute demand; only used by tariffs with demand-level charges.
    """
    kwh = _d(kwh)
    if kwh < 0:
        raise ValueError("kWh must be non-negative")
    if t.seasonal and month is None:
        raise ValueError(f"{t.key} has seasonal rates; pass month=1..12 or use annual_average_bill")
    winter = t.seasonal and month in t.winter_months
    tier1_kwh = min(kwh, t.tier_break_kwh)
    tier2_kwh = kwh - tier1_kwh

    cc = t.customer_charge * (Decimal(days) if t.customer_charge_unit == "per_day" else 1)
    dl = _demand_level_charge(t, peak_kw)

    lines = {}
    for name, c in t.charges.items():
        r = c["winter"] if winter and "winter" in c else c
        lines[name] = (tier1_kwh * r["tier1"] + tier2_kwh * r["tier2"]) / 100

    base_total = cc + sum(v for n, v in lines.items() if t.charges[n]["group"] == "base")
    adj = Decimal(0)
    if t.minimum_base_bill is not None and base_total < t.minimum_base_bill:
        adj = t.minimum_base_bill - base_total

    subtotal = cc + dl + sum(lines.values()) + adj
    tax = subtotal * GROSS_RECEIPTS_TAX if include_gross_receipts_tax else Decimal(0)
    total = (subtotal + tax).quantize(CENT, ROUND_HALF_UP)
    return Bill(t.utility, kwh, cc, dl, lines, adj, tax, total)


def annual_average_bill(t: Tariff, kwh, **kw) -> Decimal:
    """Average of the 12 monthly bills at the same usage (same as one bill for non-seasonal tariffs).

    For seasonal tariffs this matches the PSC's annualized weighting (3 winter months, 9 others).
    """
    if not t.seasonal:
        return monthly_bill(t, kwh, **kw).total
    total = sum(monthly_bill(t, kwh, month=m, **kw).total for m in range(1, 13))
    return (total / 12).quantize(CENT, ROUND_HALF_UP)
