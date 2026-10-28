The scientific validation has confirmed that the current trading engine is structurally correct but lacks statistically defensible trading edge.

Do NOT optimize the existing strategies yet.

Instead, switch into Quantitative Research mode.

Your objective is to determine WHY each strategy fails to generate positive expectancy.

For every strategy:

1. Identify the exact source of negative expectancy.

Separate the contribution of:

- Entry quality
- Exit quality
- Stop Loss placement
- Take Profit placement
- Position sizing
- Transaction costs
- Slippage
- Market regime mismatch
- Timeframe mismatch
- Signal latency
- Indicator lag
- Noise sensitivity

2. Quantify which component contributes the most to performance degradation.

3. Determine whether the strategy has an underlying edge that is merely hidden by poor execution, or whether the entry logic itself has no predictive power.

4. If the entry logic has no predictive power, explicitly recommend replacing the strategy instead of optimizing it.

5. For strategies that appear salvageable, design a research roadmap rather than implementation changes.

For each strategy provide:

- Hypothesis
- Supporting evidence
- Statistical confidence
- Recommended experiments
- Required datasets
- Success criteria

Do not modify any production code.

Do not tune parameters.

Do not optimize thresholds.

Think like the head of quantitative research at a systematic hedge fund whose responsibility is to decide whether a strategy deserves further investment or should be retired.