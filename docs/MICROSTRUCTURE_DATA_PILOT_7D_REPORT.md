# MICROSTRUCTURE_DATA_PILOT_7D_REPORT

Final measurement-only verdict: **MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL**.

This is not a predictive, Edge, or profitability result. No future returns, PnL, signal thresholds, or trading outcomes were inspected. The pilot does not become a V3 cohort by default.

## Frozen scope and evidence

- Starting report HEAD: `8a9bc9d`. This report is the sole intended commit artifact; the contract, collector, activation, raw bytes, and capture manifest were not changed.
- Frozen contract: `docs/MICROSTRUCTURE_DATA_PILOT_7D_CONTRACT.md`, SHA-256 `58e6ad82c051b5189354bd9bdc1d40a4b9f5958feb4f7808c253b50abd2a468b` (matches activation). Collector SHA-256 recorded by activation: `d74053d5043d87d041e0a385a35d9fd87e3eb705cc5d05dd49a9d92c43f12491`.
- Activation: `docs/MICROSTRUCTURE_DATA_PILOT_7D_ACTIVATION.json`, SHA-256 `3bce750c3a11d18504423cfd099b23a12eb2c448058d255b223c61df7fb3e526`.
- Capture manifest: `data/research/microstructure_pilot_7d/formal_2026-09-28/capture_manifest.json`, SHA-256 `b8b4934c94d928511368c428f0558091b065ebbeb88408af112b7899513268bc` at final audit.
- Source: public, unauthenticated Binance USD-M Futures `<symbol>@depth@100ms` diff-depth WebSocket and `/fapi/v1/depth` limit-1000 REST snapshot; BTCUSDT and ETHUSDT only. The formal window was **2026-09-28 00:00:00 UTC to 2026-10-05 00:00:00 UTC**. Preflight data were excluded. Manifest completion was 2026-10-05 00:00:03.217 UTC; both final sessions are `CLOSED`, none `RUNNING`. Previously observed collector PID 51651 was absent at final audit. No boundary extension or backfill occurred.

## Capture and reconstruction integrity

| Measure | BTCUSDT | ETHUSDT |
|---|---:|---:|
| Received diff-depth events, manifest session counters | 3,922,321 | 3,909,922 |
| Applied events | 3,922,135 | 3,909,725 |
| REST snapshots | 42 | 42 |
| Sessions/epochs | 49 | 49 |
| Detected sequence gaps inside valid sessions | 0 | 0 |
| Exact duplicates / out-of-order updates | 0 / 0 | 0 / 0 |
| Session errors | 41 | 41 |
| Approximate valid reconstructed span | 111.132 h (66.150%) | 111.378 h (66.297%) |
| Approximate invalid/unobserved span | 56.868 h (33.850%) | 56.622 h (33.703%) |
| Intervals between valid-session spans | 43 | 42 |
| Longest unobserved interval | 26.457 h | 26.457 h |

Valid span is the union of each session's recorded first-to-last valid applied-event interval, clipped to the frozen boundary. It is an **approximation from manifest endpoints**, not proof that every instant between updates was independently observed. The largest unobserved interval began about 2026-09-30 11:45:30 UTC. Additional substantial unobserved intervals were about 6.084 h (Oct 3), 5.111 h (Sep 30), and 4.674 h (Sep 28). **Zero sequence gaps inside a valid epoch does not imply seven-day continuous observation coverage.** Unknown book states across interruptions were never interpolated.

The manifest has 98 sessions: 84 `CLOSED` and 14 marked `INTERRUPTED_UNOBSERVED_GAP` by seven documented collector restarts. It records 82 per-session errors: 66 `local_clock_jump`, six WebSocket opening-handshake timeouts, six DNS `gaierror`, two stale streams, and two connection-close errors. The 66 clock detector errors are paired BTC/ETH events; earlier outcome-blind forensics associated many with host sleep/suspend and did **not** prove 66 NTP jumps. Actual NTP offset/synchronization remains `UNKNOWN`. Process exit codes/signals for the unclean stops remain unknown. No disk-reserve, raw-write, or finalized-hash failure was recorded. At final audit, free disk space was 53,681,389,568 bytes, above the frozen 10 GiB reserve.

All **932 finalized raw files**, totaling **4,850,420,515 compressed bytes** and 7,830,346 JSONL records, existed with the manifest-listed byte sizes and matched their recorded SHA-256 hashes (streamed independent readback). There were no missing finalized files. Separately, **14 unlisted/unfinalized gzip chunks** from the seven abrupt restarts remain preserved, totaling **35,649,361 bytes**. Each ended with gzip `EOFError` on full readback; they were neither repaired, deleted, hashed into the finalized manifest, nor counted as valid continuous coverage. Total raw bytes on disk, including these preserved chunks, were 4,886,069,876. This is a manifest-completeness limitation, not a license to silently promote orphan bytes into observations.

Exchange `E` and `T`, update IDs `U/u/pu`, snapshot `lastUpdateId`, local UTC receipt and monotonic receipt were retained in raw envelopes. No exchange-time/schema exception appears in session errors. One ETH depth event has local receipt **40.015 ms after** the frozen stop, despite the loop checking time before awaiting the receive. It remains in immutable raw evidence but was **excluded from the clipped formal coverage calculation**; this boundary overshoot is a collector defect for any later pilot, not authorization to rewrite this one. No latency or predictive inference was made from timestamps.

## Verdict and next decision

**PARTIAL**: public feed access, snapshot-plus-update reconstruction, valid-session sequencing, raw durability for finalized chunks, and hash readback were demonstrated. Reliable **continuous seven-complete-UTC-day observation was not**: roughly one-third of each symbol's window is unobserved, including a >26-hour interruption, and abrupt stops left unfinalized chunks. The information contract is mechanically viable in healthy sessions but not operationally qualified as an uninterrupted seven-day collector on this host. This is not `MICROSTRUCTURE_COLLECTION_PILOT_PASS`, and it is not an Edge verdict.

The earlier outcome-blind forensic report `docs/MICROSTRUCTURE_DATA_PILOT_7D_FAILURE_FORENSICS.md` documents host shutdown/sleep and unresolved process-lifecycle causes. Any later collection needs a **separately authorized prospective boundary and contract decision**, with adequate always-on process supervision, stop-boundary enforcement, and explicit orphan/clock telemetry; this report does not start Pilot-2 or V3. No existing C-11/C-33/C-35/Compression/Phase3A/V1/V2 artifact or trading policy was changed.

## Verification and safety

- `python3 -m pytest -q tests/unit/test_microstructure_pilot_7d.py`: **5 passed**. Independent manifest/hash audit: **932/932 finalized files matched**, 14 preserved unfinalized chunks identified. `git diff --check` to be run before commit.
- Four protected production persistence files had identical SHA-256 immediately before and after focused tests: `data/active_positions_journal.json` `cba98a869090f86952c6c64ca6cb029210362abc331939e9db89645307aeebd4`; `data/live_order_journal.json` `8beddcc7195088181913109f47fefd60ea511304d5fc622dfd3849837bb874fd`; `data/sl_cooldown_journal.json` `7fbe876bc3f33ecd529979f5a427d30d488b5a702c354cf33cc524eb9e19ad18`; `data/trade_journal.csv` `a3c3a2a2446f59a694e4cb519b8f0f1a2d80fa3a60fdd307b340886f6f869651`. This is a before/after check for this audit, not a claim that production was idle over seven days.
- The pilot used only public unauthenticated market-data REST/WebSocket. This final audit made **zero network requests** and performed **zero authenticated broker/account calls or orders**. No strategy, risk, execution, production persistence, frozen research, raw capture, or manifest mutation was performed.
