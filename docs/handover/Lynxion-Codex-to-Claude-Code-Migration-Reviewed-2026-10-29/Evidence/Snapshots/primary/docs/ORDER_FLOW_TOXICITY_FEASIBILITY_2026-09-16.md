# Order-Flow Toxicity Feasibility — 2026-09-16

## Question

Does the existing point-in-time taker-flow panel leave one causally distinct, low-cost incremental
NO_TRADE or state-classification question after Phase 17 and C-21/C-22, without building raw L2 or
recycling opened outcomes?

## Existing evidence

- Phase 17 directly tested incremental information. Smoothed aggressor flow had small reversal IC
  near -0.03, was about 58% correlated with recent OHLCV return, and was weaker than the OHLCV
  reversal baseline. Cost-adjusted follow and contrarian directions were negative in every fold and
  symbol.
- Phase 17 also tested flow inside trade-intensity expansion and contraction states. Both states
  remained near minus the 0.30% cost with 0/4 positive folds, so liquidity gating did not rescue it.
- C-21 tested extreme single-venue continuation on six symbols: N=2,326, expectancy -0.2086%, PF
  0.8384, and all four folds negative.
- C-22 repeated the frozen mechanism on five disjoint symbols: N=1,928, expectancy -0.1770%, PF
  0.8906, with both sides negative. The family was closed.
- C-27 tested concentrated large-aggressor exhaustion and failed every fold, side, year, and tested
  cost. C-34 tested exact Spot/perpetual flow divergence and was negative in primary and reverse
  periods with a wholly negative clustered interval.
- TASK-0369 then tested the most relevant incremental role under the new mission: conditioning the
  identical 15-minute mean-reversion baseline on extreme aggressive flow. Improvement was only
  +0.0039 percentage points; net expectancy remained -0.2881%, and every fold, symbol, and side was
  negative.

## NO_TRADE assessment

A NO_TRADE filter can be useful only when it preserves or improves an otherwise plausible positive
baseline out of sample. Here the tested baseline is negative, and flow did not add incremental
information. Selecting a new toxicity threshold, side, horizon, or diagnostic subgroup after these
opened outcomes would be post-hoc loss filtering, not a new mechanism.

VPIN or true order-book toxicity would require a distinct trade-level/L2 information set. The
current mandate forbids building that infrastructure before a specific causal question earns it,
and existing evidence provides no such trigger.

## Decision

`REJECT — NO DISTINCT EXISTING-DATA ORDER-FLOW TOXICITY TEST JUSTIFIED`.

Do not retune taker imbalance, create another flow-conditioned candidate, or build raw L2/VPIN
infrastructure. Reconsider only if independently sourced point-in-time information supplies a new
mechanism and unopened boundary.
