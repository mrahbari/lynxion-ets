### 1. Architectural Blueprint

We created the complete production blueprint for Lynxion-ETS v2, organizing the trading decision pipeline into a
multi-timeframe state machine:

• 4H Macro Regime Engine: Captures ATR volatility states, ADX trend strengths, and funding rate regimes to
enable/disable specific downstream modules.
• 1H Market Structure Engine: Identifies key swing highs/lows, S/R zones, and session volume profile (POC/VAH/VAL) to
establish directional bias.
• 15m Setup Engine: Monopolizes tactical setup generation (e.g. NGLS sweeps, NGMR range reversions) gated by the 1H
directional bias.
• 5m Execution Confirmation Engine: Confirms order-flow direction and momentum using short-term indicators (such as
OBI velocity, CVD delta, and trade intensity) before triggering trades.
• 1m Execution Optimizer: Enforces passive limit order execution ( POST_ONLY ) and tracks queue priority to capture
maker rebates and prevent spread/slippage drag.

### 2. Component Migration Matrix

• Removed (Obsolete):
•  ScalpingStrategy : 1m SMA crossovers are retired.
•  SweepScalperStrategy : Tick-level sub-second sweeps are retired due to cost friction.
•  anomaly_ml.py : Removed from live trading to prevent overfitting.
• Merged:
•  trend_mtf.py  +  volatility.py  +  funding_rate.py  watchers are merged into the 4H Macro Regime Engine and 1H
Market Structure Engine.
•  liquidity.py  +  orderflow_ws.py  are merged into the 15m Setup Engine and 5m Execution Confirmation Engine.
• Split:
•  MarketOpportunityWatcher  is split into a multi-timeframe data router and scheduling queues.
•  EngineService  is split into 15m and 5m decision components.

