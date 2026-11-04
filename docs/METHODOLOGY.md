# Methodology

## What is calculated
Bill = customer charge + sum over charges of (tier-1 kWh x tier-1 rate + tier-2 kWh x tier-2 rate), where tier 1 is the first 1,000 kWh. Rates are in cents/kWh in the data files and converted to dollars. Money uses `Decimal`; only the final total is rounded (half up, to cents).

## Per-utility treatment
- **FPL RS-1**: $10.52/month customer charge; base energy 7.865 / 8.865 and fuel 2.893 / 3.893 cents/kWh by tier; conservation, capacity, environmental, storm protection and transition credit are flat. The sheet says residential customers whose monthly base electric service costs fall below $30 pay a minimum $30 base bill; the code applies that to customer charge + base energy.
- **TECO RS**: $0.45/day customer charge (30 days assumed unless given); energy and demand charge 8.948 / 9.948 and fuel 3.210 / 4.210 by tier; conservation, capacity, environmental, storm protection plan and clean energy transition are flat. Minimum charge is the basic service charge, so no extra adjustment.

## Hand-check example (FPL, 1,000 kWh)
7.865 + 2.893 + 0.148 + 0.052 + 0.345 + 0.995 - 0.040 = 12.258 cents/kWh -> $122.58; plus $10.52 = **$133.10**.

## What this does not show
- Taxes, franchise fees and local charges (optional 2.5641% gross receipts tax exists in code, off by default).
- Time-of-use, EV and other optional rates, storm surcharges not on the sheets, or rate changes after the effective dates.
- Different clause rates take effect on different dates (see each data file); the comparison mixes them as published on 2026-11-04.
- Real bills vary with billing-period length, proration and customer-specific charges. Check against actual bills before relying on it.
