# Directional Engine signal study V1 — scientific checkpoint

**Result: `PREDICTIVE_NOT_SUPPORTED` for this frozen Level-1 question. Economic/after-cost Edge: `NOT_TESTED`.** Do not create V2 or tune this cohort based on these outcomes. This result does not imply `NO_EDGE` for Lynxion, an executable strategy failure, or negative after-cost PnL.

## Frozen identities and release evidence

- New-generation preregistration committed **before outcomes** in `6321f0b`, SHA-256 `28e2224f640fb7c61765cedbc9a7d784b75d4ffee8eb9022a50173860147b206`. Reproducible outcome evaluator committed pre-run in `b715fe7`. Parent candle capture manifest SHA-256 `4832beedbbddb4ea55da8882994cb7497f77298003f09e9642046331e8533ffb`, qualification manifest SHA-256 `2c119868cf0c839ebb934557b1faac8b2771eae722f6cce2c8a8239e2f868775`.
- Boundary: actual `TrendMTFWatcher` rolling single-timeframe close windows → `EngineService` `InterpretedSignal`; one closed 1h candle per symbol per event. No Fusion, Strategy, ExecutionIntent, simulated fill or portfolio sizing. First directional event per symbol/UTC 4h block, no confidence filter. Selected trace SHA-256 `d5f836229267d36d0f9ec62fa10281877618daf3d0ea939d40f2627688fdb54f` matches pre-outcome freeze; full trace SHA-256 `e6efa4b9625812dbb864187b6ee87b5e87b939cc1729f040e092fe9b12c25126`.
- Causal source validates raw file hashes, UTC open/close-time, 1h contiguity, OHLCV and completed availability. Fresh per-symbol/run watcher, controlled close-time clock, memory forensic sink and actual Engine logic. Repeated normalized traces and June 8/18/28 prefix cuts passed before outcomes. No OBI/CVD/BBO is supplied to this path. The old candle-reversal/Fusion study stays closed with its own 0-direction result and **no old-study outcomes opened**.
- Outcome script run twice after preregistration; both normalized JSON results SHA-256 `9792b9759f7baada0ac0c83517974f140579ae71f08f210f6aacf5bc4790a562`. Eligible event outcome rows SHA-256 `163f0d1b0cf34eae0b0e52e308b500f874a3c66170734b8addaac005bb09a8eb`.

## Frozen primary and descriptive results

Evaluation Engine events: **BUY 139, SELL 278, NEUTRAL 923**, total 1,340. First-per-symbol/4h selection: **163** (BTC 73, ETH 90); two June 30 23:00 SELL events censored for unavailable within-window +4h closes; **161 eligible** (BTC 72, ETH 89). Required >=100 and >=20 UTC event days per symbol remain satisfied. These are predictive labels from later completed closes, **not executable fills**.

| Frozen 4h side-adjusted gross close-to-close statistic | Value |
|---|---:|
| Pooled N | 161 |
| Mean | -0.001015936740 (-0.1016%) |
| Median | -0.003136703319 (-0.3137%) |
| Sample standard deviation | 0.013308974160 |
| 95% UTC-day-block bootstrap percentile interval, 10,000 draws, seed 20260926 | [-0.004156362604, 0.002108991689] |
| Secondary descriptive 1h mean (same eligible set) | -0.000728356858 |

The interval includes zero and its lower bound is not positive. Thus the preregistered positive-predictive-support criterion **fails**. The interval also spans positive values, so it does not establish a stable negative predictive effect. No independent symbol, week or 1h discovery claim is made.

Descriptive 4h means: BTC (N=72) -0.001650230828; ETH (N=89) -0.000502799950. UTC ISO weeks: W23 N50 +0.005371442968; W24 N36 -0.004830930245; W25 N33 -0.001985160196; W26 N37 -0.004266926409; W27 N5 -0.006967582217. Leave-one-week-out pooled means for omitted W23/W24/W25/W26/W27 are respectively -0.003893134806, +0.000082781389, -0.000766058818, -0.000045883371, -0.000825178872. These are robustness descriptions only. The week sensitivity and small terminal week counsel against a strong directional conclusion beyond the frozen criterion.

## Economic and production limits

The signal exists only at bar completion. Its same-bar close is not an attainable execution fill by assumption. There is no defensible historical bid/ask, spread, slippage, fee/funding and order timing model at this Engine boundary. Therefore **no after-cost Edge, PnL, win rate, Profit Factor or profitability conclusion was calculated**. No Fusion/Strategy/Live parity, position sizing or broker safety claim follows. Historical XMR cause and broker retry remain unresolved. No C-11/C-33/C-35/Compression/Phase3A definition was modified.

## Verification and preservation

Focused watcher/causal-source/semantic-lineage tests: 10 PASS / 0 FAIL before outcome run; an expanded earlier archived-route invocation was interrupted after 3 passes and is not represented as a passing suite. Post-run repeated evaluator output matched byte-for-byte. Protected production `active_positions_journal`, `sl_cooldown_journal`, `live_order_journal`, and `trade_journal` SHA-256 remained respectively `11107b33a93f7d616abc1009ce41fdba955cacb422236643d97414f14033e1ab`, `0607bcea11d4f81bf8890e0dfee39809d3d9ded4e3af96b4f64811d59e5c6a56`, `e72c03f35a18cd0732b97b901bff480977760bfebc4de603c9abb860e170f348`, `1eb076e61351de3f0cd9f4fda81493e12bdd1588f82b6e114b8c48993cda0d14`. Evaluator denies socket connections; authenticated broker requests/orders = **NONE**.

**Scientific checkpoint:** Stop. The operator must decide whether a genuinely new hypothesis/information set or a separately predeclared execution/cost research question is scientifically warranted. Do not mine this evaluation window for a favorable V2 rule.
