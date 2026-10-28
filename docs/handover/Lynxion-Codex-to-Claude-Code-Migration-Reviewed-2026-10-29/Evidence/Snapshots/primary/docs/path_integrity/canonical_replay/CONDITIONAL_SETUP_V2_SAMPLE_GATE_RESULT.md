# CONDITIONAL_SETUP_EDGE_V2 — frozen pre-outcome sample gate

Starting HEAD `7ffca59`. Frozen preregistration SHA-256 `47579b9a8e9d63633140773996bc748ee6e0947dc1e5c30e08e3def5c4dcceeb` (commit `7dd0c6d`), unchanged. Qualified raw capture manifest SHA-256 `38813362968e9f9c696fe754badeea5bb0a765b79ac05ee8ee80cf1572beac36`; no reacquisition, raw-byte edit or interval change.

This step used only causal current/past OHLCV to run existing `TrendMTFWatcher` → `EngineService` and `MarketStructureEngine`. It counted current-hour BUY/SELL/NEUTRAL and structural-bias agreement, with no future close, forward return, PnL, MFE/MAE or cost calculation. All 4,032 evaluation symbol-hours produced a current-time Engine output: BUY 492, SELL 304, NEUTRAL 3,236. Among 796 directional opportunities, symbol × ISO-week × side strata containing **both** arms retained 40 strata across 12 ISO weeks. No selected event was censored by the fixed final-hour boundary.

| Preregistered comparable arm | N (floor 300) | UTC days (floor 40) | BTC / ETH (floor 20 each) | BUY / SELL (floor 50 each) |
|---|---:|---:|---:|---:|
| Structural agreement | 556 | 57 | 220 / 336 | 365 / 191 |
| Nonagreement control | **196 — FAIL** | 45 | 75 / 121 | 118 / 78 |

All other listed count minima and the >=8 paired-ISO-week requirement passed. The frozen **>=300 comparable controls** condition failed by 104 events. Under the preregistered rule this formally classifies the V2 study as **`V2_DATA_LIMITED`**. This does **not** mean negative predictive information or no Edge. Dates, source, threshold, controls and sample floor were not changed to rescue it. **No V2 outcome was opened and no V2 scientific effect/interval was computed.** The remaining release gates are not an authorization to override the failed sample floor; the V2 execution path remains closed.

The complete count-only decision/eligibility trace was identical on repeat, matched three prefix cuts, and BTC-only matched BTC rows from the two-symbol run. Trace SHA-256 `092bae2e6df268e203925151b8c03b29c7ff67f1fdd6fade635760998a4c45fd`. These are scoped count-only determinism/prefix/state-isolation checks; they do not claim outcome-level V2 execution passed. Focused collection: **9 PASS / 0 FAIL**. Tests deny socket connects. Protected production persistence hashes before/after matched: active positions `11107b33a93f7d616abc1009ce41fdba955cacb422236643d97414f14033e1ab`; cooldown `0607bcea11d4f81bf8890e0dfee39809d3d9ded4e3af96b4f64811d59e5c6a56`; live orders `e72c03f35a18cd0732b97b901bff480977760bfebc4de603c9abb860e170f348`; trade journal `1eb076e61351de3f0cd9f4fda81493e12bdd1588f82b6e114b8c48993cda0d14`. No authenticated broker/account/order activity.

Stop at the frozen data-limited checkpoint. V1 remains closed. Do not expand dates, alter conditions or mine this capture for a new V3 without a separately selected and preregistered scientific question.
