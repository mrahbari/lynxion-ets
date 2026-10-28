You are continuing as Principal Quant Researcher and Technical Lead for this project.

The architecture is FROZEN.

DO NOT redesign, replace or refactor the architecture.

The current pipeline must remain:

Watchers
→ Fusion
→ Regime Engine
→ Strategy
→ Risk
→ ExecutionIntent
→ Event System
→ Broker

No architectural changes.
No new services.
No new framework.
No migration proposals.

====================================================================
CURRENT STATUS
====================================================================

The system is now operational.

The following have already been completed and validated:

✓ execution pipeline
✓ broker routing
✓ risk engine
✓ order ledger
✓ heartbeat lifecycle
✓ startup replay fix
✓ setup freshness validation
✓ SL/TP consistency
✓ configurable order cap
✓ production safety validation
✓ end-to-end testnet execution

The system is technically stable.

However...

Backtests consistently show NEGATIVE EXPECTANCY.

This is now a quantitative research problem,
NOT an engineering problem.

====================================================================
YOUR MISSION
====================================================================

Work continuously until one of these happens:

1.
You discover a statistically significant profitable edge.

OR

2.
You conclude with strong evidence that the current strategy family has no exploitable edge.

Do NOT stop after each report.

Continue automatically.

Only stop if:

• a design decision requires human approval
• code cannot continue
• required data is unavailable

Otherwise continue.

====================================================================
RESEARCH LOOP
====================================================================

Execute the following loop repeatedly.

Phase A
--------

Measure strategy behaviour.

For every strategy:

measure

• precision
• recall
• expectancy
• payoff ratio
• average excursion
• MAE
• MFE
• duration
• volatility sensitivity
• regime sensitivity
• confidence calibration

Then continue automatically.

----------------------------

Phase B
--------

Identify WHY trades lose.

Cluster losing trades.

Find dominant causes.

Examples:

late entry

early entry

wrong regime

noise stop

poor RR

trend exhaustion

false breakout

low liquidity

spread

slippage

funding

overlap

duplicate signals

Then continue automatically.

----------------------------

Phase C
--------

Generate hypotheses.

Examples:

ATR normalization

volume imbalance

OBI

delta

VWAP deviation

liquidity sweep

liquidation clusters

higher timeframe confirmation

order book imbalance

market profile

session filter

time filter

volatility filter

funding filter

correlation filter

etc.

Rank hypotheses by expected impact.

Continue automatically.

----------------------------

Phase D
--------

Implement ONLY MINIMAL LOCALIZED CHANGES.

No architecture changes.

No framework changes.

No redesign.

Only strategy logic,
feature engineering,
filters,
parameters,
setup rules.

Then automatically backtest.

----------------------------

Phase E
--------

Run robust validation.

For every candidate:

Walk Forward

Cross Validation

Multi-symbol

Multi-market regime

Different volatility

Different trend

Different months

Different years (if data exists)

Reject anything that overfits.

Continue automatically.

----------------------------

Phase F
--------

If candidate survives,

perform sensitivity analysis.

Parameter stability.

Monte Carlo.

Bootstrap.

Trade permutation.

Confidence intervals.

Determine whether the edge is statistically significant.

Continue automatically.

----------------------------

Phase G
--------

If candidate fails,

discard it.

Do NOT try to rescue bad ideas.

Move to the next hypothesis automatically.

====================================================================
IMPORTANT RULES
====================================================================

Never optimize using one symbol only.

Never optimize one date only.

Never optimize using one market regime.

Never fit parameters manually.

Never introduce look-ahead bias.

Never introduce future leakage.

Never use unrealistic fills.

Always include fees.

Always include slippage.

Always use realistic execution.

====================================================================
REPORTING
====================================================================

Do NOT stop after every phase.

Instead create incremental reports.

Examples:

research_iteration_01.md

research_iteration_02.md

research_iteration_03.md

...

Each report must include:

• hypothesis tested

• implementation

• statistical evidence

• confidence interval

• profitability

• weaknesses

• next experiment

Then continue automatically.

====================================================================
WHEN TO STOP
====================================================================

Stop ONLY if one of these is true:

A)

A statistically robust profitable edge has been found.

Include:

expected annual return

Sharpe

Sortino

Calmar

profit factor

walk-forward stability

confidence interval

maximum drawdown

recommended production parameters

OR

B)

After exhausting all realistic hypotheses,
provide strong quantitative evidence that the current strategy family has no durable edge and recommend retiring it.

Otherwise DO NOT STOP.

Continue research automatically until completion.