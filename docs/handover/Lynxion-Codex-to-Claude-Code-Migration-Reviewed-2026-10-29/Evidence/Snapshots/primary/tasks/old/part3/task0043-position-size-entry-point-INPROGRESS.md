Act as the Final Production Live Trading Observation Controller and Quant Operations Lead.

The system has completed:
- C1 Atomic Protection Rollback
- H1 Decimal Floor Quantization
- H2 Pre-Send SL Validation
- Exchange Preflight Enforcement
- Position Notional Protection
- Execution Buffer Protection
- HALT-ON-DRIFT Reconciliation
- 396/396 production safety tests passed

A $500 USDT micro-capital live trading deployment is now approved.

Your mission is NOT to redesign architecture.
Your mission is NOT to optimize strategies yet.
Your mission is to monitor and validate the first live production trading window scientifically.

Architecture is frozen:
Watcher → Engine → Fusion → Strategy → Risk → Execution → BingX Broker

Do not introduce new abstractions.
Do not bypass existing safety layers.
Only identify real production issues and required minimal fixes.

Perform a forensic Live Trading Observation Audit with these phases:

==================================================
PHASE 1 — Execution Reality Validation
==================================================

Verify every live order against:

1. Signal price
2. Requested execution price
3. Exchange fill price
4. Slippage percentage
5. Quantity requested
6. Quantity filled
7. Final filled notional

Hard invariant:

FINAL_FILLED_NOTIONAL <= MAX_POSITION_NOTIONAL

Report:

- Any violation
- Average slippage
- Worst slippage
- Symbol-specific slippage
- Maker/taker differences

==================================================
PHASE 2 — Risk Protection Validation
==================================================

Verify:

1. Every position has active SL on BingX.
2. SL price is calculated from actual fill price, not signal price.
3. TP price preserves original risk/reward ratio.
4. Emergency rollback never triggers unnecessarily.
5. HALT-ON-DRIFT never creates false positives.

Audit:

- SL attachment latency
- SL confirmation latency
- Missing protection events
- Reconciliation events

==================================================
PHASE 3 — Execution Ledger Integrity
==================================================

Verify consistency between:

- Strategy signal journal
- Order journal
- ExecutionTruthLedger
- BingX exchange history

Find:

- Missing trades
- Duplicate trades
- Incorrect fill prices
- Incorrect fees
- Incorrect PnL calculation
- Timestamp drift

==================================================
PHASE 4 — Capital Conservation Audit
==================================================

For every trade calculate:

Initial capital:
500 USDT

Maximum position:
50 USDT

Leverage:
1x

Margin:
ISOLATED


Verify:

- Maximum exposure never exceeded
- Daily drawdown protection works
- Loss limits work
- Emergency stop works

==================================================
PHASE 5 — Strategy Edge Observation
==================================================

DO NOT conclude profitability from small sample size.

Collect only:

- Number of trades
- Win rate
- Average win
- Average loss
- Expectancy
- Profit factor
- Maximum adverse excursion
- Maximum favorable excursion
- Holding time
- Fee impact

Minimum requirement:

Do not recommend increasing capital before:

n >= 300 live trades

AND

statistical evidence of edge exists.

==================================================
PHASE 6 — Operational Reliability
==================================================

Monitor:

- API latency
- Order failures
- Retry behavior
- Duplicate prevention
- Reconciliation frequency
- Journal persistence
- Process crashes
- Restart recovery

==================================================
FINAL OUTPUT FORMAT
==================================================

Produce:

1. Executive Production Status:
    - GREEN
    - YELLOW
    - RED

2. Capital Safety Verdict:
    - Can continue $500?
    - Must halt?
    - Any emergency action?

3. Execution Quality Report

4. Risk Protection Report

5. Accounting Integrity Report

6. Strategy Observation Report

7. Remaining Risks

8. Required Engineering Actions

Rules:
- Never approve capital increase from this observation alone.
- Never disable safety guards.
- Never optimize based on <300 trades.
- Prefer evidence over assumptions.
- If a problem is found, provide the smallest possible fix preserving current architecture.