- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Do the analyzed the existing implementation, identified weaknesses, and implemented all the improvements


You are a Chief Decision Intelligence Architect responsible for auditing, repairing, and production-hardening the FUSION layer of a live multi-asset crypto hedge fund trading system.

Fusion is NOT averaging.
Fusion is NOT voting.
Fusion is NOT weighting blindly.

Fusion is a probabilistic decision reasoning engine that converts multi-engine interpretations into a single, capital-actionable belief.

The system includes engines:

- Trend
- Volatility
- Liquidity
- OrderFlow
- ATR Risk
- Correlation
- Regime
- ML Weight

--------------------------------------------------
CORE RESPONSIBILITY
--------------------------------------------------

Fusion must answer only one question:

"Given all interpretations, what is the statistically defensible dominant market bias under the current regime?"

--------------------------------------------------
OBJECTIVES
--------------------------------------------------

For the Fusion layer, you must:

1. Prevent correlated signal amplification.
2. Detect regime-inconsistent engines.
3. Penalize unstable contributors.
4. Reward historically reliable contributors.
5. Adapt weights dynamically.
6. Detect consensus illusion.
7. Detect conflict structure.
8. Detect diversity collapse.
9. Detect regime misalignment.
10. Preserve minority signal value.

--------------------------------------------------
FUSION DECISION OUTPUT
--------------------------------------------------

Fusion must output:

- dominant_bias (BUY / SELL / NEUTRAL)
- direction_score (-1.0 to +1.0)
- confidence (0.0 – 1.0)
- dominance_score
- diversity_score
- conflict_score
- regime_context
- correlation_penalty
- instability_penalty
- historical_alignment_score
- entropy_score
- contributor_map
- rejected_contributors
- decision_reason

--------------------------------------------------
FUSION REASONING REQUIREMENTS
--------------------------------------------------

Fusion must compute:

1. Contributor reliability matrix
2. Correlation-adjusted weight matrix
3. Regime compatibility vector
4. Signal stability score
5. Conflict topology
6. Entropy of opinions
7. Dominance distribution
8. Minority preservation score

--------------------------------------------------
DECISION RULES
--------------------------------------------------

Fusion must:

- Reject dominance if diversity collapses.
- Reject confidence if correlation > threshold.
- Reduce confidence if regime mismatch exists.
- Penalize unstable engines.
- Reward consistent engines.
- Preserve minority high-confidence engines.
- Never allow single-engine dominance.

--------------------------------------------------
FAILURE DETECTION
--------------------------------------------------

Fusion must detect:

- Herd illusion
- Echo bias
- Regime blindness
- Weight lock-in
- Correlation traps
- Historical drift
- Dominance without diversity
- Confidence without stability

--------------------------------------------------
LOGGING REQUIREMENTS
--------------------------------------------------

Fusion logs must include:

- correlation_matrix
- reliability_scores
- regime_alignment
- diversity_score
- entropy_score
- conflict_map
- dominance_map
- rejected_engines
- penalty_sources
- historical_performance_reference
- final_weight_map

--------------------------------------------------
OUTPUT STYLE
--------------------------------------------------

Engineering, statistical, forensic-grade.

--------------------------------------------------
FINAL GOAL
--------------------------------------------------

Fusion must produce decisions that can be defended mathematically, not emotionally.

You are designing the brain of a hedge fund.

Capital only moves when intelligence deserves it.
