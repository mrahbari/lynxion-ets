# Phase 6 · Step 4 — Hypothesis Batch 2 (extreme-reversion lead)

_Batch-1 found short-horizon reversion BH-significant cross-symbol but NON-monotonic (edge at the extremes). Batch 2 tests extreme-emphasis forms (zero in the middle band). BTC/ETH/SOL, 15m bars, horizons [1, 4, 16, 96]. **Cumulative** multiple-testing family = 156 (batch1+batch2), BH-FDR, default REJECT._

⚠️ **In-sample-motivated:** these forms were derived from batch-1 on the SAME 1-year data, so a PROMOTE here is weaker evidence and REQUIRES true out-of-sample confirmation on a later, untouched period before any reliance.

## Verdicts (does emphasising extremes fix the monotonicity?)

| hypothesis | overall | best IC (sym@h) | decile monotonicity@best | per-symbol |
|---|---|---|---|---|
| rsi14_extreme_revert | **ARCHIVE** | ETH-USDT@1: +0.021 (p=0.000) | -0.35 | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| range48_extreme_revert | **ARCHIVE** | ETH-USDT@1: +0.046 (p=0.000) | -0.45 | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| xs_reversal_5 | **PROVISIONAL** | ETH-USDT@1: +0.027 (p=0.000) | +0.68 | BTC-USDT:ARCH, ETH-USDT:PROM, SOL-USDT:ARCH |

**PROMOTE: 0** — none
**ARCHIVE/PROVISIONAL: 3**

Edge ledger: `research/edge_discovery/measurement/results/edge_ledger.json`.

_If extreme-emphasis raised decile monotonicity above the gate (≥0.6, sign matching IC) AND it stayed BH-significant cross-symbol under the cumulative family, the lead survives as a candidate — still pending OOS confirmation. Otherwise the reversion lead is rejected and the search continues with new hypothesis classes (cross-sectional / carry once funding history is backfilled). No tuning, no execution simulation._
