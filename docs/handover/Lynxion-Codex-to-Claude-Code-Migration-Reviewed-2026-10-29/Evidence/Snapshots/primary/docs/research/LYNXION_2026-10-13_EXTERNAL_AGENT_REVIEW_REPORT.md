# Lynxion ETS — evidence packet for independent OpenAI review

Prepared after the frozen 2026-10-13 00:00 UTC Pilot-2 stop. This is a self-contained review brief, not a new experiment, trading instruction, or amendment to a frozen contract. Repository evidence is authoritative for measurement; the operator's subsequent explanation is labeled separately.

## Decisions and non-negotiable boundaries

1. The operator states that the collection stoppages were caused by problems with their laptop. This is **direct operator testimony**, consistent with observed host/process discontinuities, but logs do not independently prove the exact mechanism or assign every gap to that one cause. Do not relabel DNS/WebSocket/clock events as laptop failures without evidence.
2. Pilot-2 remains **`MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL`**. A plausible host-side explanation does not create missing observations, satisfy the frozen coverage rule, or turn within-session sequence integrity into seven-day continuity.
3. The operator rejects Pilot-3 or another repeat microstructure collection after 2026-10-13. Do not extend dates, backfill, join Pilot-1 and Pilot-2 as one cohort, or propose a new collection merely to rescue coverage. Independently frozen C-11/C-33/C-35 retain their own protocols, not a new primary collection mandate.
4. No V3 or other Edge test has been selected or authorized. Do not open future returns, PnL, labels, or signal outcomes to choose a hypothesis. No authenticated broker/account access, order action, or real-funds activation is authorized by this packet.

## Measurement record and provenance

| Item | Verified repository evidence | Limitation |
|---|---|---|
| Pilot-1 | Final `PARTIAL`, report commit `f750841`; about 66% per-symbol coverage, longest gap about 26.457 h. | Separate immutable cohort. |
| Pilot-2 contract | Public unauthenticated Binance USD-M Futures BTCUSDT/ETHUSDT 100 ms diff-depth plus limit-1000 REST snapshots; half-open 2026-10-06 00:00:00 to 2026-10-13 00:00:00 UTC. Contract SHA-256 `d10a475166954421c49492ecc65c4aa2265d95df7d5166bb2a1ffeec2e17963a`; activation SHA-256 `7d1b90492af440687511dbd035fc4f8c9eb006f8a8803d6f18805d0523d5287a`. | Measurement-only, no account or order path. |
| Final Pilot-2 storage | 1,019/1,019 finalized gzip files, 4,445,144,953 compressed bytes, 9,072,176 JSONL records passed independent path/size/SHA/gzip/count/envelope/base64/boundary readback. Capture manifest SHA-256 `6cb1af4ad41191fd125c185ac2ee775892d24e2fadf80581d56111674f60594e`. | This is not full independent order-book reconstruction. |
| Interrupted bytes | 38 manifest orphan references resolve to 10 unique preserved, unfinalized chunks (12,912,972 bytes); not repaired or counted as qualified coverage. | Do not equate 38 references with 38 files. |
| Qualified coverage | Conservative CLOSED/finalized session spans: 101.424 h BTC and 101.423 h ETH, about 60.371% each. Interrupted-session first/last spans yield an *unqualified* 76.667% comparison only. | Neither figure proves millisecond-by-millisecond continuity. |
| Outages and sequence | Longest gap between qualified CLOSED spans about 25.047 h; longest gap between all manifest-recorded valid-update spans about 17.107 h. Manifest shows zero in-session sequence gaps/duplicates/out-of-order, 32 sessions, 10 interrupted, six collector-restart records. | In-session zero gaps does **not** mean continuous seven days. |
| Lifecycle/error evidence | Eight supervisor wall/monotonic discontinuities, two child stale events, two exits, eight starts. Eighteen session errors: 14 symbol-level clock discontinuities, two DNS, two WebSocket closes. Final supervisor state `COMPLETED`; collector stopped at frozen boundary. | Absolute NTP offset, host suspension specifics, and attribution of each gap remain unknown. |
| Frozen verdict | `PARTIAL`: >=99% coverage and <=60-second-gap PASS criteria were missed; >50% conservative qualified span and readable authentic raw support bounded assessment rather than FAIL. Final report commit `b6e9e0e`. | Measurement success/failure is not predictive Edge. |

The operator's laptop explanation improves causal context for the multi-hour host/process interruptions. It **does not change the raw timestamps, missing intervals, contract, or final verdict**. The separate DNS/WebSocket/clock findings still deserve their own labels. This packet records the new testimony; it does not silently edit the finalized Pilot-2 report.

## Authorized backlog work completed

The ordered outcome-blind task board is **11/11 DONE**, with no remaining authorized queue task. It covered Pilot-2 operations, canonical backlog reconciliation, extreme-mover feasibility and time-T information contract, public Qullamaggie methodology review, inactive manual-annotation protocol, liquidation/OI/OBI reconciliation, frozen-study status audit, sibling evidence map, consolidated information-set map, and next-experiment decision package. “Done” means the assigned audit/design deliverable is complete, **not** that the underlying Edge hypothesis succeeded.

| Backlog IDs | Present disposition | What must not be inferred or restarted |
|---|---|---|
| R01 Phase3A; R15 pre-intent; R16 V1; R17 V2; R21 Phase-6 OHLCV screen | Historical inconclusive/data-limited, not identifiable, predictive not supported, or provisional source verdicts preserved; closed for this program. | No rerun, threshold rescue, or outcome-guided redesign. |
| R02 Compression/F4; R03 COMPRESSION_FORWARD_1 | Frozen/data-hungry or blocked signal-feed work; parked. | No new feed or static-export substitution under the no-repeat decision. |
| R04 C-11; R05 C-33; R06 C-35 | Existing independent frozen/prospective gates; no early economic verdict. | Do not change definitions, sample floors, or collectors from this packet. |
| R07 momentum; R08 historical OI; R09 aggregate order flow; R11 settlement clock; R12 C-18/C-19 depth; R13 Lead B | Prior tested representations rejected/closed under their recorded economic or information gates. | Do not rename the same data as a new Edge family or call aggregate depth observed tick L2. |
| R10 broad funding; R14 exit giveback; R20 sibling selection/geometry | Broad funding parked, exit giveback lacks provenance, sibling mechanism remains hypothesis-generation only. | No profitability inference from censored screenshots/messages or unverified fills. |
| R18 microstructure feasibility; R19 Pilot-1; R26 Pilot-2 | Feasibility established need for observed panel; both pilots closed `PARTIAL` as separate measurement cohorts. | No pooled continuity, automatic V3, or new capture. |
| R22 extreme movers | `INDEPENDENT_LEAD / NOT_YET_TESTED`; data classification `EXTREME_MOVER_DATA_PARTIAL`; time-T information contract completed. Historical point-in-time universe/listing and cost panel remain unqualified. | No Edge verdict, chosen thresholds, or implicit prospective universe capture. |
| R23 Qullamaggie methods | Public-method review completed as taxonomy/research discipline. | Stock setups and numerical thresholds are not validated crypto-perpetual policy. |
| R24 manual annotation | Immutable pre-outcome protocol **DESIGNED_ONLY**; window/inclusion rule not frozen; no campaign activated. | No cherry-picked examples or later labels before a separate preregistration decision. |
| R25 liquidation/OI/OBI | Overlap reconciled and still **PARKED**; observed joint panel and one falsifiable direction rule absent. | No synthetic/default OBI/CVD relabeled as observed, no interaction experiment. |

The canonical source for exact per-ID verdicts is `docs/research/LYNXION_RESEARCH_BACKLOG.md`; the exhaustive post-stop per-ID decision table is `docs/research/LYNXION_2026-10-13_NO_RECOLLECTION_DECISION_BRIEF.md`. This summary does not supersede either.

## Separate production/VST issues — do not confuse with Pilot-2

- **P0 runner/execution truth:** a stopped VST TESTNET runner and at least one unresolved local submission require reconciliation before retry or unattended restart. A local acceptance is not an independently verified broker fill. Exactly-once, restart protection, and exchange-side stop visibility are not fully proven.
- **P0 entry latency:** observed local intent-to-result examples were approximately 252–384 seconds. The delay is unacceptable for a claimed 2–3-second path, but endpoint-level broker-versus-platform attribution is not established. Instrument discovery/queue/lock/limiter/HTTP/retry/ack boundaries before optimizing or declaring BingX V2 the cause.
- **P0 unknown exits:** XAUTUSDT/NEARUSDT closing-order identity and realized PnL were unverified in the cited alerts. Preserve safety cooldown; do not turn missing history into a favorable outcome. A diagnostic candidate exists separately but is not deployed.
- **P0 Fusion/ETH:** watcher-name/role mismatch is reproducible, but its effect on missed trades is unquantified. ETH stop replacement had latency/rejection and journal SL/TP provenance defects. An isolated journal-only candidate passed focused tests but was not deployed and requires independent review.
- **Other gates:** BTCUSDC/USDT route eligibility, VST fill-versus-public-price differences, portfolio limits and protective-order behavior need evidence-based, isolated review. Do not enable real funds from this research packet. A networkless test or source-code guarantee is not a deployed-broker guarantee.

Operational repair may proceed independently with existing logs, deterministic networkless tests, explicit credential isolation, independent review of order/protection paths, and an operator gate for trading-policy or authenticated actions. It must not rewrite the scientific measurement verdict.

## Questions for the reviewing OpenAI agent

Please challenge this packet item by item and return an evidence-linked decision matrix: **accept / correct / needs evidence / defer / close / operator decision**. In particular:

1. Does the operator-reported laptop cause fit the lifecycle evidence without over-attributing each DNS, WebSocket, clock, or unobserved interval? What *existing* host logs would most efficiently refine attribution, if available?
2. Is the frozen `PARTIAL` classification correctly separated from the cause of downtime, and is any statement here stronger than the raw audit supports?
3. For R01–R26, which open decision can honestly be closed with existing unopened, point-in-time evidence? Which are structurally unidentifiable under the no-repeat-collection constraint? Do not recommend another microstructure capture as a default rescue.
4. Which one, if any, scientifically distinct Edge question merits **operator** selection and separate preregistration using already-qualified data? A valid answer is “none yet.” Do not inspect outcomes or select V3 yourself.
5. Rank the practical VST safety/provenance/latency defects separately from research by severity, cheapest decisive evidence, and safe minimum fix. Identify where authenticated read-only broker evidence or behavioral deployment approval is indispensable. Do not send or modify orders.

Please distinguish **FACT, OPERATOR TESTIMONY, INFERENCE, HYPOTHESIS, UNKNOWN**. Preserve negative/null/data-limited results. Gross predictive information is not executable Edge; executable Edge is not portfolio profitability.

## Source pointers and integrity

- Pilot-2 final report: `docs/MICROSTRUCTURE_DATA_PILOT_7D_2_REPORT.md` (`b6e9e0e`); frozen contract/activation: `docs/MICROSTRUCTURE_DATA_PILOT2_CONTRACT.md`, `docs/MICROSTRUCTURE_DATA_PILOT2_ACTIVATION.json`.
- Program handover: `docs/research/AUTONOMOUS_RESEARCH_PROGRAM_HANDOVER.md` (`ee3ca53`); task board, canonical backlog, no-repeat decision brief and next-experiment package in `docs/research/`.
- Incidents: `docs/incidents/LYNXION_2026-10-07_ENTRY_LATENCY.md`, `LYNXION_2026-10-07_XAUT_NEAR_UNKNOWN_EXIT.md`, `LYNXION_2026-10-07_FUSION_ETH_VST_FORENSICS.md`.
- Collector/supervisor frozen source SHA-256: `2f7391e75719ae69745e39504381cadfa3e43f770eee6fe4336afe548b71d94e`, `509a410368813aa28d0e593404dc0daf7969c5db4949c96d125fe10658dee2a9`.
- Pilot-2 audit focused tests: 18 passed; final full read-only raw/manifest audit: zero listed errors. Independent C-11/C-35 working-tree data changes were preserved and excluded from measurement commits.

No new data collection, future-outcome opening, authenticated request, order, V3, or real-funds action was performed to prepare this packet.
