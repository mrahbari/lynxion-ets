# Lynxion ETS – Advanced Automated Trading System

Lynxion ETS (Enterprise Trading System) is a professional-grade cryptocurrency trading platform designed for systematic, data-driven algorithmic trading.
It combines automated optimization, walk-forward validation, and multi-timeframe analysis using a clean **hexagonal architecture**.

---

## Table of Contents

* [Overview](#overview)
* [Key Features](#key-features)
* [Architecture](#architecture)
* [System Components](#system-components)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Environment Setup](#environment-setup)
* [Runners & Usage](#runners--usage)
* [Recommended Workflow](#recommended-workflow)
* [Configuration](#configuration)
* [Data Structure](#data-structure)
* [Troubleshooting](#troubleshooting)
* [Maintenance](#maintenance)
* [Contributing](#contributing)
* [License](#license)

---

## Overview

Lynxion ETS is built to support **robust strategy research, validation, and live execution** in volatile crypto markets.

Core goals:

* **Adaptive strategies** through automated hyperparameter optimization
* **Reliable data pipelines** across multiple timeframes
* **Realistic validation** using walk-forward analysis and backtesting
* **Scalable architecture** for adding strategies, exchanges, and tools
* **Production-grade risk control** and execution flow

The system is suitable for both **research/backtesting** and **live trading**.

---

## Key Features

* **Hexagonal Architecture**: Clean separation of concerns with domain, application, and infrastructure layers
* **Multi-Exchange Support**: Binance, BingX, MEXC, Phemex integration
* **Advanced Optimization**: Hyperopt integration with Walk-Forward Optimization (WFO)
* **Risk Management**: Comprehensive risk controls and position sizing
* **Real-time Monitoring**: Live dashboard and performance tracking
* **Backtesting**: Realistic backtesting with fees, slippage, and execution simulation
* **Multi-Asset Support**: Simultaneous trading across multiple cryptocurrencies
* **Configurable Strategies**: Modular strategy system with easy customization
* **Strategy Health Monitoring**: Comprehensive health monitoring with performance tracking
* **Approved Symbol Validation**: Automatic filtering of trading symbols against approved list to ensure only supported and listed symbols are processed
* **Advanced Fusion System**: Adaptive weights with diversity metrics and explainability
* **Watcher Health Management**: Comprehensive monitoring and auto-restart for watchers
* **Dynamic Registration**: Runtime registration for strategies and watchers
* **Resource Optimization**: Instance pooling and resource limitation for optimal performance
* **Enhanced Error Isolation**: Robust error handling between system components
* **Adaptive Thresholds**: Market condition-based parameter adjustments
* **Enhanced Logging System**: Comprehensive flow tracking (Watcher → Engine → Fusion → Strategy → Broker) with detailed decision logging
* **Comprehensive Background Monitoring**: Detailed visibility into background activities with periodic status updates
* **Configurable Logging**: Support for both brief and comprehensive logging modes
* Multi-exchange support (Binance, BingX, MEXC, Phemex)
* Automated hyperparameter optimization (retuning)
* Walk-forward analysis for strategy robustness
* Multi-timeframe data processing
* Realistic backtesting (fees, slippage, position sizing)
* Continuous historical data synchronization
* Clean hexagonal (ports & adapters) architecture

---

## Architecture

Lynxion ETS follows **Hexagonal Architecture**, separating core business logic from infrastructure and external systems.

```
┌──────────────┐    ┌────────────────┐    ┌─────────────────┐
│ Interface    │◄──►│ Application    │◄──►│ Infrastructure  │
│ (Runners,    │    │ (Use Cases,    │    │ (Exchanges,     │
│ CLI, APIs)   │    │ Orchestration) │    │ DBs, Brokers)   │
└──────────────┘    └────────────────┘    └─────────────────┘
                         │
                   ┌──────────────┐
                   │ Domain       │
                   │ (Strategies, │
                   │ Entities)    │
                   └──────────────┘
```

### Enhanced Architecture Components

* **Strategy Management**: Health monitoring, auto-restart, performance tracking
* **Signal Processing**: Conflict resolution, adaptive weighting, validation
* **Engine Performance**: Detailed metrics and optimization tracking
* **Fusion Intelligence**: Adaptive weights with diversity metrics and explainability
* **Watcher Orchestration**: Health monitoring, auto-restart, dynamic registration
* **Resource Optimization**: Instance pooling and limitation systems
* **Symbol Validation**: Automatic filtering against approved symbol lists to ensure only supported and listed symbols are processed through the system

### Layers

* **Domain** – Core entities, strategies, and business rules
* **Application** – Use cases and orchestration logic
* **Infrastructure** – Exchanges, brokers, storage, APIs
* **Shared** – Configuration, utilities, logging

---

## Complete Workflow: Watcher → Engine → Fusion → Strategy → Broker

The system implements a complete automated trading workflow with proper validation and monitoring:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Watcher   │───►│   Engine    │───►│   Fusion    │───►│  Strategy   │───►│   Broker    │
│             │    │             │    │             │    │             │    │             │
│ • Health    │    │ • Performance│   │ • Adaptive  │    │ • Health    │    │ • Order     │
│   Monitoring│    │   Tracking  │    │   Weights   │    │   Monitoring│    │   Execution │
│ • Auto-     │    │ • Validation│    │ • Diversity │    │ • Auto-     │    │ • Risk      │
│   Restart   │    │ • Optimization│  │   Metrics   │    │   Restart   │    │   Management│
│ • Signal    │    │             │    │ • Explain-  │    │ • Performance│   │             │
│   Validation│    │             │    │   ability   │    │   Tracking  │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Workflow Components

* **Watcher Layer**: Health monitoring, auto-restart, signal validation, error isolation, symbol filtering
* **Engine Layer**: Performance tracking, validation, optimization, processing metrics
* **Fusion Layer**: Adaptive weights, diversity metrics, explainability, conflict resolution
* **Strategy Layer**: Health monitoring, auto-restart, performance tracking, resource optimization
* **Broker Layer**: Order execution, risk management, performance monitoring

### Symbol Validation System

The system includes an advanced symbol validation mechanism that ensures only approved and supported symbols are processed:

* **Approved Symbol Lists**: Configurable JSON files containing approved trading symbols
* **Early Filtering**: Symbols are validated at the watcher level before entering the processing pipeline
* **Multi-Level Validation**: Validation occurs at data provider, broker service, and execution levels
* **Automatic Rejection**: Non-approved symbols are automatically rejected with clear logging
* **Configuration Flexibility**: Easy to update approved symbol lists without code changes
* **Performance Optimization**: Prevents system resources from being wasted on unsupported symbols

### Symbol Management Utilities

The system includes utilities to manage approved symbols:

* **Symbol Updater**: `runner_sync_approved_symbols.py` - Fetches the latest available symbols from exchange APIs and updates the approved symbols list
* **Automatic Backups**: The updater creates timestamped backups of the previous symbol list before updates
* **Multi-Source Fallback**: Tries BingX API first, falls back to Binance API, and uses existing symbols as final fallback
* **Change Tracking**: Reports added and removed symbols during updates for transparency

---

## System Components

### Strategy System

All strategies inherit from a shared base adapter and are fully isolated with enhanced monitoring and management capabilities.

**Base**

* `BaseStrategyAdapter` with health monitoring and performance tracking
* Technical indicators: RSI, EMA, SMA, Bollinger Bands, ATR, momentum, volume
* **Enhanced Features**: Health monitoring, auto-restart, performance tracking, error isolation

**Available Strategies**

* **TrendFollowStrategyAdapter** – MA crossovers with momentum confirmation
* **MeanReversionStrategyAdapter** – RSI + Bollinger Bands
* **ScalpingStrategyAdapter** – Fast MA crossovers with volume confirmation
* **BreakoutStrategyAdapter** – Consolidation and breakout detection

### Strategy Management System

* `StrategyManager` – Comprehensive strategy lifecycle management with auto-restart
* `StrategyHealthMonitor` – Real-time health monitoring and performance tracking
* Dynamic registration and resource optimization

### Signal Processing System

* `SignalConflictResolver` – Advanced conflict resolution algorithms
* `SignalValidator` – Comprehensive validation with reliability weighting
* Adaptive signal weighting based on watcher reliability

### Engine System

* Enhanced with performance tracking and optimization
* `EnginePerformanceTracker` – Detailed metrics and optimization
* Processing time monitoring and adaptive optimization

### Fusion System

* `AdvancedFusionServiceAdapter` – Adaptive weights with diversity metrics
* Enhanced explainability and conflict resolution
* Market regime awareness and correlation adjustment

### Watcher System

* Enhanced with comprehensive health monitoring
* Auto-restart capabilities and error isolation
* `WatcherManager` for centralized management
* Adaptive threshold adjustments based on market conditions

### Complete Workflow Integration

* **Watcher → Engine → Fusion → Strategy → Broker** flow with full monitoring
* End-to-end error isolation and health tracking
* Performance metrics across all system components

---

## Prerequisites

* Python **3.10+**
* pip
* 8GB RAM recommended (for optimization)
* Exchange API keys (optional for backtesting)

---

## Installation

```bash
git clone git@github.com:mrahbari/lynxion-ets.git
cd lynxion-ets

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

---

## Environment Setup

```bash
cp .env.example .env
```

Edit `.env`:

```env
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

WFO_COINS=BTCUSDT,ETHUSDT,BNBUSDT
```

---

## Runners & Usage

### Main System

```bash
python run_trading_system.py
```

#### Production Mode with Auto-Detection

To run the production system with watchers monitoring the market continuously:

```bash
# Run in production mode with auto-detection enabled
python run_trading_system.py --mode production --auto-detect --symbols BTCUSDT,ETHUSDT

# Production mode enables the complete Watcher → Engine → Fusion → Strategy → Broker flow
# --auto-detect enables automatic opportunity detection and strategy triggering
# --symbols specifies which symbols to monitor (comma-separated list)
```

```bash
# Run with comprehensive logging for detailed background activity tracking
python run_trading_system.py --mode production --auto-detect --comprehensive-logs
python run_trading_system.py --mode production --auto-detect --symbols BTCUSDT,ETHUSDT --comprehensive-logs
```

**Command Options:**
- `--mode production`: Runs the production trading system with all features enabled
- `--auto-detect`: Enables the complete Watcher → Engine → Fusion → Strategy → Broker flow for automatic opportunity detection
- `--symbols`: Specifies which symbols to monitor (e.g., BTCUSDT,ETHUSDT,SOLUSDT)
- `--comprehensive-logs`: Enables comprehensive logging with detailed background activity tracking (optional)

### Data Synchronization

```bash
python runner_resync.py --all
python runner_resync.py --download --timeframes
```

### Hyperparameter Optimization

```bash
python runner_retune.py --strategy crypto_breakout --evals 50 --days 90
```

### Walk-Forward Analysis

```bash
python runner_walkforward.py --strategy crypto_breakout --train-days 60 --test-days 15
```

### Backtesting

The system supports 11 specialized strategies defined in the StrategyType enum:

* **Trend Following (`trend_following`)** – Follows trending market movements
* **Mean Reversion (`mean_reversion`)** – Bets on price returning to mean
* **Volatility Breakout (`volatility_breakout`)** – Captures price movements during volatility expansion
* **Momentum (`momentum`)** – Capitalizes on momentum patterns and rate of change
* **Scalping (`scalping`)** – Short-term quick profit strategy
* **Breakout (`breakout`)** – Identifies resistance/support breakouts
* **Liquidity (`liquidity`)** – Based on liquidity and volume patterns
* **MTF Trend (`mtf_trend`)** – Multi-timeframe trend following
* **OI Footprint (`oi_footprint`)** – Order interest footprint analysis
* **Sweep Scalper (`sweep_scalper`)** – Sweeping liquidity strategy
* **VWAP Reversal (`vwap_reversal`)** – VWAP-based reversal strategy

Additionally, the system includes the `crypto_breakout` strategy for compatibility with existing examples.

#### Single Strategy Backtest

Run a single strategy backtest:

```bash
python runner_backtest.py --strategy trend_following --start 180d --end today --symbols BTCUSDT
```

#### Multiple Strategy Comparison

Run all available strategies and compare their performance:

```bash
python runner_backtest.py --all-strategies --start 360d --end today --symbols BTCUSDT
```

Or run specific strategies:

```bash
python runner_backtest.py --strategies trend_following mean_reversion breakout --start 180d --end today --symbols BTCUSDT
```

The system will automatically detect all available strategies from the StrategyType enum and run them in sequence, providing a comprehensive comparison of their performance.

#### Additional Options

* `--capital AMOUNT`: Set initial capital (default: 10000.0)
* `--fee RATE`: Set fee rate per trade (default: 0.001 = 0.1%)
* `--slippage FACTOR`: Set slippage factor (default: 0.0005 = 0.05%)
* `--output FILE`: Save results to JSON file
* `--validate`: Validate results after backtesting
* `--verbose`: Enable verbose output

#### What Happens After Running Backtests

After running the backtests, the system will:

1. **Execute each strategy** individually on the specified symbol(s) and timeframe
2. **Generate performance metrics** for each strategy including:
   - Total return percentage
   - Sharpe ratio (risk-adjusted return)
   - Maximum drawdown
   - Win rate
   - Total number of trades executed
3. **Compare all strategies** side-by-side in a ranked format
4. **Identify the best performing strategy** based on total return
5. **Save detailed results** (if using `--output` flag)

#### Strategy Improvements

The system now includes enhanced strategy implementations with:

- **Improved sensitivity**: More responsive entry/exit conditions
- **Volume confirmation**: Strategies consider volume patterns for validation
- **Multi-indicator confirmation**: Combines multiple technical indicators for signal validation
- **Risk-adjusted positioning**: Considers volatility and market conditions
- **Better trend identification**: Enhanced trend-following algorithms
- **Mean reversion optimization**: Improved mean reversion entry points
- **Breakout detection**: More accurate breakout identification with volume confirmation
- **Liquidity awareness**: Strategies consider market liquidity conditions
- **Regime-aware strategies**: Strategies adapt to different market conditions (trending, ranging, high/low volatility)
- **Signal density optimization**: Strategies generate more frequent trading signals while maintaining quality

These improvements help avoid overfitting while maintaining robust performance across different market conditions.

#### Example Output

When running multiple strategies, the system will provide a ranked comparison showing:

```
🏆 STRATEGY COMPARISON RESULTS
   Best Performing Strategy: sweep_scalper (Return: 0.16%)

   All Strategies Ranked by Return:
   1. sweep_scalper        Return: 0.16%, Sharpe: -0.09, Drawdown: -0.00%, Trades: 1
   2. scalping             Return: 0.14%, Sharpe: -0.09, Drawdown: -0.00%, Trades: 1
   3. trend_following      Return: -1.02%, Sharpe: -0.09, Drawdown: -1.02%, Trades: 2
   ...
```

The results show that for the tested period, the sweep_scalper strategy had the highest return (0.16%), followed by scalping (0.14%). Negative returns indicate losses during the backtest period.

#### Interpreting Results

* **Return**: Total percentage gain or loss over the backtest period
* **Sharpe Ratio**: Risk-adjusted return (higher is better, negative indicates poor risk-adjusted performance)
* **Max Drawdown**: Largest peak-to-trough decline (lower absolute value is better)
* **Win Rate**: Percentage of winning trades
* **Trades**: Total number of trades executed during the backtest

#### Comprehensive Backtesting System

The system implements a professional-grade backtesting framework with:

- **Universal backtest engine** supporting all strategy types with realistic execution simulation
- **Advanced risk management integration** with position sizing and stop-loss mechanisms
- **Comprehensive performance metrics** including Sharpe ratio, Sortino ratio, maximum drawdown, and Calmar ratio
- **Multi-asset backtest coordination** with cross-asset correlation analysis
- **Advanced data pipeline integration** with gap-free historical data validation and look-ahead bias prevention
- **Statistical validation framework** with Monte Carlo simulation and out-of-sample validation
- **Realistic execution simulation** with slippage, fees, and market impact modeling
- **Risk-adjusted evaluation** focusing on risk-return optimization rather than pure profit maximization
- **Statistical rigor** with multiple performance metrics and confidence intervals
- **Signal density auditing** to measure signal generation and filtering effectiveness
- **Market regime classification** to identify trending, ranging, and volatility conditions
- **Regime-aware strategy execution** that adapts to current market conditions

The system follows strict **look-ahead bias prevention** with proper indicator shifting, **survivorship bias elimination** using only available data at each time, and **realistic execution simulation** with slippage and fees.

#### Signal Auditing and Regime Classification

The system includes advanced analytics for strategy performance evaluation:

- **Signal Density Audit**: Tracks signals generated, filtered, and entries taken to measure strategy effectiveness
- **Entry Ratio Calculation**: Measures the percentage of signals that result in actual trades
- **Market Regime Classification**: Identifies market conditions (TREND, RANGE, HIGH_VOL, LOW_VOL) to optimize strategy selection
- **Regime-Aware Execution**: Strategies adapt their parameters based on current market conditions
- **Performance Attribution**: Links strategy performance to specific market regimes

Example output includes signal audit information:
```
Signal Audit - Generated: 42943, Filtered: 20858, Entries: 22085
```

#### Production Readiness

The backtesting system is designed for production use with:
- Comprehensive error handling and logging
- Performance monitoring and alerting
- Backup and recovery capabilities
- Audit trails for regulatory compliance
- Scalable architecture supporting hundreds of strategies and symbols

Note: Results are based on historical data and past performance does not guarantee future results. Consider transaction costs, slippage, and market conditions when interpreting results.

### Comprehensive Hedge Fund Validation System

The system now includes a complete hedge fund validation pipeline that implements enterprise-grade portfolio construction and risk management:

#### Portfolio Backtesting with Strategy Selection

Run comprehensive portfolio validation across multiple symbols and strategies:

```bash
python runner_comprehensive_validation.py --start 180d --end today --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT --capital 100000
```

This executes the complete validation pipeline including:

1. **Multi-Symbol Portfolio Backtesting**: Evaluates strategies across all specified symbols
2. **Correlation Analysis**: Calculates correlation matrices between strategy returns
3. **Strategy Admission Filter**: Selects strategies that meet performance criteria (>70% success rate, positive returns, acceptable drawdown)
4. **Dynamic Capital Allocation**: Distributes capital based on performance metrics, correlation penalties, and regime alignment
5. **Monte Carlo Risk Simulation**: Validates robustness through trade order randomization and bootstrap resampling
6. **Strategy Kill-Switch Engine**: Monitors performance and disables underperforming strategies
7. **Portfolio Walk-Forward Validation**: Validates portfolio performance across rolling time windows

#### Portfolio Risk Management Features

The system implements advanced risk controls:

- **Correlation Penalties**: Reduces allocation to highly correlated strategies
- **Drawdown Throttling**: Automatically reduces capital allocation when drawdown thresholds are breached
- **Volatility Scaling**: Adjusts position sizes based on market volatility conditions
- **Regime-Based Weighting**: Allocates more capital to strategies that match current market conditions (TREND: 40%, RANGE: 30%, HIGH_VOL: 20%, LOW_VOL: 10%)
- **Strategy Disabling**: Automatically disables strategies with rolling Sharpe < -0.2 or excessive drawdown

#### Capital Intelligence Layer

The dynamic capital allocator considers multiple factors:

- **Rolling Sharpe Ratio**: Performance metric for capital allocation
- **Expectancy**: Reward-to-risk ratio consideration
- **Regime Match Score**: Alignment with current market conditions
- **Correlation Penalty**: Diversification benefits
- **Drawdown Penalty**: Risk-based capital reduction

#### Monte Carlo Risk Simulation

Validates strategy robustness with:

- **Trade Order Randomization**: Shuffles trade sequences to test robustness
- **Bootstrap Resampling**: Samples with replacement to test statistical validity
- **Risk Metrics**: Calculates probability of ruin, value at risk, and expected shortfall
- **Confidence Intervals**: Provides statistical confidence bounds

#### Example Output

The comprehensive validation provides detailed analysis:

```
🏆 COMPREHENSIVE VALIDATION SUMMARY
   Pipeline Duration: 124.56s
   Total Strategies: 5
   Accepted Strategies: 2
   Data Symbols: 6
   Monte Carlo Success: ✅
   Walk-Forward Success: ✅
   Capital Allocator: ✅
   Kill Switch: ✅

🥇 TOP 5 PERFORMING STRATEGIES:
   1. trend_following      Return: 12.45%, Sharpe: 0.876, Status: ✅
   2. mean_reversion       Return: 8.23%, Sharpe: 0.742, Status: ✅
   3. volatility_breakout  Return: -2.15%, Sharpe: -0.342, Status: ❌
   4. ma_crossover_strategy Return: 1.05%, Sharpe: 0.123, Status: ❌
   5. rsi_strategy         Return: -0.45%, Sharpe: -0.056, Status: ❌
```

This system represents a hedge-fund grade validation pipeline that ensures only robust, profitable strategies are selected for portfolio inclusion with appropriate risk management.

### Extended Horizon Validation

The system now includes extended horizon validation to test alpha durability across longer timeframes:

```bash
python runner_extended_horizon_validation.py --horizons 180 360 720 --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT --capital 100000
```

This executes validation across multiple time periods to:

1. **Test Performance Decay**: Evaluate how strategy performance changes over longer horizons
2. **Validate Alpha Durability**: Confirm strategies survive regime transitions
3. **Analyze Stability**: Check for consistent performance across 180, 360, and 720 day periods
4. **Regime Stability Analysis**: Assess strategy performance across different market conditions over extended periods

#### Example Output

The extended horizon validation provides performance decay analysis:

```
🏆 EXTENDED HORIZON VALIDATION SUMMARY
   Pipeline Duration: 245.32s
   Total Horizons: 3
   Successful Horizons: 3
   Failed Horizons: 0

📉 PERFORMANCE DECAY ANALYSIS
   180D: Return=12.45%, Sharpe=0.876, Accepted=4
   360D: Return=11.23%, Sharpe=0.742, Accepted=3
   720D: Return=9.87%, Sharpe=0.654, Accepted=3
```

### Correlation Stress Testing

The system includes correlation stress testing to validate portfolio resilience:

```bash
python runner_correlation_stress_test.py --start 360d --end today --symbols BTCUSDT ETHUSDT SOLUSDT --levels 0.5 0.7 0.9 1.0
```

This simulates portfolio performance under different correlation scenarios:

1. **High Correlation Scenarios**: Tests what happens when all strategies become correlated
2. **Diversification Impact**: Evaluates how correlation affects portfolio performance
3. **Risk Assessment**: Identifies vulnerabilities under extreme correlation conditions
4. **Allocation Recommendations**: Provides guidance on adjusting allocations under stress

#### Example Output

The correlation stress test provides risk analysis:

```
📊 CORRELATION STRESS TEST SUMMARY
   Pipeline Duration: 89.45s
   Correlation Levels Tested: [0.5, 0.7, 0.9, 1.0]
   Critical Correlation Threshold: 0.9
   Most Vulnerable Strategies:
      1. trend_following: 45.2% degradation
      2. mean_reversion: 38.7% degradation
   Strategies for Allocation Reduction: 2
```

### Production Validation with Real Data Only

The system now enforces real data usage in production validation mode:

- **Mock Data Forbidden**: By default, mock data is not allowed in production validation
- **Environment Control**: Use `USE_MOCK_DATA_FOR_VALIDATION=true` for development/testing
- **Data Integrity**: Ensures all validation results are based on real market data
- **Regulatory Compliance**: Maintains data integrity for institutional requirements

### Shadow Deployment Preparation

The system includes shadow deployment capabilities for live testing:

```bash
python runner_shadow_deployment.py --symbols BTCUSDT ETHUSDT --strategies trend_following mean_reversion --capital 100000 --interval 60
```

Shadow deployment features:

1. **Real Market Data**: Uses live market data without executing real orders
2. **Performance Tracking**: Compares live performance to backtest results
3. **Risk Monitoring**: Implements all risk controls without actual capital exposure
4. **Alert System**: Notifies when performance deviates from expectations
5. **Gradual Transition**: Safe pathway from backtesting to live trading

#### Shadow Deployment Benefits

- **Zero Capital Risk**: Test strategies with real data without financial exposure
- **Market Condition Testing**: Validate performance across real market regimes
- **Execution Simulation**: Test order logic and timing with live data feeds
- **Performance Monitoring**: Track deviation from backtest expectations
- **Gradual Rollout**: Safe transition pathway to live trading

### Institutional Production Readiness

The system now includes comprehensive institutional-grade features for production readiness:

#### Data Provenance & Audit Trail

The system tracks data lineage with complete audit trail:

```python
data_metadata = {
    "source": "Binance",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "checksum": "...",
    "download_timestamp": "...",
    "row_count": ...,
    "git_commit": "..."
}
```

#### Reproducible Experiment Framework

Every validation run produces a unique run ID based on configuration:

```bash
RUN_ID = hash(config + strategies + symbols + date_range + git_commit)
```

Results are stored by run ID for scientific reproducibility.

#### Strategy Versioning

Each strategy carries version information:

```python
strategy_version = "1.3.2"
```

Results are mapped to specific strategy versions for change tracking.

#### Portfolio Dependency Risk Analysis

The system measures portfolio resilience if best strategy is removed:

```python
portfolio_dependency_risk = {
    'dependency_risk_score': 0.23,
    'best_strategy_contribution': 0.15,
    'portfolio_impact_if_best_removed': 0.08,
    'concentration_risk': 0.45
}
```

#### Drawdown Recovery Analysis

Measures time to recover from drawdowns:

```python
drawdown_recovery_metrics = {
    'max_drawdown': -0.12,
    'avg_recovery_time': 15.5,  # days
    'longest_recovery_time': 32,  # days
    'total_recovery_periods': 4
}
```

#### Trade Distribution Stability

Analyzes stability of key metrics over time:

```python
stability_metrics = {
    'win_rate_stability': {'mean': 0.52, 'std': 0.03, 'stability_score': 0.89},
    'avg_trade_pnl_stability': {'mean': 125.30, 'std': 45.2, 'stability_score': 0.92},
    'overall_stability_score': 0.90
}
```

#### Capital Shock Testing

Tests portfolio resilience under capital reductions:

```bash
python runner_capital_shock_test.py --shocks -0.2 -0.3 --symbols BTCUSDT ETHUSDT SOLUSDT
```

#### Shadow Deployment KPI Dashboard

Monitors key metrics for shadow deployment:

| Metric                       | Threshold | Current |
| ---------------------------- | --------- | ------- |
| Signal deviation vs backtest | < 15%     | 8.2%    |
| Win rate deviation           | < 10%     | 5.1%    |
| Avg trade PnL deviation      | < 15%     | 11.3%   |
| Trade count deviation        | < 20%     | 14.7%   |
| Regime classification drift  | < 10%     | 6.8%    |

#### Human Override Policy

Comprehensive policy document defining when human intervention is permitted (almost never).

#### Capital Deployment Phases

Structured progression from shadow to full deployment:

| Phase  | Capital | Status |
| ------ | ------- | ------ |
| Shadow | $0      | Ready  |
| Micro  | 1%      | Ready  |
| Pilot  | 5%      | Ready  |
| Growth | 25%     | Ready  |
| Scale  | 100%    | Ready  |

### Historical Data Download

```bash
# Download historical data for all configured symbols (downloads only 1m as base)
python runner_history_download.py --start 365d --end today --timeframes 1m

# Download historical data for a specific symbol (downloads only 1m as base)
python runner_history_download.py --start 90d --end today --symbols MATICUSDT --timeframes 1m

# Download with custom timeframes (space-separated) - NOTE: downloads only 1m as base, use multitimeframe_update to generate others
python runner_history_download.py --start 30d --end today --symbols BTCUSDT --timeframes 1m

# Download to custom directory (downloads only 1m as base)
python runner_history_download.py --start 180d --end today --symbols ETHUSDT --timeframes 1m --output ./custom_data
python runner_history_download.py --start 1180d --end today --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT --timeframes 1m

# Download with specific date range (downloads only 1m as base)
python runner_history_download.py --start 2023-01-01 --end 2023-12-31 --symbols SOLUSDT --timeframes 1m

# Download from specific exchange (default: binance) - downloads only 1m as base
python runner_history_download.py --start 90d --end today --symbols MATICUSDT --exchange bingx --timeframes 1m

# Download from different exchanges - downloads only 1m as base
python runner_history_download.py --start 30d --end today --symbols BTCUSDT ETHUSDT --exchange mexc --timeframes 1m
python runner_history_download.py --start 60d --end today --symbols ADAUSDT --exchange phemex --timeframes 1m

# Multiple symbols and 1m timeframe from specific exchange (other timeframes should be generated separately)
python runner_history_download.py --start 7d --end today --symbols BTCUSDT ETHUSDT SOLUSDT --timeframes 1m --exchange bingx
```

**Command Options:**
- `--start`: Start date (supports formats: 90d, 2023-01-01, today)
- `--end`: End date (supports formats: today, 2023-12-31)
- `--symbols`: Trading symbols to download (space-separated, e.g., BTCUSDT ETHUSDT)
- `--timeframes`: Timeframes to download (space-separated, default: 1m 5m 15m 30m 1h 4h 1d)
- `--output`: Output file to save results (JSON format)
- `--exchange`: Exchange to download from (default: binance, options: binance,bingx,mexc,phemex)
- `--validate`: Validate data integrity after download
- `--verbose`: Enable verbose output

### Managing Coins and Historical Data

#### Download New Coins

To download data for new coins:

```bash
# Download data for specific symbols (replace with actual symbols) - downloads only 1m data as base
python runner_history_download.py --start 90d --end today --symbols BTCUSDT ETHUSDT --timeframes 1m

# Download for all approved symbols for the last 3 months - downloads only 1m data as base
python runner_history_download.py --start 1d --end today --timeframes 1m
```

#### Update Old Coins

To update existing coins with new data:

```bash
# Run the historical data sync to update all approved symbols
python runner_historical_data_sync.py now

# Or run continuously to keep updating
python runner_historical_data_sync.py
```

#### Get 3-Month History for Specific Symbol

To get 3 months of history for a specific symbol:

```bash
# Download 3 months of data for a specific symbol - downloads only 1m data as base
python runner_history_download.py --start 90d --end today --symbols YOUR_SYMBOL --timeframes 1m

# Example for a specific coin:
python runner_history_download.py --start 90d --end today --symbols SOLUSDT --timeframes 1m
```

#### Update Multi-timeframe Data

After downloading raw 1-minute data, generate higher timeframes:

```bash
# Update multi-timeframe data from raw 1-minute data
python runner_multitimeframe_update.py --symbols YOUR_SYMBOL --timeframes 5m 15m 30m 1h 4h 1d

# Or update all symbols
python runner_multitimeframe_update.py --all --timeframes 5m 15m 30m 1h 4h 1d
```

#### Sync Approved Symbols

To ensure you have the latest list of available symbols:

```bash
# Update the list of approved symbols from exchanges
python runner_sync_approved_symbols.py
```

#### Complete Process for a New Symbol:

1. First, update the approved symbols list:
   ```bash
   python runner_sync_approved_symbols.py
   ```

2. Then download 3 months of 1-minute data (base data):
   ```bash
   python runner_history_download.py --start 90d --end today --symbols YOUR_SYMBOL --timeframes 1m
   ```

3. Generate higher timeframes from the 1-minute base data:
   ```bash
   python runner_multitimeframe_update.py --symbols YOUR_SYMBOL --timeframes 5m 15m 30m 1h 4h 1d
   ```

4. For ongoing updates, run the sync job:
   ```bash
   python runner_historical_data_sync.py now
   ```

#### Process All Symbols

You can also run these operations for ALL approved symbols:

1. Download 1-minute data for all approved symbols:
   ```bash
   python runner_history_download.py --start 90d --end today --timeframes 1m
   # Note: Without specifying --symbols, it will use all approved symbols from the environment
   ```

2. Update multi-timeframe data for all symbols:
   ```bash
   python runner_multitimeframe_update.py --all --timeframes 5m 15m 30m 1h 4h 1d
   ```

3. Sync historical data for all approved symbols (this runs continuously):
   ```bash
   python runner_historical_data_sync.py
   # Or run once:
   python runner_historical_data_sync.py now
   ```

4. Get the list of all approved symbols:
   ```bash
   python runner_sync_approved_symbols.py
   # This updates the approved symbols list from exchanges
   ```

---

## Recommended Workflow

### Production Trading (Continuous Operation)

* Run production system with auto-detection: `python run_trading_system.py --mode production --auto-detect --symbols BTCUSDT,ETHUSDT`
* Monitor logs for watcher signals and trading activity
* Review performance reports

### Daily

* Update data
* Monitor performance
* Light retuning if needed

### Weekly

* Full resync
* Walk-forward validation

### Monthly

* Deep backtesting
* Parameter stability review

---

## Configuration

### WFO Settings (`.env`)

* `WFO_COINS`
* `WFO_TRAIN_SIZE`
* `WFO_TEST_SIZE`
* `WFO_MAX_EVALS`
* `WFO_SYNC_DAYS`

### Strategy Hyperopt

* `shared/configurable_hyperopt.py`
* `configs/hyperopt_configs/`

---

## Data Structure

```
data/
├── history/
│   ├── raw/
│   └── processed/
├── results/
├── reports/
└── cache/
```

---

## Troubleshooting

**Insufficient data**

* Increase `--days` (30+ recommended)

**API rate limits**

* Add delays
* Use testnets

**Memory issues**

* Reduce symbols
* Lower `--evals`

**Missing data**

* Run history downloader

Logs are available in `logs/`.

---

## Maintenance

* Update dependencies quarterly
* Review optimization results weekly
* Clean old data monthly

---

## Contributing

1. Fork the repo
2. Create a feature branch
3. Add tests if applicable
4. Submit a PR

---

## License

MIT License. See `LICENSE`.