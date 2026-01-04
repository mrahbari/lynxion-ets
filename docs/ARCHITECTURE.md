# Hedge Fund Trading System - Architecture Documentation

## Decision Flow Architecture

### Canonical Flow
```
Watcher → Engine → Fusion → Strategy → Broker
```

### Hierarchical Multi-Watcher Architecture

The system now implements a **Hedge-Fund-Grade Multi-Watcher Architecture** with role-based decision making:

#### Core Principles (Non-Negotiable)
1. **Separation of Concerns**: Discovery ≠ Permission ≠ Direction ≠ Execution
2. **Capital Is Global, Signals Are Local**: Regime watcher `market_pulse` is always respected
3. **Confidence Is a Gate**: Signals below thresholds are ignored
4. **WAIT Is a First-Class Decision**: Not trading is treated as a valid decision

#### Watcher Classification System

##### 🧭 REGIME (Global Capital Governor)
**Purpose**: Decide *if* the system is allowed to trade
- `market_pulse`, `volatility`, `funding_rate`, `cmc_screener` (macro sentiment only)
- **Rules**: Cannot BUY or SELL, cannot be overridden by symbol signals

##### 🧠 DISCOVERY (Symbol Universe Expansion)
**Purpose**: Decide *which symbols deserve attention*
- `cmc_screener`, `anomaly_ml`
- **Rules**: Cannot approve trading, only adds symbols to pipeline

##### 🧭 DIRECTION (Symbol Bias Authority)
**Purpose**: Decide *direction* if regime allows
- `trend_mtf`, `liquidity`, `historical_candle`
- **Rules**: Minimum 2 aligned signals, must pass confidence threshold, must align with regime

##### ⚡ EXECUTION (Entry Timing & Veto)
**Purpose**: Decide *when*, not *whether*
- `orderflow_ws`, `tick_watcher`, `anomaly_ml`
- **Rules**: Cannot create direction, can veto trades

#### Mandatory Decision Flow
```
DISCOVERY → REGIME CHECK → DIRECTION CONFIRMATION → EXECUTION CONFIRMATION → POSITION SIZING → BROKER
```
No step may be skipped.

#### Global Regime Policy
| Regime         | Action             |
| -------------- | ------------------ |
| STRONG_RISK_ON | Trade normally     |
| WEAK_RISK_ON   | Trade reduced size |
| NEUTRAL        | Only A+ setups     |
| OVERHEATED     | No new entries     |
| RISK_OFF       | No trading         |

#### Confidence Threshold Policy
```python
CONFIDENCE_THRESHOLDS = {
    # Regime
    "market_pulse": 0.60,
    "volatility": 0.55,
    "funding_rate": 0.60,
    "cmc_screener": 0.65,

    # Discovery
    "anomaly_ml": 0.70,

    # Direction
    "trend_mtf": 0.55,
    "liquidity": 0.65,
    "historical_candle": 0.60,

    # Execution
    "orderflow_ws": 0.50,
    "tick_watcher": 0.45,
}
```

#### Conflict Resolution Rules
1. Regime overrides everything
2. Low confidence signals are discarded
3. Execution can veto, never initiate
4. Any unresolved conflict → WAIT

#### Symbol State Machine
Every symbol follows this lifecycle:
```
DISCOVERED → REGIME_BLOCKED | REGIME_ALLOWED → DIRECTION_PENDING → DIRECTION_CONFIRMED → EXECUTION_PENDING → READY_TO_TRADE → TRADE_EXECUTED
```

### Layer Responsibilities

#### 1. Watcher Layer (Market Perception)
- **Purpose**: Observe the market and detect raw opportunities
- **Output**: `MarketObservation` (raw market observations only)
- **Forbidden**: Strategy selection, BUY/SELL assignment, SL/TP definition

#### 2. Engine Layer (Signal Interpretation)
- **Purpose**: Convert raw observations into interpretable signals
- **Output**: `InterpretedSignal` (direction, strength, confidence)
- **Forbidden**: Strategy selection, execution decisions

#### 3. Fusion Layer (Consensus & Dominance)
- **Purpose**: Aggregate interpreted signals using hierarchical decision making
- **Output**: `FusedSignal` (dominant_bias, dominance_score, regime_context)
- **Forbidden**: Strategy selection, capital allocation

#### 4. Strategy Layer (Capital Deployment) ⚡
- **Purpose**: Decide whether and how capital should be deployed
- **Output**: `ExecutionIntent` (strategy_name, side, intent_confidence)
- **Critical Rule**: This is the **ONLY** layer that selects strategies

#### 5. Broker Layer (Execution)
- **Purpose**: Execute orders exactly as received
- **Output**: Order execution results
- **Forbidden**: Modifying intent, strategy selection

## Engine System Architecture

### Infrastructure/Engines/Adapters

The system uses multiple specialized engines that each focus on different market conditions:

- **Liquidity Engine**: Evaluates liquidity conditions and adjusts signal confidence
- **Trend Engine**: Analyzes trend strength and direction alignment  
- **Volatility Engine**: Assesses market volatility and modifies confidence accordingly

### How Engines Are Triggered

The system uses a **service-oriented approach**:

1. **All engines receive the same raw market observations**
2. **Engine Service orchestrates multiple specialized engines**
3. **Parallel processing** - All engines process simultaneously
4. **Fusion layer aggregates** processed signals

### Why Multiple Engines Are Needed

Different market conditions require different analytical approaches:
- **Liquidity Engine**: Determines if trades can execute without slippage
- **Trend Engine**: Critical for trend-following strategies
- **Volatility Engine**: Important for risk management

## Architecture Corrections Applied

### 1. Signal Entity Separation
- Created distinct entities: `MarketObservation`, `InterpretedSignal`, `FusedSignal`, `ExecutionIntent`
- Removed `strategy_name` from base `Signal` entity
- All components now use appropriate signal types

### 2. Watcher Adapter Updates
- All watcher adapters now return `MarketObservation` instead of `Signal`
- Watchers only produce raw market observations
- No strategy selection in Watcher layer

### 3. Layer Boundary Enforcement
- Each layer now has strict decision boundaries
- Strategy selection centralized in Strategy layer only
- Proper risk management from Strategy to Broker

### 4. Import Corrections
- Fixed class name in base_watcher.py to `BaseWatcher`
- All imports now correctly reference the base class

## Verification

- All watcher adapters return `MarketObservation`
- Strategy layer is the only component that selects strategies
- Risk parameters properly flow from Strategy to Broker
- System follows institutional hedge fund operational principles
- No direct execution from Watchers
- Proper capital deployment decisions in Strategy layer

## Environment Variables

The system supports the following environment variables for configuration:

- `FIXED_POSITION_SIZE_ENABLED`: Enable fixed position sizing (true/false) for testing
- `FIXED_POSITION_AMOUNT`: Fixed position amount in USD (e.g., $10 for testing)
- `DEFAULT_ACCOUNT_BALANCE`: Default account balance in USD (e.g., $10000 for production, $1000 for testing)
- `STRATEGY_MIN_CONFIDENCE_THRESHOLD`: Minimum confidence threshold for strategy execution (e.g., 0.3 for 30% testing, 0.6 for 60% production)
- `STRATEGY_HIGH_CONFIDENCE_THRESHOLD`: High confidence threshold for automatic execution (e.g., 0.7 for 70%)
- `STRATEGY_NEUTRAL_BUFFER`: Buffer around neutral signals (e.g., 0.1 for 10%)
- `DEFAULT_WATCHLIST_SYMBOLS`: Default symbols to monitor
- `CMC_API_KEY`: CoinMarketCap API key
- `BINANCE_API_KEY`: Binance API key
- `BINGX_API_KEY`: BingX API key