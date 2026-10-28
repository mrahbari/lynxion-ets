You are acting as Quant Research Lead and Principal Engineer.

Task 0020:
Derivatives Risk Gate Historical Impact Simulation

Context:
- Derivatives Data Layer is complete and validated.
- HistoricalDerivativesCollector is production-ready.
- DerivativesFeatureEngine is validated.
- Task 0019 and Task 0019.1 identified derivatives features as Risk Engine candidates.
- The strongest candidates are:
    1. oi_zscore_14d
    2. oi_liquidation_vulnerability_index (LVI)
    3. price_oi_divergence_score

Important:
The objective is NOT to find new trading signals.
The objective is to measure whether derivatives risk intelligence improves the existing trading system by reducing bad exposure.

Architecture Constraints:
- Architecture is frozen.
- No production Risk Engine code changes.
- No Strategy changes.
- No Watcher changes.
- No Fusion changes.
- No Execution changes.
- No order generation.
- Research simulation only.

Goal:
Answer this question:

"If this Risk Gate had existed historically, would it have improved portfolio quality?"

---

## Phase 1 — Historical Risk Overlay Simulation

Build a read-only simulation layer that applies risk rules on top of existing historical trades.

Do NOT regenerate signals.

Use existing executed benchmark trades and their timestamps.

For every historical trade:
- Load derivatives features available at trade decision time T.
- Apply risk overlay decision.
- Compare hypothetical outcomes.

Strict PIT rules:
- Only derivatives data timestamp <= trade timestamp is allowed.
- No future funding/OI information.
- No future OHLCV.

---

## Phase 2 — Evaluate Three Risk Modes

### Mode A — Baseline

No derivatives risk adjustment.

Current behavior:

Position multiplier:
1.0

All trades allowed.

---

### Mode B — Soft Risk Gate

Rules:

If:

oi_zscore_14d >= 1.0 and < 2.0

Then:

- Reduce new position size by 50%

Example:

original position:
$1000

simulated position:
$500


---

### Mode C — Hard Risk Gate

Rules:

If:

oi_zscore_14d >= 2.0

Then:

- Block new LONG entries.
- Reduce existing LONG exposure by 60%.

Additionally:

If:

LVI >= 25

Then:

- Block momentum-style entries.

---

## Phase 3 — Performance Comparison

Compare:

### Portfolio Metrics

For each mode calculate:

- Total Return
- Net PnL
- Maximum Drawdown
- Sharpe Ratio
- Sortino Ratio
- Profit Factor
- Win Rate
- Average Trade
- Number of Trades
- Exposure Time
- Recovery Time


---

## Phase 4 — Drawdown Protection Analysis

Focus specifically on:

- Largest losing trades
- Largest drawdown periods
- Consecutive loss sequences

Answer:

Did the risk gate successfully avoid:

- liquidation cascades?
- high leverage unwind periods?
- bad market regimes?

---

## Phase 5 — Statistical Validation

Run:

1. Bootstrap confidence intervals

2. Monte Carlo trade ordering permutation

3. Walk Forward validation:

Minimum:
4 OOS folds

Across:

BTCUSDT
ETHUSDT
SOLUSDT
XRPUSDT
BNBUSDT


---

## Phase 6 — Decision Criteria

Classify the Risk Gate:

### PROMOTE if:

- Max drawdown improves >=15%
- Sharpe improves
- No significant return destruction
- Improvement survives WFO

### TUNE if:

- Drawdown improves
- Return decreases significantly

### REJECT if:

- Improvement only exists in one period
- Trade count reduction destroys expectancy
- No statistical stability


---

## Required Deliverables

Create:

1. derivatives_risk_gate_simulation_report.md

Containing:

- Executive summary
- Methodology
- PIT validation
- Baseline vs Risk Gate comparison tables
- Drawdown analysis
- WFO results
- Final recommendation


Final Verdict must be one of:

- PROMOTE TO RISK ENGINE
- TUNE PARAMETERS
- RESEARCH ONLY
- REJECT


Remember:
This is a risk intelligence validation task, not an alpha discovery task.
Do not add trading logic.
Do not modify architecture.