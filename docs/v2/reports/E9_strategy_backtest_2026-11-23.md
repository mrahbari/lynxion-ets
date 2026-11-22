# E9 — Each platform strategy backtested alone (2026-11-23)

Script `research/v2/experiments/e9_strategy_backtest.py`; trades `E9_strategy_backtest_trades.csv`, summary
`E9_strategy_backtest_summary.csv`. Rule pre-registered in `tasks/ROADMAP_V2.md` (S2) before the run.

Setup: 10 liquid Binance USDT-M perps, each strategy on its design timeframe (1h/15m/5m), the strategy's own
`generate_signal()` fed closed bars only; live-equivalent execution: next-bar-open entry, sanitized SL/TP (what live
sends), R-mode APM (BE 1.5R, trail 1.5R after 2R), SL before TP inside a bar, stop gaps filled at the open,
0.05% taker per side + 2 bp slippage. DEV 2025-11-01..2026-06-30 (8 months).

| Strategy | Trades | PF | mean R | gross bp/trade (before fees) | symbols + | halves (R) |
|---|---|---|---|---|---|---|
| volatility_breakout | 998 | 1.01 | −0.010 | +12.0 | 5/10 | +0.008 / −0.028 |
| trend_following | 1,703 | 0.88 | −0.078 | −10.3 | 3/10 | −0.083 / −0.073 |
| mean_reversion | 2,215 | 0.86 | −0.087 | −10.7 | 0/10 | −0.108 / −0.065 |
| mtf_trend | 2,896 | 0.85 | −0.091 | −11.5 | 0/10 | −0.046 / −0.137 |
| liquidity | 3,522 | 0.85 | −0.092 | −3.0 | 1/10 | −0.073 / −0.111 |
| vwap_reversal | 9,755 | 0.84 | −0.109 | −4.4 | 0/10 | −0.100 / −0.117 |
| oi_footprint | 4,578 | 0.84 | −0.110 | −3.3 | 0/10 | −0.103 / −0.118 |
| breakout | 2,894 | 0.79 | −0.137 | −16.2 | 0/10 | −0.106 / −0.168 |

## Decision (pre-registered rule)
- **No strategy qualifies** (needed PF >= 1.2, mean R >= +0.05, both halves > 0, >= 6/10 symbols).
- 7 of 8 are negative **before fees**: the setup logic does not predict direction; this is not a cost problem.
- volatility_breakout is the only one with positive gross edge (+12 bp) and is break-even after costs — the only
  one worth redesign effort.
- The holdout (2026-07..10) was **not read**: it stays clean for any redesigned version.
- Consistent with live forensics and with E7/E8: the platform's edge cannot come from these strategies as
  implemented. XS-COMBO-V1 remains the only evidence-backed strategy.
