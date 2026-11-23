# E12 — Engine / Fusion logic review, watcher role filters, PROMUSDT re-entry incident (2026-11-23)

## 1. PROMUSDT double BUY (incident, fixed)
Exchange history (BingX VST, PROM-USDT):

| time (local) | order | result |
|---|---|---|
| 11:22:48 | BUY 37.81 @ 5.306 (OIFootprint), SL 5.252 / TP 5.430 | filled |
| 11:23:50 | STOP_MARKET SELL 37.81 @ 5.249 | **SL hit, -2.16** |
| 11:24:03 | BUY 38.29 @ 5.254 (OIFootprint, new setup) | filled 13 s after the stop |
| 11:29:12 | STOP_MARKET SELL 38.29 @ 5.168 | SL hit, -3.29 |

The second BUY was not a pyramid: the first position had already been stopped out. Root cause:
position closures are detected only by diffing reconciliation snapshots (60 s cadence). The stop-out
and the re-entry both fell between two passes, so the next snapshot still showed "PROMUSDT LONG"
(A-B-A). The first exit was never processed: no loss cooldown (60 min) before the re-entry, no
"POSITION CLOSED" Telegram, journal identity mismatch for the second close. The same-symbol duplicate
guard was correct (the exchange really was flat at 11:24:00).

Fix (`infrastructure/execution/broker_reconciliation.py`, `infrastructure/services/broker_execution_service.py`):
the reconciler publishes the symbols it last saw open; an entry for a symbol that the last pass saw open
but the broker now shows flat is held ("ENTRY HELD") until the next pass books that exit (cooldown,
trade result, notification). Cost: an entry after a TP exit can wait up to 60 s. Residual gap: an
entry, stop-out and re-entry all inside one 60 s window (the reconciler never saw the first position).
Tests: `tests/unit/test_unreconciled_exit_entry_hold.py`.

## 2. Engine / Fusion review — what actually decides a live trade
| finding | evidence | consequence |
|---|---|---|
| Fusion is called with ONE interpreted signal at a time | `event_system._process_interpreted_signal`: `fuse_signals([signal])`; hierarchical fusion is stateless per call | the DIRECTION rule "≥ 2 aligned direction observations" can never be met; every fused signal is NEUTRAL / NONE, confidence 0 % (PROMUSDT log: 7 fusions, all `no_direction_observations`) |
| Strategies ignore the fused direction and confidence | `StrategyManager.evaluate_fused_signal` → each adapter scans its own setups on its own OHLC buffer; fused signal only (a) triggers evaluation of the symbol and (b) its single-watcher `regime_context` scales the ranking 0.7–1.2 | watchers / Engine / Fusion do not choose side or veto entries. The PROMUSDT BUY came from OIFootprint with fused confidence 0 %. Telegram "Watcher: OrderFlowWSWatcher" is a label, not a contributor (orderflow_ws produced no observation) |
| Liquidity is classified as a DIRECTION watcher | `watcher_classifier.WATCHER_ROLE_MAPPING` | liquidity has no side; only trend_mtf + historical_candle could ever align, and their conditions (aligned 15m/1h/4h trend vs. a reversal against the prior 15m trend) nearly exclude each other |
| Execution confirmation is a no-op on OHLC buffers | `decision_pipeline.process_execution_intent`: missing `obi_ratio` / `cvd` default to values that confirm the setup's side | OBI/CVD "confirmation" passes every setup |
| Engine HOLD states | normal volatility (value 0 < 0.3) and liquidity ≤ 0.7 map to HOLD | no effect (fusion direction unused) |
| ConfidenceThresholds 0.45–0.70 | hand-set per watcher | gate only fusion inputs, which do not reach the trade decision |

Conclusion: tuning Engine / Fusion numbers (thresholds, weights, the 46 "lowered" constants there)
cannot change PnL today, because their output is not used for side or veto. The numbers that do decide
trades are each strategy's own setup and SL/TP parameters, and E9 already showed all 8 strategies negative
before fees on DEV and holdout. Not changed (Rule 6 / out of scope): making Fusion aggregate across
watchers would be an architecture change, and E11 shows its inputs carry no directional edge, so it
would combine noise.

## 3. Watchers in their own role (filter / veto) on the strategies' real trades
Script `research/v2/experiments/e12_watcher_role_filters.py`, rules pre-registered in its docstring. 8 strategies x
4 watcher filters (vol regime, 1h+4h trend alignment, crowded funding, 24h pulse) = 79 cells.

- **DEV passes: 1 of 79** (mean_reversion when the 24h move agrees with the trade side: n 352, mean R +0.10, PF 1.21).
  **Holdout: fails** (n 126, mean R -0.05, PF 0.93). One pass in 79 is about what chance gives.
- Pooled role value (lift in mean R vs the strategy's own average, all strategies, DEV):

| filter state | n | lift R | t |
|---|---|---|---|
| funding crowded (trade on the side that pays, abs rate >= 0.01 %) | 2,855 | **-0.052** | -2.26 |
| trend "with" (1h and 4h trend agree with the trade) | 4,857 | **-0.043** | -2.39 |
| volatility compression / expansion / normal | — | -0.007 / +0.001 / +0.003 | ≤ 0.5 |
| 24h pulse with / against | — | 0.000 | 0.0 |

- Funding as a veto (skip trades on the crowded side) is the only role effect with a consistent sign; it
  affects 10 % of trades and moves the average by about +0.005 R — far too small to rescue a -0.10 R base.
  Volatility regime separates nothing at the trade level (stops are already ATR/structure-scaled, so
  vol sizing is implicit). Trend-aligned entries are worse, not better.

## 4. Optimization decision
Per the plan, parameter optimization runs only where a component shows a baseline signal. None of the
directional watchers (E11), strategies (E9/E10) or role filters (E12) does, so no hyperopt was run: on
these components it would fit noise (E8 HistoricalCandle +20 bp → gone OOS; E10 DEV +12 bp → holdout -18 bp).
The only measured edge remains XS-COMBO-V1 (funding carry), tracked with the shadow-funding ledger.

Backlog (not done, out of scope): fail-closed OBI/CVD confirmation; Fusion role map (liquidity is not DIRECTION);
honest Telegram attribution (strategy setup, not "watcher").
