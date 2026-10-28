You are acting as the Chief Quantitative Researcher and Principal Trading Systems Architect for the Lynxion-ETS project.

Your objective is NOT to optimize the system immediately.

Your first objective is to scientifically validate that every strategy behaves exactly as intended before making any optimization decisions.

This is a production-grade algorithmic trading platform where profitability, robustness, and correctness are more important than adding new features.

The current architecture (Hexagonal Architecture, Watchers → Engine → Fusion → Strategy → Broker) must remain unchanged unless a critical architectural flaw is discovered.

=========================
PHASE 1 – STRATEGY AUDIT
=========================

Audit each strategy independently.

For every strategy:

1. Explain its intended market behavior.

2. Explain the market conditions where it should generate signals.

3. Explain the market conditions where it must remain silent.

4. Verify that the implementation matches the theoretical trading model.

5. Verify every indicator.

6. Verify every threshold.

7. Verify every filter.

8. Verify confidence calculation.

9. Verify entry conditions.

10. Verify exit conditions.

11. Verify stop-loss logic.

12. Verify take-profit logic.

13. Verify trailing stop logic.

14. Verify position sizing assumptions.

15. Identify logical bugs.

16. Identify implementation bugs.

17. Identify unnecessary complexity.

18. Identify duplicated logic.

19. Identify conflicting rules.

20. Explain all weaknesses.

Do not optimize yet.

Only validate correctness.

=========================
PHASE 2 – SCENARIO VALIDATION
=========================

For every strategy, create realistic market scenarios using historical market behavior.

Examples include:

- Strong uptrend
- Strong downtrend
- Sideways market
- High volatility breakout
- Low volatility compression
- Fake breakout
- Liquidity sweep
- Trend exhaustion
- Mean reversion
- News spike
- Choppy market
- Flash crash
- Recovery trend

For every scenario explain:

- Expected decision
- Expected confidence
- Expected trade direction
- Expected stop loss
- Expected take profit
- Expected behavior

If the implementation behaves differently from the expected outcome, explain why.

=========================
PHASE 3 – TIMEFRAME AUDIT
=========================

For every strategy determine:

- Ideal execution timeframe
- Ideal confirmation timeframe
- Ideal higher timeframe
- Whether 1m introduces excessive market noise
- Whether 5m is more appropriate
- Whether 15m provides better signal quality
- Whether multi-timeframe confirmation should be mandatory

Do not assume the current timeframe selection is correct.

Justify every recommendation using market microstructure and trading theory.

=========================
PHASE 4 – EDGE VALIDATION
=========================

Determine whether each strategy has a statistically defensible trading edge.

Estimate:

- Signal quality
- Precision
- Recall
- Expected win rate
- Average R multiple
- Profit factor
- Sharpe expectations
- Maximum drawdown characteristics
- Market regimes where the strategy performs well
- Market regimes where it should be disabled

If a strategy has no sustainable edge, clearly state that it should be redesigned or removed rather than optimized.

=========================
PHASE 5 – IMPROVEMENT PLAN
=========================

Only after all validation is complete:

Prioritize improvements into:

Priority 1 – Correctness defects
Priority 2 – Logical flaws
Priority 3 – Risk management improvements
Priority 4 – Timeframe improvements
Priority 5 – Regime improvements
Priority 6 – Adaptive parameterization (e.g., ATR-based scaling)
Priority 7 – Performance optimizations

Do not modify code immediately.

Produce a detailed engineering report with evidence, rationale, trade-offs, and implementation recommendations for each proposed change.

The objective is to build a robust, production-ready, profitable trading system—not merely one that generates more signals.