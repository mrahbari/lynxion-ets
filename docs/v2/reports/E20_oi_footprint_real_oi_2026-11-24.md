# E20 — OIFootprint with real open interest (E16-U9), 2026-11-24

**Question.** Live OIFootprint never receives open interest, so `NGOI_SETUP` always used its
volume-spike + RSI proxy. Does the coded OI hypothesis (price up + OI down > 2 % over 5 bars -> BUY
"short squeeze"; price down + OI down -> SELL "long liquidation") have edge with REAL OI?

**Method.** Unchanged adapter replayed through the E9 engine (1h bars, next-bar-open entry, SL before TP
on High/Low, fees 5 bp/side, slippage 2 bp, BE/trail). Binance USDT-M 5m open interest injected per bar,
causal (last snapshot <= bar close - 5 min). BTC, ETH, SOL, XRP, ADA. DEV 2025-11-01..2026-06-30,
HOLDOUT 2026-07-01..08-29 (OI history ends there). Rule pre-registered and committed before the run:
PASS = net mean R > 0 with n >= 30 on DEV and HOLDOUT.

| variant | window | trades | mean R | win rate | mean ret (bp) |
|---|---|---|---|---|---|
| real OI | DEV | 846 | -0.107 | 0.400 | -12.8 |
| real OI | HOLDOUT | 121 | +0.113 | 0.479 | +13.6 |
| proxy (E9, live today) | DEV | 2179 | -0.105 | 0.391 | -12.6 |
| proxy (E9, live today) | HOLDOUT | 416 | -0.021 | 0.430 | -2.6 |

**Result: FAIL** (DEV negative over 846 trades; the short holdout is not enough to overturn it).
Real OI does not rescue the setup and the proxy has no edge either.

**Decision (pre-registered).** OIFootprint retired from live: removed from `STRATEGY_ALLOWLIST`. Code,
config and the real-OI branch are kept, so it can be re-enabled by the allowlist if a future OI factor
(E13-3, cross-sectional) passes.

Reproduce: `python research/v2/experiments/e20_oi_footprint_real_oi.py`
(outputs `E20_oi_footprint_summary.csv`, `E20_oi_footprint_trades.csv`).
