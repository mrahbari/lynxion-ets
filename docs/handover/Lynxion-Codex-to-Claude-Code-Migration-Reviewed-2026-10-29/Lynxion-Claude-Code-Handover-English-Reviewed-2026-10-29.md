# Lynxion — reviewed Codex to Claude Code handover

Reviewed **2026-10-29 Europe/Stockholm** (UTC evidence 2026-10-28T22:48…22:55Z; package built 2026-10-28T23:10:06.137393+00:00).
This is the current navigation/report layer. The original 26 October package is preserved byte-for-byte under [Historical](Historical/Lynxion-Codex-to-Claude-Code-Migration-2026-10-26.zip); its claims/commands are dated evidence, not current instructions. Persian counterpart: [Lynxion-Claude-Code-Handover-Persian-Reviewed-2026-10-29.md](Lynxion-Claude-Code-Handover-Persian-Reviewed-2026-10-29.md).

## Read this first

The handover is documentation and evidence export, **not a completed product, full code/data backup, runtime deployment or transfer of sole execution ownership**. Primary source baseline is **8e9663136f85b566bdc1bc6d85e4c6b3037ecaf1**; integrated offline main is **1599af9a1932ba25aee252ae76dfa5ad6b050a76**. A containing documentation commit may later advance primary; no main changes were deployed here.

EPIC-01 is now **CLOSED_PARTIAL_DELIVERY: 9 PASS, 21 REMOVED_NOT_DELIVERED, zero active TODO**. The historical 8 PASS / 1 FAIL / 21 BLOCKED is superseded operationally, not erased. One newly completed input-classification deliverable and 21 explicit cancellations settled the list. **Original Trading V1 NOT_DELIVERED; release NO-GO.** Cancelled obligations are not fixes or hidden deferred tasks. The separately retained observed-data/maker/development experiment continues; scientific and P0 safety gates remain.

No matching local Python runner was seen at the 22:48 UTC limited process check. The journal still blocks admission on one `PROTECTION_UNKNOWN`. No fresh broker call, startup, order, reset, deployment, credential change or economic optimization was performed for this handover. A historical PID or terminal `FILLED` label is not evidence of a current runner, broker fill, PnL or protection.

Start with [Claude-Code-Start-Here.md](Claude-Code-Start-Here.md), [six-symbol catalog](Data-Catalog-Six-Symbols.md), [current-state evidence](Evidence/Current-State.json), the current EPIC board and P0 handover below. The historical 11 DONE audit queue was a finite engineering queue, not completion of the whole project.

## Canonical locations and ownership

| Location | Branch / source baseline | Role |
|---|---|---|
| `/Users/mojtaba.rahbari/Sites/python/lynxion-ets` | `task-00-ground-truth-audit` / `8e96631` | Primary runner/config/journal and collected datasets; no matching local runner at the dated check. |
| `/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets` | `main` / `1599af9`, clean at capture | Integrated offline research/backtest/Radar/WFO/maker source; `.env` absent; not runtime deployed. |
| `/Users/mojtaba.rahbari/.codex/worktrees/lynxion-epic-01-trading-v1/lynxion-ets` | `lynx/epic01-trading-v1` / `92218ed` | Earlier 5,150-row inventory source; not latest integration. |
| other worktrees | [exact observed list](Evidence/Git-worktrees.txt) | Historical sources, not independent execution owners or permission to merge in bulk. |

Primary has five pre-existing dirty research files, preserved unstaged: `data/research/c11/prospective_ledger.json`; C35 `candles.jsonl`, `decisions.jsonl`, `funding.jsonl`, `funding_coverage.jsonl`. Their bytes/mtimes/hashes are in Current-State. Their contents and raw journal are not exported. Do not reset, stash away, stage indiscriminately or delete these assets.

The hourly heartbeat `lynxion-p0-execution-recovery-and-opportunity-radar` is **ACTIVE** at capture, target thread `01a0633b-3fbe-70b0-8f07-8d48ba5e3708`. This export does not pause/delete it and the operator has not explicitly granted sole execution ownership to Claude. Begin with read-only status/source/ownership checks and coordinate one writer/launcher before mutation. Follow any later explicit human transfer direction. Do not infer continuous monitoring or work between scheduled runs.

[Repository execution policy](Evidence/Snapshots/primary/AGENTS.md) is retained where present. Routine scoped reversible engineering is authorized; secrets, real funds, destructive/data-loss/security/irreversible decisions remain actual gates. Do not weaken risk/scientific constraints to satisfy a checklist.

## Current canonical documents

- [Current project status](Evidence/Snapshots/primary/docs/LYNXION_CURRENT_STATUS_AND_BLOCKERS.md) — source paths and honest delivery limits.
- [EPIC canonical board](Evidence/Snapshots/main/docs/engineering/LYNXION_EPIC_01_TRADING_V1.md) and [explicit closeout rationale](Evidence/Snapshots/main/docs/engineering/LYNXION_EPIC_01_SCOPE_CLOSEOUT.md).
- [All 30 prior/final decisions](Evidence/Snapshots/main/docs/engineering/evidence/EPIC01_SCOPE_CLOSEOUT.json) and [input eligibility summary](Evidence/Snapshots/main/docs/engineering/evidence/EPIC01_INPUT_ELIGIBILITY_SUMMARY.json).
- [P0 recovery handover](Evidence/Snapshots/main/docs/engineering/POST_PILOT2_EXECUTION_RECOVERY_HANDOVER.md) and [P0 evidence board](Evidence/Snapshots/main/docs/engineering/POST_PILOT2_EXECUTION_RECOVERY_BOARD.md).
- [Canonical R01–R26 registry](Evidence/Snapshots/main/docs/research/LYNXION_RESEARCH_BACKLOG.md) — exact scientific verdicts preserved; dated collector labels do not certify liveness.
- [Frozen observed MTF / maker / economic contract](Evidence/Snapshots/main/docs/research/EPIC01_MTF_MAKER_ECONOMIC_CONTRACT.md) and [actual data/model evidence](Evidence/Snapshots/main/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json).
- [Radar handover](Evidence/Snapshots/main/docs/research/OPPORTUNITY_RADAR_V1_HANDOVER.md) and [Radar frozen contract](Evidence/Snapshots/main/docs/research/OPPORTUNITY_RADAR_V1_CONTRACT.md).
- [Current document index](Evidence/Current-Document-Index.md), [all current historical task files](Evidence/Task-Inventory.md), [snapshot manifest](Evidence/Source-Snapshot-Manifest.json), [exclusions/missing](Evidence/Exclusions-and-Missing.json).

Some source documents deliberately preserve their dated wording. In particular Radar's earlier `T02-S02 BLOCKED`, old contract's 8/1/21 and the original migration's pending `train_window_N` repair are historical. Latest closeout/actual code controls: live shadow port was withdrawn, callback repair completed, separate component work retained.

## P0 — why the runner cannot currently be declared recovered

The check captured 3,014 latest logical journal records: 631 FILLED / 2,315 FAILED / 67 CANCELLED / **1 PROTECTION_UNKNOWN**, zero malformed JSON lines. Terminal labels do not prove fill economics. The unknown record is:

```text
order_ref e554207318004a458b6abf16edc3f39d
UTC 2026-10-24T05:49:22.655564+00:00
TRXUSDT SELL 21.0; purpose PROTECTION; requested stop 0.328502
no returned order_id; no parent entry_order_ref / exact client identity established
```

The dated 26 October bounded GET snapshot showed TRX LONG21 with NEW stop0.32654 / TP0.35153, quantity21. A **different stop** is not exact attribution of the above attempt. Empty bounded histories, zero exact matches and bounded literal/time log searches do not prove rejection or non-submission. Historical terminal FET provenance is also unproven. Do not rerun unchanged exhausted probes without new input or a new hypothesis.

The **current start refusal is understood**: recovery must block while uncertain journal state remains. The **cause of the original runner disappearing remains unproven**; do not confuse the two. Primary has a corrected chained launcher; 13 mocked regressions protect admission/spawn/check-only/failure cases. The old `/private/tmp/lynxion_detached_testnet_launch.py` was defective; do not use it. A prior separate launch after blocked precheck was an error; CLI correctly refused. Never retry start while blocked.

Path A: obtain authoritative exact request/response/order identity evidence, then a reviewed durable recovery disposition preserving raw history. Path B: only if separately and explicitly selected/authorized, prove isolated TESTNET environment retirement/reinitialization preserving the uncertain old epoch. Generic permission is not permission for account reset, credentials change, same-account journal bypass or unknown clearing. Current flatness is not historic attribution.

No autonomous broker calls beyond fresh applicable bounded GET-only scope; no broker writes/manual orders/cancel/replace, journal/cooldown clearing, reset, restart/deployment or real funds. Existing risk policy must remain unchanged. Telegram standalone previously returned401; latest dated probe transport_error leaves current identity/delivery unverified. No token is printed or changed.

## Completed engineering — do not redo it from stale handover text

| Location | Commit | Completed result / proof limit |
|---|---|---|
| primary | cc78232, 35cef1f | Checked TESTNET launcher; 13 dated offline mocked regressions; blocked recovery prevents Popen and check-only cannot launch. No real spawn in those tests. |
| primary | 70e7f88 | Corrected UTC frozen-study status audit; no local C11/C33/C35 collectors matched, files stale since September 24. No sealed outcomes opened. |
| main | 0649178 and earlier | Explicit historical replay clocks; reject unsupported maker intents; factory/wrapper actual-symbol binding. Offline, not deployed. |
| main | 264e6fe | WFO fails when requested assets are missing/empty instead of silently dropping them. |
| main | 80eaad5 | Actual-symbol training-only optimizer/CV composition; no longer passes train_window_N as a symbol. Window labels may remain report identifiers. |
| main | 6e99742 | Missing metric values/objectives no longer become fabricated 0 / PF1. |
| main | 7eab7ae | Frozen named public-data/observed-MTF/maker/economic qualification contract before this acquisition. |
| main | 62eed43, a4edfb5 | Observed-MTF qualifier, conservative event maker model, actual partial-fill accounting entry seam; subminimum partial handling corrected. |
| main | 930464c | Recorded real source structure/coverage and fixed mechanics probes. Not strategy profit. |
| main | ed87642 | T01-S04 completed by 5,158 per-file hash/eligibility decisions; no independent OOS admitted. |
| main | 1599af9 | Scope closeout: nine accepted bounded deliveries, 21 withdrawn undelivered; no active EPIC queue, original V1 NO-GO. |
| primary | 8995ffe, 8e96631 | Current status/navigation aligned to observed data and actual EPIC closeout. |

Latest recorded selected credential-empty/network-denied historical suite: **337 PASS / 27 warnings** in the 28 October source evidence. Prior 314/308/305/290 totals describe earlier source selections. Primary launcher test total13 and Radar/ClosedBarSource/ExtremeMover23PASS/1warning are separately scoped dated results; do not add them or imply one all-project release suite. **No trading test was rerun merely for this export; no independent review of latest patches is claimed.**

The real tape probes were two predetermined separate-direction 0.001 BTC mechanics probes at 00:05 UTC: one modeled BUY fill and eight SELL partials. All nine fill entries passed quantity/fee/cash identities. These are simulated mechanics, not broker fills, exits, funding-complete PnL or actual strategy performance.

## Radar delivered and its boundary

Offline source: `/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/scripts/opportunity_radar_v1.py`. It validates six C06 M15 source files, computes fixed four-bar signed movement and observed-cohort absolute ranks, reports separate completed H1 context, and can attach same-cutoff research setup metadata. It produces one **JSON document with a rows array**, not output JSONL. It does not import live Fusion/StrategyManager or send orders. Setup-input JSONL remains optional.

Latest retained descriptive replay: six rows, `OBSERVED_IN_PANEL_TRADABILITY_UNKNOWN`, hash `00e2826377d2fcd7cc89a906c37030b11026c6d0bf3f053a8a8fac49823c937d`. Optional setup replay hash `5ee1160bc726e9cde48001177e8d97243b82bc13bbc055a87b7b398c8bf9889d`. Descriptive fixed movement ranks and context are not a signal, whole-market historical top movers, executable-cost proof or Edge.

The watcher/screener live shadow port (T02-S02) was **REMOVED_NOT_DELIVERED**, not implemented/accepted. Do not recreate it as a hidden next task. The structural detector's 143 candidates remain development-only; source contracts/manifests and full historical task snapshots are retained. No new whole-market scan/cohort/Pilot-3 is authorized by this migration request.

## Collected six-symbol data — preserve and reuse it

**BTCUSDT / ETHUSDT / SOLUSDT / BNBUSDT / ADAUSDT / XRPUSDT** are the core six. The full [bilingual data catalog](Data-Catalog-Six-Symbols.md) and [machine-readable file catalog](Evidence/Data-Catalog.json) are first-class parts of this handover, not optional footnotes.

The principal C06 M15 directory is `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c06/binance_futures_15m`. Six `<SYMBOL>.csv` files have **128,352 rows each / 770,112 total**, 2023-01-01T00:00Z through last bar open 2026-08-29T23:45Z. Actual row/timestamp scans and byte SHA-256 match. Completed-bar availability is open+15m, not candle open.

| Symbol | Rows | First bar open UTC | Last bar open UTC | File SHA-256 |
|---|---:|---|---|---|
| BTCUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `30e02acebd29a4e47032be70baa7dd3ec0c38a246915fa8329e899edbc07aabb` |
| ETHUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `d44a16a5a7363d6833d0e4e60035acd63826e3e9f65fb3aef260e4c4fde08843` |
| SOLUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `e6efc15ec3544227426076b059bcaec71a2557520d64433f08cea398c554a382` |
| BNBUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `7c9f289c34040f6228f8cdfe415fa045f641b2e7292108bf97bdde34db74c0c0` |
| ADAUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `643dc2f29d3e50fb008391fd4787472836dd88eeab7dd92f71ff0820b5dea79a` |
| XRPUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `89629283deadf39234f7d9cd07ad27f0e378c4c81e6d3a227798494667dcfd57` |

Use existing C09 older six-symbol candles, six-symbol taker flow, ±percent-band bookdepth, OI/ratio panels and documented funding subsets. Exact per-file paths, manifest/source, start/end, gaps, schemas, byte and logical-row hashes are in the catalog. Do not redownload or discard them merely because the gzip byte hash differs from the legacy normalized-row manifest digest: all 18 such canonical-row digests matched in this review. All **43 selected panel file** source hashes matched their declared scope; the two observed raw sample byte hashes also matched.

The existing micro OHLCV folder is `data/history/micro/{1m,5m}` with BTC/ETH/SOL/HYPE/WLD, five each; only three overlap the core six. They do not supply genuine historical BBO/L2. BTC-only raw aggregate trades 2024-01-01…2026-08-29 are separately retained; only their manifest was freshly checked, not every raw daily archive.

The newer observed sample is **only BTCUSDT on 2024-01-01**, under `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/epic01_mtf_maker/qualification_2026-10-28`. Two Tardis public files total 43,631,651 compressed bytes, with observed top-five snapshots/trades and both clocks. 1,440 fresh 1m quotes; 278/288 accepted 5m OBI/delta windows, ten excluded for 52 late trades. It is not six-symbol observed MTF, full exchange queue, continuous capture proof or untouched OOS. Derived hash `ba8305a23447af1c38eff4566a91341765bba2d09336864b00488a730d1600d9`.

Funding coverage must be established per symbol/date; the inspected C10/C12/C13 manifests do not prove BTC-2024 or SOL coverage. Never zero-fill absent funding. Prior six-symbol datasets are already development-opened and selected; full historical universe/independent validation is unqualified. T01-S04 classified inputs; it did not invent positive qualification.

Raw/normalized data are **not embedded in this documentation ZIP**. Claude on this machine must use the original directories. A move to another machine also needs the actual repositories/Git objects/worktrees, ignored public data, frozen assets and operational journal transferred separately under the existing boundaries. Do not recreate a blank journal or assume Git contains ignored datasets. Never put `.env` in a shared package.

## Exact work still unfinished under existing separate authority

This is a continuation map for existing work, not a new backlog or reactivation of withdrawn EPIC promises. Work safe independent units without routine confirmation; record concrete evidence when a true gate blocks a dependent step.

| Existing work | Already completed | Actual remaining output and acceptance gate |
|---|---|---|
| P0 recovery / R14 execution truth | Durable refusal, checked launcher, evidence map, bounded dated broker observations | New authoritative exact-attempt attribution and reviewed durable disposition for the TRX marker, or a separately selected/authorized genuinely isolated environment-retirement decision. No exhausted identical searches, unknown clearing or same-account new-empty-journal bypass. |
| Observed MTF binding | Two public raw files acquired, hashed; strict as-of 1m quotes and 5m OBI/delta qualified structurally | Compose **actual source-frozen** setup families with only eligible completed 5m and M15/H1 context; record exact strategy/feature/model/data/parameter hashes, warmup, decisions and rejection trace before opening economic outcomes. Do not impute the ten excluded 5m windows. |
| Maker strategy accounting | Conservative trade-through pure model; fixed tape probes; `apply_modeled_maker_fill` entry seam and 9 modeled fills accounted | Wire the declared event path through real strategy admission and portfolio lifecycle; account partials/nonfills/expiry, fees, cash/equity, exposure and duplicates. Default OHLCV canonical loop still rejects maker and must not silently relabel it as market. |
| Causal exits / costs | Contract freezes maker/taker/latency/TTL/participation assumptions | Implement/verify post-fill causal SL/TP and exit pricing on real available events/intervals; never use pre-fill candle high/low to exit. Preserve SL-first ambiguity handling, adverse slippage, observed eligible funding and peak-to-trough equity drawdown. Any missing funding or post-fill observation is an explicit gate, not zero. |
| Qualified development component baseline | Contract and source/model mechanisms exist; no strategy economic output admitted | Only after composition/input/model/cost gates pass, run a reproducible fixed, no-search development component experiment with actual decisions, full coverage/rejection/nonfill counts and complete accounting. Report economic quantities only then; one selected day cannot demonstrate general Edge or independent OOS. |
| C11/C33/C35 (R04–R06) | Frozen protocols and older state retained | Status/metadata only until each original sample/breadth/cost gate. Latest retained status audit found no matching local collector and stale September files. Do not imply collection continues, alter frozen definitions, reopen sealed outcomes early or start a replacement collector. |
| Telegram notification | Dated independent getMe401, later transport_error recorded | Current identity/delivery unverified. Operator supplies valid credentials; do not print, guess or overwrite secrets. No test messages sent by this export. |

The contract is [docs/research/EPIC01_MTF_MAKER_ECONOMIC_CONTRACT.md](Evidence/Snapshots/main/docs/research/EPIC01_MTF_MAKER_ECONOMIC_CONTRACT.md). It contains earlier EPIC counts and T01/T04/T05 references from its freeze; later scope closeout controls the original charter. The explicitly retained component work remains independently scoped. It does not promise the withdrawn full V1 report, live Radar, full Hyperopt/WFO/OOS certification or release certification.

## Edge plan and stopping conditions

There is **no qualified positive Edge or profitability conclusion**. Development candles being plentiful does not qualify source timing, complete historical market membership or independent untouched holdout. Negative prior studies are actual outcomes, not a tuning invitation.

1. Preserve existing study verdicts/protocols and identify the exact permitted unit. Use the collected six-symbol C06 and related panels for their documented development roles; use the BTC observed day only for its explicit composition study.
2. Finish causal data/strategy/execution/cost composition first. Demonstrate timestamp units, availability, missing-window exclusion, actual symbol isolation, partial/exit accounting and nonfabricated metrics with meaningful targeted regressions.
3. Freeze experiment version, parameters, data cut/source hashes, cost/funding assumptions, evaluation budget and report contract **before** economic outcomes. No parameter search in the fixed one-day unit.
4. When admitted, report a truthful development component baseline including failures/nonfills and complete after-cost ledger. A zero-trade result is not an invented PF1; an undefined metric stays undefined. This does not deliver a withdrawn whole-plan baseline.
5. Any later independent profitability claim requires a separately frozen, sufficiently powered, untouched time-based OOS design, costs, multiple-testing/family control and breadth/concentration checks. WFO optimization sees training windows only. Do not recycle opened cohorts or retrofit a holdout label.
6. A failed source/model/cost/scientific gate yields its precise limitation, not architecture churn, renamed strategies, extra test-count claims or unsupported economic optimization. Runtime gates apply independently of research success.

## Original EPIC — all 30 IDs, no omitted failed/blocked promises

The operator explicitly allowed completion or removal. Eight previous accepted bounded deliveries remain; **T01-S04** was actually completed by hashing/classifying 5,158 files; 21 obligations were explicitly withdrawn undelivered. The old FAIL is not declared fixed. No hidden backlog was created and no safety/scientific gate was removed. Complete rationale/source evidence is in the copied closeout JSON.

| ID | Original scenario | Prior state | Final disposition | Evidence / rationale |
|---|---|---|---|---|
| T01-S01 | Active strategy, watcher, Fusion and Regime composition inventoried | BLOCKED | **REMOVED_NOT_DELIVERED** | Deployed-composition certification withdrawn from this delivery; source inventory is retained but no running active set is certified. |
| T01-S02 | Raw 1m per-symbol coverage and integrity quantified | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T01-S03 | Processed MTF per-symbol coverage and resampling lineage quantified | BLOCKED | **REMOVED_NOT_DELIVERED** | Full historical processed-to-raw lineage cannot be established from the supplied provenance; no lineage will be invented or reconstructed retroactively as observed evidence. |
| T01-S04 | Development, validation and holdout eligibility classified | BLOCKED | **PASS** | Completed per-file eligibility decisions with actual SHA readback for 5158 supplied/current inputs: 5150 unqualified and eight development-only; zero validation/holdout/economic-baseline admissions. Classification completion is not data qualification. |
| T02-S01 | Existing Radar and screener reuse proven | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T02-S02 | Movement observation remains read-only at watcher/screener boundary | BLOCKED | **REMOVED_NOT_DELIVERED** | Live watcher/screener shadow-port delivery is cancelled for this charter; the delivered offline research Radar is retained without claiming live integration. |
| T02-S03 | Regime classification remains separate | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T02-S04 | Causal timestamp, source and quality fields retained | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T02-S05 | Shadow output cannot alter trading selection or routing | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T03-S01 | Watcher name/role mapping verified | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T03-S02 | Signal timestamp and freshness verified | FAIL | **REMOVED_NOT_DELIVERED** | Full historical signal/freshness parity was not accepted; the original FAIL is preserved in the closeout evidence. This scope is withdrawn, not marked fixed or PASS. Explicit replay guards remain mandatory. |
| T03-S03 | Fusion agreement, HOLD and rejection reasons reported | BLOCKED | **REMOVED_NOT_DELIVERED** | Full production/Fusion decision-trace certification is not delivered and is withdrawn from this charter; earlier bounded incident evidence is retained. |
| T03-S04 | Strategy registration, defaults, thresholds and weights verified | BLOCKED | **REMOVED_NOT_DELIVERED** | Deployed registration/default/weight certification is withdrawn; changing live admission to make a checklist green is prohibited. |
| T03-S05 | Symbol isolation, intent suppression and cooldown verified | BLOCKED | **REMOVED_NOT_DELIVERED** | Whole-system symbol/cooldown/admission acceptance is not delivered and is withdrawn; existing duplicate and risk protections remain enforced. |
| T04-S01 | Trend Pullback plan frozen from existing code | BLOCKED | **REMOVED_NOT_DELIVERED** | Requested Trend Pullback semantics are not established by NGTREND_FOLLOW; do not build or rename a new strategy to satisfy an unsupported plan label. |
| T04-S02 | Breakout/Retest plan frozen from existing code | BLOCKED | **REMOVED_NOT_DELIVERED** | Requested Breakout/Retest semantics are not established by NGBREAKOUT; the unsupported plan promise is cancelled rather than invented. |
| T04-S03 | Momentum Scalping plan frozen from existing code | BLOCKED | **REMOVED_NOT_DELIVERED** | NGLS_SWEEP is not the promised Momentum Scalping plan; that plan promise is cancelled without changing existing strategy semantics. |
| T04-S04 | Causal after-cost baseline backtests executed on qualified data | BLOCKED | **REMOVED_NOT_DELIVERED** | The original full three-plan qualified baseline is not delivered and is withdrawn. A selected one-day observed/model component does not satisfy it. The separately authorized bounded component contract is not a substitute PASS. |
| T04-S05 | Counts, expectancy, PF, drawdown, side, duration and rejections reported | BLOCKED | **REMOVED_NOT_DELIVERED** | Full-baseline economic reporting is cancelled with its undelivered baseline; metrics remain NOT_MEASURED, not fabricated zeroes. |
| T05-S01 | Parameter spaces frozen before optimization output | BLOCKED | **REMOVED_NOT_DELIVERED** | Full-plan optimization parameter-space delivery is cancelled because the required full plan/baseline is not being delivered by this charter. |
| T05-S02 | Chronological WFO train/validation/test boundaries verified | BLOCKED | **REMOVED_NOT_DELIVERED** | Full qualified-data WFO acceptance is withdrawn; tested train-only/calendar source corrections remain engineering assets, not completed real-data WFO. |
| T05-S03 | Evaluation budget and after-cost objective recorded | BLOCKED | **REMOVED_NOT_DELIVERED** | Executing an economic optimization budget without the required baseline would be invalid; full-plan search is cancelled, not run to fill a checkbox. |
| T05-S04 | Holdout and overfit verdict explicitly qualified | BLOCKED | **REMOVED_NOT_DELIVERED** | No untouched holdout is admitted; full independent OOS/overfit certification is withdrawn rather than manufacturing independence on opened data. |
| T06-S01 | Signal-to-intent simulated path verified | BLOCKED | **REMOVED_NOT_DELIVERED** | Whole-system signal-to-intent release certification is withdrawn; partial offline mechanism evidence is retained without release promotion. |
| T06-S02 | Duplicate prevention and unknown outcome tested | BLOCKED | **REMOVED_NOT_DELIVERED** | Full duplicate/UNKNOWN/restart release certification is not delivered; withdrawing this task does not clear any journal uncertainty or weaken admission. |
| T06-S03 | Protective-order semantics tested | BLOCKED | **REMOVED_NOT_DELIVERED** | Deployed protective-order certification is not delivered and is withdrawn from this EPIC; authoritative P0 protection requirements remain non-negotiable before startup. |
| T06-S04 | Journal, reconciliation and restart persistence tested | BLOCKED | **REMOVED_NOT_DELIVERED** | Whole-system persistence/reconciliation/restart certification is withdrawn; unresolved exact-attempt P0 evidence remains in its existing safety dossier. |
| T06-S05 | No-lookahead deterministic replay and P0 gate retained | BLOCKED | **REMOVED_NOT_DELIVERED** | Full deterministic/no-lookahead release acceptance is withdrawn; existing causal guards are retained and no VST/live permission is granted. |
| T07-S01 | Existing research IDs linked without verdict overwrite | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T07-S02 | Release report separates correctness, performance, OOS, readiness and Edge | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |

## Canonical research R01–R26 — preserve the verdicts

The following is the verbatim operational overlay from the canonical registry: 15 CLOSED_FINAL, 4 ACTIVE_DELIVERABLE, 3 BLOCKED_EXTERNAL, 4 RESEARCH_ASSET. It is a distinct scientific registry, not the cancelled EPIC queue. `COLLECTING` and counts in the old scientific entries are dated labels, not verified active collectors. The exact full registry and linked protocols remain in current snapshots and V1's history archive.

| ID | Preserved scientific status (dated) | Operational disposition | Existing gate / permitted next step | Dependency |
|---|---|---|---|---|
| R01 | `PHASE3A_INCONCLUSIVE_DATA_LIMITED` | `CLOSED_FINAL` | New attributable cohort/preregistration for a different study | External feed; **NO** |
| R02 | `FROZEN_PROSPECTIVE_RESEARCH_LEAD` | `BLOCKED_EXTERNAL` | Complete new sibling feed and valid activation | External feed; **NO** |
| R03 | `COMPRESSION_FORWARD_1_BLOCKED_SIGNAL_FEED`, M3 `NOT_IDENTIFIABLE` | `BLOCKED_EXTERNAL` | Source IDs, cursors, UTC/gap evidence and unopened cohort | External feed; **NO** |
| R04 | C-11 frozen prospective, dated N=5 | `ACTIVE_DELIVERABLE` | Frozen sample/breadth/cost verdict only at its existing gate | Existing collector; status-only audit **YES**, no early verdict |
| R05 | C-33 `PROSPECTIVE_COLLECTING`, dated 1,034/8,640 warmup | `ACTIVE_DELIVERABLE` | Frozen warmup/provenance gate, then its own study decision | Existing collector; status-only audit **YES** |
| R06 | C-35 `TOO_SLOW / COLLECTING`, dated 3/240 outcomes | `ACTIVE_DELIVERABLE` | Frozen sample/cost verdict only at its existing gate | Existing collector; status-only audit **YES** |
| R07 | C-14/C-15 tested momentum rejected | `CLOSED_FINAL` | Distinct mechanism and unopened cohort for any new question | Scientific choice; **NO** |
| R08 | C-16/C-17 OI net negative | `CLOSED_FINAL` | Distinct joint observed panel for any new question | External data/scientific choice; **NO** |
| R09 | Tested aggregate flow/toxicity rejected | `CLOSED_FINAL` | Qualified different source/independent protocol | External data/scientific choice; **NO** |
| R10 | `NO NEW FUNDING-STATE TEST — CONTINUE FROZEN C-11 ONLY` | `CLOSED_FINAL` | No broad-state retest; C-11 is R04 | Scientific choice for new mechanism; **NO** |
| R11 | `LOW_INFORMATION_VALUE — DO_NOT_BUILD` | `CLOSED_FINAL` | None on this study | None; **NO** |
| R12 | C-18/C-19 aggregated depth `REJECT` | `CLOSED_FINAL` | Distinct price-level hypothesis, not band-depth retuning | Scientific choice; **NO** |
| R13 | Lead B `REJECT_ECONOMIC_EDGE` | `CLOSED_FINAL` | None on opened cohort | None; **NO** |
| R14 | Lead A `INSUFFICIENT_PROVENANCE` | `ACTIVE_DELIVERABLE` | Authoritative joined mark, entry/exit fill, venue and timestamp evidence; **not** exit optimization | P0 Execution Recovery/external broker truth; requirements mapping **YES**, Edge test **NO** |
| R15 | Pre-intent `NOT_IDENTIFIABLE` | `CLOSED_FINAL` | New direction semantics would be another study | Scientific/trading decision; **NO** |
| R16 | V1 `PREDICTIVE_NOT_SUPPORTED` | `CLOSED_FINAL` | None on this study | None; **NO** |
| R17 | V2 `V2_DATA_LIMITED` | `CLOSED_FINAL` | Unopened independent cohort for any new study | Scientific choice; **NO** |
| R18 | Historical microstructure feasibility complete | `CLOSED_FINAL` | Separate qualified information/hypothesis required | No new capture authorized; **NO** |
| R19 | Pilot-1 `MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL` | `CLOSED_FINAL` | Immutable measurement evidence | None; **NO** |
| R20 | Sibling forensic mechanism map complete, Edge unknown | `RESEARCH_ASSET` | Full denominator/attribution before economics | External feed; preserve map **YES**, new test **NO** |
| R21 | Phase-6 `PROVISIONAL_ONLY`, zero full promotions | `CLOSED_FINAL` | None on opened screen | Scientific choice for new mechanism; **NO** |
| R22 | `EXTREME_MOVER_DATA_PARTIAL`, contract complete | `RESEARCH_ASSET` | Qualified time-T universe/costs and a separately frozen experiment | External data; causal interface/synthetic tests **YES**, historical ranks **NO** |
| R23 | Public methodology review complete | `RESEARCH_ASSET` | None; use only research discipline | No dependency; **NO** new task |
| R24 | Annotation protocol design complete, inactive | `RESEARCH_ASSET` | Frozen inclusion/window and authorization to activate | New collection/scientific choice; **NO** |
| R25 | Liquidation/OI/OBI reconciliation complete, joint panel absent | `BLOCKED_EXTERNAL` | Observed overlapping panel plus one directional hypothesis | External data/scientific choice; **NO** |
| R26 | Pilot-2 `MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL` | `CLOSED_FINAL` | Immutable measurement evidence, no repeat | None; **NO** |

No closed negative mechanism is reopened here. R14 depends on authoritative execution truth before exit economics; R02/R03/R25 need qualified external evidence and their original scientific activation decisions. Pilot-1/Pilot-2 PARTIAL measurement verdicts, frozen cohorts and no-repeat rules are retained. The named two-file public data unit is the explicitly bounded later exception, not permission for prospective replacement collectors or paid services.

## Reproducibility, migration and exclusions

Use the real source roots, not code copied under Evidence/Snapshots, for development. The selected code snapshots aid review; they are **not every dependency, a runnable checkout or a backup**. Root/relative paths inside historical source documents may refer to local data or omitted binary/report assets. The source/export manifest identifies each snapshot and any redaction; only the package's own report links are promised navigable within this export.

The original 26 October ZIP is byte-identical (`cca0039301ab0265d66138c4310e95bf4708542936a4c47e5a8b85a74671678f`), with all 1,459 internal checksum entries matching. It preserves 1,450 original document snapshots and 701 historical task documents across its historical source roots. Its source baselines primary958dbd7/main0649178 are obsolete for current execution. Current primary/main Markdown snapshots, all 701 current task Markdown files, latest evidence, selected changed/critical code, data manifests, source indexes and Git history are exported anew. See [coverage](Evidence/Export-Coverage.json).

Excluded: `.env`, auth/private credential files, raw operational journal contents, private/raw frozen cohorts, market data binaries/CSV/JSONL payloads other than explicit inventory/qualification evidence, virtualenv/packages, databases, Git objects, runtime logs, datasets and current secrets. Dirty asset metadata is recorded without exporting contents. Selected public data manifests are included; source data stays local. A narrow known-secret-pattern scan/redaction is documented; it is not a universal historical secret guarantee. Original local source is never redacted/modified by the exporter.

Read-only byte verification: `python3 verify_package.py` from this package checks every manifest entry; it never imports Lynxion, acquires data or starts a process. The accompanying ZIP has a sibling SHA256 file. Fresh source-status, data scope/byte hashes, package checksums, 30-ID/26-ID coverage, all701 task coverage and source preservation were checked as artifact checks; these are not new strategy/runtime tests.

Proceed with the concrete [Claude continuation runbook](Claude-Code-Start-Here.md). Report changed source, actual tests run, commit, review scope, proof limits and exact remaining gate in the **existing** boards. Do not make new architectural cleanup or claim all project work complete from the 11-task historical queue, a cancelled EPIC or a growing test count.




‌TAEGET : 
The primary objective is to turn Lynxion into a continuously evolving, data-driven quantitative research platform capable of identifying, validating, and developing genuine trading edges across all eligible symbols on our target exchanges. The agent should independently explore and determine the most promising research approaches across order flow, order book dynamics, derivatives, liquidity, market regimes, cross-exchange behavior, and machine learning, without being restricted to predefined methods or assumptions. It should systematically audit existing strategies to identify weaknesses, hidden strengths, inefficiencies, and opportunities for improvement, while also discovering entirely new, statistically robust and exploitable trading edges. The agent is expected to propose its own research methodologies, data sources, tools, experiments, and implementation plans, prioritizing evidence-based findings, rigorous validation, and real-world trading viability over speculative optimization.