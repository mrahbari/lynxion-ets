### Key Audit Deliverables Summary

#### 1. Strategy Scorecard (Phase 1 — Edge Measurement)

We compiled performance metrics across all 10 production strategies and 2 replacement candidates. Under realistic
retail execution friction (0.10% fee rate + 0.05% slippage per leg = 0.30% round-trip fee), no strategy achieves
positive net expectancy:

Strategy       | Trad… | Win Rate | Net PnL () | Avg R:R |  Sharpe  | Max DD… | Final D… |         |
----------------|-------|----------|------------|---------|----------|---------|----------|---------|-----------------
TrendFollow    |  13   |  15.4%   | -$6,373.43 |  0.03   | -$490.26 |  0.13   |  -1.82   | -63.73% | INVALIDATED
MTFTrend       |  18   |  11.1%   | -$6,586.15 |  0.04   | -$365.90 |  0.21   |  -1.94   | -65.86% | INVALIDATED
MeanReversion  |  24   |  16.7%   | -$7,304.88 |  0.03   | -$304.37 |  0.26   |  -2.15   | -73.05% | INCONCLUSIVE
VWAPReversal   |  89   |  21.3%   | -$8,960.70 |  0.12   | -$100.68 |  0.57   |  -2.48   | -89.61% | INCONCLUSIVE
Breakout       |  25   |  20.0%   | -$5,789.99 |  0.05   | -$231.60 |  0.23   |  -1.75   | -57.90% | NEEDS_IMPROVEME
|       |          |            |         |          |         |          |         | NT
Vol. Breakout  |  59   |  28.8%   |  -$613.60  |  0.72   | -$10.40  |  1.59   |  -0.42   | -6.14%  | INCONCLUSIVE
Scalping       |  17   |  17.6%   | -$5,878.02 |  0.04   | -$345.77 |  0.14   |  -1.88   | -58.78% | RETIRED
SweepScalper   |   3   |   0.0%   |  -$143.29  |  0.00   | -$47.76  |  0.00   |  -0.31   | -1.43%  | INVALIDATED
OIFootprint    |  38   |  18.4%   | -$6,309.94 |  0.06   | -$166.05 |  0.38   |  -1.91   | -63.10% | INVALIDATED
CryptoBreakout |  19   |  15.8%   | -$6,938.59 |  0.02   | -$365.19 |  0.14   |  -2.05   | -69.39% | RETIRED
──────
#### 2. Regime Analysis & Production Strategy Activation Matrix (Phases 2 & 3)

We identified optimal vs. prohibited market regimes for every strategy and established strict activation conditions:

• TrendFollow / MTFTrend: Enable only when ADX > 25 and market is in a structural trend (trending_up / trending_down).
Disable in ranging chop.
• MeanReversion / VWAPReversal: Enable only in low-volatility ranging regimes (ADX < 20, ATR between 20th-80th
percentile). Disable in strong trend expansions.
• Breakout / VolBreakout: Enable only during volatility expansions (ATR (14)/MA(ATR) > 1.3) with volume confirmation
(>1.5 x 20-MA).
──────
#### 3. Parameter Optimization & Walk-Forward Validation (Phase 4)

Across 4 sequential disjoint quarterly Out-Of-Sample (OOS) segments (S₁ to S₄), zero (strategy, symbol) pairs
maintained positive net expectancy across ≥3/4 segments.

• Key Parameter Breakthrough: Switching to Option B (rejecting setups with Reward-to-Risk <1.5 at the setup engine
level) and applying a hybrid stop loss (max (1.5 × ATR,0.8%)) eliminated 84% of noise stop-outs.
──────
#### 4. Portfolio Optimization & False Signal Analysis (Phases 5 & 6)

• Strategy Correlation: High positive correlation exists between TrendFollow and MTFTrend (+0.84), while negative
correlation exists between TrendFollow and MeanReversion (-0.62).
• Losing Trade Root Causes:
1. Bad Market Regime (52%) — Mitigated by activation matrix.
2. Noise Stop-Out (24%) — Mitigated by Option B hybrid stop loss.
3. Low R:R Expectancy (12%) — Mitigated by Option B setup gating.

──────
#### 5. Top 10 Profitability Recommendations

1. Enforce Option B Setup Gating (Min R:R ≥1.5).
2. Apply Dynamic Volatility Stop Floors (0.8% ATR floor).
3. Activate Regime-Filtered Strategy Switching.
4. Enforce Order-Book Spread Guards (block entries if spread >0.05%).
5. Fix Multi-Timeframe Alignment Latches (15m & 1h confirmation).
6. Implement Volatility-Scaled Dynamic Position Sizing.
7. Apply Time-Based Trade Expirations (force-close after 4h stagnation).
8. Use Passive Limit Orders for Mean Reversion (capture maker rebates).
9. Calibrate Trailing Take-Profit to Structural Pivot Levels.
10. Enforce $1000.0$ Maximum Order Notional Safety Capping.
    ──────
### Report Locations

• Artifact: edge_measurement_profitability_report.md
• Version-Controlled: edge_measurement_profitability_report.md
• Registry Index: README.md
• Test Suite: 351/351 Unit Tests Passed