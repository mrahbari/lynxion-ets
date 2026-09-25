# Edge-measurement readiness — bounded audit

Repository baseline: `0d557ba`. This is a provenance/gate audit, not a backtest or an edge verdict. Lynxion remains the platform. No frozen C-11/C-33/C-35/Compression or Phase-3A definition is changed.

## Research levels and decision boundary

- **Level 1, signal edge:** canonical Lynxion observation → Engine → Fusion → aggregator → StrategyManager decisions, then a preregistered fixed-horizon/MAE/MFE or explicitly priced fixed-notional outcome. Portfolio sizing and correlation can be excluded *from that question*; this cannot be reported as production portfolio profitability. After-cost language still requires explicit entry/exit, spread, slippage, fees and applicable funding.
- **Level 2, portfolio edge:** the same decisions plus queued admission, Risk sizing/correlation, concurrent positions, caps, Guard, causal fills and cost/portfolio accounting. Level-1 evidence cannot substitute for this level.
- Neither level may use `BacktestStrategyProvider`'s named adapter → `generate_signal()` → mock `FusedSignal` route as evidence for the canonical decision system (`docs/path_integrity/HISTORICAL_PATH_PROVENANCE.md`).

## Required gate table

| Gate | Level-1 status | Level-2 status | Direct evidence / smallest missing proof |
|---|---|---|---|
| Future leakage | PARTIAL | PARTIAL | `HistoricalClosedBarSource` rejects future/duplicate/gap/invalid bars and the completed-bar driver feeds only closes. No end-to-end feature/adapter audit or decision trace proves all warmup, normalization and HTF inputs causal. The legacy `portfolio_walk_forward_validator.py` still contains `ffill` followed by `bfill`; it is not the new canonical source and must remain excluded. |
| Closed-bar semantics | PARTIAL | PARTIAL | `completed_through(T)` enforces `close_time <= T`; historical watcher receives that close. Comparable live watcher semantics and active HTF alignment have not been proved. |
| Decision-path validity | FAIL | FAIL | `ReplayDecisionRunScope` invokes the same event handlers, Engine, Fusion, synchronous aggregator and StrategyManager, but no frozen normalized trace proves strategy selection/ExecutionIntent across a representative causal fixture, and the actual queued owner is not composed. The legacy mock-Fusion path remains noncanonical. |
| State isolation | PARTIAL | FAIL | Two decision scopes have distinct router/Fusion/strategy/Risk objects. `BaseStrategyAdapter.data_buffer` is one list per adapter, not symbol-keyed; `ensure_data_buffer` fills it only when empty. Multi-symbol strategy-buffer separation is not proved and must not be inferred from two watcher buffers. Full owner/guard/position/reconciliation/cooldown lifetime is also not one replay scope. |
| Event-time determinism | PARTIAL | FAIL | ReplayClock, historical close timestamp and synchronous aggregator exist. Active adapter/strategy paths still contain wall-clock fallbacks (`strategy_adapters.py`, `setup_engine.py`, named adapters); decision relevance must be tested on the selected research subset. Queued Live worker selection depends on delivery/wake ordering. |
| Signal-level sizing independence | PASS | NOT_APPLICABLE | A Level-1 predictive or fixed-notional question can explicitly exclude portfolio quantity; correlation's unrecorded Live wake-up timing then cannot affect the measured signal outcome. This does **not** validate Risk sizing or portfolio PnL. |
| Execution simulation validity | FAIL | FAIL | `SimulatedBrokerAdapter` only records accepted orders; it intentionally has no fills, protective-order outcomes, high/low tie rule or portfolio PnL. The old `RealisticBacktester` implements costs but uses a divergent decision path; it is not a canonical substitute. Fixed-horizon predictive outcomes must be labelled non-execution outcomes until a causal fill contract exists. |
| Cost model | FAIL | FAIL | No canonical research outcome model binds frozen fee, spread, slippage and applicable funding assumptions to canonical intents/fills. Existing legacy backtester cost knobs do not establish canonical after-cost results. Gross directional statistics cannot be called after-cost edge. |
| Reproducibility | PARTIAL | FAIL | Source, replay clock, local scope and simulated broker have focused deterministic tests. A new read-only normalized event trace repeats through Observation, Engine and Fusion on a two-bar fixture, but it emits no ExecutionIntent. Adapters may lazily request historical data through the global broker registry with `download_enabled=True`; point-in-time provider binding and frozen configuration/data hashes are not proved. |
| Prefix invariance | FAIL | FAIL | Source and normalized Observation/Engine/Fusion trace prefix tests pass for a tiny fixture, but no selected strategy/ExecutionIntent or outcome is present. `HASH(decisions <= T)` through canonical StrategyManager and outcome evaluation has not been run. |
| Production-state isolation | PARTIAL | PARTIAL | Focused offline suites kept four protected production journal hashes unchanged; full research/owner/outcome composition is not yet constructed and therefore cannot be certified production-state-free. |

**Gate verdict: `EDGE_MEASUREMENT_NOT_READY`.** This is not a negative edge result. The earliest shared blocker is a frozen, normalized, decision-level trace through the *existing* canonical Engine/Fusion/aggregator/StrategyManager under explicit event time/configuration, followed by a full decision-level prefix test. To claim *after-cost* Level-1 edge, a causal outcome/fill and cost contract is additionally required. Do not build a second strategy engine to satisfy this.

## P0 issue classification (one class per issue)

| Issue | Classification | Causal reason / disposition |
|---|---|---|
| End-to-end canonical signal/intent trace and frozen config | EDGE_MEASUREMENT_BLOCKER | Without it, observed performance cannot be attributed to Lynxion's actual strategy competition. Next engineering unit should instrument existing events, not recreate selection. |
| Decision-time wall-clock fallbacks on selected strategy/Fusion path | EDGE_MEASUREMENT_BLOCKER | If reachable, identical historical input can yield different admission/intent timestamps or outcomes. Audit and migrate only reached calls; prove with a clock-perturbation test. |
| Strategy adapter lazy data fetch and shared buffer | EDGE_MEASUREMENT_BLOCKER | `BaseStrategyAdapter.ensure_data_buffer` resolves the global broker registry, requests downloadable history, and stores it in one adapter-wide buffer. Without point-in-time data binding, historical decisions can depend on unavailable/future/external data; in multi-symbol research one symbol can inherit another's buffer. A deliberately single-symbol subset avoids the second issue but not the first. Do not silently change Live strategy semantics. |
| Full decision-level prefix invariance and feature provenance | EDGE_MEASUREMENT_BLOCKER | Appended future data might alter earlier warmup/selection; source-only invariance is insufficient. |
| Causal signal outcome/fill and explicit after-cost model | EDGE_MEASUREMENT_BLOCKER | No canonical fee/spread/slippage/funding-adjusted expectancy can be asserted without these. A fixed-horizon *predictive* statistic may be separately reported without an execution claim. |
| Queue worker batch/delivery order for multi-intent execution | PRODUCTION_VALIDATION_BLOCKER | Reversed equal-event-time deliveries change first processed symbol (focused test). It blocks multi-intent execution/portfolio parity, not a clearly bounded pre-queue Level-1 signal question. A Live economic ordering change needs explicit review. |
| Correlation publication phase/history | PRODUCTION_VALIDATION_BLOCKER | Snapshot pinning is verified, but historical Live worker wake-ups were not recorded. Level-2 historical timing parity is unavailable; Level-1 explicitly excludes sizing. |
| Missing historical order-flow/tick/screener and unresolved MTF archive | EDGE_MEASUREMENT_BLOCKER | Blocks claims about the full enabled watcher universe or any strategy requiring those inputs. A preregistered candle-only subset can be measured, clearly labelled; no proxy data. |
| Broker timeout/restart and VST runtime verification | PRODUCTION_VALIDATION_BLOCKER | Needed for reliable live execution evidence, not for a network-free signal outcome experiment. `BROKER_RETRY_SEMANTICS_UNRESOLVED`. |
| XMR historical root-cause reconstruction | PRODUCTION_VALIDATION_BLOCKER | Important execution forensics, but no proven dependency of an isolated pre-queue signal measurement; retain blocker. `XMR_ROOT_CAUSE_UNRESOLVED`. |
| UI/Telegram/monitoring polish | NONBLOCKING_ENGINEERING_DEBT | No demonstrated causal effect on the offline research path; parked. |
| Exact live/replay watcher equivalence outside the defined subset | UNKNOWN_REQUIRES_EVIDENCE | Source/archive/timestamp mapping not fully audited; never infer full parity from subset tests. |

## Minimal critical path

1. Freeze one non-profit-selected, historically available watcher/strategy/config subset; record enabled strategies, config hash, input/timeframe provenance. Keep unavailable watchers excluded by evidence, not proxy substitution.
2. Add a normalized trace tap around existing router/aggregator/StrategyManager outputs; test deterministic repeated runs, two-run/two-symbol isolation, and decision-time wall-clock independence for *reached* components. Do not alter strategy/Fusion logic.
3. Run prefix T versus T+future through the reached canonical signal/intent path, including warmup, UTC boundary and active MTF only if actual completed HTF data exist. A failure blocks outcomes.
4. Define preregistered Level-1 outcome semantics and conservative explicit costs on the same fixed fixture/data source; verify high/low ambiguity and no impossible fills. Do not reuse legacy mock-Fusion PnL.
5. Only then run one untouched baseline for the validated level. Keep Level-2 queue/Risk/portfolio parity a separate release gate and park unrelated infrastructure.

No profitability run, hypothesis reopening, threshold choice or optimization occurred in this audit.
