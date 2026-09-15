# Lynxion Roadmap Index

**Updated:** 2026-09-14

**Repository checkpoint:** `f505114`

**Economic verdict:** `COLLECTING — PROFITABILITY NOT PROVEN`

This file is the canonical navigation page for Lynxion planning. It resolves the roles of older
roadmaps without deleting their historical analysis.

For a complete handoff to another AI or technical reviewer, start with `docs/AI_START_HERE.md`.
When only one attachment can be provided, use `docs/LYNXION_SINGLE_FILE_AI_HANDOFF.md`; it embeds
the complete orientation, current evidence, roadmap, validation rules, and continuation prompt.

## Authority order

1. `tasks/00-right-path.md` — governing mission, execution rules, scientific gates, and stop
   conditions.
2. `docs/INVESTOR_RELEASE_ROADMAP.md` — short-term delivery scope and release track.
3. `docs/INVESTOR_DELIVERY_EDGE_ACCELERATION_PLAN.md` — long-term economic-validation track and
   bounded hypothesis process.
4. `docs/EDGE_ACCELERATION_WITHOUT_PLATFORM_EXPANSION.md` — active engineering/hypothesis budget
   and decision-before-build discipline.
5. `docs/LYNXION_PROGRESS_LEDGER.md` — append-only execution history and current operational state.
6. Candidate preregistrations under `tasks/research/` — frozen rules for each experiment.

If a summary conflicts with a frozen candidate preregistration, the preregistration governs that
candidate. If an older roadmap conflicts with `tasks/00-right-path.md`, the latter governs.

## Current short-term roadmap

- The initial package is frozen as `INVESTOR_REVIEW_READY — TECHNICAL VST/SHADOW ONLY` at evidence
  boundary `1f07520`; this is not a profitability or pilot-readiness verdict.
- Preserve the deterministic broker-free demo, bounded BingX VST evidence, fail-closed risk and
  protection controls, evidence index, architecture map, and explicit limitations.
- Complete only evidence-supported correctness fixes that prevent configured behavior from working.
- Continue the bounded broker-boundary audit after TASK-0334 closed non-finite BingX position
  exposure admission; each further correction requires a reproduced fail-open or correctness defect.
- TASK-0335 also closes non-finite order size/price at the shared order-path risk gate; repository
  completion is not evidence that an already-running process has loaded either correction.
- The +12% activation/+5% net-floor exit shadow remains blocked from activation until fresh
  single-runner, read-only proof shows zero missing stops and the applicable runtime/authenticated
  approval exists.
- Do not allow packaging work or optional cleanup to displace edge validation.

## Current long-term roadmap

- Continue the bounded, preregistered search for positive net expectancy after fees, funding, and
  slippage, with chronological OOS/WFO, uncertainty, drawdown, concentration, and prospective gates.
- C-35 is `COLLECTING`: 103 decisions, two completed positive cost-adjusted outcomes, both SHORT and
  across two symbols. The sample is insufficient; aggregate economics remain sealed until every
  frozen gate in `tasks/research/edge-candidate-register-v34.md` passes.
- C-11 is `COLLECTING`: three completed outcomes; the N=3 positive mean is concentrated in one
  large ETHUSDT result and is not edge evidence. Only funding
  settlements strictly after epoch `1788082349` are eligible.
- C-33 is `COLLECTING`: controlled recovery excluded the stale interval without backfill and the
  resumed single public session has advanced the cohort from 740 to 901 eligible buckets. The next
  frozen checkpoint is 1,000.
- Keep `NO_TRADE_DEFAULT` for economic admission until a candidate clears every frozen gate.
- Apply the ranked decision in `docs/EDGE_ACCELERATION_DECISION_2026-09-14.md`: C-33 liveness is
  restored minimally; continue it without backfill, continue C-35 to its 168-decision rate
  checkpoint, keep C-11 as low-cost background research, and reject new carry/basis or broad L2
  construction.

## Historical-document policy

- Superseded strategy roadmaps and old project-context snapshots were removed in TASK-0326 because
  their Alpha/edge labels and mutable runtime assertions could mislead reviewers. Git history
  retains the tracked versions if forensic recovery is ever required.
- `docs/INVESTOR_RELEASE_GAP_ASSESSMENT.md` is a dated 2026-09-09 snapshot. Its two demo-scope P0
  blockers were subsequently closed by TASK-0225 and TASK-0226; TASK-0234 froze the technical-only
  investor verdict.

## Context maintenance rule

Update this index and the `Current task`/`Status` header in `docs/LYNXION_PROGRESS_LEDGER.md` when a
release verdict, research gate, canonical candidate, or material blocker changes. Hourly collection
checkpoints remain in the ledger and do not require rewriting every roadmap document.
