- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Take a look at ./logs/forensic.log which is already implemented and the history of successful order placement is there! 
- Review the implemented codes specially ./infrastructure/logging/forensic_logger.py for more clarification.

---

# 🎯 ADVANCED FORENSIC PROMPT — STRATEGY FILTERING GOVERNANCE

You are acting as a Quantitative Strategy Forensic developer for an institutional hedge fund.

Your task is to analyze the behavior of the `volatility_breakout` strategy, specifically its signal filtering logic, fix and enhance the implementations.

Context:
The strategy is rejecting a large percentage of incoming signals. While this suggests strong quality control, it also raises the risk of:

- Over-filtering
- Alpha suppression
- Regime blindness
- Structural bias
- Missed opportunity cost
- False confidence in low sample performance

Your objectives:

1. Determine whether the current filtering logic is:
   - Statistically justified
   - Regime adaptive
   - Sample-size aware
   - Bias-controlled
   - Causally defensible

2. Identify and fix:

   A) Which exact filters are responsible for the majority of rejections  
   B) Whether those filters are acting independently or redundantly  
   C) Whether rejection reasons are correlated with future profitable moves  
   D) Whether rejection logic changes across regimes  
   E) Whether rejection improves or degrades long-term expectancy  

3. Produce a **Filter Accountability Report** containing:

   - Rejection Rate by Filter (%)
   - Rejection Rate by Regime
   - Rejection Rate by Volatility State
   - Rejection Rate by Trend Context
   - Rejection Rate by Session / Liquidity Window

4. For each filter, classify it as:

   - Alpha-Protective
   - Alpha-Neutral
   - Alpha-Suppressive
   - Noise-Based
   - Regime-Misaligned

5. Calculate a **Filter Contribution Score**:

   FilterContribution = 
   (Expected_PnL_with_filter - Expected_PnL_without_filter) 
   adjusted by opportunity cost and variance impact.

6. Identify any filters that:

   - Reduce drawdown but destroy expectancy
   - Increase win rate but reduce profitability
   - Improve backtest but harm forward performance
   - Are only valid in specific regimes

7. Propose and handle as much as possible:

   - Which filters must become regime-conditional
   - Which filters must become probabilistic instead of binary
   - Which filters must be removed
   - Which filters must be weakened
   - Which filters must be strengthened

8. Design a **Dynamic Filter Governance Layer** that:

   - Allows filters to self-downgrade
   - Allows filters to self-disable
   - Allows filters to self-weight
   - Tracks historical effectiveness per regime
   - Prevents permanent dominance of any single filter

9. Produce a **Scientific Verdict**:

   Is `volatility_breakout` currently:

   - Under-selective
   - Over-selective
   - Balanced
   - Statistically blind
   - Regime fragile
   - Or scientifically mature?

10. Final Output Requirements:

   - Fix observation.
   - Improved code.
   - No compliments.
   - No assumptions.
   - All conclusions must be evidence-based.
   - Highlight every area where the system is currently trading on belief instead of proof.

Assume the strategy will manage 8-figure capital.

Your responsibility is to protect capital, not to defend design decisions.

Be strict.
Be quantitative.
Be institutional.