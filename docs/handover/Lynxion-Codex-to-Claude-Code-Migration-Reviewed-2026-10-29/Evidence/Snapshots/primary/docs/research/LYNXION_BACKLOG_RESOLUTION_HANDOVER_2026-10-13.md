# Backlog resolution and next capability — handover

Date: 2026-10-13. Baseline main HEAD `025094a`. Scope: documentation resolution, existing P0 evidence mapping and research-only Extreme-Mover interface. No broker/VST access, data collection, outcome inspection, trading-policy change, or deployment.

## Completed

1. [Canonical backlog](LYNXION_RESEARCH_BACKLOG.md): all R01–R26 have exactly one operational disposition (`CLOSED_FINAL`, `ACTIVE_DELIVERABLE`, `BLOCKED_EXTERNAL`, `RESEARCH_ASSET`) plus remaining deliverable, reopening evidence, dependency and autonomous-work answer. The scientific verdict in every original entry is preserved. The earlier [decision list](LYNXION_2026-10-13_PARKED_ITEMS_DECISION_LIST.md) provides per-item rationale. Closed experiments do not imply entire information families are impossible.
2. R14 Lead A: added authoritative mark/fill/order/route/clock/protective-state evidence requirements to the **existing** isolated `POST_PILOT2_EXECUTION_RECOVERY_BOARD.md` (P0 worktree commit `1e4b38e`). This maps existing execution-truth work; it creates no exit optimization or protective-order policy.
3. Structural Pullback Failure V1: in its separate research worktree, all 19 offline tests passed; contract SHA-256 `abf0cb341ed54e068218aadb6ca5b16b28a7cb7484773e52fba542dec38a7300`, candidate JSONL SHA-256 `260c987f232eb1036b90f736bc28d43179de309fbb577f22accc0ba7e40b9594`, and manifest SHA-256 `87614bf598d05cb6f37047f308e6dd34ba6b6877ef210f83e6b3bb68e5e7dad6` matched its recorded handover. Its 143 candidates remain development-only. No detector implementation was repeated or activated. A fresh candidate replay was not performed in this task; its earlier handover records one.
4. [Extreme-Mover reuse/result](EXTREME_MOVER_REUSE_AND_CAPABILITY_RESULT.md): inspected CMC screener, volatility/momentum/regime/ranking and local historical panels; none proves a complete historical time-T perpetual universe. Added pure `domain/extreme_mover_opportunity.py`, eight cleared-environment deterministic synthetic tests, and canonical synthetic record SHA-256 `d2817f155c90edb3ee708c6cfde9f21fed7c53ff9851057bed6eabed808cc98b`. Mixed cutoff, late receipt, absent symbol and source-value errors fail closed. No real historical rank was generated; that data path is `BLOCKED_EXTERNAL`.

## Scientific and safety boundary

The output is a metric-agnostic rank **view**, not a mover hypothesis, top-N selector, strategy or confidence. Venue, metric formula/window, eligibility thresholds, cost assumptions and outcome remain unfrozen. Caller-provided source hashes are retained but not independently certified by the pure function. Historical whole-universe provenance, listing/delisting/status changes, synchronized bars and executable quotes/costs remain missing. `EXTREME_MOVER_DATA_PARTIAL` remains the data verdict; no `EDGE_CONFIRMED`, profitability or live-readiness claim follows. Pilot-1 and Pilot-2 are separate immutable `PARTIAL` measurement cohorts; no repeat collection was started.

## Verification and commits

- Main commits: `8bc7d1c` backlog overlay; `b609b20` research interface and reuse assessment; one bounded follow-up commit records mixed-cutoff validation and this handover. Final main HEAD is this handover's containing commit.
- Isolated P0 worktree: `1e4b38e` board-only Lead A dependency map; no P0 runtime/code change.
- `python3 -m unittest tests.unit.test_extreme_mover_opportunity`: 8 PASS under `/usr/bin/env -i` with bytecode disabled. Structural detector: 19 PASS under the same isolation pattern. `git diff --check`: PASS before commits.
- Pilot-2 contract and activation hashes rechecked against recorded values; no protected artifact changed. Unrelated C-11/C-35 collector working-tree writes were left untouched.

## Exact remaining decisions

No open-ended backlog task was created. R04–R06 retain only their existing frozen gates and require a fresh **status** check before any statement about current collection. R02/R03/R25 require external evidence plus a separate scientific decision. R14 remains unidentifiable for exit Edge until P0 produces an authoritative joined record. R22's real historical ranking is blocked by incomplete time-T universe provenance. Structural Pullback Failure's independent after-cost test remains `EXPERIMENT_NOT_YET_FEASIBLE`. Opening future outcomes, initiating new collection, changing trading behavior or activating VST/real trading each remains separately gated.
