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


@dataclass(frozen=True)
class Tariff:
    key: str
    utility: str
    schedule: str
    customer_charge: Decimal
    customer_charge_unit: str  # per_month | per_day
    tier_break_kwh: Decimal
    minimum_base_bill: Decimal | None
    charges: dict  # name -> {tier1, tier2, group} in cents/kWh
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Bill:
    utility: str
    kwh: Decimal
    customer_charge: Decimal
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
    return Tariff(
        key=Path(path).stem,
        utility=d["utility"],
        schedule=d["schedule"],
        customer_charge=Decimal(str(cc["amount"])),
        customer_charge_unit=cc["unit"],
        tier_break_kwh=Decimal(str(d["tier_break_kwh"])),
        minimum_base_bill=None if mb is None else Decimal(str(mb)),
        charges={
            k: {
                "tier1": Decimal(str(v["tier1"])),
                "tier2": Decimal(str(v["tier2"])),
                "group": v["group"],
            }
            for k, v in d["energy_charges_cents_per_kwh"].items()
        },
        meta={k: d[k] for k in ("effective", "retrieved", "sources", "notes")},
    )


def load_all(data_dir: Path = DATA_DIR) -> list[Tariff]:
    return [load_tariff(p) for p in sorted(Path(data_dir).glob("*.json"))]


def monthly_bill(t: Tariff, kwh, days: int = 30, include_gross_receipts_tax: bool = False) -> Bill:
    """Bill before franchise fees; optional 2.5641% gross receipts tax."""
    kwh = Decimal(str(kwh))
    if kwh < 0:
        raise ValueError("kWh must be non-negative")
    tier1_kwh = min(kwh, t.tier_break_kwh)
    tier2_kwh = kwh - tier1_kwh

    cc = t.customer_charge * (Decimal(days) if t.customer_charge_unit == "per_day" else 1)

    lines = {}
    for name, c in t.charges.items():
        cents = tier1_kwh * c["tier1"] + tier2_kwh * c["tier2"]
        lines[name] = cents / 100

    base_total = cc + sum(v for n, v in lines.items() if t.charges[n]["group"] == "base")
    adj = Decimal(0)
    if t.minimum_base_bill is not None and base_total < t.minimum_base_bill:
        adj = t.minimum_base_bill - base_total

    subtotal = cc + sum(lines.values()) + adj
    tax = subtotal * GROSS_RECEIPTS_TAX if include_gross_receipts_tax else Decimal(0)
    total = (subtotal + tax).quantize(CENT, ROUND_HALF_UP)
    return Bill(t.utility, kwh, cc, lines, adj, tax, total)
