# E51 / E52 — DVOL stress overlay for XS-COMBO; stablecoin-supply impulse (2026-11-26)

Both experiments were pre-registered in commit cacaba3, before they were run.

## E51 — H3: halve XS-COMBO after implied-vol shocks

**Setup.**
- Shock = BTC DVOL 7-day log change above its DEV 90th percentile (+11.7 %).
- After a shock, V1 runs at half gross for 7 days (about 20–25 % of days).
- Each switch costs 0.05 %.
- V1 = 7-phase average.

| Window | V1 ann / Sharpe / max DD | Overlay ann / Sharpe / max DD |
|---|---|---|
| DEV 2021-04..2024 | +28.3 % / 1.77 / −16.7 % | +22.8 % / 1.58 / −14.1 % |
| TEST 2025–26 | +30.0 % / 1.43 / −15.0 % | +27.1 % / 1.37 / −13.0 % |

**REJECT.**
- The overlay cuts drawdown by 2–3 points but lowers the Sharpe in both windows.
- XS-COMBO earns part of its return right after stress. This confirms E38: weak periods are followed by recovery.
- De-risking on stress gives up that recovery. No change to F1.

## E52 — H4: long the market when stablecoin issuance surges

**Setup.**
- Weekly z-score of the 7-day % change in total USD stablecoin supply against the prior year.
- Long an equal-weight liquid basket for 7 days when z > 1. Funding and switch costs included.

| Window | H4 ann / Sharpe / exposure | Always long | 28-day momentum timing |
|---|---|---|---|
| DEV 2020-06..2024 | +28.7 % / 0.83 / 15 % | +68.0 % / 0.74 | +68.3 % / **0.98** |
| TEST 2025–26 | −18.8 % / −0.98 / 7 % | −40.1 % / −0.53 | +10.2 % / **0.26** |

**REJECT.**
- In both windows the signal is worse than plain momentum timing.
- In 2025–26 it lost money while invested only 7 % of the time.
- Stablecoin issuance does not time the altcoin market here.

## Status of the five hypotheses

| # | Status |
|---|---|
| H1 settlement flow (E49) | rejected |
| H2 cross-venue funding (E50) | running |
| H3 DVOL overlay (E51) | rejected |
| H4 stablecoin impulse (E52) | rejected |
| H5 listing announcements | prospective only, not started |
