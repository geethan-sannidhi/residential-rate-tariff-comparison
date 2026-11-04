# Methodology

## What is calculated
Bill = customer charge + demand-level charge (OUC only) + sum over charges of (tier-1 kWh x tier-1 rate + tier-2 kWh x tier-2 rate), where tier 1 is the first 1,000 kWh. Flat schedules use the same rate in both tiers. Rates are stored in cents/kWh and converted to dollars. Money uses `Decimal`; only the final total is rounded (half up, to cents).

**Seasonal rates.** Duke's base energy rate is higher in December-February. `monthly_bill` requires a month for seasonal schedules; `annual_average_bill` averages the 12 monthly bills at the same usage, which equals the PSC's own weighting (3 winter months, 9 others). The comparison table uses the annual average; the CSV also has July and January columns.

**Demand-level charge.** OUC adds $5, $10 or $15 a month depending on the month's highest 15-minute demand (<8 kW, 8-12 kW, >=12 kW). Usage alone doesn't determine it, so the comparison assumes Tier 1; pass `peak_kw` to change it.

## Per-utility treatment
- **FPL RS-1**: $10.52/month; base energy 7.865 / 8.865 and fuel 2.893 / 3.893 cents/kWh by tier; other clauses flat. A $30 minimum base bill applies to customer charge + base energy.
- **FPL Northwest Florida**: identical to RS-1 except the former-Gulf transition rider (+$4.21 per 1,000 kWh in the PSC table) replaces FPL's -$0.40 credit. Modeled as a flat 0.421 cents/kWh; the FMEA 1,200 kWh bill confirms the flat treatment.
- **Duke RS-1**: $14.43/month; base energy 7.731 / 8.503 (Mar-Nov) and 8.805 / 10.302 (Dec-Feb); fuel 3.465 / 4.535; ECCR 0.386, CCR 0.133, ECRC 0.040, asset securitization 0.238, storm protection 0.936 cents/kWh. Base rates from Sheet 6.120 and factors from BA-1 Sheet 6.105, both effective September 1, 2026. Sheet 6.105 is a scanned page; the values were read from the rendered image, not OCR.
- **Tampa Electric RS**: $0.45/day (30 days assumed); energy and demand 8.948 / 9.948 and fuel 3.210 / 4.210; other clauses flat.
- **FPUC RS**: $24.40/month; base 2.867 / 4.695 (settlement Rate Year 2); fuel and purchased power 8.820 / 10.070 (Order PSC-2025-0436-FOF-EI); conservation 0.321 and storm protection 1.656 cents/kWh, taken from the PSC's October 2026 per-1,000-kWh table and modeled as flat.
- **JEA**: $21.00/month; energy 7.815 / 9.705 cents/kWh; fuel 4.975 cents/kWh (November 2026; JEA changes fuel monthly).
- **City of Tallahassee**: $10.29/month (single phase); energy 9.518 and fuel/purchased power 4.065 cents/kWh on all usage. The page shows no effective date.
- **OUC (Orlando)**: $18.50/month + demand-level charge; base 5.935 / 8.435; fuel 4.767 cents/kWh. Effective November 1, 2026.

## Hand-check example (Duke, 1,000 kWh, January)
8.805 + 3.465 + 0.386 + 0.133 + 0.040 + 0.238 + 0.936 = 14.003 cents/kWh -> $140.03; plus $14.43 = **$154.46**.

## Rate history
`data/history/` holds each investor-owned schedule's 2026 rate versions (same format as `data/*.json`) with the months each is documented for. They exist to validate the calculator against 2026 published bills (`docs/BILL_VALIDATION.md`); the comparison tools use the current rates in `data/`.

## Open items
- **Duke base-rate timing.** Duke filed its second 2026 solar base-rate change as effective September 1, but the PSC's September 1 table and FMEA's September bills still use the June base rates; the PSC's October 1 table is the first to show the new ones.
- **Duke fuel.** The PSC's October 1, 2026 summary shows Duke fuel at $41.27 per 1,000 kWh, which equals Duke's January-May 2026 factor; Duke's Sheet 6.105 effective September 1, 2026 shows 3.465 cents ($34.65). The tool follows the tariff sheet. If a later mid-course change raised fuel again, `data/duke_rs1.json` needs updating.
- **Municipal effective dates.** Tallahassee's page has no date, and JEA, Tallahassee and OUC all changed rates in fall 2026, after the latest independent comparison.

## What this does not show
- Gross receipts tax, regulatory assessment fee, franchise fees, public service and municipal utility taxes (an optional 2.5641% gross receipts tax exists in code, off by default). These differ by utility and city, so real bills will be higher.
- Time-of-use, EV, solar and other optional rates; three-phase service.
- Municipal utilities are not rate-regulated by the PSC, and their fuel charges change more often than investor-owned utilities' annual factors.
- Rates change during the year (fuel, storm, mid-course corrections). The comparison is a snapshot as of 2026-11-04.
- Real bills vary with billing-period length, proration and customer-specific charges.
