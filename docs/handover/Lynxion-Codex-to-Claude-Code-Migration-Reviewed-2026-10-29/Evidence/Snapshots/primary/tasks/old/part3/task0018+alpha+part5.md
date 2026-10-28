Task 0021 — Derivatives Risk Gate Interaction Analysis

Role:
Act as Senior Quant Researcher and Principal Software Engineer.

Objective:
Perform a read-only quantitative research analysis to determine whether the newly validated Derivatives Risk Gate features can improve the expectancy of existing surviving strategies.

The objective is NOT to modify production code, NOT to integrate the Risk Gate, and NOT to create trading logic.

Research Question:

"Can the Derivatives Risk Gate convert any existing strategy from negative expectancy to positive expectancy by avoiding structurally dangerous market regimes?"

---

## Non-Negotiable Constraints

1. Architecture remains completely frozen.
2. No production files may be modified.
3. No Strategy Adapter changes.
4. No Watcher changes.
5. No Fusion changes.
6. No Risk Engine implementation changes.
7. No Execution Engine changes.
8. No Backtester behavior changes.

This task is strictly:
READ → SIMULATE → MEASURE → REPORT

---

# Phase 1 — Strategy Universe Selection

Use only currently approved/surviving strategies.

Exclude all retired strategies.

Analyze at minimum:

- Liquidity Strategy
- Mean Reversion Strategy
- OI Footprint Strategy
- Sweep Scalper Strategy

If additional production-ready strategies exist, include them but clearly separate:
- validated strategies
- experimental strategies

---

# Phase 2 — Baseline Measurement

For each strategy and asset combination:

Assets:

- BTCUSDT
- ETHUSDT
- SOLUSDT
- XRPUSDT
- BNBUSDT


Generate baseline statistics without Risk Gate:

Metrics:

- Total Trades
- Win Rate
- Net PnL
- Average Trade Return
- Profit Factor
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Expected Value per Trade
- Long vs Short performance separately


Maintain the exact existing execution assumptions:

- Existing fees
- Existing slippage model
- Existing execution rules

No optimistic assumptions.

---

# Phase 3 — Risk Gate Overlay Simulation

Apply the Derivatives Risk Gate as an external portfolio overlay.

Do NOT modify strategy signals.

The overlay should only simulate:

## Gate A — OI Warning

Condition:

1.0 <= oi_zscore_14d < 2.0

Simulation:

- Reduce allowed position size by 50%

---

## Gate B — OI Hard Long Block

Condition:

oi_zscore_14d >= 1.0

Simulation:

For new LONG entries:

- Reject admission

For SHORT entries:

- No change


---

## Gate C — LVI Protection

Condition:

LVI >= 25

Simulation:

Apply position scaling:

Multiplier:

1 / sqrt(1 + LVI / 10)

---

# Phase 4 — Comparative Analysis

For every strategy:

Compare:

Mode A:
Original Strategy

Mode B:
Strategy + OI Warning Gate

Mode C:
Strategy + Hard Long Block

Mode D:
Strategy + OI + LVI Combined


Create comparison table:

| Strategy | Mode | PnL | Sharpe | PF | Max DD | Win Rate | Avg Trade |
|----------|------|-----|--------|----|--------|----------|-----------|

---

# Phase 5 — Statistical Validation

For every promising improvement:

Require:

1. Bootstrap:

1000 samples

Report:

- Mean improvement
- 95% Confidence Interval


2. Walk Forward Validation:

Minimum:

4 folds

Report:

- Number of positive folds
- Consistency of improvement


3. Trade Count Preservation:

Ensure:

- Risk Gate does not artificially remove almost all trades.

Report:

Trade reduction percentage.

---

# Phase 6 — Alpha Discovery Check

Explicitly answer:

Does Risk Gate:

A) Improve already profitable strategies?

B) Convert losing strategies into profitable strategies?

C) Only reduce drawdown?

D) Destroy existing alpha?


Provide evidence.

---

# Phase 7 — Strategy Interaction Ranking

Rank strategies:

## Category 1:
Risk Gate creates meaningful improvement

Criteria:

- PF improvement > 10%
- Drawdown reduction >15%
- Positive WFO consistency


## Category 2:
Risk Gate improves risk but not expectancy


## Category 3:
Risk Gate has no measurable impact


## Category 4:
Risk Gate damages strategy


---

# Phase 8 — Final Research Verdict

Provide:

1. Executive Summary

2. Best strategy + Risk Gate combination

3. Worst interaction

4. Whether Risk Gate should become:
  - Production Risk Engine candidate
  - Research-only feature
  - Retired


5. Recommended next research phase.

---

Important:

Do not claim success unless:
- improvement survives WFO,
- confidence intervals support it,
- improvement is not caused only by removing trades.

The goal is not to prove Risk Gate works.

The goal is to discover whether it creates measurable, repeatable economic advantage.