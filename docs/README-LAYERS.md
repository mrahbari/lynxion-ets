# Enterprise Hedge Fund Trading System

## Overview
This is an institutional-grade algorithmic trading platform designed for hedge fund operations, following clean architecture principles and proper decision flow boundaries.

## Architecture Principles

### Decision Flow Architecture
The system follows the canonical hedge fund decision flow:

```
Watcher → Engine → Fusion → Strategy → Broker
```

Each layer has strict decision boundaries to ensure proper risk management and institutional compliance.

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

#### Watcher Layer (Market Perception)
- Detects raw market opportunities and anomalies
- Outputs: `MarketObservation` (raw market observations only)
- **Forbidden**: Strategy selection, execution decisions

#### Engine Layer (Signal Interpretation)
- Converts raw observations into interpretable signals
- Outputs: `InterpretedSignal` (direction, strength, confidence)
- **Forbidden**: Strategy selection, execution decisions

#### Fusion Layer (Consensus & Dominance)
- Aggregates interpreted signals using hierarchical decision making
- Resolves conflicts based on watcher roles and confidence thresholds
- Outputs: `FusedSignal` (dominant bias, consensus strength)
- **Forbidden**: Strategy selection, capital allocation

#### Strategy Layer (Capital Deployment) ⚡
- Decides whether and how capital should be deployed
- Outputs: `ExecutionIntent` (strategy_name, side, confidence)
- **Critical Rule**: This is the **ONLY** layer that selects strategies

#### Broker Layer (Execution)
- Executes orders exactly as received
- **Forbidden**: Modifying intent, strategy selection

## Key Features

### Multi-Asset Support
- Supports multiple cryptocurrency pairs
- Configurable symbol monitoring
- Automatic market discovery

### Risk Management
- Institutional-grade risk controls
- Proper capital allocation
- SL/TP enforcement

### Engine System
- Specialized engines for different market conditions
- Liquidity, Trend, and Volatility engines
- Parallel processing capabilities

### Clean Architecture
- Hexagonal architecture implementation
- Proper separation of concerns
- Testable components

## Architecture Corrections

The system has been updated to fix critical architecture violations where Watchers were directly executing trades. All components now follow the proper decision flow:

- ✅ Watchers only produce raw market observations
- ✅ Strategy layer is the only component that selects strategies  
- ✅ Proper risk management from Strategy to Broker
- ✅ No direct execution from Watchers
- ✅ Institutional compliance achieved

## Usage

### Production Mode
```bash
python run_trading_system.py --mode production --auto-detect
```

### Backtesting
```bash
python run_trading_system.py --mode backtest --symbol BTCUSDT
```

### Optimization
```bash
python run_trading_system.py --mode optimize --strategy crypto_breakout
```

## Configuration

Environment variables for configuration:
- `DEFAULT_WATCHLIST_SYMBOLS`: Default symbols to monitor
- `CMC_API_KEY`: CoinMarketCap API key
- `BINANCE_API_KEY`: Binance API key
- `BINGX_API_KEY`: BingX API key
- `FIXED_POSITION_SIZE_ENABLED`: Enable fixed position sizing (true/false) for testing
- `FIXED_POSITION_AMOUNT`: Fixed position amount in USD (e.g., $10 for testing)
- `DEFAULT_ACCOUNT_BALANCE`: Default account balance in USD (e.g., $10000 for production, $1000 for testing)
- `STRATEGY_MIN_CONFIDENCE_THRESHOLD`: Minimum confidence threshold for strategy execution (e.g., 0.3 for 30% testing, 0.6 for 60% production)
- `STRATEGY_HIGH_CONFIDENCE_THRESHOLD`: High confidence threshold for automatic execution (e.g., 0.7 for 70%)
- `STRATEGY_NEUTRAL_BUFFER`: Buffer around neutral signals (e.g., 0.1 for 10%)

## Documentation

- [Architecture Documentation](ARCHITECTURE.md) - Detailed architecture principles
- [Decision Flow Audit v3](decision_flow_audit_v3.md) - Complete architecture correction report
- [API Documentation](docs/api.md) - Technical API reference

## License

Enterprise license - for institutional use only.