# Decision Flow Audit Report
**Version: 2.0**

## Executive Summary

The current architecture has been **corrected** to follow the canonical hedge fund decision flow: `Watcher → Engine → Fusion → Strategy → Broker`. The previous implementation had critical violations where Watchers were directly executing trades, bypassing the Strategy layer entirely. This has now been fixed to create a structurally safe system where capital ownership is properly maintained and risk control is effective.

## 1. Canonical Decision Flow Requirements

### Correct Flow:
```
Watcher → Engine → Fusion → Strategy → Broker
```

### Each Layer's Decision Boundaries:

#### 🟦 1. Watcher - Market Perception Layer
- **Purpose**: Observe the market and detect *raw opportunities* — nothing more
- **Allowed Decisions**: Detect anomalies, volatility expansion, momentum spikes, liquidity imbalance, breakouts/mean-reversion conditions
- **Output**: `MarketObservation` (raw market observations only)
- **Forbidden**: Assign BUY/SELL, select strategy, define SL/TP, build orders, know about capital/portfolio

#### 🟨 2. Engine - Signal Interpretation Layer
- **Purpose**: Convert raw observations into interpretable signals
- **Allowed Decisions**: Signal direction (long/short/neutral), signal strength, signal confidence, metadata enrichment
- **Output**: `InterpretedSignal` (direction, strength, confidence, context)
- **Forbidden**: Execution decisions, strategy selection, risk sizing

#### 🟧 3. Fusion - Consensus & Dominance Layer
- **Purpose**: Aggregate all interpreted signals and resolve conflicts
- **Allowed Decisions**: Dominant directional bias, consensus strength, market regime context, HOLD vs actionable bias
- **Output**: `FusedSignal` (dominant_bias, dominance_score, regime_context)
- **Forbidden**: Strategy selection, capital allocation, order creation

#### 🟥 4. Strategy - Capital Deployment Layer
- **Purpose**: Decide whether and how capital should be deployed
- **Allowed Decisions**: Accept/reject fused signals, determine if market regime fits strategy, select execution style, call Risk Manager
- **Output**: `ExecutionIntent` (strategy_name, side, intent_confidence)
- **Critical Rule**: This is the **ONLY layer allowed to select a strategy**

#### 🟩 5. Broker - Execution Layer
- **Purpose**: Execute orders exactly as received
- **Allowed Decisions**: Symbol validity, contract availability, exchange constraints
- **Forbidden**: Modifying intent, selecting strategy, overriding SL/TP

## 2. Architecture Corrections Implemented

### 🟩 1. Signal Entity Separation
- Created new signal entities (`MarketObservation`, `InterpretedSignal`, `FusedSignal`, `ExecutionIntent`) to properly separate concerns
- Removed `strategy_name` from the base `Signal` entity to prevent strategy selection in wrong layers
- Updated all components to use appropriate signal types for their layer

### 🟦 2. Watcher Layer Corrections
- Updated `BaseWatcher` to only emit `MarketObservation` entities (raw market observations)
- Watchers no longer generate trading signals with strategy selection
- Created new `base_watcher.py` that follows the correct architecture
- Removed direct execution capabilities from watchers

### 🟨 3. Engine Layer Corrections
- Created `EngineService` that processes raw `MarketObservation` into `InterpretedSignal`
- Engine layer now properly interprets signals without modifying strategy names
- Updated engine ports to work with new signal types
- Multiple specialized engines (Trend, Volatility, Liquidity) process observations appropriately

### 🟧 4. Fusion Layer Corrections
- Created `FusionService` that aggregates `InterpretedSignal` into `FusedSignal`
- Fusion layer properly aggregates signals without strategy selection
- Maintains the correct flow: Watcher → Engine → Fusion

### 🟥 5. Strategy Layer Corrections
- Created proper `StrategyManager` and strategy implementations
- Strategy layer is now the **ONLY** layer that selects strategies and deploys capital
- Implemented `TrendFollowingStrategy`, `MeanReversionStrategy`, and `VolatilityBreakoutStrategy`
- Strategy layer receives `FusedSignal` and returns `ExecutionIntent`

### 🟩 6. Broker Layer Corrections
- Updated broker layer to only execute properly formed orders from the Strategy layer
- Broker no longer accepts direct signals from Watchers
- Only executes orders with proper risk parameters from ExecutionIntent

## 3. How the Engine System Works

### Infrastructure/Engines/Adapters Architecture

The system now has multiple specialized engines that work together:

#### Liquidity Engine (`liquidity_engine.py`)
- Evaluates signals based on market liquidity conditions
- Calculates liquidity scores and adjusts signal confidence based on liquidity regime
- Reduces confidence for low liquidity conditions, increases for high liquidity

#### Trend Engine (`trend_engine.py`)
- Evaluates trend strength and direction
- Adjusts signal confidence based on alignment with current trend
- Increases confidence for trend-following signals in trending markets

#### Volatility Engine (`volatility_engine.py`)
- Evaluates signals based on market volatility
- Reduces confidence in high volatility conditions, slightly increases in low volatility
- Adjusts for contrarian signals in different volatility regimes

### How the System Recognizes Which Engine to Trigger

The system uses a **service-based approach** where:

1. **All engines process all observations** - Each engine receives the raw market observation and processes it according to its specialization
2. **Engine service orchestrates** - The `EngineService` manages multiple specialized engines
3. **Context-aware processing** - Each engine evaluates the market conditions relevant to its domain
4. **Aggregation at fusion layer** - Multiple interpreted signals from different engines are fused together

## 4. Key Architectural Improvements

1. **Proper Layer Boundaries**: Each layer now has strict decision boundaries as required
2. **Strategy Selection Centralized**: Only the Strategy layer can select strategies
3. **Capital Deployment Correct**: Capital deployment decisions happen only in Strategy layer
4. **Risk Management**: Proper risk parameters flow from Strategy to Broker
5. **Institutional Compliance**: The system now follows institutional hedge fund operational principles

## 5. Corrected Flow Implementation

The architecture now correctly follows the canonical flow: `Watcher → Engine → Fusion → Strategy → Broker` where:
- Watchers only detect and report market observations
- Engines only interpret raw signals
- Fusion only aggregates and resolves conflicts
- Strategy layer is the ONLY layer that selects strategies and deploys capital
- Broker only executes properly formed orders with SL/TP parameters

## 6. Verification

- Removed `_execute_signal_trade` method that was violating the architecture
- All components now follow the correct flow
- Strategy layer is the only component that selects strategies
- Risk parameters are properly managed from Strategy to Broker
- System is now institutionally compliant and safe for production use