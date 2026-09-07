# Lynxion Engineering Progress Ledger

## Current goal

Establish a statistically defensible, cost-adjusted trading edge while preserving execution
correctness, experimental validity, and VST risk controls.

## Current task

Keep TASK-0156 collecting separately. TASK-0165 activated one approved C-33 public-data collector;
TASK-0166 must add a deterministic liveness/bucket auditor while collection continues.

## Status

TASK 000 operational closure and TASK 001/002 attribution are complete. Controlled edge
research remains in progress; C-01 through C-31 historical candidates have not cleared their
frozen promotion gates and production strategy logic is unchanged.

## Latest verified findings

- TASK-0165 is ACTIVE/COLLECTING with explicit operator authorization. Exactly one standalone
  public-data process was verified (PID 86852) on source commit `1c46d42`, with activation boundary
  `1788694535` and historical import disabled. Its first 17 records use one session, unique keys,
  four heartbeats and twelve complete symbol klines; minimum epoch `1788694536` is strictly after
  activation. No liquidation or outcome was yet admitted. Thirteen focused tests and the full suite
  pass with 916 passed and one optional import-linter skip.

- Three failed C-33 activation attempts are retained outside the active cohort. They fail-closed on
  same-second activation, live discriminator nesting/universe filtering, and a partial first candle;
  no failed-cohort candle or liquidation observation was imported into the active ledger.

- TASK-0164 is COMPLETE at repository level. Review canonicalized numeric event identity, added
  original/fill consistency, and verified fail-closed boundary/interruption behavior. No connection
  was made. C-33 is now at an approval gate: its continuous public websocket collector is a new
  long-lived runtime, which the current heartbeat is not authorized to start.

- TASK-0163 is COMPLETE at repository level. A standalone, fail-closed collector now preserves raw
  USD-M liquidation snapshots, exact closed one-minute candles, public time heartbeats, and session
  lifecycle with append-only restart dedupe. Network requires an explicit flag and was not used;
  signal, outcomes, broker, orders, and runtime remain unopened. Eight focused tests and the full
  suite pass with 911 passed and one optional import-linter skip.

- TASK-0162 is COMPLETE. C-33 freezes a forward-only Binance USD-M liquidation-exhaustion reversal
  using liveness-complete five-minute buckets, a causal 30-day p99 plus absolute/dominance gates,
  next-minute/four-hour execution, funding, costs, temporal folds, clustered uncertainty, breadth,
  concentration, and drawdown. The feed is explicitly treated as censored snapshots. No stream,
  observation, outcome, broker, or runtime was opened.

- TASK-0161 is COMPLETE. The next independent direction is prospective reversal after an exceptional
  cluster of exchange-labelled Binance USD-M forced liquidations. The public stream provides causal
  event/trade time and fill fields but is explicitly a latest-event-per-symbol 1,000-ms snapshot,
  so it cannot be represented as complete liquidation volume. No connection or outcome was opened.

- TASK-0160 is COMPLETE and C-32 is `DATA_BLOCKED` before its first observation. Official Binance
  depth semantics match the collector, but the official BingX depth shape lacks the frozen per-book
  server timestamp; newer BingX instructions also require signed key-bearing market-data requests.
  Substitution would alter the preregistration, so no activation manifest or network call occurred.
  Eleven focused tests and the full suite pass with 903 passed and one optional import-linter skip.

- TASK-0159 is COMPLETE at repository level. Its standalone collector validates synchronized public
  Binance/BingX books, walks depth for identical quantity, hashes raw responses, and fail-closes on
  boundary, duplicate, stale, malformed, crossed, or insufficient-depth observations. Network use
  requires an explicit flag and was not activated; no outcome, broker, order, or runtime was opened.
  Ten focused tests and the full suite pass with 902 passed and one optional import-linter skip.

- TASK-0158 is COMPLETE. C-32 freezes a prospective boundary, public Binance/BingX perpetual books,
  exact time/depth validity, 1,000-USDT two-leg VWAP, 0.60% admission, convergence/four-hour exit,
  funding, 0.30% primary and 0.50% stress friction, chronological folds, clustered uncertainty,
  breadth, concentration, and drawdown gates. No observation or outcome was opened and no network,
  broker, or runtime path was called.

- TASK-0157 is COMPLETE. It prohibits further variants from the opened directional panels and
  admits one distinct market-neutral direction for data-feasibility preregistration only:
  prospective cross-venue perpetual price dislocation using executable public quotes and full
  two-leg costs. No edge is claimed, no outcome was opened, and no runtime setting changed.

- C-31 Spot-led perpetual underreaction is REJECTED with zero admitted trades. Across each symbol,
  roughly 1,041-1,251 primary Spot shocks cleared the frozen shock gates, but none had a same-sign
  perpetual response at or below 50% of Spot. At hourly resolution the venues were already too
  synchronized for the preregistered state to exist; relaxing the opened response threshold is
  prohibited. The report reproduced byte-for-byte; six focused tests and the full suite pass with
  892 passed and one optional import-linter skip.

- Before C-31 outcomes were opened, its evaluator enforced all frozen hashes, exact
  completed Spot/perpetual alignment, causal shock thresholds, underreaction direction/ratio,
  contiguous next-open execution, funding boundaries, fold isolation, clustered uncertainty, and
  the conjunctive gate. Independent review adds strict sign/response and fold-crossing tests. Six
  focused C-31 tests and eleven relevant tests passed.

- C-31 is preregistered with outcomes unopened. It tests a new same-asset cross-venue price-
  discovery mechanism using exact aligned Spot/perpetual bars, causal Spot-shock thresholds, frozen
  underreaction ratio, next-open perpetual execution, funding/costs, temporal reverse, uncertainty,
  breadth, and concentration gates. It is not a basis or cross-symbol lead-lag variant.

- C-30 is REJECTED and the positioning-divergence family is closed. Its +0.3617% primary expectancy
  and PF 1.5219 came from only 56 trades, including 52 DOT and only two LONGs; the clustered interval
  crossed zero, concentration was 75.74%, two folds were negative, and later primary years had no
  observations. Reverse was just 13 all-SHORT trades. These sparse positives cannot be promoted or
  re-sliced despite remaining positive at 0.50% cost. The report reproduced byte-for-byte; ten
  focused tests and the full suite pass with 886 passed and one optional import-linter skip.

- Before outcomes were opened, C-30's evaluator reused C-29's unchanged mechanics and
  substituting only the preregistered disjoint universe, four frozen hash maps, report identity, and
  bootstrap seed. C-29's default identity/seed remain unchanged, and import-order isolation passes
  in both directions.

- C-30's first direct CLI preflight exposed a local module-resolution error before any source was
  loaded or outcome calculated. The wrapper now supports both package import and direct-script
  execution, with a subprocess regression test; the frozen research specification is unchanged.

- C-11 updated at `2026-09-06T08:52:47+00:00`: its first prospective BTC outcome is COMPLETE with
  -0.0366% net return after frozen cost and funding (N=1, PF=0). Its funding timestamp `1788595200`
  is strictly after boundary `1788082349`; no history was imported. This single loss is not a
  candidate verdict and C-11 correctly remains `COLLECTING` until every frozen gate is satisfied.

- C-30 is preregistered with outcomes unopened as the single independent confirmation of C-29 on
  five disjoint symbols. Signal, alignment, 24-hour execution, costs, funding, uncertainty, and
  absolute sample gates are unchanged; all new input hashes are frozen. Failure closes this family.

- C-29 positioning divergence is REJECTED. Primary N=202, net expectancy was only +0.0010% and PF
  1.0010 at 0.30% cost, with a wide clustered interval crossing zero. SHORT, 2025, and 2026 were
  negative; LONG had only 39 observations; expectancy failed at 0.50% cost. The positive-looking
  reverse sample had only 20 all-SHORT trades versus its frozen N>=150 gate, so it cannot support
  promotion or a post-result variant. The report reproduced byte-for-byte; seven focused tests and
  the full suite pass with 883 passed and one optional import-linter skip.

- Before C-29 outcomes were opened, its evaluator enforced every
  frozen source hash, exact five-minute pre-decision positioning alignment, causal thresholds,
  contiguous next-open/24-hour execution, funding boundaries, overlap and fold isolation, and the
  conjunctive frozen gate. Independent review adds explicit tests that the decision-time metric is
  ignored and fold-crossing positions are excluded. Seven focused tests now cover causal alignment,
  direction, funding boundaries, empty fail-closed behavior, source hashes, and fold isolation. The
  report was then generated once without changing the frozen specification.

- C-29 pre-outcome review corrected an input-provenance omission: its 2021-2022 reverse sample
  requires the separately frozen C-09 native futures price files, not the 2023+ primary files.
  Their six exact hashes are now preregistered and mandatory alongside metrics, primary price, and
  funding hashes. Outcomes remain unopened; no signal or gate parameter changed.

- C-29 is admitted and preregistered with outcomes unopened. It uses previously untested official
  global-account and top-trader position-size ratios, exact pre-decision alignment, causal rolling
  thresholds, next-open execution, funding/cost accounting, temporal reverse validation, and strict
  uncertainty/breadth gates. It is one positioning-divergence specification, not an OI/taker retune.

- C-28 volatility-sweep rejection is REJECTED. Its 986 primary trades lost 0.2581% per trade after
  frozen cost/funding, PF was 0.6782, and the daily-clustered 95% interval was fully negative.
  Every fold, side, symbol, and year was negative; 2023 temporal reverse was also negative at
  -0.3081% with PF 0.5804 over 518 trades. Only concentration passed, so no diagnostic reslicing or
  production change is allowed. The report reproduced byte-for-byte; five focused tests and the
  full suite pass with 876 passed and one optional import-linter skip.

- Before C-28 outcomes were opened, independent evaluator review added exact
  SHA-256 enforcement for every frozen price and funding input so changed sources fail before any
  outcome is calculated. Five disconnected tests verify this guard alongside
  causal exclusion of the current candle, frozen LONG/SHORT rejection direction, strict funding
  settlement boundaries, and fail-closed empty metrics. The report was then generated once without
  changing any frozen parameter.

- C-28 is preregistered with outcomes unopened. It tests a distinct failed-extreme volatility-sweep
  rejection mechanism across six native futures symbols, with causal range/extreme lookbacks,
  next-open execution, funding and cost accounting, temporal reverse validation, daily-clustered
  bootstrap uncertainty, breadth/concentration gates, and a single immutable verdict specification.

- TASK-0156 is COMPLETE and the corrected stop-identity runtime is active on the approved BingX VST
  path. Preflight reported TESTNET with `live_trading=False`; exactly one replacement runner was
  observed. Its new empty cohort freezes boundary `2026-09-05T18:38:08.780489+00:00`, commit
  `bf93cc0`, and `historical_import_allowed=false`. Its first observed event is strictly after the
  frozen boundary and the current audit has zero violations, so its honest verdict is `COLLECTING`;
  no trailing or profitability conclusion is yet justified.

- TASK-0155 is COMPLETE at repository level. A wrapper subprocess test proves commit mismatch exits
  before the runtime entrypoint. Six focused tests and the full 871-test suite pass with one optional
  import-linter skip. The current runner and legacy cohort remain unchanged; a new-cohort restart is
  still approval-gated.

- TASK-0155 now has a fail-closed launch resolver: same-commit cohorts continue, while commit
  mismatch, malformed manifest, or non-empty unmanifested roots abort before runtime. Explicit new
  roots must be empty and receive actual HEAD/new run/new UTC metadata. Five disconnected tests and
  wrapper syntax validation pass; the active runner was not reloaded.

- TASK-0155 identifies a provenance-critical restart defect: `lynxion` reuses the existing
  manifest's old commit without comparing it to HEAD. Restarting TASK-0154 directly would mix two
  code revisions under one frozen cohort label. A fail-closed commit guard and a separate new-cohort
  activation are preregistered; no reload is permitted yet.

- TASK-0154 is COMPLETE at repository level and runtime-inactive. Exact-ID and fallback visibility,
  structured query failures, unchanged exhaustion counts, and zero false commits have failure-
  injection coverage. Thirty-two focused tests and the full 865-test suite pass with one optional
  import-linter skip. A controlled runner reload is a separate approval gate.

- TASK-0154 now performs exact placement-order-ID visibility when identity is available, rejects
  every mismatched frozen attribute, requires exchange identity for labelled fallback matching,
  and emits structured non-sensitive query/match evidence. Twenty-six focused tests pass. Poll and
  retry counts are unchanged and the running process has not loaded these repository changes.

- TASK-0154 now preserves the placement exchange order ID in each causal response event, including
  explicit null when absent, without changing visibility matching or state behavior. Twenty-two
  focused regressions pass; runtime remains on the prior commit and was not reloaded.

- TASK-0154's first repository unit distinguishes a genuinely successful empty pending-order query
  from nonzero exchange responses, malformed payloads, and exceptions, while preserving the legacy
  list API. Error evidence is deliberately non-sensitive. Twelve focused regressions pass; no
  runtime or broker state changed.

- TASK-0153 is COMPLETE with verdict PARTIAL_ATTRIBUTION. Its deterministic counter separates
  symbol/attempt response and visibility outcomes; four focused tests and the full 851-test suite
  pass with one optional import-linter skip. The closing snapshot has 84 requests: 73 accepted,
  10 rejected, one missing response, 65 visibility failures, and eight verified paths. Local
  evidence defects are confirmed; the exchange-side cause remains unknown.
- TASK-0154 freezes the minimal repository correction: preserve placement identity, distinguish
  pending-query failure from success-empty, prefer exact order-ID visibility, label fallback
  matching, and add failure-injection coverage. Runtime activation is explicitly excluded.

- TASK-0153 reaches PARTIAL_ATTRIBUTION at the source-semantics layer. Placement treats BingX
  `code=0` as success even when `order_id` is absent; pending-order API and transport errors collapse
  to the same empty list as a valid empty query; visibility does not correlate the placement order
  ID and can accept an identity-less match. Three disconnected tests reproduce these defects. The
  evidence cannot yet prove why ADA/NEAR orders were absent exchange-side.

- TASK-0153 preregisters a bounded, read-only attribution of accepted-but-invisible stop
  replacements. It separates explicit price rejection from placement acceptance, pending-order
  normalization/filtering, timing, and false-positive response semantics. Any justified correction
  must be frozen separately; this diagnosis cannot call a broker or change runtime behavior.

- TASK-0152 is COMPLETE. Its deterministic read-only auditor reports every frozen sample, breadth,
  terminal-completeness, stop-chain, and integrity gate, with strict DATA_INVALID precedence and no
  outcome opening. Eleven focused tests and the full 847-test suite pass with one optional
  import-linter skip. The live cohort remains COLLECTING.

- TASK-0152 now proves byte-for-byte read-only determinism and separately reports duplicate IDs,
  lifecycle regressions, sensitive fields, and unknown causal references. Nine focused tests pass;
  the live cohort has zero such integrity violations and remains COLLECTING.

- TASK-0152 now evaluates all frozen coverage thresholds explicitly and cannot transition from
  COLLECTING unless every gate passes. Seven focused tests cover exact boundary values. The live
  cohort currently passes only verified-stop-chain commit integrity; it has no completed exits and
  remains ineligible for any policy comparison.

- TASK-0152 now measures terminal linkage, complete fill economics, exit-type/week coverage, and
  trailing eligibility while preserving unknowns. Six focused tests pass. The live cohort still
  has zero completed identities, so terminal percentages correctly remain null and no exit-policy
  conclusion can be calculated.

- TASK-0152 now audits stop chains by exact causal references. Five focused tests pass. The latest
  read-only snapshot has 34 requests: one complete verified/committed chain, 29 visibility
  failures, three rejected responses, and one accepted response without a visibility result.
  Integrity violations remain zero; the operational visibility concern remains unresolved.

- TASK-0152's core read-only auditor passes four focused tests and reports 11 identities plus 239
  valid post-boundary events with no integrity violation; the cohort has no completed identity and
  remains COLLECTING. Operationally, 25 stop-replace responses were accepted, but only one DOGE
  mutation became exchange-visible while 24 visibility checks failed (21 ADA, 3 NEAR); three
  rejected responses explicitly report a stop below current price. This is evidence of unresolved
  protective-order visibility, not evidence that trailing is reliable.

- TASK-0152 preregisters a deterministic, read-only auditor for every frozen TASK-0151 sample,
  breadth, terminal-completeness, causal-chain, and integrity gate. Its output is limited to
  COLLECTING, DATA_INVALID, or eligibility for a separately preregistered policy comparison; it
  cannot tune thresholds, import history, call a broker, or modify evidence.

- C-11 admitted its first prospective candidate at the 2026-09-05 08:00 UTC BTCUSDT funding
  settlement. The observation is strictly after boundary `1788082349`, has severity ratio 2.8409,
  and remains PENDING until its frozen 24-hour virtual exit is available. No pre-boundary record
  exists; N=0 completed and the verdict correctly remains COLLECTING.

- TASK-0151 is ACTIVE/COLLECTING. The operator restarted exactly one auto-detection VST runner via
  `./lynxion` at 06:49:11 UTC on commit `54d7c9c`. The manifest freezes boundary
  `2026-09-05T06:49:11.585276+00:00`, run ID `task0151-20260905T064911Z`, and prohibits historical
  import. The snapshot and ledger validate; the first of one event is strictly post-boundary and
  no pre-boundary observation exists. Only `POSITION_OBSERVED` has been emitted, so no trailing,
  terminal-completeness, or profitability conclusion is available.

- TASK-0151 received explicit operator approval. Opt-in auto-detection wiring now shares one run ID,
  identity snapshot, boundary-enforcing event observer, and activation manifest across position
  management and reconciliation. Conflicting cohorts and pre-boundary events fail closed. Twenty-
  eight focused tests and the full 836-test suite pass with one optional import-linter skip; runtime
  activation remains pending the wiring commit and frozen launch metadata.

- TASK-0151 now freezes its deployment and rollback checklist: establish exactly one VST runner and
  orchestrator, test shared wiring, record activation UTC/commit before events, reload that runner
  once, validate forward-only artifacts and protection read-only, and disable injection with one
  rollback reload on failure. Proposed production evidence paths remain unwritten pending approval.

- TASK-0151 now freezes the forward data gate before activation: at least 100 post-boundary
  completed VST positions, 30 trailing-eligible closures, eight UTC weeks, five symbols, both sides,
  high identity/terminal completeness, complete stop causal chains, and zero duplicate, lifecycle,
  corruption, sensitive-field, or pre-boundary violations. These are collection gates only; no
  threshold comparison or policy outcome may be opened from them.

- TASK-0151's read-only preflight finds two internal reconciliation constructors and an import-time
  active-position singleton. A valid deployment must configure one shared run ID, identity store,
  and event ledger before threads start and inject the same components into the active VST
  orchestrator. Repository state cannot establish which orchestrator/process is currently running;
  that must be verified in the approved runtime preflight before a single controlled reload.

- TASK-0150 rejects a code correction: the remaining unsupported `record_result` statement is
  unreachable for simulated fills because `journal_ref` is created only for real-send routes and
  remains null in paper mode. Paper evidence already uses the Execution Truth Ledger. Eighteen
  focused tests pass; changing dead guarded code would be cleanup rather than correctness work.
- TASK-0151 reaches the runtime approval boundary. The repository evidence chain is ready for a
  forward-only VST cohort, but activation requires composition wiring, new production observation
  files, a frozen UTC boundary, and a controlled VST runner reload. No such action is authorized by
  the current automation.

- TASK-0149 is COMPLETE at repository level. Reconciliation now resolves an exact exchange order
  ID to one journal lifecycle reference and uses the supported terminal transition; unknown and
  ambiguous identities remain unchanged. Twenty-one focused tests and the full 832-test suite pass
  with one optional import-linter skip; no runtime or trading behavior was changed.
- A second pre-existing `record_result` call remains isolated to the multi-broker simulated-fill
  branch. TASK-0150 limits its correction to repository tests and the existing terminal transition;
  no paper order, real order, or runtime action is permitted.

- TASK-0149's first unit restores exact terminal journal identity resolution: one unique exchange
  order ID maps to its existing lifecycle reference, while missing/ambiguous matches remain
  unchanged. Reconciliation now uses the journal's supported `record_terminal` transition instead
  of the nonexistent `record_result`; 21 focused tests pass and the full suite remains.

- TASK-0148 is COMPLETE and runtime-disabled. Real temporary snapshot/ledger tests validate the
  end-to-end terminal chain, null preservation, restart idempotency, corrupt/ambiguous identity
  rejection, selector call invariants, and observer failure isolation. Nineteen focused tests and
  the full 830-test suite pass with one optional import-linter skip; no production artifacts exist.
- TASK-0148 also confirms a pre-existing terminal journal-sync mismatch: reconciliation calls
  `live_order_journal.record_result`, which the current journal does not expose. The caught failure
  does not stop closure handling, but terminal synchronization is ineffective. TASK-0149 freezes a
  minimal repository-only correction before any forward-evidence runtime gate.

- TASK-0148's first disconnected unit uses the real snapshot and ledger on temporary paths. It
  validates complete and incomplete terminal evidence, restart idempotency, ambiguous identities,
  corrupt snapshots, null preservation, and persisted lifecycle transitions. Seventeen focused
  tests pass; selector-level failure injection and the full suite remain.

- TASK-0148 freezes the final repository-only gate before any forward exit-data deployment can be
  considered: real identity snapshot, terminal extractor, exit ledger, and reconciliation closure
  must work together only on temporary paths, remain restart-idempotent, preserve null unknowns,
  and isolate every storage/observer failure from operational reconciliation.

- TASK-0147 is COMPLETE at repository level and remains runtime-disabled. The reconciliation
  service can optionally resolve one exact open identity from its already-selected terminal order,
  emit null-preserving terminal evidence, and advance lifecycle state without adding broker calls
  or changing operational closure behavior. Twenty-three focused tests and the full 824-test suite
  pass with one optional import-linter skip; no production snapshot or exit ledger was created.

- TASK-0147 freezes the optional reconciliation boundary: reuse the existing history call and order
  selector, resolve one exact open identity, emit admitted terminal evidence, and advance identity
  completeness without altering operational reconciliation. Missing/ambiguous evidence and observer
  failures remain observational; runtime and production storage stay disabled.
- TASK-0146 is COMPLETE and disconnected. Its pure extractor fail-closes unknown identity/side or
  symbol mismatches and admits fill economics only from frozen authoritative fields; missing data
  remains null and incomplete. Five focused extractor tests and the full 817-test suite pass with
  one optional import-linter skip. No runtime import, broker call, or production file was added.
- TASK-0145 freezes terminal-field admission from the already-selected reconciliation order. Exact
  symbol/explicit side identity is mandatory; malformed or missing economics remain null, and an
  outcome is complete only with authoritative fill price, quantity, realized PnL, fees, and exchange
  time. Existing mocked terminal fixtures are incomplete and cannot support cost-adjusted outcomes.
- TASK-0144 is COMPLETE at repository level and remains runtime-disabled. ActivePositionManager can
  optionally persist authoritative open identity and update quantity/time without duplication;
  disabled/corrupt/conflicting/ambiguous/write-failure paths cannot change actions or broker calls.
  Eleven focused identity/capture tests and the full 812-test suite pass with one optional
  import-linter skip. No production snapshot or ledger exists.
- TASK-0144 freezes the minimal integration boundary: ActivePositionManager may write authoritative
  open-position identity through an optional store, but the canonical singleton and composition
  roots remain disabled. Store failures must be observational only; no broker calls, reconciliation,
  fills, production files, or prospective boundary are permitted.
- TASK-0143 is COMPLETE and disconnected. The restart-safe identity snapshot enforces deterministic
  IDs, authoritative normalized fields, secret/corruption rejection, atomic replacement, monotonic
  lifecycle/time, and fail-closed ambiguous matching. Five focused identity tests, six ledger tests,
  and the full 806-test suite pass with one optional import-linter skip. No runtime component imports
  it and no production snapshot exists.
- TASK-0142 verifies that terminal-fill integration cannot yet be validly joined. Reconciliation
  persists only active symbols, so side, entry, quantity, leverage, manager position key, and run
  identity are lost at closure; terminal order payloads may also omit fill price, fees, quantity,
  trigger details, or time. Symbol/latest-order matching is ambiguous. TASK-0143 is limited to a
  disconnected, fail-closed identity snapshot contract before any fill observer is allowed.
- TASK-0141 is COMPLETE at repository level and remains runtime-disabled. Existing positive stop
  hydration now records the exact selected order ID/price/source, authoritative leverage, existing
  profit-lock classification, and post-hydration state. It adds no broker call or mutation; observer
  failure is isolated. Thirty-three focused regressions and the full 801-test suite pass with one
  optional import-linter skip; no production ledger file was created.
- TASK-0140 confirms the forward causal chain is still incomplete across restart and terminal fill.
  Existing hydration drops selected stop identity and emits no event; reconciliation is separate and
  drops fill price, quantity, fees, trigger details, and stable manager linkage from the evidence
  contract. TASK-0141 is limited to observing the existing hydration read; runtime must remain off.
- TASK-0139 is COMPLETE at repository level and remains runtime-disabled. Existing stop attempts
  now preserve structured visibility evidence and emit a causal request, response, visibility, and
  post-mutation state-commit chain with collision-free IDs. Broker requests, polls, sleeps, retries,
  stop decisions, and state behavior are unchanged. Thirty focused regressions and the full
  798-test suite pass with one optional import-linter skip; no production ledger file was created.
- TASK-0139's first unit preserves structured evidence from the existing pending-stop query: the
  matched exchange order ID, actual visible stop price, and UTC observation time. The public sync
  result and existing one-poll-success/three-poll-exhaustion behavior are unchanged; 21 focused
  regressions pass.
- TASK-0139 now emits causally linked verified/failed visibility evidence after each accepted
  existing stop attempt without changing broker requests, verification polls, sleeps, or retries.
  Twenty-three focused regressions pass; caller-side state-commit linkage remains.
- TASK-0138 finds TASK-0137 necessary but insufficient for profit-lock inference. The existing
  pending-stop verification discards matched order identity and visible price; local state commits,
  restart hydration, and later exit reconciliation are not causally linked. The next sealed unit
  may expose structured evidence from the existing query and emit visibility/state events without
  adding any broker call or enabling runtime collection.
- TASK-0137 is COMPLETE at repository level and remains runtime-disabled. The optional observer
  records eligible position/manager evaluations plus one causally linked request/response pair for
  every existing stop-sync attempt, including thresholds, accepted result, and response latency.
  It adds no broker request, visibility query, retry, or state mutation. Six focused observer tests
  and the full 793-test suite pass with one optional import-linter skip; no production ledger file
  was created and no composition root enables collection.
- TASK-0137 freezes a repository-only integration boundary: observe existing manager evaluations
  and stop-sync attempts through an optional sink, add no broker calls or retries, keep runtime
  disabled, and defer visibility claims, prospective boundary, and deployment to later gates.
- TASK-0136 rejects immediate `+10/+4-5` threshold tuning as non-distinct: at 10x the existing
  intended +10% trigger and 0.5% price trail already imply about +4.95% locked ROE before friction.
  The 50-position giveback cannot distinguish stop math from cadence, broker visibility, restart,
  slippage, or fill failures. TASK-0137 will connect forward observability without changing policy.
- TASK-0135 repository implementation is COMPLETE. ActivePositionManager now uses per-position
  authoritative leverage and skips all stop mutation when it is unavailable; it cannot substitute
  the prior 10x default. Thirty-four focused tests and the full 787-test suite pass, with one
  optional import-linter skip. Runtime/deployment and VST observation remain unperformed and gated.
- TASK-0135 implementation has started: execution/order contracts carry requested leverage,
  hydrated positions retain validated authoritative leverage and isolated state, and the formatted
  BingX adapter clone preserves the invariant. Six focused contract/hydration tests pass; no broker
  endpoint, runtime, account setting, or order was touched.
- TASK-0135's mocked final admission boundary now establishes isolated mode and configured leverage,
  performs a post-write readback, and fails closed on missing, malformed, stale, cross-margin,
  excessive, conflicting, broker-error, or mismatched state before order execution. Twenty-two
  focused leverage/failure-injection tests pass; no authenticated endpoint was called.
- TASK-0135 now freezes the minimal fail-closed correction boundary and its failure-injection tests,
  and repository-only implementation is now authorized while runtime/deployment remains blocked.
- TASK-0135's implementation map inventories every canonical contract, live Order constructor,
  risk-adjusted clone, BingX admission/hydration boundary, and position-manager consumer. No current
  BingX leverage/margin endpoint exists locally; official semantics must be verified before coding.
- Official BingX references now verify GET/POST margin-mode and side-specific leverage contracts plus
  per-position `leverage`/`isolated` readback. No authenticated endpoint was called and the active
  automation still blocks implementation.
- TASK-0134 implements the disconnected exit-event ledger writer/validator with atomic daily JSONL
  append, secret rejection, causal validation, corruption detection, and deterministic hashes. It is
  not imported by any runtime path and changed no production behavior.
- TASK-0133 freezes the forward exit-observability contract: append-only manager evaluations,
  stop request/response/visibility/state transitions, restart hydration, leverage readback, and exit
  fills. No trailing threshold is selected and no production path changed.
- TASK-0132 verifies a P0 fail-open leverage defect: configured `max_leverage=5.0` is absent from
  ExecutionIntent/Order/Position, BingX admission neither sets nor verifies exchange leverage,
  hydration drops it, and ActivePositionManager independently assumes 10x. A characterized 10x
  authoritative snapshot is admitted under a mocked 5x configuration. No runtime setting changed.
- Post-C27 synthesis pauses historical candidate creation: available families are rejected or
  already assigned to C-11 prospective confirmation, and no unopened mechanism currently clears
  the sequential admission gate. Next work moves to authoritative leverage correctness and the
  event observability required for a future forward profit-lock comparison.
- C-27 concentrated-aggressor exhaustion is REJECTED: 186 primary trades had -0.3418% expectancy,
  PF 0.2533, and a daily-clustered 95% interval wholly below zero. Every fold, both sides, both
  primary years, and the 2024 temporal reverse were negative; even gross expectancy before the
  frozen 0.30% cost was negative. No threshold or direction variant is admitted on this panel.
- TASK-0128's data gate is KEEP: all 972 expected official BTCUSDT aggregate-trade archives were
  checksum verified and produced 93,312 complete native 15-minute rows from 2024-01-01 through
  2026-08-29. Core integrity violations and missing intervals are zero, the normalized SHA-256 is
  `3e5975b6e1369685877c57944375a330548515ce7eb064f240b3c81885ef9edf`, and the 20 GiB storage
  reserve was preserved. No trading outcome was opened.
- TASK-0129 read-only exit audit reconstructed the latest 50 completed BingX VST positions. In a
  10x sensitivity view, 23 reached estimated MFE >=10% ROE, 19 reached >=12%, and 14 reached >=10%
  before exiting below +5% net ROE; nine finished between +2% and +5%. Forty-eight exits were
  `STOP_MARKET` and two were `TAKE_PROFIT_MARKET`. One-minute candle extremes make MFE/MAE estimates,
  not proof that the manager observed the extreme or successfully amended the exchange stop.
- BingX `allOrders` omitted historical leverage. All three currently open VST positions report 10x,
  while loaded risk settings report `max_leverage=5.0` and ActivePositionManager models ROE with a
  hard-coded default 10x. Add a separate fail-closed leverage-consistency audit; do not change live
  leverage or trailing thresholds from this diagnostic sample.

- Post-TASK-0127 synthesis retains the full-corpus NO_GO but finds a bounded BTC-only panel feasible:
  2024–2026 compressed size is 18.35 GB (~17.1 GiB). Dates and acquisition-only features are frozen
  before inspection; TASK-0128 must preserve the 20 GiB reserve and cannot define an outcome.
- TASK-0127 is NO_GO under the frozen storage gate: complete BTC/ETH aggTrades coverage exists and
  sample checksums/schema pass, but the compressed corpus is ~45.8 GiB and cannot coexist with the
  required 20 GiB reserve on ~57.9 GiB free storage. No bulk download or outcome was opened.
- Post-C26 synthesis forbids response-band/horizon/symbol variants and pauses candidate churn.
  TASK-0127 evaluates a genuinely richer aggregate-trade source using listings and minimal schema
  samples only, with a storage gate before any bulk download.
- C-26 is preregistered with outcome unopened: exact completed UTC-hour BTC shocks above causal
  p95/720 and 1.50%, same-direction alt response ratio 0–0.35, next-open directional alt entry,
  exact four-hour exit, actual funding, 0.30% cost, clustered uncertainty, and frozen gates.
- Post-C25 synthesis closes direct basis convergence and admits causal BTC-lead/alt-underreaction
  as the next distinct market-context family. No conditional membership has been computed; one
  complete specification must be frozen before evaluation.
- C-25 is preregistered with outcome unopened. It preserves C-24's p99/2,880, 0.40% floor,
  two-leg execution, convergence/timeout, funding, costs, periods, bootstrap, and gates unchanged;
  only the disjoint five-symbol universe and its breadth denominator differ.
- TASK-0123 data gate is KEEP: 6,685 checksum-verified spot archives yielded 128,346 complete
  rows per DOGE/LINK/LTC/DOT/AVAX, zero core violations, explicit maintenance gaps, and exact
  alignment of every retained timestamp to the C-22 futures panel. No C-25 outcome was opened.
- Post-C24 synthesis permits exactly one unchanged, disjoint confirmation on DOGE/LINK/LTC/DOT/
  AVAX. C-24's sparse positive cells remain rejected; no threshold, horizon, exit, cost, or symbol
  slice may change. TASK-0123 is data acquisition only and cannot open conditional outcomes.
- C-24 is preregistered with outcome unopened: positive basis above causal prior-2,880 p99 and
  0.40%, next-open LONG spot/SHORT perpetual, causal convergence-or-24h exit, actual funding,
  two-unit capital normalization, clustered bootstrap, reverse period, and frozen stability gates.
- Post-C23 synthesis is complete. Funding-persistence variants are barred; the next admitted
  independent family is direct delta-neutral spot/perpetual basis convergence. It differs from
  directional C-20 and funding-selected C-23 and is enabled by TASK-0118's official spot panel.
- TASK-0118's official spot data gate is KEEP. C-23 is now preregistered with outcome unopened:
  equal-notional LONG spot/SHORT perpetual after causally unusual positive completed funding,
  next-open execution through the next settlement, explicit two-unit capital normalization, and
  clustered uncertainty.

- Generic profit-lock behavior was observed after runtime reload on ETHUSDT and BNBUSDT:
  their exchange-side stops moved beyond entry in the profitable direction without manual or
  symbol-specific intervention.
- The manager now waits for broker-side order visibility before local success, starts its loop
  after `is_running` is set, isolates broker failures, prioritizes BingX VST, and hydrates the
  exchange stop after a restart.
- Latest read-only VST coverage check: 10 open positions, each with one exchange-side
  `STOP_MARKET` and one `TAKE_PROFIT_MARKET` order. Coverage is not treated as proof of
  a profit lock.
- Final entry admission now reads authoritative BingX positions and atomically enforces
  capacity, duplicate-symbol, exposure, cooldown, order-risk, and stop requirements at the
  broker boundary. A dry live check failed closed at the configured 10-position capacity.

## Changes made

- `8c09624` verify pending exchange stops before local success.
- `43afd7b` start background protection loops reliably.
- `8cd80e1` isolate non-primary broker failures.
- `25d069f` prioritize BingX VST protection checks.
- `f649444` hydrate existing exchange stops after restart.
- `700c748` enforce dynamic blacklist at the final broker boundary.
- `b7cc9c3` keep the empty-opportunity loop idle-safe.
- `7418c7d` enforce broker-backed final entry risk admission.

## Test evidence

- TASK-0134 disconnected ledger suite: 6 passed, covering deterministic append/validation,
  corruption, duplicates, timestamps, sensitive fields, causal references, state commits, and
  concurrent writers. Full post-task suite: 773 passed, 1 optional layering test skipped.
- TASK-0132 focused leverage/risk-admission characterization: 25 passed; the three new tests prove
  leverage is absent from Order/Position, a 10x authoritative snapshot does not fail against a
  mocked 5x configuration, and ActivePositionManager independently defaults to 10x.
- C-27 full post-outcome suite: 764 passed, 1 optional layering test skipped (`import-linter` is
  not installed locally).
- C-27 pre-outcome focused suite: 5 passed for causal threshold exclusion, signal conjunction,
  reversal direction, next-open/exact-four-hour execution, funding sign, missing paths, and costs.
- Focused active-position regression tests: 11 passed after the restart-hydration correction.
- Full post-correction suite: 622 passed, 1 optional layering test skipped
  (`import-linter` is not installed locally). This includes 461 unit, 109
  characterization/contract, and 52 smoke/E2E tests.
- Final TASK-0092 suite: 637 passed, 1 optional layering test skipped; this includes four
  focused C-01/C-02/C-03 evaluator regressions.
- Final TASK-0093 suite: 642 passed, 1 optional layering test skipped; this includes five
  focused cross-sectional leakage/execution regressions.
- TASK-0094 acquisition suite: 646 passed, 1 optional layering test skipped; this includes four
  pagination/range/integrity regressions.
- TASK-0095 suite: 651 passed, 1 optional layering test skipped; this includes five C-06
  point-in-time/execution regressions.
- TASK-0096 suite: 656 passed, 1 optional layering test skipped; this includes five C-07
  causality/state/execution regressions.
- TASK-0097 suite: 661 passed, 1 optional layering test skipped; this includes five C-08
  causality/pair-execution regressions.
- TASK-0098 suite: 667 passed, 1 optional layering test skipped; this includes the parameterized
  holdout acquisition and five C-09 causality/execution regressions.
- TASK-0099 suite: 676 passed, 1 optional layering test skipped; this includes four funding
  acquisition and five C-10 causal/economic regressions.
- TASK-0100 collector suite: 680 passed, 1 optional layering test skipped; first prospective
  update correctly remained COLLECTING with N=0 and no pre-boundary leakage.
- TASK-0101 suite: 684 passed, 1 optional layering test skipped; this includes the parameterized
  funding acquisition and C-12 evaluator boundary regressions.
- TASK-0102 suite: 685 passed, 1 optional layering test skipped; C-13 reused the frozen C-12
  mechanics with only report identity and dataset paths parameterized.
- TASK-0103 suite: 689 passed, 1 optional layering test skipped; four C-14 tests cover causal
  daily aggregation, next-open entry, the fixed 28-day exit, future mutation, and costs.
- TASK-0104 suite: 692 passed, 1 optional layering test skipped; C-15 adds custom-universe
  acquisition, disjoint-universe, and pre-admission LONG filtering coverage.
- TASK-0106 suite: 697 passed, 1 optional layering test skipped; five OI acquisition tests cover
  checksum binding/resume, exact/conflicting duplicates, and optional-ratio missingness.
- TASK-0107 suite: 701 passed, 1 optional layering test skipped; four C-16 tests cover strict
  pre-decision alignment, current-observation exclusion, next-open/24h execution, funding sign,
  and cost application.
- TASK-0108 suite: 704 passed, 1 optional layering test skipped; C-17 adds new-universe
  disjointness, OI-contraction construction, and explicit acquisition-task provenance coverage.
- TASK-0109 focused suite: 12 passed. The official book-depth panel retained 380,974–381,838
  normalized five-minute rows per symbol from 8,002 checksum-verified archives, with zero final
  integrity violations. Decimal-rendered integer levels and later official fractional extra levels
  have explicit regression coverage.
- TASK-0110 focused suite: 10 passed across C-18 causality/execution and TASK-0109 acquisition
  regressions. C-18 uses strict pre-decision book alignment, causal thresholds, prior-bar 24-hour
  close, correct funding sign, and an explicit minimum-sample gate.
- TASK-0112 focused acquisition suite: 5 passed. The premium-index panel retained 205,981–233,560
  unique 15-minute rows per symbol from 14,101 checksum-verified archives, with zero core integrity
  violations and explicit unfilled source gaps.
- TASK-0114 acquisition: 8,022 checksum-verified archives produced exactly 128,352 aligned native
  15-minute taker-flow rows per symbol, with zero schema/timestamp/OHLC/flow/duplicate/gap violations.
- TASK-0118 acquisition: 8,022 checksum-verified official spot archives produced 128,346 complete
  native 15-minute rows per symbol. Core integrity violations are zero; one common partial
  maintenance candle per symbol was excluded, all 36 resulting source gaps remain explicit, and
  every retained timestamp aligns to the futures panel. The frozen data gate is KEEP.

## Rejected hypotheses

- Higher win rate alone is not evidence of an edge.
- Adding new strategies, ML, or capital scaling before attribution/OOS evidence is not justified.
- C-04 VWAP reversal: all four folds, all symbols, and both sides were negative after costs.
- C-01 trend BUY and C-03 volatility breakout: negative aggregate expectancy and failed
  stability gates.
- C-02 trend SELL: positive aggregate expectancy (+0.5389%, N=17) but insufficient fold
  samples, negative BTC expectancy, and ETH dependence; rejected for robustness.
- C-05 cross-sectional momentum: only 9 completed trades survived the frozen 30-symbol
  alignment rule; expectancy -3.8162%, PF 0.1982, and 95% cluster CI crosses zero. Rejected
  without lowering the threshold post-result.
- C-06 market-neutral extreme reversal: 15,810 pairs, -0.2999% net expectancy, PF 0.1345,
  bootstrap CI entirely negative, all folds/sides/symbols negative. Gross expectancy is
  effectively zero and the candidate is rejected.
- C-07 volume-confirmed acceleration: 8,245 trades, -0.2834% net expectancy, PF 0.6331,
  confidence interval entirely negative, all folds/sides/symbols/volume buckets negative.
- C-08 daily relative-strength pair: 559 pairs, -0.0738% net expectancy and PF 0.9124 at
  primary cost; only one fold positive. LONG/BTC-positive cells are clues discovered post-result
  and cannot be validated by re-slicing the same four folds.
- C-09 independent long/BTC-positive holdout: 135 trades, -0.3000% net expectancy, PF 0.8854,
  only one positive fold, and effectively zero gross expectancy. The C-08 clue did not reproduce.
- C-10 causal extreme-negative funding: aggregate +0.2008%, PF 1.1175, and all four folds
  positive, but CI crosses zero and ETH is slightly negative. Frozen gate rejects; post-result
  severity >=2 is retained only for a new prospective cohort.
- C-12 cross-symbol funding generalization: 455 trades, +0.5403% expectancy, PF 1.2763, all
  four folds and all three symbols positive, and 39.91% concentration. The bootstrap 95% lower
  bound was -0.0549%, so the preregistered confidence gate rejects despite broad stability.
- C-13 unchanged temporal generalization: 628 trades, -0.0595% expectancy and PF 0.9555 at
  0.30% cost; only two folds and XRP were positive. The later sample falsifies temporal
  stability of the base negative-funding rebound rule.
- C-14 long-horizon time-series momentum: the reverse-time period was strongly positive, but
  the primary 2023–2026 sample had 228 trades, -2.5269% expectancy, PF 0.7286, and only one
  positive fold. The signal is temporally unstable and rejected.
- C-15 independent LONG holdout: +1.4752% expectancy and PF 1.1504 over 82 trades, but CI crossed
  zero, only one adequately sampled fold was positive, only two adequately sampled symbols
  were positive, and concentration exceeded its ceiling. Rejected for robustness.
- C-16 OI-confirmed impulse: 2,471 primary trades, -0.1763% funding-inclusive expectancy,
  PF 0.8818, all four folds negative, only XRP positive, and reverse-time expectancy negative.
  The intended OI expansion/continuation mechanism is rejected.
- C-17 OI-flush reversal: 2,124 primary trades, -0.3546% expectancy, PF 0.7983, CI fully below
  zero, and every fold/side/symbol negative. A new universe independently rejects the distinct
  OI contraction/reversal mechanism.
- C-18 near-book depth continuation: 2,154 primary trades, -0.3568% funding-inclusive expectancy,
  PF 0.7685, CI fully below zero, and every fold/side/symbol negative. The 2023 temporal reverse
  sample was also negative (-0.2313%, PF 0.8230, N=726). This exact L2 continuation mechanism is
  rejected without post-result slicing.
- C-19 liquidity-withdrawal differential: 1,973 primary trades, -0.3533% expectancy, PF 0.7720,
  CI fully below zero, every fold and both sides negative, and only ETH positive. The temporal
  reverse was also negative (-0.3631%, PF 0.7368, N=668). The dynamic near-book mechanism is closed.
- C-20 symmetric premium-basis convergence: 1,264 primary trades, -0.2721% funding-inclusive
  expectancy, PF 0.8125, and every fold/side/symbol negative. The 2023 reverse sample was positive
  (+0.2649%, PF 1.2297, N=490), so the mechanism is temporally unstable and rejected.
- C-21 aggressive taker-flow continuation: 2,326 primary trades, -0.2086% expectancy, PF 0.8384,
  CI fully below zero, and all four folds negative. Reverse-time was also negative (-0.3853%,
  PF 0.6827, N=831); narrow LONG/ETH cells are diagnostic only and not promoted.
- C-22 independent taker-flow confirmation: 1,928 primary trades, -0.1770% expectancy, PF 0.8906,
  only 2/4 folds and 1/5 symbols positive; reverse was -0.4288% with PF 0.7015. This second disjoint
  failure closes taker-flow continuation under the sequential policy.
- C-23 delta-neutral positive-funding carry: 3,407 primary pairs, -0.1914% net expectancy at the
  frozen 0.20% capital cost, PF 0, clustered CI fully negative, and every fold/symbol negative.
  Gross basis plus funding was only +0.0086%; reverse 2023 was also negative (-0.1902%, N=1,033).
  The unlevered next-settlement carry mechanism is rejected as economically unable to clear costs.
- C-24 delta-neutral basis convergence: the frozen >0.40%/causal-p99 signal produced only seven
  primary pairs. Net expectancy was +0.1038% with a positive clustered interval, but every minimum
  sample/breadth gate failed and reverse N was only two. The sparse result is rejected and its
  threshold cannot be relaxed on the opened panel.
- C-25 unchanged independent basis convergence: only two primary pairs survived, both DOGE, with
  +0.3117% expectancy; reverse had zero pairs. Sample, breadth, concentration, PF, and reverse gates
  failed. Together with C-24, this closes direct basis convergence without threshold relaxation.
- C-26 BTC-lead/alt-underreaction: 103 primary trades, -0.2102% expectancy, PF 0.744, CI crossing
  zero, and only one positive fold. Reverse 2023 was -0.9667%, PF 0.238, with every fold/side/symbol
  negative. The frozen market-context propagation candidate is rejected.
- C-27 concentrated-aggressor exhaustion: 186 primary trades, -0.3418% expectancy, PF 0.2533,
  clustered CI fully below zero, and every fold/side/year negative. Reverse 2024 was -0.4978%,
  PF 0.1936, N=71. The exact large-trade concentration reversal is rejected without variants.

## Open risks

- Recent exit evidence is consistent with profit giveback after favorable excursion. Required
  follow-up: correlate manager evaluation timestamps, submitted/replaced stop prices, exchange order
  visibility, mark-price trigger semantics, fills/slippage, and restart hydration for each position.
  Preregister any +10/+12 trigger and +4/+5 lock comparison on a separate forward/OOS sample.
- Exchange leverage currently reports 10x on open VST positions despite a loaded 5x local risk cap;
  the authoritative leverage-set/admission path has not yet been proven fail-closed.

- The current historical files do not provide point-in-time funding or bid/ask observations;
  frozen cost assumptions must remain explicit.
- Initial candidates have small samples under path-dependent execution; positive-looking narrow
  cells cannot be promoted without robust OOS support.
- The stored 15m universe is fragmented: 915/920 four-hour decision timestamps failed C-05's
  preregistered minimum of 30 symbols after contiguous-history validation.
- The existing `fetch_long_history.py`/`BinanceClient` path calls Spot `/api/v3/klines`, not
  USDT-margined perpetual futures; it cannot silently supply the next futures experiment.
- TASK-0094 acquired 128,352 exactly aligned native futures 15m bars per symbol across six
  majors (2023-01-01 through 2026-08-29), with zero gaps or integrity violations.
- TASK-0109 retained the official ten-level historical book-depth panel. The archive later adds
  `-0.20/+0.20` levels; they are censused but excluded from the frozen panel. Cadence gaps remain
  explicit and no observations are synthesized.
- Existing project-context documents outside the active task/ledger may contain stale claims.

## Next task

Keep TASK-0151's forward-only exit-evidence cohort collecting under its frozen gates while the
engineering loop continues with the next independent, preregistered profitability hypothesis.
Do not tune exit thresholds from the opened cohort or spend roadmap cycles on leverage refinement
unless new evidence shows that it blocks valid edge measurement.

## 2026-09-06 — TASK-0166 C-33 collection auditor

- Added a deterministic read-only auditor for the active prospective C-33 append-only ledger.
- It fail-closes on activation-boundary, manifest, key, raw-hash, lifecycle, universe, or timestamp
  violations and treats incomplete liveness buckets as missing rather than zero activity.
- Live snapshot: `COLLECTING`, seven eligible completed five-minute buckets, one expected partial
  activation bucket excluded, and two eligible observed forced-liquidation snapshots. No threshold,
  signal, trade, or outcome gate has been opened.
- Verification: 4 focused tests passed; full suite 920 passed with one optional import-linter skip.
- Next: TASK-0167 forward-only warmup materializer specification while collection continues.

## 2026-09-06 — TASK-0167 C-33 forward warmup materializer

- Added a deterministic snapshot-bound materializer for eligible completed C-33 five-minute buckets.
- Every eligible bucket expands across the six frozen symbols; verified liveness silence is represented
  as explicit zero BUY/SELL observed snapshot activity, while incomplete buckets remain absent.
- No percentile, dominance, signal, trade, funding, or outcome calculation is opened.
- Focused verification: 6 auditor/materializer tests passed. Live snapshot remains `COLLECTING` with
  19 eligible buckets and 114 bucket-symbol rows at the captured read.
- Next: TASK-0168 reproducible live warmup artifact and continued forward collection toward 8,640
  eligible buckets per symbol.

## 2026-09-06 — TASK-0168 C-33 live warmup snapshot

- Committed the first reproducible C-33 warmup artifact, bound to exact event-source SHA-256
  `c72b3e2207e6873c66ae5084baea432d84ed3c9211a5e48cee69c2bc35ac06bb`.
- Snapshot contains 25 eligible completed buckets and 150 exact bucket-symbol rows. Of 175 stored
  liquidation snapshots, 170 are in eligible buckets; excluded partial-bucket events remain absent.
- Eligible observed notional is 901,832.46278 USDT across 54 non-zero bucket-symbol rows. This is
  collection evidence only, not an edge result; `COLLECTING` remains mandatory.
- Next: TASK-0169 deterministic committed-snapshot verification without opening thresholds/signals.

## 2026-09-06 — TASK-0169 C-33 snapshot verifier

- Added a deterministic offline verifier for committed C-33 warmup artifacts, including exact schema,
  frozen universe, UTC bucket boundaries, row uniqueness/order, digest format, and count/notional checks.
- TASK-0168 independently verifies at 25 buckets, 150 rows, 170 eligible observed snapshots, and
  901,832.46278 USDT observed notional; verdict remains `COLLECTING`.
- Verification: 12 focused tests and the full 928-test suite pass; one optional import-linter check is skipped.
- Next: TASK-0170 sparse milestone cadence so C-33 collection does not consume the edge roadmap with
  repetitive audits while its prospective warmup matures.

## 2026-09-06 — TASK-0170 C-33 sparse checkpoint cadence

- Frozen evidence milestones: 25, 100, 500, 1,000, 2,000, 4,000, 8,000, and 8,640 eligible buckets.
- The checker verifies the prior committed artifact and fails closed on count regression; it never
  writes a snapshot or opens signal/outcome calculations.
- The 25-bucket checkpoint is complete. Until 100 buckets, C-33 returns to quiet liveness/error
  monitoring so the roadmap can resume independent profitability research.
- Live check: 38 eligible buckets; no checkpoint due. Nineteen focused tests and the full 935-test
  suite pass, with one optional import-linter skip.
- Next: TASK-0171 select a genuinely independent candidate from unused causal mechanisms/data.

## 2026-09-06 — TASK-0171 next independent edge selection

- Selected C-34 cross-venue aggressive-flow divergence; no conditional outcome was opened.
- The candidate uses the previously unused causal disagreement between Spot and USD-M perpetual
  taker-buy shares. It is not a threshold/horizon/symbol variant of rejected single-venue taker flow
  and does not reuse C-31's nonexistent price-underreaction state.
- Official aligned Spot and futures flow panels can support strict point-in-time reconstruction,
  explicit source gaps, exact funding, and 0.30%/0.50% cost evaluation.
- Next: TASK-0172 freeze the single C-34 specification and all robustness/rejection gates before
  calculating any forward return.

## 2026-09-06 — TASK-0172 preregister C-34 cross-venue flow divergence

- Committed Edge Candidate Register v33 before opening any C-34 conditional outcome.
- Frozen one exact Spot-versus-futures aggressive-flow disagreement signal, causal prior-180 p90
  thresholds, Spot direction, exact next-open/24-hour execution, funding, 0.30% primary/0.50% stress
  cost, temporal folds/reverse, clustered uncertainty, breadth, concentration, and drawdown gates.
- All 24 Spot/futures-flow/perpetual-price/funding file hashes and strict missing-data rules are bound.
- Before any outcome opened, manifest content digests were replaced by actual full compressed-file
  digests; no candidate mechanic changed.
- Next: TASK-0173 implement the evaluator unchanged with hash-first and causality/execution tests.

## 2026-09-06 — TASK-0173 implement C-34 evaluator

- Implemented register v33 without opening frozen panel outcomes.
- Hash-first enforcement, exact completed-window alignment, prior-only p90 thresholds, opposition,
  direction, 24-hour next-open execution, funding, costs, folds, daily clustering, and all frozen
  gates are explicit.
- Next: TASK-0174 independent implementation review and tests before the one authorized outcome run.

## 2026-09-06 — TASK-0174 review and open C-34

- Seven focused regressions and the full 942-test suite passed (one optional import-linter skip)
  before the frozen outcome run.
- C-34 is **REJECTED**: primary N=688, expectancy -0.2800%, PF 0.7733, daily-clustered 95% CI
  [-0.5296%, -0.0341%], only one positive fold, both sides negative, all years negative, and four of
  six symbols negative. Reverse 2023 was also negative (-0.2987%, PF 0.7210, N=267).
- Even 0.20% friction remained negative (-0.1800%); 0.50% produced -0.4800%. Concentration passed
  but cannot rescue the negative economics. Report reproduced byte-for-byte.
- C-11's due update added no record; all funding timestamps remain strictly post-boundary and its
  verdict remains `COLLECTING` at N=1.
- Next: TASK-0175 cross-family synthesis and historical-research stop/admission decision.

## 2026-09-06 — TASK-0175 cross-family historical stop decision

- **STOP CURRENT HISTORICAL PANEL:** no candidate passed all frozen profitability, uncertainty,
  temporal, breadth, concentration, drawdown, and stress-cost gates.
- Further combinations or threshold/symbol/direction/horizon variants on the opened price, volume,
  funding, OI, depth, basis, positioning, taker-flow, and Spot/perpetual panels are now disallowed as
  insufficiently independent and too exposed to data snooping.
- This does not stop the objective: C-11, C-33, and the forward exit-management cohort continue under
  their prospective gates.
- A new historical candidate requires a genuinely new public point-in-time source, distinct mechanism,
  executable economics, reliable timestamps, and unopened boundary.
- Next: TASK-0176 new-source feasibility review; select at most one defensible source or record
  `NO_ADMISSIBLE_SOURCE` without manufacturing another hypothesis.

## 2026-09-06 — TASK-0176 new public source feasibility review

- Verdict `NO_ADMISSIBLE_SOURCE`; no C-35 was created and no outcome/data endpoint was opened.
- Deribit DVOL history lacks the executable historical option surface needed for an options-premium
  test; DVOL as a directional filter would reuse opened BTC outcomes.
- Binance dated/COIN-M futures remains an already tested basis/carry family and adds multiplier,
  lifecycle, roll, and synchronized-depth requirements.
- Public stablecoin history lacks established immutable point-in-time revision/publication metadata;
  stronger flow endpoints are paid and therefore approval-gated.
- Next: TASK-0177 audit the active forward-exit cohort against frozen coverage/linkage gates and the
  operator's profit-giveback concern without changing the +5% policy.

## 2026-09-06 — TASK-0177 active forward-exit cohort audit

- The cohort remains `COLLECTING`: 4,356 prospective events cover 14 identities but
  no completed position yet, so no exit-profitability verdict is possible.
- Four accepted stop replacements have complete visibility/commit chains, but 11 of
  15 responses were rejected and mutation latency reached roughly 248 seconds.
- Recorded attempts include a nonexistent `UNIUSDT` position plus invalid stop-price
  and timestamp responses. Below-6%-ROE LINK/BCH attempts were subsequently attributed
  to the separate intended three-hour time-decay rule, not a leverage defect. None of
  this is proof for a new 5% floor.
- Next: TASK-0178 read-only source/event diagnosis of leverage attribution, stale
  positions, stop validation, and latency before any code or policy change.

## 2026-09-06 — TASK-0178 forward-exit mutation latency diagnosis

- Corrected TASK-0177 attribution: the below-6% LINK/BCH breakeven requests came from
  the intended three-hour time-decay rule (1.75% fee-coverage ROE at observed 5x), not
  from incorrect leverage selection.
- Diagnosed the execution concern as a synchronous queue/retry problem: all BingX
  traffic shares a five-request-per-minute blocking token bucket, stop replacement is
  serial, and manager/adapter/HTTP retry layers can nest.
- The failed UNI sequence alone occupied roughly 235.5 seconds. Position and mark
  price are not refreshed immediately before later submissions, explaining stale
  `position not exist` and invalid stop-price responses without proving exchange fault.
- Status: `DIAGNOSED_NOT_FIXED`; this can contaminate exit-edge measurement and must
  be bounded before a 5% profit-floor experiment. Next: TASK-0179 minimal fail-closed
  correction specification and tests, with no deployment or threshold change.

## 2026-09-06 — TASK-0179 fail-closed stop-mutation contract

- Froze a minimal correction contract without changing exit policy: one global BingX
  capacity, FIFO priority for trade mutations, bounded queue admission, and terminal
  stale-snapshot error classification.
- `position not exist` and wrong-side stop-price errors must stop immediately and wait
  for a fresh evaluation; timestamp failures get at most one newly signed retry.
- Existing protective stops cannot be cancelled on queue, transport, stale-position,
  invalid-price, or ambiguous failures. State still advances only after exact broker
  visibility and commit evidence.
- Added explicit queue/adapter/total latency and retry-decision telemetry requirements.
- Next: TASK-0180 implement deterministic tests and the minimal source change; no
  threshold change, broker access, runtime reload, or deployment.

## 2026-09-06 — TASK-0180 extended BingX exit audit preregistration

- Preregistered the operator-requested extension before reopening outcomes: latest 100
  reconstructable VST positions, with 150 allowed only if the same response already
  contains them.
- Froze a newest-50 versus older-50 temporal comparison and the existing net/MFE/MAE,
  giveback, exit-type, side, symbol, concentration, and friction-aware diagnostics.
- Historical leverage absence and one-minute excursion limitations remain explicit.
  This audit cannot select or deploy a 5% floor from its own result.
- Next: perform one read-only acquisition and then resume implementation of the bounded
  stop-mutation correction from TASK-0179.

## 2026-09-06 — TASK-0180 extended BingX exit audit outcome

- The official maximum single response reconstructed 98 completed VST positions;
  this remains explicitly short of the preregistered N=100 target.
- Persistent giveback is supported diagnostically: 56/98 reached estimated 10x MFE
  >=10%, and 27 of those exited below +5%. Median estimated MFE was +11.61%, median
  net exit +2.29%, and median giveback 10.19 points.
- Persistence held across temporal blocks: newest 49 had 12 giveback cases and older
  49 had 15; their median giveback was 10.10 versus 10.26 points.
- Aggregate realized net PnL was +6.001067 with PF 1.6088, but the older block was
  much weaker, SHORT aggregate was negative, and symbol contribution was uneven.
- All 98 historical leverage fields were absent and MFE uses one-minute extremes.
  Result: `PERSISTENT_GIVEBACK_DIAGNOSTIC`, not evidence selecting a 5% policy.
- Post-result provenance clarification: the operator confirmed every scoped trade was
  10x isolated and verified in the BingX account. The 10x metrics therefore match the
  stated account policy, although the archived `allOrders` artifact cannot independently
  reproduce leverage because its per-trade fields remain absent.
- Next: resume the bounded stop-mutation correction; use the prospective lifecycle
  cohort for any future frozen exit-policy comparison.

## 2026-09-06 — TASK-0181 stop-failure classification primitive

- Added a pure fail-closed classifier with no broker or retry behavior change.
- Stale position/side/price failures are terminal, timestamp invalid/expired is the
  sole retryable class, and unknown failures are ambiguous-terminal.
- Next: TASK-0182 consume the classification in synchronization, add telemetry, and
  prove bounded attempts without deployment or threshold changes.

## 2026-09-06 — TASK-0182 bounded stop-retry consumer

- Wired terminal failure classification into stop synchronization without changing
  exit thresholds, leverage, limiter capacity, broker settings, or runtime state.
- Stale/ambiguous failures now defer after one attempt; timestamp failures receive at
  most one newly signed outer retry; adapter exceptions no longer multiply retries.
- Prospective responses now include failure class and retry decision. Exact visibility
  remains mandatory before any local state commit.
- Next: TASK-0183 bounded FIFO priority admission in the existing global limiter.

## 2026-09-07 — TASK-0183 bounded FIFO priority limiter

- Added optional FIFO priority and monotonic timeout to the existing single token
  bucket; ordinary callers remain unchanged and no exchange capacity was increased.
- Priority waiters cannot bypass aggregate capacity and timed-out waiters cannot block
  the queue.
- Next: TASK-0184 wire bounded priority only to stop mutations with stage telemetry
  and failure-injection tests; no runtime reload or broker call.

## 2026-09-07 — TASK-0184 stop priority-admission wiring

- BingX conditional stop POSTs now request FIFO priority from the unchanged global
  bucket with a 15-second local admission deadline.
- Admission timeout fails before HTTP, and queue wait is included in prospective
  response telemetry. Ordinary BingX calls remain non-priority and blocking.
- Repository-only: no runner reload, broker request, account change, capacity increase,
  or exit-policy change occurred.
- Next: TASK-0185 independent review/tests and explicit cohort/deployment decision.

## 2026-09-07 — TASK-0185 stop-admission independent review

- Review found and fixed one capacity-accounting gap: transient HTTP retries previously
  reacquired no token because admission sat outside the retry callback. Every physical
  attempt now consumes the unchanged global capacity and contributes queue timing.
- All frozen retry, priority, visibility, and state-commit invariants are preserved.
- Verdict: `REPOSITORY_READY — DEPLOYMENT_GATED`. The live process still runs old code;
  reload requires a new empty prospective cohort bound to the new commit and explicit
  runtime approval. No runtime or broker action occurred.

## 2026-09-07 — TASK-0186 C-33 100-bucket checkpoint

- Crossed the frozen 100-bucket milestone at 140 eligible five-minute buckets and
  committed a verified 840-row snapshot across all six frozen symbols.
- The snapshot contains 1,179 eligible liquidation records and 25,517,715.59057 USDT
  observed notional; source and artifact hashes are fixed and offline verification is
  valid.
- Verdict remains `COLLECTING`; no signal, threshold, virtual trade, funding, or
  outcome was opened. Next sparse checkpoint is 500 buckets.

## 2026-09-07 — TASK-0187 pre-deployment forward-cohort audit

- The old runtime cohort now has 6,677 events and 43 stop requests: 23 accepted, 20
  rejected, and two accepted NEAR replacements that failed exact visibility before a
  later `position not exist` response.
- ETH/XRP added stale wrong-side stop-price failures; response latency remains roughly
  23–348 seconds even for accepted requests.
- All 21 visible chains committed and the ledger has no structural violation, but the
  operational verdict is `COLLECTING_WITH_RECURRING_EXECUTION_ERRORS`.
- This confirms deployment urgency without changing the approval gate or allowing old
  events into a post-fix cohort.

## 2026-09-07 — TASK-0188 controlled deployment runbook

- Froze the VST-only reload sequence without executing it: exact runner identification,
  final old-cohort audit, graceful stop, new empty commit-bound cohort, existing launcher,
  one-runner/testnet checks, and read-only visible-stop verification.
- C-33 is explicitly excluded from interruption and no policy/settings override is
  permitted.
- Fail-closed aborts cover duplicate runner, live mode, non-empty root, commit mismatch,
  pre-boundary event, historical import, or missing broker-visible protection.
- Status remains `READY — EXPLICIT RUNTIME APPROVAL PENDING`.

## 2026-09-07 — TASK-0189 prospective net-floor preregistration

- Preregistered one shadow-only +12% activation / +5% net-profit-floor candidate
  against the current reviewed policy before any post-fix outcome exists.
- The 98 historical exits and all pre-fix lifecycle events are excluded; no threshold
  variants or post-result symbol/side/regime slices are allowed.
- Frozen gates include actual fees, funding, primary/stress slippage, delayed executable
  stop crossing, paired clustered bootstrap, four time folds, both sides, breadth,
  concentration, drawdown, and tail risk.
- Minimum coverage is 100 paired terminals, 30 +12%-eligible positions, eight weeks,
  five symbols, and both sides. Status is `OUTCOMES UNOPENED — RUNTIME DISABLED`.
- No policy or runtime changed; activation still depends on TASK-0185 deployment approval
  and a new empty cohort.

## 2026-09-07 — TASK-0190 shadow net-floor math

- Implemented disconnected +12% activation and cost-reserved +5% net-floor price math
  for both sides; no cohort or outcome was read.
- The frozen formula requires authoritative 10x leverage, entry/expected-exit fee
  fractions, and 0.10% remaining slippage; invalid or missing inputs fail closed.
- Runtime wiring, policy changes, broker access, and event membership remain absent.
- Next: TASK-0191 causal shadow transitions and subsequent-observation crossing tests.

## 2026-09-07 — TASK-0191 causal shadow transitions

- Added disconnected, strictly ordered shadow state transitions for the frozen
  +12%/+5% candidate.
- Same-observation activation/fill is forbidden; subsequent gaps fill at observed mark;
  baseline and candidate stops remain monotonic for both sides.
- No cohort, outcome, broker, runtime, or production policy was accessed or changed.
- Next: TASK-0192 bind validated post-fix lifecycle events without opening outcomes.

## 2026-09-07 — TASK-0192 shadow lifecycle input binding

- Added hash-first binding for a future post-fix lifecycle snapshot: exact commit/run,
  strict boundary, no historical import, causal schema, order, mark source, frozen
  thresholds, and authoritative 10x leverage all fail closed.
- The binder emits only disconnected state-machine observations; no current cohort,
  membership, fill, PnL, or outcome was opened.
- Next: TASK-0193 per-position grouping and authoritative fee-source contract.

## 2026-09-07 — TASK-0193 shadow fee-provenance gap

- The future shadow policy cannot yet prove its net +5% floor: manager observations
  contain no entry commission/fee rate, hydrated identities commonly lack exchange
  entry linkage, and terminal events expose only exit-order commission.
- Verdict: `DATA_CONTRACT_BLOCKED — ENTRY_FEE_PROVENANCE MISSING`. Guessing zero,
  historical averages, or a hard-coded fee is forbidden.
- Minimal resolution is observational: preserve supplied exchange linkage and admit a
  matching filled entry order/commission before activation; ambiguous evidence excludes
  the position.
- Next: TASK-0194 exact field map and pure disconnected entry-fee extractor. Runtime
  wiring stays behind the existing controlled-reload approval gate.

## 2026-09-07 — TASK-0194 entry-fee evidence extractor

- Added a disconnected fail-closed extractor for one authoritative filled entry order,
  matching position ID when supplied or an explicitly unique symbol/side/price/quantity/
  time composite fallback.
- Ambiguous, post-observation, reduce-only, missing-fee, or cross-position rows are
  excluded; no history endpoint or outcome was opened.
- Entry commission provenance is now representable. Expected exit fee schedule remains
  missing and cannot be silently proxied from the entry fee.
- Next: TASK-0195 explicit pre-activation fee-schedule snapshot contract.

## 2026-09-07 — TASK-0195 fee-schedule snapshot contract

- Added a disconnected fail-closed contract for a sourced BingX perpetual account-tier
  taker-fee schedule captured and effective no later than shadow activation.
- The admitted exit-cost percentage is bound to a canonical SHA-256; wrong market,
  incomplete provenance, invalid rates, non-UTC time, and post-activation evidence fail.
- No broker endpoint, runtime, cohort outcome, strategy, or account setting was accessed.
- Next: TASK-0196 group validated observations and join both fee evidence inputs without
  evaluating terminal outcomes.

## Operator decision required

**NO for TASK-0106.** The operator granted standing authorization on 2026-08-29 for ordinary engineering/research,
verified commits, and controlled VST/paper runtime reloads after pre/post protection checks.
Real funds, secrets, destructive/data-loss operations, security-boundary changes, paid services,
legal/compliance decisions, and irreversible choices remain separately approval-gated. The official
free Binance archive reopens historical OI acquisition without a paid-service or execution decision.
