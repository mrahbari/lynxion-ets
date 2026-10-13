# Lynxion canonical research backlog

**Registry baseline:** repository HEAD `1e6b359` on 2026-09-27; status reconciled 2026-10-13. **Documentation/governance only.** This is an index to source evidence, not a replacement for any frozen protocol or verdict. Historical counts are dated observations from cited reports, **not refreshed collector readings**. `UNKNOWN` and `INSUFFICIENT_EVIDENCE` mean no status is inferred. The primary Pilot-2 measurement phase is now **CLOSED / MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL** at its frozen 2026-10-13 00:00 UTC boundary. Pilot-1 is also closed; V3 is not authorized. The operator has ruled out a repeat microstructure collection after Pilot-2; see the [no-repeat decision brief](LYNXION_2026-10-13_NO_RECOLLECTION_DECISION_BRIEF.md). Other already-frozen prospective collectors are independent background work, not a new primary phase.

## How to read the entries

Each entry records: ID/name; family; **scientific status** (exact source verdict preserved); **operational priority** (ACTIVE/BACKGROUND/PARKED/CLOSED/BACKLOG, never a profitability ranking); question; information set; decision boundary; data source; historical/prospective design; whether outcomes were opened; evidence and exact verdict; value and why inactive; dependencies and contamination risks; next authorized step and approval gate; files, commits and frozen hashes. An absent field is `UNKNOWN`, not an invitation to fill it from intuition. `Outcome opened` distinguishes selection/diagnostic labels from economic outcomes where material.

Registry taxonomy: `IDEA`, `INDEPENDENT_LEAD`, `FEASIBILITY`, `PREREGISTERED`, `COLLECTING`, `FROZEN_PROSPECTIVE`, `DATA_LIMITED`, `NOT_IDENTIFIABLE`, `PREDICTIVE_NOT_SUPPORTED`, `ECONOMIC_GATE_FAILED`, `PARKED`, `CLOSED`, `INSUFFICIENT_EVIDENCE`. These are **index categories only**; quoted source verdicts below remain authoritative. A phase may be operationally parked even when its scientific protocol remains frozen. `Priority` concerns *whether work may run now*, not expected profit.

## Frozen, completed, and independently collecting investigations

### R01 — Phase 3A opportunity fingerprint

- **Family/status/priority:** external selection; `DATA_LIMITED` / exact `PHASE3A_INCONCLUSIVE_DATA_LIMITED`; CLOSED.
- **Question/info/boundary/source/design/outcomes:** whether archived sibling HMT selections had a pre-signal fingerprint; six causal public Binance 15m proxy-OHLCV features, matched at first sibling-message time; archived Telegram plus public Binance; retrospective. **Selection contrasts opened YES; future-return/economic outcomes NO.**
- **Evidence/meaning/inactivity:** 56 matched cases/23 UTC days; none of six passed frozen BH q<=.10 plus |d|>=.40. This neither confirms F4 nor proves absence of a fingerprint. Phase 3A is closed; opened cases cannot be reused for tuning.
- **Dependencies/risks/next/approval/references:** clean new directly attributable inbound signal cohort; attribution, small N, private/censored message history. Next authorized action: preserve verdict only; any new scientific design requires separate pre-outcome approval. [Verdict](../../research/external_signal_study/phase3_point_in_time/diagnostics/PLACEBO_AND_PHASE3A_VERDICT.md); commits `b9ec946` prereg, `a8a0db4` closure; prereg SHA-256 `96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193`.

### R02 — Compression / F4 as a frozen lead

- **Family/status/priority:** external selection / completed-bar compression; `FROZEN_PROSPECTIVE` / exact `FROZEN_PROSPECTIVE_RESEARCH_LEAD`, `COMPRESSION_FORWARD_VALIDATION_DATA_HUNGRY`; PARKED.
- **Question/info/boundary/source/design/outcomes:** whether the original 8/32 fully closed 15m-bar range ratio recurs before **new** sibling HMT selections versus frozen controls; public Binance proxy plus attributable sibling feed; prospective plan. **New prospective contrast/economic outcome NO.** Phase 3A's old selection screen was opened separately.
- **Evidence/meaning/inactivity:** Phase 3A F4 nominal clue failed multiplicity/power. It is a research lead, not an Edge. Missing complete feed and exact attribution prevent activation; not a reason to implement Compression in production.
- **Dependencies/risks/next/approval/references:** immutable complete feed, causal close times, frozen M2, M3 identifiability caveat; no old-cohort recycling. Next: only under existing feed gate, with separate activation; any formula/cohort/economic change needs a new pre-outcome decision. [Plan](../../research/external_signal_study/post_phase3a/COMPRESSION_FORWARD_VALIDATION_PLAN.md); commit `f85c22b`; original prereg hash as R01, plan hash `UNKNOWN`.

### R03 — COMPRESSION_FORWARD_1 prospective cohort

- **Family/status/priority:** external selection / F4 replication; `FROZEN_PROSPECTIVE` but exact operational `COMPRESSION_FORWARD_1_BLOCKED_SIGNAL_FEED`, M3 `NOT_IDENTIFIABLE`; PARKED.
- **Question/info/boundary/source/design/outcomes:** can *new, complete* sibling signals support the same frozen F4 case/control comparison? Prospective first-message cohort strictly after a recorded activation boundary; source is public proxy candles plus private inbound sibling messages. **New outcomes/contrasts NO.**
- **Evidence/meaning/inactivity:** M2 append-only specification is frozen, but source/message IDs, UTC send/receipt, HMT/TFS provenance, cursor and gap/reconnect audit of a qualifying continuous inbound feed were not established in cited work. Static exports/backfills do not qualify. This is a data/identifiability gate, not a negative F4 result.
- **Dependencies/risks/next/approval/references:** verify a qualified feed and pre-observation activation/empty cohort; never alter old Phase 3A/F4/M2. No activation without those gates; new semantics or Phase 3B economics require operator decision. [M2 specification](../../research/external_signal_study/post_phase3a/COMPRESSION_FORWARD_1_M2_SPEC.md), [plan](../../research/external_signal_study/post_phase3a/COMPRESSION_FORWARD_VALIDATION_PLAN.md); commits `32dbbe6`, `f85c22b`; M2 SHA-256 `5f9b9c37a26b997b34e48d2c9af66fa3e16a3c0838e504e8d4da9f010af20c08` (verified in this registry turn).

### R04 — C-11 severe-negative-funding shadow

- **Family/status/priority:** funding tail; `COLLECTING` / exact frozen prospective C-11 gate; BACKGROUND only.
- **Question/info/boundary/source/design/outcomes:** whether severe-negative BTC/ETH funding rebound survives prospective validation; public funding settlements and causal completed candles; settlement-triggered shadow cohort, strictly after frozen epoch `1788082349`. **Some prospective outcomes recorded under its own protocol YES; aggregate result remains gate-controlled, not a confirmed Edge.**
- **Evidence/meaning/inactivity:** [portfolio review](../RESEARCH_PORTFOLIO_REVIEW_2026-09-27.md) cites N=5 at its dated checkpoint versus >=100 total and >=30/symbol. Sparse sample is inconclusive; no early threshold/horizon change. Not the primary clock.
- **Dependencies/risks/next/approval/references:** wait for all frozen sample/breadth/cost gates; optional stopping, backfill, symbol concentration. Next authorized step only its already-frozen independent monitoring; modifying definitions or unsealing early needs operator review. [C-11 task](../../tasks/task0100-c11-prospective-funding-shadow.md), [portfolio review](../RESEARCH_PORTFOLIO_REVIEW_2026-09-27.md); source-task commit `bc6835b`; frozen protocol hash `UNKNOWN`.

### R05 — C-33 forced-liquidation prospective stream

- **Family/status/priority:** liquidation/OI; `COLLECTING` / exact `PROSPECTIVE_COLLECTING`, rate too slow for primary clock; BACKGROUND only.
- **Question/info/boundary/source/design/outcomes:** whether public `!forceOrder@arr` data can support a later liquidation question; Binance latest-snapshot/censored five-minute buckets, prospective only. **Predictive/economic outcome NO** at cited 1,034-bucket checkpoint versus 8,640-bucket warmup.
- **Evidence/meaning/inactivity:** this is not a complete forced-liquidation tape and does not overlap older historical OI dates causally. A missing event is not a negative event. No signal verdict follows.
- **Dependencies/risks/next/approval/references:** continue only its own frozen collector/rules, no backfill or proxy substitution; new joint OI/liquidation design or changed feed requires approval. [Feasibility](../LIQUIDATION_OI_FEASIBILITY_2026-09-16.md), [public collector task](../../tasks/task0163-forced-liquidation-event-collector.md); feasibility commit `9dabf4a`; frozen hash `UNKNOWN`.

### R06 — C-35 frozen compression-release cohort (not F4)

- **Family/status/priority:** prospective Lynxion setup/economic gate; `COLLECTING` / exact `TOO_SLOW / COLLECTING`; BACKGROUND only.
- **Question/info/boundary/source/design/outcomes:** whether its own frozen compression-release cohort passes a prospective after-cost gate; public candles/funding and fixed decision ledger, not sibling F4; prospective. **Some position outcomes exist under sealed protocol YES; aggregate economics not a verdict.**
- **Evidence/meaning/inactivity:** dated [decision board](../EDGE_RESEARCH_DECISION_BOARD.md) reports 292 decisions/3 completed positions against 240-outcome target. It is neither confirmed nor rejected; throughput too slow for the primary phase. Current live counts are not inferred from that report.
- **Dependencies/risks/next/approval/references:** preserve frozen source/cost/NO_TRADE_DEFAULT and never turn missed DNS intervals into no-signal observations. Existing monitoring is outside this registry task. Any cohort or policy change needs review. [Decision board](../EDGE_RESEARCH_DECISION_BOARD.md), [C-35 task](../../tasks/task0260-c35-outcome-orchestration.md); board commit `d5dc26a`; frozen hash `UNKNOWN`.

### R07 — historical momentum C-14/C-15 and prior price momentum

- **Family/status/priority:** OHLCV time-series and cross-sectional momentum; `ECONOMIC_GATE_FAILED` / exact feasibility `REJECT — NO DISTINCT LOW-COST MOMENTUM TEST JUSTIFIED`; CLOSED.
- **Question/info/boundary/source/design/outcomes:** own-series trailing-return and disjoint-universe long-only confirmation using public perpetual OHLCV, next-open/cost-aware historical boundaries. **Outcomes YES.** C-14 N=228, -2.5269% expectancy/PF .7286; C-15 N=82 superficially positive but failed confidence, fold, breadth and concentration gates.
- **Evidence/meaning/inactivity:** tested implementations failed frozen economic/robustness criteria; not a theorem against every momentum idea. No lookback/side/volatility-sizing rescue on opened cohorts.
- **Dependencies/risks/next/approval/references:** only a genuinely new causal mechanism/unopened cohort could justify a new study; parameters/position sizing are not a new information set. New hypothesis/preregistration requires operator scientific decision. [Feasibility](../TIME_SERIES_MOMENTUM_FEASIBILITY_2026-09-16.md); commit `9a27284`; frozen hashes `UNKNOWN`.

### R08 — historical OI continuation and exhaustion C-16/C-17

- **Family/status/priority:** OI/liquidation-adjacent; `ECONOMIC_GATE_FAILED` for tested OI mechanisms; CLOSED.
- **Question/info/boundary/source/design/outcomes:** whether observed historical five-minute OI with price impulse supports continuation or OI-contraction exhaustion; six-symbol official OI/price panels, retrospective cost-aware tests. **Outcomes YES.** C-16 N=2,471 net -0.1763%; C-17 N=2,124 net -0.3546%.
- **Evidence/meaning/inactivity:** frozen OI-only mechanisms failed, not a complete liquidation-tape test. Old OI panel cannot be joined to later C-33 without overlapping point-in-time data.
- **Dependencies/risks/next/approval/references:** valid new overlapping observed data and independent question would be needed; no threshold/horizon rescue. Operator approval for new experiment. [Feasibility](../LIQUIDATION_OI_FEASIBILITY_2026-09-16.md); commit `9dabf4a`; frozen hashes `UNKNOWN`.

### R09 — order flow, toxicity, and flow filters

- **Family/status/priority:** observed taker aggregates/aggTrades, not complete L2; `ECONOMIC_GATE_FAILED` / exact `REJECT — NO DISTINCT EXISTING-DATA ORDER-FLOW TOXICITY TEST JUSTIFIED`; CLOSED for tested representation.
- **Question/info/boundary/source/design/outcomes:** whether Phase-17 and C-21/22/27/34 flow direction or TASK-0369's flow conditioning adds information/cost survival; Binance kline taker-buy volume and trade aggregates at historical 5m/15m boundaries. **Outcomes YES.** C-21 N=2,326 and C-22 N=1,928 were net negative; TASK-0369 incremental improvement only +0.0039 percentage points, net -0.2881%.
- **Evidence/meaning/inactivity:** source flow is genuinely observed in aggregate but partly OHLCV-redundant; rejected tests do **not** test a continuous audited price-level book. Do not mine toxicity thresholds or post-hoc filter a negative baseline.
- **Dependencies/risks/next/approval/references:** only separately qualified new information and unopened protocol may revive a distinct question; synthetic/default OBI/CVD is not observed. Operator scientific decision needed. [Feasibility](../ORDER_FLOW_TOXICITY_FEASIBILITY_2026-09-16.md); commit `8fb634d`; frozen hashes `UNKNOWN`.

### R10 — broad funding state, C-10/C-12 and carry/basis

- **Family/status/priority:** observed funding and price; `CLOSED` for broad states, exact `NO NEW FUNDING-STATE TEST — CONTINUE FROZEN C-11 ONLY`; PARKED as a new direction.
- **Question/info/boundary/source/design/outcomes:** whether funding level/sign/change, broad state or carry economics add a causal edge; public settlement funding and historical OHLCV, retrospective cost-aware tests. **Outcomes YES.** C-12 descriptive +0.5403% but clustered CI [-0.0549%, +1.1266%] crossed zero; broad states unstable, carry/basis rejected.
- **Evidence/meaning/inactivity:** severe tail remains C-11's independent prospective question; broad historical descriptive positives are not confirmation. Do not create a new funding percentile or recycle old labels.
- **Dependencies/risks/next/approval/references:** await C-11's frozen gate for that tail; new source/mechanism needs independent preregistration and operator decision. [Feasibility](../FUNDING_STATE_FEASIBILITY_2026-09-16.md); commit `1984bc7`; frozen hashes `UNKNOWN`.

### R11 — funding settlement market-quality clock

- **Family/status/priority:** timing/execution quality, not funding direction; `CLOSED` / exact `LOW_INFORMATION_VALUE — DO_NOT_BUILD`.
- **Question/info/boundary/source/design/outcomes:** whether actual settlements materially worsen market quality enough for a no-trade rule; observed funding times, 15m activity/flow, depth snapshots and matched clock controls, retrospective. **Market-quality contrasts YES; trade-PnL outcome NO.** 24,048 symbol-settlement records/4,008 settlement-time clusters.
- **Evidence/meaning/inactivity:** activity rose but frozen adverse execution-risk materiality gates failed. No new rule justified, no profitability conclusion.
- **Dependencies/risks/next/approval/references:** no post-hoc threshold or fold rescue; any distinct execution-cost study requires its own decision. [Verdict](../../tasks/task0393-funding-clock-verdict.md); commit `6fcd3ea`; frozen hashes `UNKNOWN`.

### R12 — C-18/C-19 observed aggregated book-depth studies

- **Family/status/priority:** observed historical aggregated depth; `ECONOMIC_GATE_FAILED` / both exact `REJECT`; CLOSED.
- **Question/info/boundary/source/design/outcomes:** static band-depth imbalance (C-18) and four-hour relative near-book liquidity withdrawal (C-19); official Binance six-symbol percentage-band `bookDepth` archives, strict prior snapshot and costs, retrospective. **Outcomes YES.** C-18 N=2,154, -0.3568% net/PF .7685; C-19 N=1,973, -0.3533% net/PF .7720.
- **Evidence/meaning/inactivity:** real aggregated depth has been tested; these results neither qualify nor reject a new continuous price-level BBO/L2 information set. Do not relabel old band data as L2 tick tape or retune it.
- **Dependencies/risks/next/approval/references:** separate prospective measurement integrity first for a genuinely new book state; any later hypothesis needs approval/preregistration. [C-18](../../tasks/task0110-bookdepth-imbalance-c18.md), [C-19](../../tasks/task0111-liquidity-withdrawal-c19.md); commits `1d4a50e`, `93b59d2`; data manifest `data/research/bookdepth/manifest.json`, frozen protocol hashes `UNKNOWN`.

### R13 — Lead B quarter-hour aggressor-flow economics

- **Family/status/priority:** observed BTC aggregate trades and clock; `ECONOMIC_GATE_FAILED` / exact `REJECT_ECONOMIC_EDGE`; CLOSED.
- **Question/info/boundary/source/design/outcomes:** whether first-ten-second BTC aggressor-flow sign at frozen quarter-hour clock opportunities survives 12h executable costs; public raw Binance BTCUSDT aggTrades plus funding, pre-frozen chronological holdout, historical. **Outcomes YES.** 480 trades/240 UTC days, pre-cost +0.017280% versus net -0.282720% at 0.30% friction; frozen economic gate failed.
- **Evidence/meaning/inactivity:** small observed association does not survive costs; not a refutation of all market microstructure. No phase/side/threshold/cost rescue or reuse of opened holdout.
- **Dependencies/risks/next/approval/references:** new independent data and question, not Lead-B tuning; any new study needs scientific approval. [Verdict](../../tasks/task0388-lead-b-economic-holdout-verdict.md); prereg [here](../LEAD_B_ECONOMIC_HOLDOUT_PREREGISTRATION.md); verdict commit `c4ce43e`; prereg SHA-256 `a8d8b82e3ec19a5285555e615ac09a7c99808a34b9d14b8e61b502e0e4d2f358` (current file hash).

### R14 — Lead A edge-retention / profit-giveback state

- **Family/status/priority:** exit-state provenance; `INSUFFICIENT_EVIDENCE` / exact `INSUFFICIENT_PROVENANCE — DO NOT ESTIMATE EXIT EDGE`; PARKED.
- **Question/info/boundary/source/design/outcomes:** can an ex-ante observable state explain giveback before realized exits? Historical trade journal/public one-minute candles plus limited forward manager marks; provenance diagnostic, not a clean prospective exit experiment. **Historical descriptive outcomes seen YES; a joined confirmatory exit-edge outcome NO.**
- **Evidence/meaning/inactivity:** 1,913 journal rows exist, but market identity of candle path and joined authoritative forward exit fills were not established; forward exit-fill count was zero in the cited readiness artifact. It motivates data provenance, not a profitable exit rule.
- **Dependencies/risks/next/approval/references:** one unopened cohort with authoritative marks and realized exit fills; selection of recent winners, inferred leverage, wrong market path. No exit-policy change or economic claim; fresh collection/design needs operator authorization. [Gate](../../tasks/task0383-lead-a-provenance-gate.md), [readiness JSON](../reports/lead_a_data_readiness.json); source-gate commit `c0ea79d`; frozen hash `UNKNOWN`.

### R15 — original candle-reversal pre-intent study

- **Family/status/priority:** OHLCV Watcher→Engine→Fusion; `NOT_IDENTIFIABLE` / exact `PRE_INTENT_STUDY_NOT_IDENTIFIABLE_UNDER_CURRENT_SEMANTICS`; CLOSED and immutable.
- **Question/info/boundary/source/design/outcomes:** whether causal `candle_reversal_*` observations become a directional pre-intent Fusion event; qualified public BTC/ETH USD-M 1h capture, retrospective frozen study. **Future/economic outcomes NO.** 1,340 outputs: BUY 0, SELL 0, NEUTRAL 1,340.
- **Evidence/meaning/inactivity:** no source-defined Engine direction for those observations and singleton Fusion lacks two aligned directions. Failure of sample identifiability is **not** `NO_EDGE` or negative expectancy. Do not map reversal names to BUY/SELL to rescue the study.
- **Dependencies/risks/next/approval/references:** closed; new directional semantics are a new research/trading choice requiring operator decision, not a fix to this study. [Closure](../path_integrity/canonical_replay/PRE_INTENT_SIGNAL_STUDY_CLOSURE_V1.md); commit `0986f3e`; original prereg SHA-256 `454485ff11fad12a9ad355517d3c1461b1df1676e182937c6c2d7e02d10a8cac`, data addendum `b17e50a75591b26d08f435d460e9a9a8ca928ef0aab633b73de2ba495416bae5`.

### R16 — DIRECTIONAL_EDGE_STUDY_V1

- **Family/status/priority:** narrow OHLCV direction; `PREDICTIVE_NOT_SUPPORTED`; CLOSED and immutable.
- **Question/info/boundary/source/design/outcomes:** whether existing TrendMTFWatcher→Engine BUY/SELL predicts 4h side-adjusted close movement; qualified public BTC/ETH USD-M 1h archive, retrospective pre-outcome frozen Level-1 study, **no Fusion/Strategy/intent**. **Gross predictive outcomes YES; economic/after-cost NO.** 161 eligible selected events, mean -0.001015936740, 95% day-cluster interval [-0.004156362604, +0.002108991689].
- **Evidence/meaning/inactivity:** frozen positive-predictive-support criterion failed; interval also spans positive effects, so stable negative effect not established. No executable fill/cost claim, V1 residual mining or 4h horizon retuning.
- **Dependencies/risks/next/approval/references:** closed; a distinct, outcome-blind scientific generation requires operator selection. [Result](../path_integrity/canonical_replay/DIRECTIONAL_EDGE_STUDY_V1_RESULT.md), [prereg](../path_integrity/canonical_replay/DIRECTIONAL_EDGE_STUDY_V1_PREREGISTRATION.md); commits `6321f0b` pre-outcome, `6bf53fd` result; prereg SHA-256 `28e2224f640fb7c61765cedbc9a7d784b75d4ffee8eb9022a50173860147b206`.

### R17 — CONDITIONAL_SETUP_EDGE_V2

- **Family/status/priority:** OHLCV structural setup selection; `DATA_LIMITED` / exact `V2_DATA_LIMITED`; CLOSED and immutable.
- **Question/info/boundary/source/design/outcomes:** does existing MarketStructureEngine agreement add information beyond unchanged Engine direction? Public BTC/ETH USD-M 1h July–September capture, historical later unopened window, symbol×week×side controls. **Future/economic outcomes NO.** 556 comparable eligible versus 196 controls; frozen control floor 300 failed.
- **Evidence/meaning/inactivity:** sample inadequacy is not a negative predictive result; eligibility-only trace passed scoped determinism/prefix checks. No date extension, threshold change, control redesign or V2 outcome opening.
- **Dependencies/risks/next/approval/references:** closed; separate independent hypothesis and unopened cohort would require new scientific decision. [Sample verdict](../path_integrity/canonical_replay/CONDITIONAL_SETUP_V2_SAMPLE_GATE_RESULT.md), [prereg](../path_integrity/canonical_replay/CONDITIONAL_SETUP_EDGE_V2_PREREGISTRATION.md); commits `7dd0c6d` pre-outcome, `46ae180` gate; prereg SHA-256 `47579b9a8e9d63633140773996bc748ee6e0947dc1e5c30e08e3def5c4dcceeb`.

### R18 — observed microstructure data feasibility

- **Family/status/priority:** exchange-native price-level data measurement; `FEASIBILITY` / exact `PROSPECTIVE_MICROSTRUCTURE_COLLECTION_REQUIRED`; CLOSED feasibility gate, successor Pilot-2 R26 has also closed with a separate measurement verdict; R19 Pilot-1 is closed.
- **Question/info/boundary/source/design/outcomes:** whether a complete timestamped/auditable BBO/L2 information set already exists; inventory of public Binance `bookDepth`, taker kline aggregates, BTC raw aggTrades and runtime WS code; read-only historical/prospective source audit. **Predictive/economic outcomes NO in this gate.**
- **Evidence/meaning/inactivity:** observed aggregate depth/trades exist, and C-18/C-19 already tested band depth; no locally qualified continuous price-level book with `U/u/pu`, receipt times and gap audit. Synthetic strategy OBI/CVD/BBO defaults do not count. This supports collection feasibility work, not an Edge claim.
- **Dependencies/risks/next/approval/references:** complete public capture and integrity proof; source substitutions or any later predictive hypothesis need separate approval. [Feasibility](../MICROSTRUCTURE_MEASUREMENT_FEASIBILITY_2026-09-27.md); commit `acda00e`; report SHA-256 `e81e71d35c05951d011b707bb51c58bda75ec8a4059c57da9f9b75934adeee70` (current file hash).

### R19 — MICROSTRUCTURE_DATA_PILOT_7D

- **Family/status/priority:** public prospective data integrity; `CLOSED` / exact `MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL`; CLOSED. Its separate successor Pilot-2 has now also closed under R26 without joining the cohorts.
- **Question/info/boundary/source/design/outcomes:** can public Binance USD-M BTCUSDT/ETHUSDT diff-depth at 100ms plus public `/fapi/v1/depth?limit=1000` snapshot yield a durable sequenced price-level book? Formal **2026-09-28 00:00 UTC through 2026-10-05 00:00 UTC**, seven complete UTC days, raw+receipt/event clocks and gap/reconnect manifests. **Predictive/economic outcomes NO and forbidden.** A segregated preflight is not formal data.
- **Evidence/meaning/inactivity:** [final report](../MICROSTRUCTURE_DATA_PILOT_7D_REPORT.md) verifies 932 finalized hashes, zero detected sequence gaps inside valid epochs, but only ~66% valid-session coverage per symbol and a 26.457-hour unobserved interval. Seven restarts and host sleep/shutdown are documented; no continuous seven-day evidence or Edge result follows. Pilot-1 cannot be rescued by extension/backfill.
- **Dependencies/risks/next/approval/references:** preserve exact source/symbols/UTC boundaries, append-only raw, `pu` continuity, disk reserve and invalid intervals; no synthetic book state. [Pilot-2 readiness](../MICROSTRUCTURE_PILOT2_READINESS_RESULT.md) passed separately; Pilot-1 remains closed, not merged into its successor. Changed information semantics or a V3 hypothesis require operator decision. [Contract](../MICROSTRUCTURE_DATA_PILOT_7D_CONTRACT.md), [activation](../MICROSTRUCTURE_DATA_PILOT_7D_ACTIVATION.json), [forensics](../MICROSTRUCTURE_DATA_PILOT_7D_FAILURE_FORENSICS.md); commits `35056cc`, `ad6c3b2`, `773786b`, `f750841`; frozen contract SHA-256 `58e6ad82c051b5189354bd9bdc1d40a4b9f5958feb4f7808c253b50abd2a468b`, activation SHA-256 `3bce750c3a11d18504423cfd099b23a12eb2c448058d255b223c61df7fb3e526`.

### R20 — sibling-platform forensic and selection/geometry leads

- **Family/status/priority:** external decision-process hypothesis generation; `INSUFFICIENT_EVIDENCE` for Edge / exact forensic completion `FORENSIC_RECONSTRUCTION_COMPLETE_CANDIDATE_SELECTED`; PARKED.
- **Question/info/boundary/source/design/outcomes:** what selection, geometry, direction, invalidation, target and management behavior can be observed in sibling messages/screenshots? Private archived Telegram, retrospective forensic only; source-level Lynxion comparison is **mechanical**, not equivalent execution. **Selective historical outcome posts exist YES; complete prospective denominator or verified after-cost outcome NO.**
- **Evidence/meaning/inactivity:** selective watchlists and some geometry/management observed; ranking, candidate denominator, human/engine attribution, exact target-space veto and profitability unknown. Broad *hypothesis* sequence: **Opportunity Selection → Setup Geometry → Direction → Structural Invalidation → Target Space → Risk**. The mechanism is **not proven**.
- **Dependencies/risks/next/approval/references:** direct prospective provenance and independent preregistration before any predictive/economic use; incomplete/censored outcomes, screenshot selection and transfer-to-Lynxion risk. No sibling profit claim, no new branch during R19. [Forensic decision](../../research/external_signal_study/final_forensic_reconstruction/06_FINAL_FORENSIC_DECISION.md); commit `a6e0277`; frozen hash `UNKNOWN`.

### R21 — Phase-6 OHLCV regime/volatility search

- **Family/status/priority:** price-derived volatility/regime; `PARKED` / exact `PROVISIONAL_ONLY` and zero full promotions in cited portfolio review; CLOSED historical screen.
- **Question/info/boundary/source/design/outcomes:** whether OHLCV regime gates improve directional IC; multi-symbol historical 8h OHLCV, retrospective large tested family. **Predictive labels YES; trade-cost/economic outcome NO in cited screen.**
- **Evidence/meaning/inactivity:** cited search had 1,047 cumulative tests and a provisional high-volatility-reversion IC, with only 2/24 partial promotions and zero full promotions. This is not a deployable Edge and increases multiple-testing burden for any rearrangement of the same indicators.
- **Dependencies/risks/next/approval/references:** a genuinely independent mechanism/unopened protocol would be required; no post-hoc regime threshold selection. [Phase-6 source](../archive/phase6/reports/phase6-step8-regime-conditional.md), [portfolio review](../RESEARCH_PORTFOLIO_REVIEW_2026-09-27.md); source commit `a4687e3`, review `eb28913`; frozen hash `UNKNOWN`.

## Newly registered, outcome-unopened leads — **not V3**

### R22 — CROSS_SECTIONAL_EXTREME_MOVER_SETUP

- **Family/status/priority:** cross-sectional selection plus observable participation/setup; `INDEPENDENT_LEAD / NOT_YET_TESTED`; BACKLOG.
- **Question/info/boundary/source/design/outcomes:** does point-in-time ranking of unusually strong/weak crypto-perpetual movers, combined with independently observed participation and a causal short consolidation/first pullback plus liquidity/market-quality condition, select short-horizon opportunities with incremental predictive information versus ordinary opportunities? Conceptual downside mirror: bottom mover → negative/abnormal participation → bounce/pullback → failure → downside continuation. **Universe at T and every eligibility input must be known at T.** Source, cohort, market venue and historical completeness `UNKNOWN`; future prospective/historical boundary `UNDEFINED`; **outcomes NO**.
- **Evidence/meaning/inactivity:** operator-registered independent lead, **not** a tested signal or expected-profit claim. Existing momentum C-14/C-15 and V1 make overlap plausible; selection/participation/setup would need to be genuinely distinct and proven, not renamed momentum.
- **Dependencies/risks/next/approval/references:** [outcome-blind feasibility](POST_PILOT_INDEPENDENT_BACKLOG_FEASIBILITY.md) recorded `EXTREME_MOVER_PROSPECTIVE_UNIVERSE_FEASIBLE_HISTORICAL_UNQUALIFIED`; the later [detailed data audit](CROSS_SECTIONAL_EXTREME_MOVER_FEASIBILITY.md) uses the task-queue measurement class `EXTREME_MOVER_DATA_PARTIAL`, not a changed scientific verdict. The [outcome-blind information contract](CROSS_SECTIONAL_EXTREME_MOVER_INFORMATION_CONTRACT.md) is complete; it is **not** a source qualification or experiment activation. A complete historical point-in-time universe is unqualified; delistings/survivorship, ranks, market quality and independent sample remain unresolved. BingX's published swap API requires an API key even for market-data calls and was not accessed. No Top N, gain/loss %, volume multiplier, pullback %, horizon, spread, stop/target or acceptance threshold is frozen; no backfit to examples. Next: operator scientific choice, not another autonomous collection under the no-repeat decision. [Momentum feasibility](../TIME_SERIES_MOMENTUM_FEASIBILITY_2026-09-16.md); frozen hash `NONE`.

### R23 — Qullamaggie/public momentum methodology review

- **Family/status/priority:** external methodology, not transferable evidence; `IDEA` / source-backed methodology review complete, no Lynxion Edge claim; BACKLOG.
- **Question/info/boundary/source/design/outcomes:** what publicly documented relative-strength/weakness, strong prior movement, consolidation, breakout, episodic participation/volume, first-pullback, setup selection, asymmetric-payoff and systematic screenshot/case-study **research methods** might help frame later falsifiable questions? Source: author-published public methodology now cited in the separate review; no Lynxion decision boundary/cohort; **outcomes NO**.
- **Evidence/meaning/inactivity:** Qullamaggie stock-market methodology is **not evidence** of short-horizon crypto-perpetual Edge. Do not copy stock thresholds, holding periods, stops, targets, sizing or claimed performance into Lynxion. Methodology review is hypothesis-generation discipline, not strategy transplantation.
- **Dependencies/risks/next/approval/references:** [source-backed review](QULLAMAGGIE_METHOD_RESEARCH_REVIEW.md) separates author-described stock setups from a Lynxion analogy/hypothesis; transferability and survivorship/screenshot-selection risks remain. The methodology review is complete. Next: no strategy transplantation; a trading rule/study needs separate operator decision. Source: operator directive and linked author articles; frozen hash `NONE`.

### R24 — MANUAL_PROSPECTIVE_SETUP_ANNOTATION

- **Family/status/priority:** prospective observational protocol lead; `INDEPENDENT_LEAD / NOT_YET_TESTED`; BACKLOG.
- **Question/info/boundary/source/design/outcomes:** can a future operator-defined observation session capture **all** candidates without cherry-picking? Prospective manual timestamp, symbol, venue/source, screenshot/raw evidence and contemporaneous selection reason; exact selection rule and session window **not yet defined**; **outcomes NO** and collection **NOT STARTED**.
- **Evidence/meaning/inactivity:** this is a data-governance idea, not Edge evidence. A future protocol must freeze session/window before observation, retain winners, losers, no-trades, failed setups and no-fills, forbid hindsight edits to reasons, and separate setup annotation from later outcome labeling.
- **Dependencies/risks/next/approval/references:** the [design-only protocol](MANUAL_PROSPECTIVE_ANNOTATION_PROTOCOL.md) specifies an all-candidate immutable observation record and separate later outcome labels; inclusion rule/window remain UNDEFINED. Design work is complete; no collection has started. Activating collection or labels requires a frozen operator-approved rule. Source: operator directive; frozen hash `NONE`.

### R25 — liquidation / OI / observed OBI interaction proposal

- **Family/status/priority:** cross-information interaction; `PARKED` pending overlap/provenance; BACKLOG, **not a new experiment**.
- **Question/info/boundary/source/design/outcomes:** could genuinely observed liquidation, OI and OBI identify continuation **or** reversion? Source/boundary/cohort `UNKNOWN`; proposed future design only; **outcomes NO for this proposal**. Existing C-16/C-17/C-33/B1 and flow/OBI/CVD work are separate previously reported evidence, not this proposal's results.
- **Evidence/meaning/inactivity:** “mean reversion OR continuation” is not a falsifiable directional hypothesis without a **prospectively frozen direction-selection rule**. Historical liquidation/OI resolution and causal overlap are unproven for this conjunction. Liquidation magnitude, OI change, sigma, compression window and OBI threshold were conceptual knobs, **not frozen values**. Independent N/power must be set pre-outcome; liquidation spread/slippage can be abnormal.
- **Dependencies/risks/next/approval/references:** [outcome-free overlap reconciliation](POST_PILOT_INDEPENDENT_BACKLOG_FEASIBILITY.md) confirms C-16/C-17 OI, C-33 censored liquidation, C-18/C-19 aggregated depth and Strategy OBI/CVD defaults are not a proven joint observed panel. Remains PARKED. Direction rule, thresholds or experiment require operator scientific decision. [OI feasibility](../LIQUIDATION_OI_FEASIBILITY_2026-09-16.md), [strategy-input gap](../path_integrity/canonical_replay/STRATEGY_INPUT_PROVENANCE_GAP.md); related commit `9dabf4a`; frozen hash `NONE`.

### R26 — MICROSTRUCTURE_DATA_PILOT_7D_2

- **Family/status/priority:** public prospective price-level data-integrity measurement; `CLOSED` / exact **`MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL`** at the precommitted 2026-10-13 stop. No Edge status exists.
- **Question/info/boundary/source/design/outcomes:** can resident supervision plus fail-closed reconstruction sustain a fresh seven-complete-UTC-day BTCUSDT/ETHUSDT public Binance USD-M 100 ms depth and 1000-level snapshot capture? Exact half-open UTC boundary **2026-10-06 00:00:00 to 2026-10-13 00:00:00**. Local root `data/research/microstructure_pilot2/formal_2026-10-06/` is separate from Pilot-1 and technical soaks. Predictive/economic outcomes **NO; forbidden**.
- **Evidence/meaning/inactivity:** [readiness result](../MICROSTRUCTURE_PILOT2_READINESS_RESULT.md) records R1–R14 mechanical PASS after a separately preserved failed-R12 soak and corrected detector. The [contract](../MICROSTRUCTURE_DATA_PILOT2_CONTRACT.md) and [activation](../MICROSTRUCTURE_DATA_PILOT2_ACTIVATION.json) were committed before the start. The [final report](../MICROSTRUCTURE_DATA_PILOT_7D_2_REPORT.md) records 1,019/1,019 finalized files passing full storage/envelope readback and a conservative ~60.371% qualified CLOSED-session span per symbol. Multi-hour gaps violate PASS; preserved provenance and >50% span support PARTIAL. Measurement success/failure is not predictive Edge.
- **Dependencies/risks/next/approval/references:** preserve complete raw/manifest evidence and explicit uncertainty; no rescue by changing dates or joining cohorts. The operator rejects a repeat collection. The next independent Edge experiment, if any, is an operator scientific decision requiring separate preregistration; this verdict does not authorize V3. Commits `6665b97` readiness, `4f351dc` contract, `647ab4b` activation; contract SHA-256 `d10a475166954421c49492ecc65c4aa2265d95df7d5166bb2a1ffeec2e17963a`, activation SHA-256 `7d1b90492af440687511dbd035fc4f8c9eb006f8a8803d6f18805d0523d5287a`.

## Governance: independent information families, not a “super strategy”

Extreme-mover cross-sectional selection (R22), observed price-level microstructure (R18–19), liquidation/OI/OBI (R08/R25), funding (R04/R10–11), and sibling-style setup geometry (R01–03/R20) remain **independent leads**. Pairing them is a new interaction hypothesis, not a free extension. Any future interaction needs an explicit new information set, causal boundary, multiplicity family, unopened cohort and preregistration **before** outcomes. Scientific status never follows operational priority.

Permanent anti-data-mining rules: hypothesis and semantics **before** outcome; freeze source/cohort/thresholds before outcomes; no silent parameter changes or rescue of failed/data-limited studies; no favorable synthetic microstructure or missing-history backfill; no future leakage, future-derived normalization or `bfill`; preserve point-in-time availability and completed-bar boundaries; gross predictive information ≠ executable after-cost Edge ≠ portfolio profitability; training/opened data cannot become untouched confirmation data; seven-day pilot data are **not automatically V3-confirmatory**; exploratory findings need independent confirmation; record null/negative results and **all** winners, losers, no-trades, failed setups and no-fills; never delete inconvenient observations.

The unchanged high-level scientific sequence is **Measurement Trust → Information-Set Qualification → Independent Hypothesis → Preregistration → Causal/OOS Test → Cost Survival → Prospective Confirmation → Execution Validation → Portfolio/Risk → VST → Controlled Live**. This registry authorizes no Edge experiment, framework migration or production policy change. Authenticated VST/live activity requires its own operator approval. Current primary work is the frozen Pilot-2 collection and final audit, with Pilot-1 R19 closed; C-11/C-33/C-35 retain only their existing protocols and must not be called live from stale files alone. The ordered outcome-blind work queue is [the task board](LYNXION_RESEARCH_TASK_BOARD.md).
