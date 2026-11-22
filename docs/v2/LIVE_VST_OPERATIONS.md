# XS-COMBO-V1 forward test on BingX VST — operations

Started 2026-11-22 01:00 UTC. Book: 20,000 VST gross (10k long / 10k short), 20 + 20 names, leverage 1x,
weekly rebalance (every 7 days), daily equity report to Telegram.

| Action | Command (from repo root) |
|---|---|
| Install daily job (02:15 local) | `cp research/v2/live/com.lynxion.v2.xs-combo.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.lynxion.v2.xs-combo.plist` |
| Run manually (report + rebalance if due) | `cd research/v2 && python3 -m live.rebalancer --mode auto` |
| Dry-run a rebalance | `cd research/v2 && python3 -m live.rebalancer --mode rebalance --dry-run` |
| Emergency stop (blocks all orders) | `touch data/v2_live/STOP` |
| Remove the daily job | `launchctl unload ~/Library/LaunchAgents/com.lynxion.v2.xs-combo.plist` |

Files: `data/v2_live/orders.jsonl` (every order + exchange response), `equity.csv`, `targets/<date>.json`, `state.json`.
Host is hard-coded to `open-api-vst.bingx.com` (demo); this code cannot trade real funds.

Evaluation plan: after 8–12 weeks compare weekly VST returns to the backtest's expected
(~+0.5%/week on the book, weekly vol ~3%); decision on real capital only after that, with operator approval.
The old runner (`run_trading_system.py`) must not run on the same account at the same time.

## Update 2026-11-22: sizing, stops, notifications
- Sizing comes from the platform `.env`: gross book = `RISK_VST_MAX_PORTFOLIO_NOTIONAL_USDT` (3,200 → ~80 USDT per name),
  per-order cap = `MAX_ORDER_NOTIONAL_AMOUNT`, max names = `MAX_TOTAL_POSITIONS`. `--book` overrides for one run.
- Every position side gets an exchange-side `STOP_MARKET` (closePosition, mark price) at 50% from entry
  (`V2_STOP_LOSS_PCT`, default 50). Tighter stops destroy this strategy in the dev period
  (`docs/v2/reports/E5_stop_check_dev.csv`: 35% → SR 1.42, 25% → 0.85 vs 1.94 none; 50% → 1.79 with lower max DD).
  The daily run re-checks and repairs stops and cancels orphan stops; names closed since the last rebalance are reported.
- Telegram: one message per order (OPEN/ADD, REDUCE, CLOSE, with errors) plus the daily summary.
- Scheduler installed 2026-11-22: `launchctl list | grep com.lynxion.v2.xs-combo`.
- 2026-11-22: XS-COMBO positions also get a 40% TAKE_PROFIT_MARKET (`V2_TAKE_PROFIT_PCT`). Dev check with TP from
  day 2 (`E5_tp_check_dev_skipday1.csv`): none SR 1.79 / max DD -16.6%; 40% SR 1.98 / -10.9%; 30% SR 1.79 / -10.8%;
  20% SR 1.11. Tight TPs cut the weekly carry winners; wide TPs only bank extreme spikes.

## Update 2026-11-22 (evening): platform stop management, strategy data, exit reporting
- **Strategy candles (P0):** each strategy now prices a symbol from that symbol's own candles, reloaded every
  `STRATEGY_BUFFER_REFRESH_SECONDS` (60). Before this fix one stale buffer priced every symbol, so live
  platform trades before 2026-11-22 ~20:00 local are not evidence for or against TrendFollow/VWAPReversal/OIFootprint.
  Intents whose stop is on the wrong side of the live price (or >25% away) are rejected (`STRATEGY_LEVELS_INCONSISTENT`).
- **Dynamic stops (`APM_STOP_MODE=r`, default):** R = the position's initial stop distance. Breakeven +0.15% at 1.5R,
  then trail 1.5R behind the best price after 2R; ratchet-only, steps ≥0.25R, ≤1 amendment/60s.
  Knobs: `APM_BE_TRIGGER_R`, `APM_BE_BUFFER_PCT`, `APM_TRAIL_AFTER_R`, `APM_TRAIL_DISTANCE_R`, `APM_MIN_STEP_R`,
  `APM_MIN_AMEND_SECONDS`, `APM_DEFAULT_RISK_PCT`; `APM_STOP_MODE=legacy` restores the old ROE rules.
  Evidence: `docs/v2/reports/E7_exit_policy_replay_2026-11-22.md`.
- **Exit alerts:** the closing order is searched from the time the position was last seen open (BingX returns the
  oldest page first), and the trade-journal collector polls every `TRADE_JOURNAL_POLL_SECONDS` (300) so it no longer
  trips BingX's allOrders ban (100410), which used to turn exits into "UNKNOWN — closing order not identified".
