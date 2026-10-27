# Frozen / collecting studies — status-only audit

## 2026-10-27 22:05 UTC — requested unfinished-backlog status refresh

Completed a fresh **metadata-only** local status audit; no sealed outcomes, candidate
counts, sample gate or economics were opened. Limited sanitized Python process-name
matching for c11/c33/c35/forced_liquidation/funding_shadow found no matching resident
local collector. This does not exclude remote hosts, renamed processes or intermittent
schedulers. Current collector liveness is NOT VERIFIED, not healthy because an old
protocol label says COLLECTING. No process was started/stopped or protocol changed.

| Artifact | Bytes | Last modification UTC |
|---|---:|---|
| C11 prospective_ledger.json | 2946 | 2026-09-24T08:41:40+00:00 |
| C33 events.jsonl | 60142613 | 2026-09-24T14:52:10+00:00 |
| C35 candles.jsonl | 7027000 | 2026-09-24T13:08:44+00:00 |
| C35 decisions.jsonl | 60760 | 2026-09-24T13:09:25+00:00 |
| C35 funding.jsonl | 42511 | 2026-09-24T09:42:21+00:00 |
| C35 funding_coverage.jsonl | 295470 | 2026-09-24T13:08:46+00:00 |

All five previously dirty C11/C35 files remain untouched. This completes the current
authorized status-audit action, NOT these prospective studies or their frozen sample
requirements. Their old outcomes/gates are unchanged. Any resumed collection must be
treated as a separately scoped restoration of its exact existing protocol with explicit
gap accounting and source/host verification, not synthetic backfill, early unsealing,
a replacement cohort or permission to repeat Pilot1/2. No liveness guarantee or new
scientific result follows. The historical audit and constraints below remain preserved.

2026-10-05. **Read-only status audit, not a gate execution or outcome refresh.** The canonical statuses and exact verdicts are in [R02–R06](LYNXION_RESEARCH_BACKLOG.md). No frozen definition, file or collector was changed. Local file modification times are not proof of a presently healthy process, and sealed economic outcomes were not inspected.

| Study | Existing scientific/operational state | Latest scoped evidence and next frozen gate | Current health certainty |
|---|---|---|---|
| C-11 | `COLLECTING`, background only | [Task](../../tasks/task0100-c11-prospective-funding-shadow.md) and [portfolio review](../RESEARCH_PORTFOLIO_REVIEW_2026-09-27.md) document a settlement-triggered shadow after frozen epoch `1788082349`, with dated N=5 versus >=100 total and >=30/symbol. `data/research/c11/prospective_ledger.json` is dirty independent work; not opened here. | **UNKNOWN live liveness**; dated evidence cannot be promoted to today's count. Next: existing independent frozen monitor/sample and cost gates only. |
| C-33 | `PROSPECTIVE_COLLECTING`; censored `!forceOrder@arr`, not full tape | [Feasibility](../LIQUIDATION_OI_FEASIBILITY_2026-09-16.md) documents a 1,034-bucket dated checkpoint below 8,640 warmup, then its own 180-day/300-outcome gate. Local `events.jsonl` and activation manifest exist; no new count was computed. | **UNKNOWN live liveness**. A file's existence or September modification time is not a heartbeat. Next: its independent frozen collection, without backfill. |
| C-35 | `TOO_SLOW / COLLECTING`, background only; not F4 | [Throughput gate](../../tasks/task0390-c35-throughput-gate.md) mechanically deprioritized it after the 168-decision checkpoint; later dated backlog review cites 292 decisions/3 completed positions versus 240-outcome target. Local candle/decision/funding files are dirty independent work and not parsed. | **UNKNOWN live liveness/current counts**. Next: existing frozen cost/sample gate only; no acceleration by threshold or interval changes. |
| Compression/F4 | `FROZEN_PROSPECTIVE_RESEARCH_LEAD`; separate from C-35 | [Forward plan](../../research/external_signal_study/post_phase3a/COMPRESSION_FORWARD_VALIDATION_PLAN.md) retains the original completed-bar F4 and prospective controls. Phase 3A was inconclusive/data-limited, not confirmation. | No qualifying new inbound sibling feed verified in repository. No prospective F4 contrast opened. |
| COMPRESSION_FORWARD_1 | `COMPRESSION_FORWARD_1_BLOCKED_SIGNAL_FEED`; M3 `NOT_IDENTIFIABLE` | [M2 spec](../../research/external_signal_study/post_phase3a/COMPRESSION_FORWARD_1_M2_SPEC.md) requires complete immutable inbound signal IDs, UTC send/receipt, labels, cursor and gap audit before activation. Static exports do not qualify. | Blocked by feed provenance; no activation or new cohort verified. Do not rescue with historical exports. |

## 2026-10-10 local liveness addendum (outcome-blind)

The operator requested a fuller audit of unfinished backlog items. A read-only local process-list filter found **no resident process identifiable as a C-11, C-33, or C-35 collector** at this checkpoint. The latest local modification times for `c11/prospective_ledger.json`, `c33/events.jsonl`, and `c35/candles.jsonl`/`decisions.jsonl` were all on 2026-09-24. This does **not** prove that no external host, intermittent scheduler, or independent writer exists; it does mean that the older `COLLECTING` scientific/protocol label must not be presented as verified *current local liveness*. No sealed outcomes, count gates, or private account data were opened. No collector was started or altered.

Disposition: preserve the three frozen protocols and their old verdicts; mark present local liveness **NOT VERIFIED / stale local artifacts** until their own authorized operator/runtime evidence establishes otherwise. Do not manufacture a completion verdict from inactivity, restart them under the Pilot-2 measurement task, or begin a replacement collection after the frozen Pilot-2 stop. Pilot-2 retains P0 operational priority. Any changed definition, early unsealing, source substitution, or cancellation of an independently frozen study requires its own decision.
