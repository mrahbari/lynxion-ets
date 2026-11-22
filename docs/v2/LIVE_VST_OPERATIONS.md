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
