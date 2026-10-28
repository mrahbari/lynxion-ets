# MICROSTRUCTURE_DATA_PILOT_7D_2_REPORT

Final **measurement-only** verdict: **MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL**.

This is not an Edge, predictive, execution, or profitability result. No future returns, labels, PnL, signal quality, or V3 outcome was opened. The operator has rejected Pilot-3/repeat collection; this report does not authorize one.

## Frozen boundary and provenance

- Formal half-open interval: **2026-10-06 00:00:00 UTC to 2026-10-13 00:00:00 UTC**, seven complete UTC days. No date/source/symbol/depth change, backfill, or Pilot-1 concatenation.
- Public unauthenticated Binance USD-M Futures BTCUSDT and ETHUSDT `<symbol>@depth@100ms` diff-depth WebSocket; public `/fapi/v1/depth` limit-1000 REST snapshots. Raw exchange bytes remain base64 in append-only gzip JSONL envelopes. Local wall receipt, monotonic receipt, exchange timestamps and sequence identifiers remain distinct.
- Contract SHA-256 `d10a475166954421c49492ecc65c4aa2265d95df7d5166bb2a1ffeec2e17963a`; activation SHA-256 `7d1b90492af440687511dbd035fc4f8c9eb006f8a8803d6f18805d0523d5287a`; collector SHA-256 `2f7391e75719ae69745e39504381cadfa3e43f770eee6fe4336afe548b71d94e`; supervisor SHA-256 `509a410368813aa28d0e593404dc0daf7969c5db4949c96d125fe10658dee2a9`. The activation names the same contract/collector/supervisor hashes.
- Final capture manifest SHA-256 `6cb1af4ad41191fd125c185ac2ee775892d24e2fadf80581d56111674f60594e`, path `data/research/microstructure_pilot2/formal_2026-10-06/capture_manifest.json`. It records completion at **2026-10-13 00:00:03.260194 UTC**; supervisor state is `COMPLETED` for `frozen_stop_boundary` at 00:00:03.514845 UTC. Both final sessions are `CLOSED`; last child PID 801 was absent at the final read-only check. There is no post-stop depth envelope among finalized files.

## Finalized and interrupted evidence

| Measure | BTCUSDT | ETHUSDT |
|---|---:|---:|
| Manifest sessions | 16 | 16 |
| Received depth events, manifest counters | 4,545,629 | 4,529,760 |
| Applied updates, manifest counters | 4,545,580 | 4,529,705 |
| REST snapshots, manifest counters | 13 | 13 |
| Manifest sequence gaps / duplicates / out-of-order | 0 / 0 / 0 | 0 / 0 / 0 |
| Session errors | 9 | 9 |
| Finalized gzip chunks | 511 | 508 |
| Finalized compressed bytes | 2,302,298,640 | 2,142,846,313 |
| Finalized JSONL records | 4,542,394 | 4,529,782 |
| Conservative qualified CLOSED-session span | 101.424 h (60.371%) | 101.423 h (60.371%) |
| Conservative excluded/unqualified span | 66.576 h (39.629%) | 66.577 h (39.629%) |
| Longest gap between qualified CLOSED spans | 25.047 h | 25.047 h |

The coverage calculation is the union of each **CLOSED, finalized** session's recorded first-to-last applied-event UTC **processing** interval, clipped to the frozen boundary. Ten other sessions are `INTERRUPTED_UNOBSERVED_GAP`. Although some contain finalized chunks, their exact independently replayed valid processing subspans were **not established**; they are conservatively excluded from qualified coverage rather than silently promoted. If every manifest-recorded first-to-last applied interval in those interrupted sessions were included, the unqualified upper comparison would be 128.801 h (76.667%) per symbol. That number is **not** the qualified coverage or proof of continuity. The true qualified span may lie between these figures, but either interpretation exceeds 50% and fails PASS by a wide margin. Processing spans are approximations, not proof of observation at every millisecond; raw receipt timestamps are not relabeled as processing times.

The largest interval between qualified CLOSED spans is 2026-10-07 20:01:58 to 2026-10-08 21:04:47 UTC (25.047 h). It includes an interrupted epoch with recorded updates, so it is **not** a claim that no bytes were received for all 25 hours. Considering all manifest-recorded valid-update intervals, including unqualified interrupted epochs, the largest first-to-last gap is about **17.107 h**, 2026-10-08 03:58:23 to 21:04:47 UTC, for each symbol. Other material recorded-update gaps are about 8.867 h (Oct 9), 4.521 h (Oct 9), 3.877 h and 3.585 h (Oct 12). None was filled or inferred. Zero reported sequence gaps *inside sessions* does not imply seven-day continuity.

The manifest contains **1,019 finalized files**, **4,445,144,953 compressed bytes**, and **9,072,176 JSONL records**. Independent readback checked every listed finalized path, size, SHA-256, gzip stream, exact record count, envelope identity/kind, base64 field, and formal depth-receipt boundary: **1,019/1,019 passed, zero listed errors, zero unlisted raw files**. This is a storage/provenance audit, **not** an independent full order-book reconstruction replay. The collector's 0 sequence-gap/duplicate/out-of-order counts remain manifest evidence with that limitation.

Six `collector_restart` records repeat references to preserved orphan files: **38 references identify 10 unique unfinalized gzip chunks**, totaling **12,912,972 unique bytes**. Their listed size/hash readback matched. They were not repaired, deleted, or counted as finalized evidence or qualified coverage. Repeated references are not 38 distinct files. At final audit disk free was **61,817,716,736 bytes**, above the frozen 10 GiB reserve; no disk-reserve or raw-write failure is recorded.

## Lifecycle and uncertainty

- Supervisor evidence: eight `child_start`, two `child_stale`, two `child_exit`, eight `wall_monotonic_discontinuity`, six collector-restart manifest records and one `completed` event. Status transitions and raw epochs preserve discontinuities. The longest outages coincide with periods where process/host evidence is incomplete; **host sleep/shutdown versus other local causes is not conclusively attributable for every gap**.
- Per-session errors total 18: fourteen symbol-level wall/monotonic discontinuities paired across BTC/ETH, two DNS `gaierror`, and two WebSocket close errors. A clock discontinuity is not proof of an NTP adjustment. Absolute NTP offset and silent-feed behavior during unobserved intervals remain `UNKNOWN`.
- The snapshot/bridge and incremental sequence code is mechanically covered by focused unit tests; the final audit did not independently replay all 9.07 million depth updates into complete price-level books. No authenticated endpoint, account/broker API, or order was used for collection or this audit.

## Verdict and next boundary

**PARTIAL**, not PASS: authentic public-source raw provenance, readable finalized evidence, correct half-open stop behavior and >50% conservative qualified span permit a bounded integrity assessment. The frozen PASS requirement of >=99% per symbol and no unobserved interval >60 seconds is clearly unmet. **FAIL is not justified** by the available evidence: the conservative qualified span is >50% for both symbols, finalized storage passed complete readback, and no unisolatable source/timestamp/boundary corruption was found. This is a measurement classification only and does not qualify predictive Edge.

Pilot-1 stays immutable and separate. No Pilot-3, boundary extension, new data capture, V3, or trading-policy change follows automatically. The next choice is the operator's scientific/operational decision package using the existing evidence and explicitly stated unknowns.

Verification: `python -m pytest -q tests/unit/test_microstructure_pilot_7d.py tests/unit/test_microstructure_pilot_supervisor.py tests/unit/test_audit_microstructure_capture.py` — **18 passed**. Full read-only audit: `python scripts/audit_microstructure_capture.py docs/MICROSTRUCTURE_DATA_PILOT2_ACTIVATION.json` — exit 0, 1,019 finalized files and all manifest orphan references checked, zero errors. Existing C-11/C-33/C-35/F4/Phase3A/V1/V2 and Strategy/Fusion/Risk/Broker artifacts were not modified for this report. Existing unrelated C-11/C-35 working-tree changes were preserved and excluded from this commit.
