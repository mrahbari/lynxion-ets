# Microstructure Pilot-2 remediation and pre-soak readiness contract

Status: **FROZEN BEFORE TECHNICAL SOAK**. This is a measurement-only plan. Pilot-1 and its raw/manifest evidence remain immutable. No V3, predictive outcome, or new trading rule is authorized.

## Pilot-1 evidence matrix (repository and host audit, 2026-10-05)

| Category | FACT | INFERENCE | HYPOTHESIS / UNKNOWN |
|---|---|---|---|
| Scope/integrity | Frozen contract SHA-256 `58e6ad82c051b5189354bd9bdc1d40a4b9f5958feb4f7808c253b50abd2a468b`; BTCUSDT/ETHUSDT public Binance USD-M diff-depth and snapshots; Sep 28–Oct 5 UTC. Final report `f750841`: 932/932 finalized file hashes matched; 66.15%/66.30% approximate valid-session span, longest missing span 26.457 h. | Valid reconstruction was demonstrated only inside epochs, not over outages. | Absolute clock/NTP accuracy is UNKNOWN. |
| Sequence/restart | 98 epochs, 84 normally closed, 14 interrupted; seven process restart records; zero in-epoch sequence gaps or counted duplicates/out-of-order. Each restart used a new book/session and snapshot. Fourteen unfinalized gzip chunks remain preserved, outside the finalized manifest. | Existing fail-closed replay of the book is correct in scope; process continuity and orphan finalization were inadequate. | Exit code/signal/cause of each unclean stop is UNKNOWN. |
| Clock/host | 66 `local_clock_jump` errors; prior forensics correlated large paired wall-minus-monotonic changes with macOS sleep/wake. `last reboot` associates outages 1, 4, and 5 with host shutdown. Oct 3 `pmset` shows repeated sleep from 15:04 CEST after the 12:55 UTC last valid updates. | Most detector events likely represent suspend/resume rather than demonstrated NTP jumps. Host sleep substantially contributed to missing coverage. | Exact per-event NTP corrections and whether sleep killed the collector in every case are UNKNOWN. |
| Transport | Session errors: six DNS `gaierror`, six WebSocket opening-handshake timeouts, two stale streams, two connection-close errors. No recorded REST schema or disk-reserve/write error. | Transport interruptions caused additional explicit epochs while the process was alive. | Local-versus-remote cause of each timeout/DNS error is UNKNOWN. |
| Monitoring/lifecycle | Pilot-1 had only in-process retry plus four-hour periodic checks, no resident OS process supervisor or durable child exit status. Outages 2, 3, and 6 lack a host reboot between last valid event and restart. | Delayed external detection allowed avoidable gaps; an OS supervisor is needed. | Why those processes vanished is UNKNOWN; a Python crash is not proven. |
| Stop boundary | One ETH raw depth message was received 40.015 ms after the frozen stop (preserved but excluded from clipped formal coverage). | Time was checked before awaiting receive, not atomically at append. | No economic impact is inferred or investigated. |

Seven restart markers, pairing BTC/ETH epochs by occurrence: (1) Sep 28 last valid 03:50 UTC, recovery 08:30; (2) Sep 28 16:08 → 16:42; (3) Sep 28 19:30 → 20:44; (4) Sep 30 05:04 → 10:11; (5) Sep 30 11:45 → Oct 1 14:12, with an unbootstrapped intervening epoch; (6) Oct 1 21:16 → 21:43; (7) Oct 3 12:55 → 19:00. These are last-valid-to-first-recovery bounds, **not proved process-exit times**. Prior forensic details: `docs/MICROSTRUCTURE_DATA_PILOT_7D_FAILURE_FORENSICS.md`.

## Minimum remediation boundary

Keep the same public source, two symbols, 100 ms price-level depth, 1000-level snapshot, exchange IDs/timestamps, local wall and monotonic receipt timestamps, snapshot/bridge/`pu` continuity rules, and fail-closed gaps. Add only: an explicit after-receive stop guard; an honest wall/monotonic discontinuity label (not an unproven NTP jump); durable heartbeat/exit/restart telemetry; a bounded, observable local process supervisor; and explicit orphan detection. Host sleep is a **separate environmental condition** that no process supervisor can repair while the host is suspended. No trading application component changes.

## Frozen Pilot-2 technical-soak gates

The soak is segregated technical data, never Pilot-2 or confirmatory research. Its criteria are fixed here **before** running it. Offline deterministic fault-injection plus a bounded public BTC/ETH capture are both required where relevant; failure cannot be waived based on a convenient capture.

| Gate | Objective PASS requirement |
|---|---|
| R1 bootstrap | Both symbols obtain a real public snapshot and valid first `U <= lastUpdateId <= u` bridge during the segregated soak. |
| R2 sequence | At least 1,000 applied updates per symbol in the soak; every valid epoch follows `pu == previous u`; all mismatches invalidate rather than publish a book. |
| R3 disconnect | Injected connection loss creates an explicit invalid interval and a new epoch; no synthetic continuity. |
| R4 death detection | Forced collector SIGKILL is detected by the supervisor within 15 s while the host is awake. |
| R5 bounded restart | A healthy child restarts within 30 s after the injected death; more than three deaths within 10 min causes a durable terminal failure, not an infinite silent loop. |
| R6 re-bootstrap | Restart uses a new session ID and real new snapshot/bridge before a derived book is valid. |
| R7 timestamps | Exact raw `E/T` and `U/u/pu` bytes survive; local UTC wall and monotonic receipt times remain distinct; no message at/after stop is accepted as formal data. |
| R8 clock | Injected wall-minus-monotonic discontinuity fails closed and is labeled `wall_monotonic_discontinuity`; it is **not** labeled a proven NTP jump. Source clock synchronization remains UNKNOWN without direct evidence. |
| R9 raw durability | Finalized raw chunks are readable and hash-identical; forced death leaves any partial chunk explicitly orphaned and never counted as finalized or continuous. |
| R10 manifest | All finalized files are listed with matching bytes/hashes, and any orphan is reported separately. |
| R11 disk guard | Simulated free space below the fixed 10 GiB reserve prevents capture without deleting or overwriting data. |
| R12 monitoring | Dead or stale child/heartbeat is detected within 30 s while awake; old files alone cannot imply health. |
| R13 network safety | Public unauthenticated REST/WebSocket only; zero account/broker/order calls. |
| R14 preservation | Pilot-1 raw/manifest/contract hashes and protected research working-tree files are unchanged by soak/tests; no production trading source changed. |

All R1–R14 are mandatory. Additionally, the intended host must demonstrate awake operation over the bounded soak (minimum 20 minutes) and the supervisor must be configured to start without manual foreground watching. A detected host sleep, absent process-supervision installation, or an unresolved fail-closed clock condition is a readiness **FAIL**, not a reason to redefine the source or claim continuous observation. Only after every gate passes may a fresh seven-complete-UTC-day Pilot-2 contract/boundary be frozen and activated.
