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
