# Phase 6 · Step 3 — First Signal Hypotheses (predictive-power results)

_Pre-registered batch of 10 hypotheses, FROZEN params, run ONCE through the Step-1 harness. BTC/ETH/SOL, 1m→15min bars (BTC-USDT:35042, ETH-USDT:35041, SOL-USDT:35041 bars), horizons [1, 4, 16, 96] (15m/1h/4h/1d). Multiple-testing family = 120 (10×3×4); BH-FDR, default posture REJECT. Signal quality only — no SL/TP, cost, or simulation._

## Verdicts

| hypothesis | class | overall | best IC (sym@horizon) | per-symbol verdicts |
|---|---|---|---|---|
| reversal_5 | statistical_reversion | **ARCHIVE** | ETH-USDT@1: IC=+0.040 (p=0.000) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| reversal_20 | statistical_reversion | **ARCHIVE** | ETH-USDT@1: IC=+0.029 (p=0.000) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| momentum_20 | momentum | **ARCHIVE** | ETH-USDT@1: IC=-0.029 (p=0.000) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| momentum_96 | momentum | **ARCHIVE** | BTC-USDT@16: IC=-0.028 (p=0.086) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| rsi14_reversal | statistical_reversion | **ARCHIVE** | ETH-USDT@1: IC=+0.049 (p=0.000) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| range48_revert | statistical_reversion | **ARCHIVE** | ETH-USDT@1: IC=+0.044 (p=0.000) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| vol_scaled_reversal_20 | statistical_reversion | **ARCHIVE** | ETH-USDT@1: IC=+0.031 (p=0.000) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| volume_spike_reversal_48 | flow_proxy | **ARCHIVE** | BTC-USDT@4: IC=-0.013 (p=0.017) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| xs_reversal_20 | cross_sectional | **ARCHIVE** | SOL-USDT@16: IC=+0.027 (p=0.072) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| xs_momentum_96 | cross_sectional | **ARCHIVE** | SOL-USDT@96: IC=+0.025 (p=0.475) | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |

**PROMOTE: 0** — none
**PROVISIONAL: 0** — none
**ARCHIVE: 10**

Edge ledger: `research/edge_discovery/measurement/results/edge_ledger.json`.

**Honest lead (archived, not promoted):** the short-horizon reversion family
(`rsi14_reversal`, `range48_revert`, `reversal_5`) shows a **BH-significant,
cross-symbol same-sign** IC at the 15m horizon (BTC +0.044 / ETH +0.049 / SOL
+0.037, adj_p≈0). It archived because the decile relationship is **non-monotonic**
(edge concentrated at the signal extremes, not linear across the distribution) —
so it fails the monotonicity robustness gate. This is the single most promising
direction for a *future, separately-authorized* refinement pass (e.g. an
extreme-only formulation), **not** a promotion. Everything else is at noise level.

_Interpretation note: these are conventional OHLCV signals on a 1-year sample. A PROMOTE here means a statistically robust, multiple-testing-corrected, cross-symbol-consistent predictive edge at the SIGNAL level — it does NOT yet imply tradeable profit (cost/geometry are evaluated later by the separate execution stack). PROVISIONAL = edge in some symbols but not cross-symbol robust. Funding/OI hypotheses are deferred until a longer history is backfilled (OI capped at ~30d)._
