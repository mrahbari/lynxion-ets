# Phase 6 · Step 6 — Funding-Reversion Lead, Wider-Universe Re-test

_Pre-specified batch-3 funding hypotheses re-tested on 24 symbols, multi-year **8h** bars (native funding cadence; ~3285 bars/sym median). Horizons [3, 9, 12] (1d/3d/4d); lead = 4d. Lookahead-safe asof align. **Cumulative** family = 372, BH-FDR, default REJECT._

## Lead breadth @ 4d horizon (the key question: does it generalise?)

| hypothesis | overall | mean IC@4d | +IC & sig | symbols promoted |
|---|---|---:|---|---:|
| funding_revert | **ARCHIVE** | -0.003 | 1/24 (neg-sig 0) | 0/24 |
| funding_z_revert | **ARCHIVE** | +0.009 | 1/24 (neg-sig 0) | 0/24 |
| xs_funding_revert | **ARCHIVE** | -0.006 | 0/24 (neg-sig 2) | 0/24 |

**Universe:** 24 symbols with ≥200 aligned 8h funding+price bars.

**Lead does NOT clear the gate even on wider/longer data.** funding_revert: mean IC@4d -0.003, 1/24 symbols positive-and-significant, 0/24 individually promoted, overall ARCHIVE.

_Honest read: a true funding-crowding reversion edge should show a positive mean IC@4d with a clear majority of symbols positive-and-significant. Read the breadth columns, not just the verdict. If breadth is weak/mixed, the BTC@4d result from batch 3 was likely idiosyncratic/sample-driven. No tuning, no execution simulation._
