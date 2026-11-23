# Lynxion v2 — Edge Discovery Roadmap (Claude, started 2026-11-22)

Codex-era tasks (task0077–task0457 and older) are archived under `tasks/archive/codex-2026/`.
They are reference only; their negative results tell us where NOT to search
(six majors, 15m–24h horizons, taker execution). v2 starts from a different premise.

## Thesis

Crypto edges that survive costs are most likely **cross-sectional** (ranking hundreds of
symbols against each other), at **hourly-to-weekly horizons** with controlled turnover,
built from **price, volume, funding, basis/premium, OI** on the **full Binance USDT-M universe
including delisted symbols**. Single-symbol, short-horizon taker strategies on BTC/ETH were
exhaustively negative and are out of scope.

## Ground rules (lightweight, but strict where it matters)

1. Data: Binance public archives (`data.binance.vision`), checksum-verified. Execution: BingX.
2. Point-in-time: a bar is usable only after it closes; universe membership uses only past data;
   delisted symbols stay in the sample until delisting (no survivorship bias).
3. Splits — fixed now, before any result:
   - **Development:** 2020-01-01 → 2024-12-31 (all research, walk-forward inside it).
   - **Sealed holdout:** 2025-01-01 → 2026-10-31. Opened **once** per surviving strategy in EPIC-4.
   - **Forward:** live paper on BingX VST after EPIC-4.
4. Costs always on: fee 5 bp/side (taker) + liquidity-bucket slippage + actual funding.
   Stress test at 2x costs.
5. Every backtest run is logged automatically in a trial registry; significance uses the
   Deflated Sharpe Ratio over the *actual* number of trials (multiple-testing control by math,
   not by banning data reuse).
6. A strategy "survives" development only if: DSR p<0.05, positive net Sharpe in ≥ 4/5
   development years, net of 2x costs still positive, no single symbol > 10% of PnL.
7. No hourly checkpoint docs. One short report per finished task in `docs/v2/reports/`.

## EPICs and tasks

| ID | Task | Acceptance | Status |
|---|---|---|---|
| **E0** | **Foundation** | | |
| E0-1 | Archive Codex tasks, new branch `claude/edge-v2` | tasks archived, roadmap written | DONE |
| E0-2 | Retire journal epoch 1 (operator: no open BingX trades) | archive + hashes + disposition, clean journal | DONE |
| E0-3 | Telegram self-test tool | `scripts/telegram_selftest.py` passes | DONE (2026-11-22) |
| E0-4 | Full-universe data lake: 1h klines, funding, premium index | ~923 symbols, checksums OK, manifest | DONE (1.8 GB) |
| E0-5 | Renew BingX VST API keys | signed GET returns code 0 | DONE (account flat) |
| **E1** | **Research harness** | | |
| E1-1 | Panel builder: PIT universe, returns, funding, premium, liquidity buckets | unit tests for lag/alignment | DONE |
| E1-2 | Cross-sectional portfolio backtester (weights → net PnL with fees, slippage, funding, turnover) | hand-computed test cases match | DONE |
| E1-3 | Trial registry + Deflated Sharpe + yearly / symbol-concentration stats | every run logged | DONE |
| E1-4 | Anti-lookahead guards: shuffled-signal null, +1 bar shift test | null Sharpe ≈ 0 | DONE |
| **E2** | **Factor wave 1 (dev period only)** | | |
| E2-1 | Momentum / reversal (1d, 3d, 1w, 4w lookbacks) | report | DONE |
| E2-2 | Funding carry (level, change) | report | DONE |
| E2-3 | Premium/basis level & change | report | DONE |
| E2-4 | Volatility / beta / idiosyncratic vol, liquidity (Amihud), volume shocks | report | DONE |
| E2-5 | Listing-age effects (new listings, pre-delisting) | report | TODO |
| E2-6 | Regime conditioning (BTC trend / market vol) of survivors | report | TODO |
| **E3** | **Combination & ML** | | |
| E3-1 | Multi-factor linear combination of survivors (walk-forward weights) | report | DONE |
| E3-2 | Gradient-boosting cross-sectional ranker (walk-forward, purged) vs linear | report | TODO |
| E3-3 | Turnover / rebalance-frequency optimisation (cost-aware) | report | TODO |
| E3-4 | OI / long-short ratio metrics for liquid subset (download `metrics`) | report | TODO |
| **E4** | **Holdout verdict** | | |
| E4-1 | Freeze final candidates (code hash + params) | frozen file | DONE |
| E4-2 | Open holdout once; verdict EDGE / NO EDGE | report | DONE |
| E4-3 | Capacity & BingX tradability (symbol overlap, min size, fees) | report | DONE |
| **E5** | **Execution on BingX (only if E4 = EDGE)** | | |
| E5-1 | Lean portfolio rebalancer (target weights → orders), rate-limit aware | first VST rebalance 39/40 | DONE (2026-11-22) |
| E5-1b | Sizing from platform .env (`RISK_VST_MAX_PORTFOLIO_NOTIONAL_USDT`, `MAX_ORDER_NOTIONAL_AMOUNT`, `MAX_TOTAL_POSITIONS`) | book resized to 3,200 | DONE (2026-11-22) |
| E5-1c | Exchange-side disaster stop on every position (50%, dev check `docs/v2/reports/E5_stop_check_dev.csv`), daily repair | all positions protected | DONE (2026-11-22) |
| E5-2 | Telegram: one message per trade + daily summary | messages received | DONE (2026-11-22) |
| E5-2b | Daily launchd job `com.lynxion.v2.xs-combo` (02:15 local) | loaded | DONE (2026-11-22) |
| E5-3 | Forward paper on VST, live-vs-model tracking report | weekly report | IN PROGRESS |
| E5-4 | Real-capital decision | operator approval | GATED |

## Sprint plan — 4 weeks (VST account usable only until ~2026-12-22)

Principle: less offline testing, more live VST trading. Offline work is limited to quick
dev-period checks that decide whether a candidate goes live. Every live position has a stop.
Note: 4 weeks of live data cannot statistically prove a Sharpe ~1 edge; it validates
execution realism (fills, slippage, funding received vs model, tracking error, operations).

| Week | Dates | Tasks | Done when |
|---|---|---|---|
| W1 | 11-22 → 11-29 | E5-1b/1c/2/2b (done 11-22). S0 (11-24 → 11-26): review the 10 platform strategies (VWAP reversal, MTF trend, Donchian/breakout, trend-follow, mean-reversion, sweep scalper, liquidity, short-term reversal, OI footprint) through the platform backtest engine on the liquid wide universe (not 6 majors), with costs; keep/kill each. S1: live-vs-model tracking report (daily, auto). S2: quick dev checks of edge-2 candidates — B1 funding-only daily carry, B2 OI / long-short ratio (download `metrics` for liquid subset), B3 listing-age, B4 (operator idea) separate strategy, own sleeve/ledger/Telegram tag: momentum entries on liquid names, LONG strong / SHORT weak, ATR/trailing stop; judged beta-adjusted and vs buy-and-hold. 2nd rebalance 11-29. | tracking report runs; best candidate chosen |
| W2 | 11-30 → 12-06 | S3: best candidate live on VST as a 2nd sleeve (net target weights, per-sleeve model ledger, stops). S4: risk guard — per-name cap + extreme-funding exit. | 2 sleeves trading |
| W3 | 12-07 → 12-13 | S5: mid-sprint review: slippage/funding vs model, stop hits, tracking error; kill or keep each sleeve. | review report |
| W4 | 12-14 → 12-20 | S6: final report + real-capital go/no-go package (sizing, limits, kill switch). | report; E5-4 decision by operator |

## Out of scope (explicitly)

Existing intraday strategies (VWAPReversal, trend_following, …; PF 0.21 on 418 trades),
Codex cohorts C-11/C-33/C-35, microstructure collectors, investor-release track.

## Results log
- 2026-11-22: XS-COMBO-V1 holdout PASS (Binance SR 1.39; BingX SR 0.96). See docs/v2/reports/E2_E4_RESULTS_2026-11-22.md
- 2026-11-22: R22 extreme movers (operator idea) REJECTED on dev (best PF 1.05, SR 0.19; shorts PF 0.69). docs/v2/reports/R22_extreme_movers_dev_2026-11-22.md
- 2026-11-22: VST book resized to .env cap (3,200 gross), 50% disaster stops, per-trade Telegram, daily launchd installed.

## S1 — platform strategies tested ONE AT A TIME on VST (started 2026-11-22 22:16 local)
Why: every strategy was disabled on evidence produced while all of them priced entries from one stale,
foreign-symbol candle buffer (fixed 1f3028a). Historical per-strategy PF (e.g. VWAPReversal 0.16, MTFTrend
0.35, TrendFollow 1.64) is therefore not evidence either way. Only post-fix trades count.

Operator decision: test strategies one by one, not all together. `scripts/s1_strategy_rotation.py`
(launchd `com.lynxion.s1-rotation`, hourly) runs one strategy alone until 40 closed trades or 48h, sends
its result to Telegram, switches `STRATEGY_ALLOWLIST` and restarts the runner via the safe launcher.
Order: VWAPReversal, OIFootprint, TrendFollow, MeanReversion, MTFTrend, SweepScalper, Breakout,
volatility_breakout, Liquidity (<= 18 days). crypto_breakout excluded. Progress: `--status`.

Pre-registered decision rule (fixed before any results; 9 strategies tested):
- Per strategy, only trades entered during its own window, journal label, net of fees.
- Candidate edge only if: n >= 40 closed trades, PF >= 1.3, mean PnL > 0, and positive in both halves
  of its own time-ordered trades. Report the number of strategies tested (9) next to any winner.
- A window that ends at 48h with < 40 trades is "inconclusive", not a pass.
- Survivors get a second, combined VST run before any real-capital discussion.

## S1 update (2026-11-22 23:00): live one-at-a-time rotation stopped
Operator decision: a 48h live window per strategy sees one regime (Monday open after a sell-off) and ~40 trades —
mostly noise. Strategy selection moves to long offline backtests (S2); VST keeps running the normal allowlist
(TrendFollow, VWAPReversal, OIFootprint) to validate execution realism.

## S2 — per-strategy long backtest (E9), pre-registered rule (fixed before any results)
Script `research/v2/experiments/e9_strategy_backtest.py`. 8 strategies tested alone (sweep_scalper excluded: 1m
design TF too slow for a year; crypto_breakout = breakout alias). 10 liquid perps, design timeframe, live-equivalent
execution (next-bar entry, sanitized SL/TP, R-mode APM, SL-first, fees+slippage).
- DEV 2025-11-01..2026-06-30 decides candidates: trades >= 100, PF >= 1.2, mean R >= +0.05, both halves of its
  dev trades > 0, and >= 6/10 symbols positive.
- HOLDOUT 2026-07-01..2026-10-31 confirms, read once: mean R > 0 and PF >= 1.1. Report "8 strategies tested".
- Only candidates that pass both go to a VST run; everything else is documented as no-edge (as implemented).

### S2 result (2026-11-23): no platform strategy passes; holdout untouched
See `docs/v2/reports/E9_strategy_backtest_2026-11-23.md`. All 8 fail on DEV (PF 0.79–1.01); 7/8 negative before
fees. volatility_breakout (+12 bp gross) is the only redesign candidate. Holdout 2026-07..10 kept unread.

### S2 follow-up (2026-11-23): TrendMTF fixed; volatility_breakout redesign fails DEV
See `docs/v2/reports/E10_trend_mtf_fix_and_vol_breakout_redesign_2026-11-23.md`. TrendMTF was not multi-timeframe
(5/15/30 samples of 1m bars); now real closed 15m/1h/4h bars. It works (48x more signals) but has no OOS edge
(4h: dev +20 bp t 1.4, validation -12 bp). volatility_breakout: 4 pre-registered variants (squeeze / Donchian,
15m/1h/4h, HTF trend filter, ATR stops) all fail DEV (PF 0.84-0.96, ~0 gross); no holdout read; strategy stays off.
