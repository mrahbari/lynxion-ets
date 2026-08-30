# TASK-0107 — OI-Confirmed Price Impulse C-16

**Status:** IN PROGRESS — PROTOCOL FROZEN

## Objective

Evaluate one causal price-impulse continuation hypothesis that directly consumes official
open-interest history and actual funding cashflows.

## Acceptance Criteria

- Commit this protocol before aligning OI with price or evaluating outcomes.
- Test strict pre-decision OI/price alignment and current-observation exclusion.
- Use next-open entry, exact 24h exit, overlap rejection, and actual funding signs.
- Keep primary/reverse, folds, symbols, and sides separable.
- Apply the frozen conjunctive gate without same-sample amendments.
- Do not modify production, risk, symbol eligibility, or order handling.
