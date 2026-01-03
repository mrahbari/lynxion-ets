# Decision Flow Audit Report
**Version: 1.0 - Original Audit (Historical Reference)**

## Executive Summary

The original architecture **severely violated** the canonical hedge fund decision flow: `Watcher → Engine → Fusion → Strategy → Broker`. The most critical issue was that **Watchers were directly executing trades**, bypassing the Strategy layer entirely. This created a structurally unsafe system where capital ownership was violated and risk control was illusionary.

**Note**: This version represents the original audit findings. The architecture has since been corrected as documented in decision_flow_audit_v2.md.

## 1. Canonical Decision Flow Requirements

### Correct Flow:
```
Watcher → Engine → Fusion → Strategy → Broker
```

### Each Layer's Decision Boundaries:

#### 🟦 1. Watcher - Market Perception Layer
- **Purpose**: Observe the market and detect *raw opportunities* — nothing more
- **Allowed Decisions**: Detect anomalies, volatility expansion, momentum spikes, liquidity imbalance, breakouts/mean-reversion conditions
- **Output**: `MarketObservation` / `RawSignal`
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

## 2. Current Architecture Violations

### 🚨 Critical Violation: Watcher Layer

**Issues Found:**
1. **Direct Order Execution**: The `MarketOpportunityWatcher` directly executes trades via `_execute_signal_trade()` method
2. **Strategy Selection**: Watcher selects strategies via `_suggest_strategy_for_signal()` method
3. **Capital Deployment**: Watcher makes capital deployment decisions instead of Strategy layer
4. **Signal Entity Violation**: `Signal` entity contains `strategy_name` field

**Code Evidence:**
- `/infrastructure/watchers/market_opportunity_watcher.py` lines 1370-1372:
  ```python
  if processed_signal.signal_type.name in ['BUY', 'SELL'] and processed_confidence > 0.5:
      self.logger.info(f"🎯 EXECUTING TRADE: {processed_signal.signal_type.name} for {processed_signal.symbol.value} with confidence {processed_confidence:.2%}")
      self._execute_signal_trade(processed_signal, opportunities['strategy_suggestion'])
  ```

- Lines 1381-1383:
  ```python
  if original_signal_type in ['BUY', 'SELL'] and original_confidence > 0.5:
      self.logger.info(f"Executing unfused signal directly: {original_signal_type} for {symbol_str} with confidence {original_confidence:.2%}")
      self._execute_signal_trade(signal, self._suggest_strategy_for_signal(signal))
  ```

### 🟨 Engine Layer Issues

**Issues:**
1. **Strategy Awareness**: Engines modify `strategy_name` in signals (e.g., `strategy_name=f"{signal.strategy_name}_trend_filtered"`)
2. **Signal Modification**: Engines are modifying strategy information that should only be handled by Strategy layer

### 🟥 Strategy Layer Bypass

**Critical Issues:**
1. **Completely Bypassed**: The Strategy layer is supposed to be the ONLY layer that selects strategies, but this is happening in Watcher
2. **No Capital Deployment Logic**: Strategy layer should decide whether to accept/reject fused signals and deploy capital
3. **No Risk Management**: Strategy layer should call Risk Manager before execution

### 🟩 Broker Layer Issues

**Issues:**
1. **Risk Parameter Injection**: Broker is adding SL/TP parameters that should come from Strategy layer
2. **Execution Without Proper Intent**: Broker executes orders that should have been properly formed by Strategy layer

## 3. Specific Architecture Violations

### ❌ Violation 1: Watcher Assigns BUY/SELL
- **Issue**: Watchers generate signals with BUY/SELL already assigned
- **Location**: `/domain/entities/trading_entities.py` - Signal entity
- **Problem**: Watchers should only detect raw opportunities, not assign direction

### ❌ Violation 2: Watcher Selects Strategy
- **Issue**: `_suggest_strategy_for_signal()` method in watcher
- **Location**: `/infrastructure/watchers/market_opportunity_watcher.py` line 1526
- **Problem**: Strategy selection should happen ONLY in Strategy layer

### ❌ Violation 3: Watcher Creates Orders
- **Issue**: `_execute_signal_trade()` method directly creates and executes orders
- **Location**: `/infrastructure/watchers/market_opportunity_watcher.py` line 1582
- **Problem**: Should pass to Strategy layer first

### ❌ Violation 4: Watcher Knows About Capital
- **Issue**: Watcher calculates position sizes and executes trades
- **Location**: Position sizing logic in `_execute_signal_trade()`
- **Problem**: Capital deployment is Strategy layer responsibility

## 4. Required Corrections

### Immediate Fixes Needed:

1. **Remove Direct Execution from Watcher**
   - Remove `_execute_signal_trade()` calls from watcher
   - Watcher should only emit `MarketObservation`/`RawSignal`

2. **Fix Signal Entity**
   - Remove `strategy_name` from base `Signal` entity
   - Create separate signal types for different layers

3. **Implement Proper Strategy Layer**
   - Create Strategy layer that receives fused signals
   - Strategy layer should select appropriate strategy
   - Strategy layer should create execution intent
   - Strategy layer should call Risk Manager

4. **Fix Engine Layer**
   - Remove strategy name modifications
   - Engines should only interpret raw signals

5. **Fix Broker Layer**
   - Broker should only execute properly formed orders with SL/TP
   - Remove risk parameter injection from broker

### Correct Implementation Flow:
```
Watcher (detects anomalies) → RawSignal → Engine (interprets) → InterpretedSignal → 
Fusion (aggregates) → FusedSignal → Strategy (selects strategy, deploys capital) → 
ExecutionIntent → Broker (executes) → Order
```

## 5. Institutional Risk Assessment

This architecture creates **5 critical institutional failures**:

1. **Capital Ownership Violation**: Watchers own capital instead of Strategies
2. **Impossible Portfolio Attribution**: Cannot track which strategy generated which trades
3. **Backtest ≠ Live Behavior**: Different execution paths between backtesting and live
4. **Risk Manager Becomes Cosmetic**: Risk controls bypassed by direct execution
5. **Execution Cannot Be Governed**: No proper approval/decision layer for capital deployment

## 6. Recommendation

The system needs a complete architectural refactor to implement the proper decision flow. The current implementation is structurally unsafe for institutional use and violates fundamental hedge fund operational principles.

The architecture must be corrected to ensure that:
- Watchers only detect and report market observations
- Engines only interpret raw signals
- Fusion only aggregates and resolves conflicts
- Strategy layer is the ONLY layer that selects strategies and deploys capital
- Broker only executes properly formed orders