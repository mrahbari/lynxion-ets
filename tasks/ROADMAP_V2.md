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

### S2 follow-up 2 (2026-11-23): watcher logic review (E11) and XS-COMBO shadow funding
`docs/v2/reports/E11_watcher_logic_review_2026-11-23.md`. 8 watchers had implementation bugs (fixed, live). Re-test on a
fresh window (2026-03..06): no directional watcher has an edge after the fixes; Volatility forecasts next-hour vol
(rank corr ~0.6, all windows) -> candidate for risk sizing. XS-COMBO: BingX VST settles no funding (the strategy's
whole edge), so the daily run now books shadow funding at real BingX/Binance rates (`data/v2_live/tracking.csv`).

### S2 follow-up 3 (2026-11-23): Engine/Fusion review, role filters (E12), PROMUSDT re-entry fix
`docs/v2/reports/E12_engine_fusion_review_and_role_filters_2026-11-23.md`. Fusion runs per single interpreted signal
(direction rule unreachable, every fused signal NEUTRAL 0 %) and strategies ignore its output, so Engine/Fusion numbers
cannot change PnL; trades are decided by each strategy's own setups (E9: all negative). Watcher role filters on E9 trades:
1/79 DEV pass, fails holdout; only crowded-funding veto has a consistent (tiny) effect. No hyperopt run (nothing to fit).
Fixed: same-symbol re-entry between two reconciliation passes after an exchange stop (PROMUSDT A-B-A); entry now held
until the exit is booked.

### S2 follow-up 4 (2026-11-23) — E13 XS-COMBO leg risk, post-fix trades, false closures
- E13: no per-leg stop / equal-risk variant passes the pre-registered rule; XS-COMBO keeps the 50 % stop, risk is bounded by book size. Report `docs/v2/reports/E13_xs_combo_risk_and_false_closures_2026-11-23.md`.
- Post-fix trades: 17, +8.0 USDT; OIFootprint 7/7 SL (4 from pre-fix A-B-A re-entries). Too few to tune.
- Fixed: BingX VST empty position lists booked 12 open positions as UNKNOWN closures; exits now confirmed on consecutive passes (704c73c).
- Backlog: empty-list blips in exposure checks and the `get_position` duplicate guard.
- Symbol universe: `runner_sync_approved_symbols.py` now builds the venue's liquid universe daily (launchd 00:30 UTC, ccxt, follows `DEFAULT_BROKER`); old copy-all sync replaced. Ops: `docs/v2/LIVE_VST_OPERATIONS.md`.

## S4 working plan (agreed 2026-11-23): time-boxed, every task ends in a decision
Rules (no open-ended research): each task has a time box; it ends either with a fix running on VST or a
pre-registered pass/fail number; a task that cannot change what or how we trade is dropped.

| Week | Days | Task (time box) | Done when |
|---|---|---|---|
| W1 | 11-23 | E15-W0 fix: CANCELLED after measurement (Binance vs BingX/VST 1m closes differ 0.2-3.9 bp; not worth changing every strategy's input) | done |
| W1 | 11-24..26 | E15-W1..W9 watcher reviews (max half a day each; fix P1 only) | each watcher: verdict + P1 fixed |
| W1 | 11-27 | E13-2 XS-COMBO rebalance frequency / cost (1 day, offline, existing harness) | pass/fail vs live parameters; adopt only on pass |
| W1 | 11-29 | XS-COMBO 2nd rebalance (scheduled) | done |
| W2 | 11-30..12-02 | E15-F1 Fusion, E15-G1..G3 engines (max 1 day each) | verdict + P1 fixed |
| W2 | 12-03..05 | E15-S1..S3 live strategies, entry logic vs canonical definition + E11-4 signal-to-order latency (1 day each); re-run E9 for any fixed strategy (same rule) | per strategy: bug list, E9 rerun result |
| W2 | 12-06 | E9-1 XS-COMBO as the first portfolio strategy on platform infra (2 days, into W3) | weekly rebalance through the platform |
| W3 | 12-07..10 | E15-S4..S10 other strategies (half a day each; rerun E9 only if a bug is found) | verdicts |
| W3 | 12-07..13 | E13-3 OI factor (2 days); E6-3 universe threshold review; E14-3 decision from one week of shadow | pass/fail each |
| W4 | 12-14..17 | E15-X1..X4 execution/risk/reporting review; phase-2 fixes ranked by expected PnL impact | fixes live on VST |
| W4 | 12-18..20 | E12-3 final report + real-capital go/no-go package | operator decision |

Entry problem (gross edge ~0 R before costs, E9): handled inside the plan, not as separate research:
data venue (W0), entry logic per strategy vs its definition (S1..S10), signal-to-order latency (E11-4),
then E9 rerun of every changed strategy with the unchanged pass rule.

## S3 plan (agreed 2026-11-23): epics and tasks
Order: E6 -> E7 (parallel offline) -> E8 -> E9. Platform runs live on VST throughout; every position keeps a stop.

| ID | Task | Acceptance | Status |
|---|---|---|---|
| **E6** | **Tradable universe (best symbols only)** | | |
| E6-1 | Venue-agnostic daily liquid universe (5 M median 7d quote volume, >= 30 d), hot reload, discovery gate | 77 names, launchd 00:30 UTC | DONE (2026-11-23) |
| E6-2 | Verify first scheduled sync run + platform picks up the list without restart | log line + validator count | TODO (2026-11-24) |
| E6-3 | Threshold review after ~2 weeks of trades (per-band SL slippage, mean R) | report | TODO (~2026-12-07) |
| **E7** | **Meta-labeling (Lopez de Prado) as the standard Fusion/Engine** | | |
| E7-1 | Literature review: meta-labeling, signal fusion, calibration, purged/embargoed CV | `docs/v2/reports/E14_meta_labeling_2026-11-23.md` §1 | DONE |
| E7-2 | Pre-register E14: features = all watcher states per symbol at entry, model learned on DEV only, rule fixed before results | rule in script docstring, committed a54c372 before run | DONE |
| E7-3 | Run E14 on E9 trades (DEV 2025-11-01..2026-06-30, holdout 2026-07-01..10-31) | FAIL: OOF AUC 0.47-0.50, holdout lift -0.01 R | DONE |
| E7-4 | Decision: PASS -> refactor Fusion/Engine into the meta-label filter (same interfaces); FAIL -> keep interfaces, bypass in decision path | FAIL: kept as is, re-open when an input has AUC >= 0.55 | DONE |
| **E8** | **Execution cost: maker (limit) entries** | | |
| E8-1 | Offline: fill rate / adverse selection of a post-only entry at signal price on E9 trades (1m data) | PASS: +0.04 R/signal (+0.03 R edge-neutral), DEV and holdout; `E16_maker_entry_2026-11-23.md` | DONE |
| E8-2 | Maker entries on the platform | DROPPED 2026-11-23 (operator: keep market entries if too complex). Built and run on VST (2461d55..072eca4), then reverted: 4 live defects in 2 h (wrong service routing, 30 s pending-tracker expiry -> duplicate OKB/DOT entries, attached SL/TP not journaled -> PROTECTION_UNKNOWN, silent logs); VST book spread ~27 bp makes the prod cost gain unmeasurable there; strategies have no edge yet, so +0.04 R/signal does not change the verdict. Revisit only when a strategy is profitable | WON'T DO (for now) |
| **E9** | **Two strategy categories: single-symbol and portfolio** | | |
| E9-1 | Integrate XS-COMBO as the first "portfolio strategy" on platform infra (adapter, journal, Telegram, config, reconciliation), logic frozen | weekly rebalance runs through platform | TODO |
| E9-2 | Offline: XS-COMBO rank as a filter for single-symbol strategies (pre-registered on E9 trades) | FAIL: DEV lift +0.08 R (t 8) reverses in holdout (-0.02 R); `E15_xs_rank_filter_2026-11-23.md` | DONE |
| **E10** | **Slimming / cleanup (Fusion/Engine excluded until E7-4)** | | |
| E10-1 | Inventory of unused modules/files with evidence | list for operator approval | TODO |
| E10-2 | Delete only approved items | tests green vs baseline | GATED on operator |
| **E11** | **Ops hygiene** | | |
| E11-1 | VST empty-list blips in exposure checks and `get_position` duplicate guard | tests | TODO |
| E11-2 | Push branch `claude/edge-v2` (operator GitHub sign-in) | pushed | GATED on operator |
| E11-3 | Telegram trade messages name the real deciding component (strategy setup), not Fusion/Engine numbers that do not affect the trade. Note: `calculate_dynamic_metrics` (decision_pipeline.py) builds the displayed confidence partly from a hash of the symbol name and price, i.e. not a probability | message text + test | TODO |
| E11-4 | Signal-to-order latency measured from live logs (candidate -> order sent) | p50/p95 in report | TODO |
| E11-5 | Observe the closure debounce and the same-side cap on real events | log evidence | TODO (passive) |
| E11-7 | Triage the 24 remaining pre-existing test failures: fix config-drift expectations, investigate stop-path (14) and BingX LIMIT protection (2) failures, delete only tests with no use | DONE 2026-11-23: 0 failures, 1386 passed (11 obsolete removed, 24 stale tests fixed; no code defect) |
| E11-6 | Old backup copies in `data/approved-symbols/` (14 files): delete or keep | operator decision | DONE (deleted 2026-11-23, operator approved) |
| **E13** | **New edge inputs (profitability queue, each pre-registered, DEV then holdout)** | | |
| E13-1 | CVD (taker buy - sell volume) as an entry confirmation on E9 trades | FAIL: pooled lift ~0 R (t < 1) for 5/15/60 min, 0/48 DEV cells; `E17_cvd_confirmation_2026-11-23.md` | DONE |
| E13-2 | XS-COMBO rebalance frequency / turnover, cost-aware (= E3-3), the only measured edge | report | TODO |
| E13-3 | OI / long-short ratio metrics for the liquid subset (= E3-4) as a cross-sectional factor | report | TODO |
| E13-4 | Listing-age and regime conditioning (= E2-5, E2-6) | report | TODO |
| **E14** | **OBI/CVD confirmation: real data, then fail-closed (operator approved 2026-11-23, incl. OrderFlowWS change)** | | |
| E14-1 | Wire real order-flow into `DecisionPipeline.process_execution_intent` (today `latest_bar` never carries `obi_ratio`/`cvd`, defaults always pass): OrderFlowWS trade-flow imbalance (buy-sell)/total as CVD; OBI from the order book (BingX depth) if available | values present on every live intent, with timestamp | DONE (8f82cd8): `infrastructure/execution/orderflow_snapshot.py`, BingX depth top-20 + 5 min public trades, 60 s TTL |
| E14-2 | Shadow mode first: log per intent the confirmation verdict with real values, do not block; Telegram/journal unchanged | >= 1 week of verdicts vs trade outcomes | IN PROGRESS (live since 2026-11-23 17:32 UTC, log tag `ORDERFLOW_SHADOW`) |
| E14-3 | Fail-closed behind a flag: missing or stale (> N s) OBI/CVD -> no entry, logged with reason. Enable only after E14-2 shows coverage ~100 % and the confirmation does not cut winners (and E13-1 offline result) | unit tests; flag on in VST | GATED on E14-2 |
| **E15** | **Layer-by-layer baseline review (operator 2026-11-23): one component at a time, until every layer does its own job** | | |
| | Phase 1 = each component does its stated job correctly (role, live inputs, logic vs standard definition, no lookahead, reachable outputs, live output distribution, tests). Phase 2 (after all of phase 1) = fix quality gaps. Findings per component in `docs/v2/reviews/LAYER_REVIEW.md`. A defect that stops a component doing its job at all is fixed in phase 1; everything else is listed for phase 2. | | |
| E15-W0 | Watcher data feed (MonitoringAnalysisService): which bars/timeframes/funding/book each watcher receives, closed-bar only, freshness | DONE review: does its job; venue gap measured 0.2-3.9 bp (no switch); BingX-only symbols lag up to 5 min (P2); no trade feed (W6) | DONE |
| E15-W1 | Volatility watcher | does its job; P2: baseline overlap, no intraday seasonality, uncalibrated confidence, dead code | DONE |
| E15-W2 | TrendMTF watcher | P1 fixed: spurious regression t (72 % false trends on random walks) -> drift t, joint threshold calibrated to 5 % null rate | DONE |
| E15-W3 | FundingRate watcher | P1 fixed: per-period rate vs per-8h thresholds (4h contracts) -> 8h-normalised; 'normal' today is correct (calm market) | DONE |
| E15-W4 | MarketPulse watcher | P1 fixed: 33 % 'strong' labels on random walks -> vol-scaled 15m z-score + Wilder RSI (5 % null) | DONE |
| E15-W5 | Liquidity watcher | does its job; P2: absolute depth scale saturates (not relative to order size); role/engine mapping issues -> F1/G1 | DONE |
| E15-W6 | OrderFlowWS watcher (no trade feed: never emits) | P1 fixed: public trades now fed (reuses the E14 fetch); P2: 100-trade window, unscaled thresholds | DONE |
| E15-W7 | HistoricalCandle watcher | does its job (textbook patterns with ATR context on closed 15m); P2: re-emits the same pattern for 15 min, legacy code | DONE |
| E15-W8 | AnomalyML watcher | does its job (robust MAD z of last 1m bar); engine maps anomalies to contrarian BUY/SELL -> G1 | DONE |
| E15-W9 | Not live: CMC screener (off), Tick watcher: keep / retire | both retire candidates (E10) | DONE |
| E15-F1 | Fusion: input (one signal per call), weighting, direction rule, output contract vs strategies | P1 fixed: symbol-state fusion (all watchers' latest state, contract roles, regime from validated evidence); hierarchical path kept for replays | DONE |
| E15-G1 | EngineService (watcher -> fusion -> strategy routing, gates) | review | IN PROGRESS |
| E15-G2 | MarketStructureEngine / setup engine (levels the strategies use) | review | TODO |
| E15-G3 | MacroRegimeEngine / regime gate | review | TODO |
| E15-S1..S3 | Live strategies: TrendFollow, VWAPReversal, OIFootprint (each vs its canonical definition) | review x3 | TODO |
| E15-S4..S10 | Other strategies: breakout, donchian_breakout, liquidity, mean_reversion, mtf_trend, short_term_reversal, sweep_scalper | review x7 | TODO |
| E15-X1 | DecisionPipeline (confirmation, optimizer, SL/TP sanitizing, confidence) | review | TODO |
| E15-X2 | Orchestrator + execution (sizing, guards, order, journal) | review | TODO |
| E15-X3 | Risk: APM stop management, side cap, cooldowns, reconciliation | review | TODO |
| E15-X4 | Telegram / reporting (honest attribution) | review | TODO |
| **E16** | **Architect review: make every component better without losing what works (operator 2026-11-23)** | | |
| | Pass grade per component (all five): (1) declared contract: role, labels, horizon, claim; (2) correct and causal, unit-tested; (3) null calibration: non-neutral rate on a random walk documented and <= ~10 %; (4) validity: its claim holds on its own target out of sample (pre-registered, DEV then HOLDOUT once); (5) confidence calibrated (reported ~ empirical rate). Grade A = all five with a validated predictive claim; B = correct and calibrated but descriptive only (claim downgraded honestly, confidence = base rate); F = otherwise. Iterate designs on DEV only; HOLDOUT read once per final design. Never remove a working capability: new behaviour behind the same labels/interfaces, old paths kept until E10. | | |
| E16-W0 | Watcher validity harness: replay historical 1m bars through the live watcher classes exactly as the feed does, collect observations, score contract/null/validity/calibration | `e18_watcher_validity.py`, results `E18_watcher_validity.csv` | DONE |
| E16-W1..W8 | Grade and improve each watcher (Volatility, TrendMTF, FundingRate, MarketPulse, Liquidity, OrderFlowWS, HistoricalCandle, AnomalyML) until A or B | A: Volatility, AnomalyML (validated, calibrated). B: TrendMTF, MarketPulse, HistoricalCandle, FundingRate, Liquidity, OrderFlowWS (descriptive; directional confidence use decided in F1/G1) | DONE |
| E16-WB | Watcher base design: contract attributes, as-of bar time and warm-up flag in metadata, calibrated confidence hook (non-breaking) | contract + as-of stamped on every observation; base analyze applied to all watchers | DONE |
| E16-F/G/S/X | Same method for Fusion, Engines, Strategies, Execution/Risk after E15 phase 1 of each layer | grades | TODO |
| **E12** | **Live validation and go/no-go (VST until ~2026-12-22)** | | |
| E12-1 | Single-symbol strategies: live vs E9 backtest parity per strategy (stop R, TP R, duration, slippage, fees) | weekly report | TODO |
| E12-2 | XS-COMBO: live vs model tracking (= E5-3) | weekly report | IN PROGRESS |
| E12-3 | Final report + real-capital go/no-go package (sizing, limits, kill switch) | report; decision by operator (E5-4) | TODO (~2026-12-20) |

## Backlog (deferred, not scheduled)
- **Maker (post-only limit) entries** (E8-1 PASS offline, E8-2 dropped; revisit once a strategy has edge). Lesson: PendingOrdersTracker expires holds after 30 s. Entries are always MARKET today; the pipeline already computes a maker
  price + POST_ONLY that the orchestrator discards. Expected gain only ~0.02-0.03 R/trade (taker 0.05 % vs maker
  0.02 % on a ~201 USDT / 2.58 USDT-risk median trade: 0.078 R -> 0.055 R; with maker TP 0.045 R) against a
  ~-0.10 R base. Needs a resting-order lifecycle (timeout cancel, partial fill + SL, exposure counting) and risks
  adverse selection (winners don't fill). Revisit after the symbol-universe change is measured.
- **Approved-symbols refresh interval.** Daily 00:30 UTC (rule uses 7 completed daily candles; more often adds
  nothing). Revisit only if the list churns too much (then weekly) or misses fast-rising names.
  Operator idea (2026-11-23): refresh after the London and New York sessions. 00:30 UTC already runs after the
  NY close and the daily candle; a post-London run only helps if the rule used intraday (rolling 24h hourly)
  volume, not a 7-day median of daily candles. Test that variant only if fast-rising names are being missed.
- **Universe threshold.** 5 M USDT median 7-day quote volume (77 BingX names; 10 M gave 47). Compare per-band SL
  slippage and mean R after ~2 weeks of trades.
- **CMC screener watcher off** (`CMC_SCREENER_ENABLED=false` in .env, 2026-11-23): duplicate trigger, not used
  in trade decisions. Re-enable only with evidence of a role.
- **Same-side cap** now enforced (2026-11-23): `SafetyConfig.max_long/short_positions` (15 / 15 in the live
  settings) was loaded but never checked. Kept at 15: post-fix maximum seen was 9 longs, so it does not reduce the
  sample; it only stops a correlated pile-up. Lower it only if same-side clusters dominate losses.
- Empty-list blips (BingX VST) in exposure checks and the `get_position` duplicate guard.
- Orchestrator LIQUIDITY DEPTH GUARD never runs: it calls `broker.fetch_order_book`, which no broker implements (found 2026-11-23).
