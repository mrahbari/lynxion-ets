# Lynxion autonomous research program — final handover

Checkpoint: 2026-10-13 after the frozen 00:00 UTC Pilot-2 stop. Starting HEAD for the ordered backlog program: `8b3ab1e`; pre-handover HEAD after the measurement report: `b6e9e0e`. The ending HEAD is the commit containing this handover (resolve `git rev-parse HEAD` in the checkout); a Git commit cannot embed its own stable hash in its contents.

## Pilot-2: accepted measurement result

- Frozen contract SHA-256 `d10a475166954421c49492ecc65c4aa2265d95df7d5166bb2a1ffeec2e17963a`; activation SHA-256 `7d1b90492af440687511dbd035fc4f8c9eb006f8a8803d6f18805d0523d5287a`; exact half-open boundary 2026-10-06 00:00:00 to 2026-10-13 00:00:00 UTC. No extension, source/symbol change, preflight inclusion, or Pilot-1 concatenation.
- Final **`MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL`**, measurement only. See [full report](../MICROSTRUCTURE_DATA_PILOT_7D_2_REPORT.md). Supervisor and manifest completed just after the frozen stop; last child PID absent; no finalized depth receipt outside the boundary.
- 1,019/1,019 finalized files, 4,445,144,953 compressed bytes and 9,072,176 JSONL records passed complete independent storage/envelope readback, including size/hash/count/boundary. Thirty-eight manifest orphan references refer to ten unique preserved files, not 38 distinct chunks. Zero unlisted raw files.
- Conservative qualified CLOSED-session span: 60.371% per symbol. The all-recorded 76.667% comparison includes interrupted sessions and is **not** a qualified coverage claim. Longest gap between qualified spans ~25.047 h; longest gap between all manifest-recorded valid-update spans ~17.107 h. Six collector-restart records, ten interrupted sessions, eight supervisor clock-discontinuity events, DNS and WebSocket errors remain explicit. Zero *manifest-reported* in-session sequence gaps is not continuity.
- PASS fails the frozen >=99%/<=60-second gap gates. FAIL is not supported because authentic/readable finalized provenance and the conservative >50% span permit bounded assessment. Full independent price-level book replay was not performed; absolute NTP offset and exact root cause of each host/process outage remain `UNKNOWN`. No Edge conclusion exists.
- Pilot-1 remains separately `MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL` (report commit `f750841`); neither pilot is rescued by joining cohorts. The operator explicitly rejects Pilot-3/repeat collection.

## Backlog queue and research disposition

The [task board](LYNXION_RESEARCH_TASK_BOARD.md) is **11 DONE / 0 remaining** for the authorized outcome-blind queue. The [canonical backlog](LYNXION_RESEARCH_BACKLOG.md) preserves R01–R26 exact source verdicts. The [no-repeat decision brief](LYNXION_2026-10-13_NO_RECOLLECTION_DECISION_BRIEF.md) is the full per-item disposition; this handover does not rewrite historical outcomes.

| Family / deliverable | Final position |
|---|---|
| Extreme movers | [Feasibility](CROSS_SECTIONAL_EXTREME_MOVER_FEASIBILITY.md) `EXTREME_MOVER_DATA_PARTIAL`; [time-T information contract](CROSS_SECTIONAL_EXTREME_MOVER_INFORMATION_CONTRACT.md) complete, study `INDEPENDENT_LEAD / NOT_YET_TESTED`. Complete point-in-time historical universe/listing and execution-cost panel remain unqualified. No outcomes or candidate thresholds opened. |
| Qullamaggie/public methods | [Review](QULLAMAGGIE_METHOD_RESEARCH_REVIEW.md) complete: research/setup taxonomy only, no stock-to-crypto transfer claim or imported numerical threshold. |
| Manual annotation | [Protocol](MANUAL_PROSPECTIVE_ANNOTATION_PROTOCOL.md) **DESIGNED_ONLY**, inactive. Inclusion/window not frozen; no annotation collection or later labels. |
| Liquidation/OI/OBI | [Overlap reconciliation](LIQUIDATION_OI_OBI_RECONCILIATION.md) complete; proposal remains **PARKED**. Observed joint panel and one falsifiable direction rule are absent; no synthetic/default OBI/CVD substitution. |
| Frozen/closed studies | [Status audit](FROZEN_STUDIES_STATUS.md), [sibling evidence map](SIBLING_RESEARCH_EVIDENCE_MAP.md), and [information-set map](LYNXION_INFORMATION_SET_MAP.md) complete. C-11/C-33/C-35 retain independent frozen gates; their live collector state was not comprehensively established here. Phase3A, Compression/F4, V1/V2 and rejected prior studies were not rerun or retuned. |
| Next experiment | [Decision package](NEXT_EDGE_EXPERIMENT_DECISION_PACKAGE.md) complete, **no candidate selected**. Neither Pilot-2 measurement nor extreme-mover feasibility is an Edge result. |

## Separate practical engineering and unresolved risks

No Strategy/Fusion/Risk/Broker behavior change was deployed by this measurement program. Read-only incident work documented (a) multi-minute VST intent-to-result latency without endpoint-level attribution, (b) `UNKNOWN` XAUT/NEAR exit identity and PnL, (c) a reproducible Fusion watcher-name mismatch whose effect on trade frequency is unquantified, (d) ETH stop-replacement delay/rejection and journal provenance, and (e) unresolved submission/exactly-once and restart-protection risks. Isolated candidates elsewhere are **not deployed**. VST fake-adapter tests do not prove real exchange behavior; a local accepted request does not prove a fill. These are operational safety priorities, not profitability evidence. No authenticated account/broker request or order was made for this program; real-funds activation is not authorized by this handover.

## Commits in the program range

The range `8b3ab1e..b6e9e0e` includes both research-governance work and separately requested VST/incident work; listing a commit here does **not** mean it was deployed to the active collector. Chronological IDs:

`17c511b`, `68c22b1`, `b433112`, `4e1f292`, `def4ac0`, `92f8ca7`, `0b6871a`, `5f9efc7`, `370732d`, `2a41be9`, `daaec75`, `9c1d087`, `7163d12`, `526748b`, `187b182`, `9ff74fc`, `175be78`, `cfc0141`, `9fd15f1`, `f668076`, `1275a20`, `b312453`, `be86d7e`, `3bb4995`, `c117dec`, `e278bfe`, `b30756c`, `96d11e4`, `3833e96`, `2afd78c`, `a5326e6`, `47a92fd`, `b6e9e0e`, plus the commit containing this handover. Consult `git log --oneline 8b3ab1e..HEAD` for exact subjects and full immutable hashes.

Verification for the final measurement commit: 18 focused tests passed; `git diff --check` and staged diff reviewed. Contract, activation, collector, supervisor and completed manifest hashes were read back; the frozen files and raw capture were not modified. Existing dirty C-11/C-35 working-tree data were preserved and excluded from commits. No future return, PnL, predictive effect, V3, authenticated endpoint, or order activity occurred in this program's measurement/backlog work.

## Exact next decision

The operator must decide whether **any one** distinct Edge question can be preregistered with already-qualified point-in-time evidence, unopened outcomes, sample/power and after-cost criteria **without another collection**. Current evidence does not make microstructure, extreme movers, or sibling/F4 automatically ready. A scientifically valid answer may be **no new Edge experiment now**. Separately, prioritize existing VST safety/provenance and latency defects with networkless tests and independent review; authenticated account/order access, altered trading policy, and real funds remain their own explicit gates. Do not build a combined “super-strategy” or start V3 by implication.
