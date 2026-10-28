As the Technical Lead, I am initiating the Final Profitability Validation & Root Cause Audit.

The previous profitability report indicates that no strategy achieved positive net expectancy under the current configuration.

Before we conclude that the strategies themselves lack an edge, I want to verify that the observed losses are not caused by configuration, execution realism, regime filtering, parameter selection, or implementation artifacts.

This is a READ-ONLY audit.

Do NOT modify any code.

Do NOT tune any parameters.

Do NOT optimize anything.

Your task is to determine WHY the current results are poor.

────────────────────────────────────

Phase 1 — Backtest Integrity

Verify the following:

• no look-ahead bias
• no candle leakage
• no future data usage
• no duplicate executions
• no duplicate signals
• fills occur only after signals
• execution timing is realistic
• fee model is correct
• slippage model is correct
• leverage is applied correctly
• liquidation logic (if any)
• funding calculations (if applicable)

Report every issue.

────────────────────────────────────

Phase 2 — Strategy Signal Quality

For each strategy report:

• total signals
• executed trades
• filtered trades
• rejection reasons
• average holding time
• average stop distance
• average take profit distance
• average RR
• expectancy before fees
• expectancy after fees

Determine whether losses originate from

• poor entries
• poor exits
• poor stop placement
• poor TP placement
• fees
• slippage
• wrong regime
• low RR
• overtrading
• undertrading

────────────────────────────────────

Phase 3 — Regime Validation

For every strategy determine:

During which regime was it profitable?

Trending Up

Trending Down

Range

High Volatility

Low Volatility

News-like spikes

Sideways

For each regime provide

Trades

Win Rate

Net PnL

Average RR

Expectancy

State whether the current RegimeEngine is activating the strategy in the correct situations.

────────────────────────────────────

Phase 4 — Parameter Sensitivity

Without changing code,

evaluate whether the current default parameters are located near a profitable region or whether profitability only appears under unrealistic overfitted parameters.

Highlight:

Highly sensitive parameters

Stable parameters

Dangerous parameters

Parameters that should never be optimized

────────────────────────────────────

Phase 5 — Risk Engine Analysis

Verify that

position sizing

SL distance

TP distance

confidence multiplier

ATR multiplier

portfolio exposure

all interact consistently.

Determine whether any component unintentionally destroys expectancy.

────────────────────────────────────

Phase 6 — Portfolio Analysis

Determine whether

strategies interfere with each other,

compete for capital,

or block better opportunities.

Calculate

strategy correlation

capital utilization

idle time

portfolio efficiency

────────────────────────────────────

Phase 7 — Production Readiness

Answer only YES or NO for each:

Does the architecture support profitable trading?

Does the execution engine behave correctly?

Does the sizing engine behave correctly?

Does the strategy framework behave correctly?

Does the Regime Engine behave correctly?

Does Fusion behave correctly?

Does Risk behave correctly?

Can profitability be achieved through better strategy logic and parameter tuning alone?

Or is there a fundamental architectural issue?

────────────────────────────────────

Final Deliverable

Produce a technical report containing:

1. Executive Summary

2. Root Causes ranked by impact

3. Architectural Issues

4. Strategy Issues

5. Risk Issues

6. Regime Issues

7. Execution Issues

8. Estimated Profitability Potential

9. Top 20 improvements ranked by expected impact

10. Which improvements are mandatory before production

11. Which improvements are optional

12. GO / NO GO recommendation

Do not propose major architectural redesigns.

Respect the existing architecture.

Focus on identifying the true sources of negative expectancy.