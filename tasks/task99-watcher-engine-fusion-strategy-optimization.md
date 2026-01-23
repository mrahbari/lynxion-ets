You are acting as a Senior Hedge-Fund Systems Architect
responsible for auditing, repairing, and production-hardening
a live multi-layer crypto hedge fund trading system.

You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.

Your task is NOT to redesign everything.
Your task is to REMOVE bias, REDUCE fragility, and IMPROVE statistical defensibility.

--------------------------------------------------
SYSTEM LAYERS & RESPONSIBILITY CONTRACTS
--------------------------------------------------

WATCHERS = market perception sensors  
ENGINES  = probabilistic interpreters  
FUSION   = decision reasoning system  
STRATEGIES = capital deployment modules  

No layer may violate its responsibility.

--------------------------------------------------
WATCHER LAYER (PERCEPTION ONLY)
--------------------------------------------------

Watchers observe raw market reality.
They must NOT interpret, predict, trade, or bias.

For EACH watcher:

1. Observation Responsibility
   - Exact market phenomenon observed

2. Purity Enforcement
   - How interpretation leakage is prevented

3. Data Integrity Risks
   - Where observation can degrade or lie

4. Output Redesign
   - Raw, normalized, unbiased observation format

5. Confidence Calculation
   - Measurement reliability only (not trade confidence)

6. Noise Suppression
   - How false measurements are filtered

7. Statistical Validation
   - Metrics that prove observation stability

8. Temporal Consistency
   - Time alignment and update frequency

9. Redundancy Control
   - How overlap with other watchers is handled

10. Failure Detection
    - When and how this watcher must be muted

11. Engine Compatibility
    - How engines should consume this data

--------------------------------------------------
ENGINE LAYER (INTERPRETATION ONLY)
--------------------------------------------------

Engines transform observations into probabilistic beliefs.
They must NOT trade or size positions.

For EACH engine:

1. Engine Purpose
   - Market dimension interpreted

2. Structural Weaknesses
   - Where it drifts or lies

3. Signal Redesign
   - How watcher data is interpreted

4. Confidence Redesign
   - Statistical confidence, not intuition

5. Noise Suppression
   - False interpretation reduction

6. Performance Memory
   - Metrics tracked about itself

7. Degradation Detection
   - When reliability decays

8. Fusion Interaction
   - How fusion should weight or penalize it

9. Failure Protection
   - How engine output is blocked safely

--------------------------------------------------
FUSION LAYER (DECISION REASONING)
--------------------------------------------------

Fusion converts multiple interpretations into a single
capital-actionable belief.

Fusion must prevent:
• Correlated signal amplification
• Dominance without diversity
• Confidence without stability

Fusion must compute:
- Reliability matrix
- Correlation-adjusted weights
- Regime compatibility
- Entropy and diversity
- Conflict topology

Fusion outputs:
- dominant_bias
- direction_score
- confidence
- dominance_score
- diversity_score
- conflict_score
- regime_context
- contributor_map
- rejected_contributors
- decision_reason

--------------------------------------------------
STRATEGY LAYER (CAPITAL DEPLOYMENT)
--------------------------------------------------

Strategies are execution modules.
They must obey fusion, not override it.

For EACH strategy:

1. Strategy Purpose
2. Hidden Failure Modes
3. Entry Redesign
4. Exit Redesign (SL / TP / Trailing)
5. Risk & Position Sizing
6. Regime Compatibility
7. Fusion Dependency
8. Failure Protection
9. One Expectancy Improvement

--------------------------------------------------
GLOBAL CONSTRAINTS
--------------------------------------------------

• No hindsight bias
• No perfect data assumptions
• No magic indicators
• No black-box confidence
• Must be implementable in production

--------------------------------------------------
FINAL GOAL
--------------------------------------------------

Transform the system from:
"many signals pretending to be intelligence"

into:
"a statistically defensible decision-making organism"

You are designing for hedge fund survival,
not backtest beauty.
