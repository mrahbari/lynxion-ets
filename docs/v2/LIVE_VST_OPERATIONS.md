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

## Platform symbol universe (approved symbols), since 2026-11-23
`approved_symbols.json` is the platform's symbol gate: execution, runtime discovery (including
`EXTRA_WATCHLIST_SYMBOLS`) and data availability only use symbols on it. It is rebuilt daily from the
execution venue's own liquidity by the approved-symbols sync (it replaces the old copy-every-contract sync).

| Action | Command (from repo root) |
|---|---|
| Install daily job (00:30 UTC) | `cp scripts/launchd/com.lynxion.approved-symbols-sync.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.lynxion.approved-symbols-sync.plist` |
| Run now / preview without writing | `python3 interface/cli/sync_approved_symbols.py` / `... --dry-run` |
| Remove the daily job | `launchctl unload ~/Library/LaunchAgents/com.lynxion.approved-symbols-sync.plist` |

Rule: linear USDT perpetual, active, not a stablecoin, >= 30 completed daily candles, median daily quote volume of
the last 7 completed days >= 5 M USDT (10 M gave 47 BingX names, 5 M gives 77: more trades to measure, the < 2 M names that produced gap stops stay out); symbols with an open platform position are always kept. Env overrides:
`UNIVERSE_MIN_MEDIAN_QUOTE_VOLUME_USDT`, `UNIVERSE_MIN_LISTING_DAYS`.
Output: `application/configs/approved_symbols.json` and `data/approved-symbols/approved_symbols.json` (same list,
one per reader), `data/approved-symbols/universe_report.json` (why each symbol passed or failed), log
`logs/approved_symbols_sync.log`. The running platform hot-reloads the list; no restart needed.
Failure safety: if the venue cannot be read or fewer than 20 symbols pass, the previous list is kept.

Exchange migration: the venue is `UNIVERSE_EXCHANGE`, else `DEFAULT_BROKER` (any ccxt id). Switching the platform's
`DEFAULT_BROKER` switches the universe on the next run, no code change (checked 2026-11-23 at 10 M: bingx 47, binance 176,
mexc 71 symbols). Symbol names are the venue's contract id without separators (BTC-USDT / BTC_USDT -> BTCUSDT),
which is the platform's internal format. Run the sync once by hand right after a switch.

## R5 degradation monitor (since 2026-11-25)

The daily job ends with `live/monitor.py` (read-only). It appends `data/v2_live/monitor.csv`, keeps
`monitor_state.json`, and adds an "R5 monitor" block to the daily Telegram report. Statuses: OK / WARN (backtest p10) /
ALERT (p2.5) for validated alarms; INFO for return, drawdown and beta (not validated as alarms); NA while the live
sample is short (realized carry needs 28 days). It never acts: WARN/ALERT lines carry a review proposal for the
operator only. Thresholds: `research/v2/results/xs_combo_monitor_thresholds.json` (rebuild with
`experiments/e38_xs_combo_monitor_baseline.py`). Details: `docs/v2/reports/R5_xs_combo_degradation_monitor_2026-11-25.md`.

## Coins overview scanner (since 2026-11-25, information only)

`research/v2/live/scanner.py`, LaunchAgent `com.lynxion.v2.scanner` (every 4 h, 3 minutes after the 4h close:
01/05/09/13/17/21 local, UTC+1). Telegram: sentiment / confidence / energy, market regime (BTC vs EMA50d, breadth,
median funding), top 7 longs and 7 shorts (score -50..+50, strength / momentum / short-term dots, extension and
funding flags) with a mechanical limit and stop per coin. Universe: Binance perps also listed on BingX, 30-day median
volume >= $10M (not limited to the approved list). Not a watcher: it never feeds the engine or places orders;
cross-sectional trend ranking has no proven edge (E2). Every run is logged to `data/v2_live/scanner_log.jsonl` for
forward evaluation. Stop: `launchctl bootout gui/$(id -u)/com.lynxion.v2.scanner`.

Radar additions (2026-11-25): coins already held by the platform or the XS-COMBO sleeve are marked "in position";
stops wider than 8 % are marked "wide SL". R25 shadow: each run also logs the E42 variant-B short list to
`data/v2_live/radar_shadow_b_short.jsonl` (never shown in Telegram, never used by the Radar ranking); evaluation rule
pre-registered in `docs/v2/reports/E42_radar_timing_2026-11-25.md`.

## Research shadows (log only, never trade)

- R25 Radar B-short: inside the Radar run -> `data/v2_live/radar_shadow_b_short.jsonl`.
- R28 XS-COMBO + retail fade: inside the weekly rebalance -> `data/v2_live/shadow_r28/<date>.json`.
- R31 unlock shorts: LaunchAgent `com.lynxion.v2.unlock-shadow` (03:30 local daily) -> `data/v2_live/unlock_shadow.jsonl`;
  evaluation `research/v2/experiments/r31_unlock_shadow_eval.py` (counts only until 40 events or 2027-06-30).
Pre-registrations: `docs/v2/reports/E42_radar_timing_2026-11-25.md`, `R28_retail_fade_shadow_prereg_2026-11-26.md`,
`R31_unlock_shadow_prereg_2026-11-26.md`.
