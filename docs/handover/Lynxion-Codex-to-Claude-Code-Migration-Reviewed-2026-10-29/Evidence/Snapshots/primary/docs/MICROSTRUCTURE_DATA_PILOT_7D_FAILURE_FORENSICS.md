# Microstructure Pilot-1 — outcome-blind failure forensics

Evidence cutoff: 2026-10-01 14:13 UTC. This is **not** the final Pilot-1 PASS/PARTIAL/FAIL report. No future returns, PnL, predictive labels, or Edge outcomes were inspected. Formal collection remains frozen at 2026-09-28 00:00:00 UTC through 2026-10-05 00:00:00 UTC.

## Frozen recovery rule

The unchanged collection contract SHA-256 is `58e6ad82c051b5189354bd9bdc1d40a4b9f5958feb4f7808c253b50abd2a468b`; the unchanged collector SHA-256 is `d74053d5043d87d041e0a385a35d9fd87e3eb705cc5d05dd49a9d92c43f12491` (activation record: `docs/MICROSTRUCTURE_DATA_PILOT_7D_ACTIVATION.json`). The contract's “Reconstruction and missing data” section **permits process restart but requires invalidation and re-bootstrap from a new public snapshot and epoch after any restart or disconnect**. It does not mandate an OS-level automatic process restart, nor permit backfill, interpolation, a different feed, a shifted boundary, or an extension. The collector implements new session IDs and books per attempt; on process restart it verifies finalized file hashes, marks prior `RUNNING` sessions `INTERRUPTED_UNOBSERVED_GAP`, and records `collector_restart` and unfinalized chunk paths. The contract requires the final integrity verdict only after the frozen stop.

One recovery launch was performed at approximately 2026-10-01 14:13 UTC with the unchanged activation/source. It recorded a fifth `collector_restart`, created new BTC/ETH epochs, and new raw files began receiving bytes. Process PID 36533 was live immediately afterward. This does **not** validate or fill any earlier gap. No Pilot-2 boundary or collector was started.

## Process-outage chronology

Times below are UTC. “Last valid” is the latest `last_valid_event_utc_ns` in both affected sessions, rounded to seconds. It is **not** a proved process-exit timestamp. Exit codes, signals, and termination stack traces were not captured. The restart marker is the first durable detection/recovery record, not the true moment of failure.

| Outage | Last valid BTC / ETH | Host/process evidence | Detected and restarted | Root-cause classification |
|---|---|---|---|---|
| 1 | Sep 28 03:50:04 / 03:50:04 | `last reboot` records host shutdown Sep 28 06:02 CEST (04:02 UTC), then reboot 08:00 CEST (06:00 UTC). Both sessions lacked normal closure; two unfinalized chunks existed. | Sep 28 08:30:30 | `HOST_SHUTDOWN_ASSOCIATED`; host shutdown certainly terminated a surviving collector, but its exact earlier exit time/cause is `UNKNOWN`. |
| 2 | Sep 28 16:08:52 / 16:08:52 | Both sessions lacked normal closure; no intervening host reboot in `last reboot`; no collector exception/exit status was preserved. | Sep 28 16:42:02 | `PROCESS_LIFECYCLE_UNKNOWN`; network, OS kill, terminal-session termination, or other cause not proven. |
| 3 | Sep 28 19:30:47 / 19:30:47 | Both sessions lacked normal closure; no intervening host reboot; no exception/exit status was preserved. | Sep 28 20:44:06 | `PROCESS_LIFECYCLE_UNKNOWN`. |
| 4 | Sep 30 05:04:47 / 05:04:47 | `last reboot` records shutdown Sep 30 07:07 CEST (05:07 UTC) and reboot 08:29 CEST (06:29 UTC). Both sessions lacked normal closure. | Sep 30 10:11:23 | `HOST_SHUTDOWN_ASSOCIATED`; exact pre-shutdown termination cause/time remains `UNKNOWN`. |
| 5, after the four original stops | Sep 30 11:45:30 / 11:45:30 | Both sessions remained marked `RUNNING` with zero new events; process absent when checked Oct 1. `last reboot` records shutdown Sep 30 14:11 CEST (12:11 UTC) and reboot 19:07 CEST (17:07 UTC). | Oct 1 ~14:13 | `HOST_SHUTDOWN_ASSOCIATED`; exact exit cause/time remains `UNKNOWN`. |

The lower-bound unobserved intervals from last valid observation to recovery are approximately 4h40m, 33m, 1h13m, 5h07m, and 26h27m respectively; actual re-bootstrap validity begins **after** each recovery marker. These are not claims of exact outage duration. Earlier interruption sessions and all cumulative orphan paths remain preserved. An orphan is an unfinalized/unmanifested chunk, not proof of its byte-level corruption and not eligible to be silently promoted into validated continuous coverage.

## Clock and host-suspend finding

**FACT:** The manifest contains 33 `local_clock_jump` errors (32 in synchronized BTC/ETH pairs plus one BTC-only event). Reading only raw envelope receipt clocks—not exchange prices or outcomes—shows the difference between adjacent `receipt_utc_ns - receipt_monotonic_ns` values jumped by **25.550 to 7,195.249 seconds** (median 996.813 seconds). Each BTC/ETH pair had matching jump magnitude to millisecond precision. For example, at Sep 28 11:38:15 UTC both offsets increased by 7,195.249 seconds, while `pmset -g log` records a clamshell sleep beginning Sep 28 11:38:15 CEST and a maintenance wake about two hours later. The 25.550-second BTC-only case is near the documented Sep 29 23:22:41–23:23:48 CEST low-power sleep/wake. `pmset` also records repeated clamshell, idle, maintenance and low-power sleeps during the capture.

**INFERENCE:** The dominant “clock jump” mechanism is host suspension versus the collector's wall-minus-`time.monotonic_ns()` detector, not 33 demonstrated NTP adjustments. The fail-closed invalidation/re-bootstrap is consistent with the contract because observation was interrupted. The error label does not distinguish host sleep from true clock discipline changes.

**UNKNOWN:** NTP synchronization/offset evidence was never captured (`activation.preflight.clock_sync_offset_evidence = UNKNOWN`), and no complete time-service trace was available. A true clock adjustment during any particular interval cannot be excluded solely from these paired envelopes.

## Independent cause categories

| Category | FACT | INFERENCE / HYPOTHESIS | UNKNOWN |
|---|---|---|---|
| `COLLECTOR_SOFTWARE` | Source catches connection/schema/clock exceptions and retries with fresh book/session while alive; finalized hashes are checked on restart. No traceback proves a Python crash at the five unclean process stops. | The 1-second wall-minus-monotonic rule labels host suspend as `local_clock_jump`; this is a detector-specific classification issue, not proof of wrong raw data. | Whether any collector bug caused an unclean process stop. |
| `PROCESS_LIFECYCLE` | Four restarts were durably recorded before this audit; a fifth was recorded in recovery. Prior `RUNNING` epochs were marked interrupted. No OS supervisor is specified or implemented in the collector. | Outages 1, 4 and 5 are associated with host shutdown. | Exact process exit times, exit codes/signals and cause for outages 2 and 3. |
| `HOST_SLEEP_OR_SUSPEND` | `pmset` documents repeated sleep/wake; paired receipt-clock offsets move together across these intervals. | This explains most clock-jump failures and loss of real-time observation while sleeping. | Complete per-event sleep attribution for every jump. |
| `CLOCK/NTP` | Both receipt clocks are preserved; 33 detector errors occurred; NTP offset evidence is marked `UNKNOWN`. | Most errors are suspend/detector effects, not demonstrated NTP jumps. | Actual NTP corrections and absolute clock accuracy. |
| `NETWORK` / `DNS` | Four `gaierror: [Errno 8] nodename nor servname provided, or not known` errors occurred at Sep 30 10:37 UTC (two per symbol). Other sessions later received valid data, so that DNS event was transient; it did not prove outage 4 or 5's process termination. | Host sleep can interrupt network connectivity. | Root cause and duration of the DNS fault; network availability throughout every unobserved interval. No separate DNS polling was done. |
| `WEBSOCKET/REST` | Six WebSocket opening-handshake timeouts, one keepalive ping timeout and two stale-depth-stream errors were recorded. Twenty-two BTC plus twenty-two ETH snapshots were obtained by the evidence cutoff; no REST schema/snapshot exception was recorded. | Transport issues caused discrete invalidation/re-bootstrap while the collector remained alive. | Whether remote service or local network caused each timeout. |
| `WATCHDOG/MONITORING` | The script monitors stale streams, disk reserve, and clock changes **in-process**; scheduled checks later found absent processes and manually initiated restarts. It has no autonomous OS process supervisor. | A sleeping/shut-down host and periodic rather than continuous checks permit long detection latency. | Scheduler run history/exit telemetry sufficient to explain every missed or delayed check; absence of a chat notification alone is not proof no check ran. |
| `DISK/RESOURCE` | Free space at Oct 1 check was ~56 GiB, above the fixed 10 GiB stop reserve. No `disk_reserve`, write, or finalized-hash error was recorded; 354 finalized chunks totaling ~2.12 GB passed hash verification at the pre-recovery snapshot. | Disk exhaustion is not supported as a cause of the documented stops. | Other resource pressure or OS termination evidence. |

## Coverage and monitoring conclusion

`gaps == 0` in the in-memory/book sequence records means no *detected `pu`-chain break inside an already valid session*. It does **not** mean continuous observation across sleep, disconnect, restart, failed handshake, shutdown, orphaned chunk, or absent process. Every epoch boundary requires a fresh snapshot and valid bridge; unknown intervening book states remain unobserved. Raw depth events and reconstructed books are measurement evidence only, not predictive evidence.

The current watcher is a periodic integrity check, not a continuously resident process supervisor. In-process retries explain recovery from documented handshake/stream errors while the program remained alive; they cannot resurrect a vanished process or run while the host is shut down. The frozen pilot must not be extended or backfilled to compensate. The final PASS/PARTIAL/FAIL classification remains deferred until 2026-10-05 00:00 UTC.

## Mechanical follow-ups, not deployed in this pilot

For a separately authorized future collection, retain termination status and a durable process heartbeat; supervise a collector on an always-on host; record host sleep/wake and clock-discipline evidence; distinguish suspend-duration changes from true NTP steps in error telemetry; and test recovery on deliberate kill/suspend/network loss. None of these suggestions changes Pilot-1 source, symbols, depth, raw bytes, frozen boundary, or scientific semantics. No Pilot-2 activation is authorized here.
