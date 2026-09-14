# Lynxion Roadmap Index

**Updated:** 2026-09-14

**Repository checkpoint:** `357077a`

**Economic verdict:** `COLLECTING — PROFITABILITY NOT PROVEN`

This file is the canonical navigation page for Lynxion planning. It resolves the roles of older
roadmaps without deleting their historical analysis.

## Authority order

1. `tasks/00-right-path.md` — governing mission, execution rules, scientific gates, and stop
   conditions.
2. `docs/INVESTOR_RELEASE_ROADMAP.md` — short-term delivery scope and release track.
3. `docs/INVESTOR_DELIVERY_EDGE_ACCELERATION_PLAN.md` — long-term economic-validation track and
   bounded hypothesis process.
4. `docs/LYNXION_PROGRESS_LEDGER.md` — append-only execution history and current operational state.
5. Candidate preregistrations under `tasks/research/` — frozen rules for each experiment.

If a summary conflicts with a frozen candidate preregistration, the preregistration governs that
candidate. If an older roadmap conflicts with `tasks/00-right-path.md`, the latter governs.

## Current short-term roadmap

- The initial package is frozen as `INVESTOR_REVIEW_READY — TECHNICAL VST/SHADOW ONLY` at evidence
  boundary `1f07520`; this is not a profitability or pilot-readiness verdict.
- Preserve the deterministic broker-free demo, bounded BingX VST evidence, fail-closed risk and
  protection controls, evidence index, architecture map, and explicit limitations.
- Complete only evidence-supported correctness fixes that prevent configured behavior from working.
- The +12% activation/+5% net-floor exit shadow remains blocked from activation until fresh
  single-runner, read-only proof shows zero missing stops and the applicable runtime/authenticated
  approval exists.
- Do not allow packaging work or optional cleanup to displace edge validation.

## Current long-term roadmap

- Continue the bounded, preregistered search for positive net expectancy after fees, funding, and
  slippage, with chronological OOS/WFO, uncertainty, drawdown, concentration, and prospective gates.
- C-35 is `COLLECTING`: 88 decisions, two completed positive cost-adjusted outcomes, both SHORT and
  across two symbols. The sample is insufficient; aggregate economics remain sealed until every
  frozen gate in `tasks/research/edge-candidate-register-v34.md` passes.
- C-11 is `COLLECTING`: two completed outcomes and one pending ETHUSDT candidate; only funding
  settlements strictly after epoch `1788082349` are eligible.
- C-33 is `COLLECTING`: 740 eligible buckets at the latest verified checkpoint; the next frozen
  checkpoint is 1,000.
- Keep `NO_TRADE_DEFAULT` for economic admission until a candidate clears every frozen gate.

## Historical documents

- `tasks/comprehensive_strategy_and_platform_roadmap.md` and
  `tasks/comprehensive_strategy_logic_audit_and_long_term_roadmap.md` are retained as legacy
  hypothesis inventories. Their Alpha/edge labels, performance tables, targets, and suggested
  production changes are not current validated conclusions and are not execution authority.
- `docs/INVESTOR_RELEASE_GAP_ASSESSMENT.md` is a dated 2026-09-09 snapshot. Its two demo-scope P0
  blockers were subsequently closed by TASK-0225 and TASK-0226; TASK-0234 froze the technical-only
  investor verdict.

## Context maintenance rule

Update this index and the `Current task`/`Status` header in `docs/LYNXION_PROGRESS_LEDGER.md` when a
release verdict, research gate, canonical candidate, or material blocker changes. Hourly collection
checkpoints remain in the ledger and do not require rewriting every roadmap document.
