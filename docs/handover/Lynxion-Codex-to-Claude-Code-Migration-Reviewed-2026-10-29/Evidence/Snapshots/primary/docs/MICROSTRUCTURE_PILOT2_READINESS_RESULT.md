# Pilot-2 measurement readiness result — technical soak 3

Decision: **MECHANICAL_READINESS_PASS** against the R1–R14 criteria frozen in `MICROSTRUCTURE_PILOT2_READINESS.md` (SHA-256 `5391627a5070a247fc8e6a3d78d3befba4c0ea3c185ee809ce83257672bda23b`). This is **not** Pilot-2, V3, a predictive result, or proof that a seven-day host cannot later fail. Earlier soak 2 remains an explicit R12 failure in `MICROSTRUCTURE_PILOT2_SOAK_2_RESULT.md`; its data were not concatenated into this test.

## Frozen scope and evidence

- Pilot-1 remains `MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL`, report commit `f750841`; original contract, activation and manifest hashes remain respectively `58e6ad82c051b5189354bd9bdc1d40a4b9f5958feb4f7808c253b50abd2a468b`, `3bce750c3a11d18504423cfd099b23a12eb2c448058d255b223c61df7fb3e526`, and `b8b4934c94d928511368c428f0558091b065ebbeb88408af112b7899513268bc`. Pilot-1's ~66% valid-session spans and 26.457-hour maximum unobserved gap are not repaired or combined with this soak.
- Activation: `docs/MICROSTRUCTURE_PILOT2_SOAK_ACTIVATION_3.json`, SHA-256 `45bf4420eeba02f6ada3c513debf81c8cece872401ecf0b3cf4dfd064590cb0e`, committed in `6617f17` before **2026-10-05 05:45:00–06:05:00 UTC**. Public Binance USD-M BTCUSDT/ETHUSDT 100 ms diff-depth and 1000-level REST snapshot only. Collector SHA-256 `2f7391e75719ae69745e39504381cadfa3e43f770eee6fe4336afe548b71d94e`; corrected supervisor SHA-256 `509a410368813aa28d0e593404dc0daf7969c5db4949c96d125fe10658dee2a9`.
- Segregated local root: `data/research/microstructure_pilot2/soak/soak_2026-10-05_0545/`. Capture manifest SHA-256 `86cb43d7c43ec8411dfef3bcbb648e8f5d20f9cd0235cb2eb69e6a92dc88046a`; supervisor-state SHA-256 `d91f8d8cc7fe8c757f1c4105c406271047c86a009cecfb1f4a43a5c00f8f859c`. These are local technical evidence, not a research cohort.

## Frozen gate evaluation

| Gate | Result and evidence |
|---|---|
| R1 snapshot/bridge | **PASS.** Final post-recovery BTC and ETH sessions each recorded one real raw REST snapshot; independent raw replay found one valid bridge per symbol. |
| R2 sequence | **PASS.** Final BTC: 8,677 depth and 8,675 bridge/applied; final ETH: 8,652 depth and 8,649 bridge/applied. Independent replay matched the manifest, with only two/three pre-snapshot events respectively and zero sequence gaps or invalid books. Earlier intentionally interrupted epochs are not claimed as valid continuous coverage. |
| R3 disconnect | **PASS.** Injected transport-loss unit test verified invalidation/new epoch. Two live fault injections created four explicit `INTERRUPTED_UNOBSERVED_GAP` symbol epochs, followed by fresh distinct sessions; no synthetic continuity or backfill. |
| R4 death detection | **PASS.** Only the soak child PID 22046 was intentionally SIGKILLed at `1791179240690785000` ns; supervisor recorded exit `-9` at `1791179241970333000` ns, about 1.28 s later. |
| R5 bounded restart | **PASS.** Replacement PID 27765 started at `1791179244124374000` ns, about 3.43 s after injection. Offline restart-budget test confirms a fourth death in ten minutes yields durable terminal state, not an infinite loop. |
| R6 re-bootstrap | **PASS.** After both SIGKILL and stale-heartbeat recovery, new BTC/ETH session IDs and raw snapshots were required; independent book replay re-established bridge without inheriting previous-book state. |
| R7 timestamps/boundary | **PASS.** Finalized raw envelopes retain distinct receipt UTC and monotonic nanoseconds; decoded source payloads retain `E/T/U/u/pu` or snapshot `lastUpdateId`. All 17,329 finalized depth receipts were within `[05:45,06:05)` UTC. Completion at 06:05:03 UTC was metadata finalization, not a late depth observation. |
| R8 clock | **PASS for frozen detector scope.** Offline wall/monotonic perturbation fails closed as `wall_monotonic_discontinuity`, not an unproven NTP jump. No detector event or host sleep/wake occurred in this awake soak; absolute NTP offset remains **UNKNOWN**. |
| R9 raw durability | **PASS.** Two finalized gzip chunks are readable with matching bytes/hashes. Four unique intentionally interrupted gzip chunks (2,941,836 bytes) are preserved with matching recorded hashes as incomplete orphans, outside finalized coverage. Repeated failure-log references do not create additional files. |
| R10 manifest | **PASS.** Two finalized files, 10,521,355 compressed bytes and 17,331 JSONL records (depth plus two snapshots) passed independent size/SHA-256/readback. The exact set of four unlisted raw files equals the manifest-recorded unique orphan set. |
| R11 disk guard | **PASS.** Offline test proves free space below 10 GiB blocks capture before raw writes; actual host had ~50 GiB free at finish, above reserve. No disk error observed. |
| R12 monitoring | **PASS.** A live SIGSTOP of only child PID 27765 produced `stale_process_heartbeat` at `1791179403447614000` ns, about **26.46 s** after the last BTC receipt recorded in health, within the frozen 30 s limit. Supervisor removed the stopped child and started PID 29006 in fresh epochs. Offline tests reject wrong PID, stale process heartbeat, and stale symbol feed; old files alone never imply health. |
| R13 safety | **PASS.** Collector/supervisor source and capture use public unauthenticated REST/WebSocket only. Zero account, broker, VST or order calls in this technical test. |
| R14 preservation | **PASS.** Pilot-1 contract/activation/manifest hashes and protected production persistence hashes matched their pre-soak values; no Strategy/Fusion/Risk/Broker or frozen research source was edited. C-11/C-35 working-tree changes were left untouched by this work. |

The LaunchAgent `com.lynxion.microstructure-pilot2-soak-3` ran under `caffeinate -is` with a macOS prevent-system-sleep assertion until completion. `pmset -g log` showed no sleep/wake event within the 20-minute soak. Supervisor state is `COMPLETED`; both final sessions are `CLOSED`. Focused tests: `python3 -m pytest -q tests/unit/test_microstructure_pilot_7d.py tests/unit/test_microstructure_pilot_supervisor.py` → **16 passed**; `git diff --check` passed. No future returns, PnL, signal feature, or trading outcome was inspected.

## Boundary of the decision

This PASS authorizes only the already-approved preparation of a **fresh seven-complete-UTC-day Pilot-2**, using the same observed price-level information family and a separately frozen contract/activation before its start. The deliberate faults created real unobserved intervals inside this soak; zero in-session sequence gaps must never be called continuous coverage. Host shutdown, closed-lid sleep, and future network outages remain operational risks to be recorded in Pilot-2 rather than hidden. Pilot-2 data do not automatically become V3 data.
