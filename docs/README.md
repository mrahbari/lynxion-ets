# Lynxion ETS - Enterprise Trading System

## 🚀 Complete System Overview

Lynxion ETS (Enterprise Trading System) is a professional-grade hedge fund trading system implementing hexagonal architecture with advanced Walk-Forward Optimization (WFO) capabilities. The system follows the complete workflow: **Watcher → Engine → Fusion → Strategy → Broker** with production-ready quality.

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Key Features](#key-features)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Runner Scripts](#runner-scripts)
7. [Risk Management](#risk-management)
8. [Performance](#performance)
9. [Troubleshooting](#troubleshooting)

## Architecture Overview

### Core Workflow: Watcher → Engine → Fusion → Strategy → Broker

```
Downloader → Resample Engine → Data Loader → Strategy Engine → Watcher Layer → MultiSymbol Router → Execution Engine → Brokers
```

### Hexagonal Architecture Components:
- **Domain Layer**: Pure business logic with interfaces (ports)
- **Application Layer**: Orchestration and use cases (orchestrators)
- **Infrastructure Layer**: Concrete implementations (adapters)

### Key Components:
- **Watchers**: Market Opportunity Watcher, CMC Screener, Multiple Specialized Watchers
- **Engines**: Multiple algorithmic engines with dynamic weighting
- **Fusion**: Signal aggregation with correlation adjustment
- **Strategies**: Multi-strategy implementation with risk management
- **Brokers**: Multi-exchange integration with order management

## Key Features

### 🎯 **Complete WFO Pipeline**
- **Training Window**: 90 days
- **Testing Window**: 30 days
- **Sliding Step**: 30 days
- **Complete Architecture**: SlidingWindowSplitter → CrossValidationEngine → HyperoptAdapter → WFOOrchestrator

### 📈 **Advanced Capabilities**
- Multi-asset parameter optimization
- Cross-validation with robustness testing
- Parameter aggregation across assets
- Realistic backtesting with fees/slippage
- Lookahead bias prevention through proper indicator shifting

### 🔄 **Data Resampling**
- Zero-drift resampling from 1m base data to higher timeframes
- `1m → 5m`: 5-minute bars from 1-minute data
- `1m → 15m`: 15-minute bars from 1-minute data
- `1m → 30m`: 30-minute bars from 1-minute data
- `1m → 1h`: 1-hour bars from 1-minute data

### 🧠 **Advanced Intelligence**
- **Machine Learning Fusion**: ML-based signal fusion using Random Forest, Gradient Boosting, and Ensemble methods
- **Hyperopt Integration**: Real hyperparameter optimization with TPE, Random, and Annealing algorithms
- **Dynamic Risk Adjustment**: Market regime-aware risk management
- **Smart Position Sizing**: Multiple algorithms (Kelly, ATR-based, Optimal F, Volatility-targeted)

### 🛡️ **Risk Management**
- Stop-loss and take-profit with priority logic
- Portfolio exposure limits
- Drawdown monitoring
- Correlation risk management
- Market regime-based position sizing
- Dynamic risk adjustment based on volatility and correlation
- Position sizing algorithms with configurable parameters

## Installation

### Prerequisites
- Python 3.9+
- Pip package manager

### Setup
```bash
# 1. Clone or download the repository
git clone https://github.com/your-repo/lynxion-ets.git
cd lynxion-ets

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create environment file
cp .env.example .env
# Edit .env with your configuration settings

# 5. Create required directories
mkdir -p ./data/history/{raw/1m,processed/{5m,15m,30m,1h}}
mkdir -p ./data/results/{wfo,backtest,hyperopt}
mkdir -p ./logs
```

## Configuration

### Environment Variables
Key configuration options in `.env`:
```bash
# WFO Settings
WFO_COINS=BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT,AVAXUSDT,DOGEUSDT,TRXUSDT,ATOMUSDT,TONUSDT,LINKUSDT,TRXUSDT,NEARUSDT,EGLDUSDT,APTUSDT,AAVEUSDT,CROUSDT,UNIUSDT,INJUSDT,FILUSDT,ARBUSDT,PEPEUSDT,APTUSDT,GMXUSDT,ORDIUSDT,RUNEUSSDT
WFO_TRAIN_SIZE=90
WFO_TEST_SIZE=30
WFO_STEP_SIZE=30
WFO_MAX_EVALS=100

# RETUNE Settings
RETUNE_ENABLED=true
RETUNE_INTERVAL_HOURS=6
RETUNE_PERFORMANCE_THRESHOLD=0.15
RETUNE_EVALS_PER_CYCLE=20

# Risk Management
RISK_MAX_POSITION_SIZE=0.20
RISK_MAX_TOTAL_EXPOSURE=0.80
RISK_MAX_DRAWDOWN=0.15
RISK_MAX_LEVERAGE=5.0

# Performance Settings
MAX_CACHE_AGE_HOURS=24
MAX_COIN_CACHE_SIZE=50
```

## Usage

### 🏃‍♂️ **Quick Start**

#### 1. Run with Default Configuration
```bash
# Run the main trading system
python run_trading_system.py --mode optimize --strategy crypto_breakout --symbol BTCUSDT

# Run backtest with optimized parameters
python run_trading_system.py --mode backtest --strategy crypto_breakout --symbol BTCUSDT --use-optimized-params

# Run auto-retune on multiple symbols
python run_trading_system.py --mode retune --strategy crypto_breakout --symbols BTCUSDT,ETHUSDT,SOLUSDT

# Run in production mode
python run_trading_system.py --mode production --strategy crypto_breakout
```

#### 2. Auto-Detection Mode
```bash
# Run in auto-detection mode (watcher detects opportunities and triggers strategies automatically)
python run_trading_system.py --mode production --auto-detect --symbols BTCUSDT,ETHUSDT

# Run auto-detection with all configured coins
python run_trading_system.py --mode production --auto-detect
```

### 📊 **Complete WFO Pipeline**
```python
from application.walk_forward.wfo_orchestrator import WFOOrchestrator

# Configuration for the pipeline
wfo_config = {
    'train_size': 90,
    'test_size': 30,
    'step': 30,
    'max_evals': 100,
    'results_dir': './data/results/wfo',
    'risk_config': {
        'initial_capital': 1000000.0,
        'fee_rate': 0.001,
        'slippage_factor': 0.0005
    }
}

# Initialize orchestrator
orchestrator = WFOOrchestrator(config=wfo_config)

# Define a strategy function
def my_strategy(row, params):
    # Example strategy - replace with your logic
    rsi = row.get('rsi', 50)
    if rsi < 30:
        return 1  # Buy
    elif rsi > 70:
        return -1  # Sell
    else:
        return 0  # Hold

# Run the complete pipeline
results = orchestrator.run_complete_wfo_pipeline(
    symbols=['BTCUSDT', 'ETHUSDT'],
    strategy_name='my_strategy',
    strategy_func=my_strategy
)
```

### 🔄 **Resync Data**
```bash
# Run complete resync process (download, timeframe processing, validation)
python runner_resync.py --all

# Run only download and sync
python runner_resync.py --download --timeframes

# Run for specific symbols
python runner_resync.py --all --symbols BTCUSDT ETHUSDT
```

## Runner Scripts

### Available Runner Scripts

The system provides several specialized runner scripts in the root directory:

#### 1. **Resync Runner** (`runner_resync.py`)
Orchestrates downloader, sync, and retune processes for data consistency.
```bash
python runner_resync.py --all

# Run only download and timeframe processing
python runner_resync.py --download --timeframes

# Run for specific symbols
python runner_resync.py --symbols BTCUSDT ETHUSDT
```

#### 2. **Retune Runner** (`runner_retune.py`)
Automated hyperparameter retuning for trading strategies.
```bash
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT --evals 50 --days 90
```

#### 3. **History Download Runner** (`runner_history_download.py`)
Download historical market data for multiple symbols and timeframes.
```bash
python runner_history_download.py --start 2023-01-01 --end 2023-12-31 --symbols BTCUSDT ETHUSDT
```

#### 4. **Multi-Timeframe Update Runner** (`runner_multitimeframe_update.py`)
Aggregates 1-minute data to higher timeframes following the proper MTF sync pattern.
```bash
python runner_multitimeframe_update.py --symbols BTCUSDT --timeframes 5m 15m 30m 1h 4h 1d
```

#### 5. **Backtest Runner** (`runner_backtest.py`)
Execute comprehensive backtesting for trading strategies.
```bash
python runner_backtest.py --strategy rsi_strategy --start 2023-01-01 --end 2023-12-31 --symbols BTCUSDT
```

#### 6. **Walk-Forward Runner** (`runner_walkforward.py`)
Execute walk-forward optimization and analysis.
```bash
python runner_walkforward.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --train 90 --test 30 --step 30
```

#### 7. **Machine Learning Fusion Runner** (`runner_ml_fusion.py`)
Execute ML-based signal fusion with advanced algorithms.
```bash
python runner_ml_fusion.py --method random_forest --symbols BTCUSDT ETHUSDT --lookback 30
```

#### 8. **Advanced Position Sizing Runner** (`runner_position_sizing.py`)
Execute advanced position sizing using multiple algorithms.
```bash
python runner_position_sizing.py --algorithm kelly --symbols BTCUSDT --portfolio 100000
```

### Runner Script Options
All runner scripts support common options:
- `--validate`: Validate results after processing
- `--output FILE`: Save results to JSON file
- `--verbose`: Enable detailed output
- `--config FILE`: Load configuration from JSON file
- `--algorithm METHOD`: Specify algorithm for ML/fusion methods

## Risk Management

### Core Risk Controls
- **Position Sizing**: Based on multiple algorithms (Kelly, Fixed Fractional, ATR-based, Volatility-targeted)
- **Portfolio Exposure Limits**: Maximum percentage of capital per position and total exposure
- **Drawdown Controls**: Automatic trading halt when drawdown threshold exceeded
- **Correlation Management**: Limit position overlap across strategies
- **Market Regime Detection**: Adjust risk parameters based on volatility and trend conditions
- **Dynamic Risk Adjustment**: Automatically adjust position sizes and risk limits based on market conditions
- **Order Management**: Proper SL/TP execution using candle high/low

### Advanced Risk Configuration
Risk parameters are configured in `.env` file with comprehensive settings:
```bash
# Position Sizing Parameters
RISK_MAX_POSITION_SIZE=0.20                    # Max 20% per position
RISK_KELLY_FRACTION=0.25                       # Use 25% of full Kelly recommendation
RISK_FIXED_FRACTIONAL_PERCENTAGE=0.02          # Risk 2% of portfolio per trade
RISK_ATR_MULTIPLIER=2.0                        # Use 2x ATR for stop distance
RISK_VOLATILITY_TARGET=0.15                    # Target 15% annual volatility

# Portfolio Risk Limits
RISK_MAX_TOTAL_EXPOSURE=0.80                   # Max 80% total exposure
RISK_MAX_DRAWDOWN=0.15                         # Max 15% drawdown
RISK_MAX_LEVERAGE=5.0                          # Max 5x leverage

# Correlation and Diversification
RISK_MAX_CORRELATION_BETWEEN_STRATEGIES=0.7    # Max 70% correlation
RISK_DIVERSIFICATION_FACTOR=0.85               # Reduce position with increasing correlation

# Market Regime Adjustments
RISK_HIGH_VOLATILITY_THRESHOLD=0.025           # Threshold for high volatility regime
RISK_LOW_VOLATILITY_THRESHOLD=0.008            # Threshold for low volatility regime
RISK_TREND_STRENGTH_THRESHOLD=0.003            # Threshold for trend strength
```

## Performance

### System Characteristics
- **Low Latency**: Optimized for high-frequency signal processing
- **Scalable Architecture**: Supports multiple symbols and strategies
- **Memory Efficient**: Data caching with size limits
- **Parallel Processing**: Concurrent operations where possible

### Performance Metrics
- **Sharpe Ratio**: Risk-adjusted return metric
- **Win Rate**: Percentage of profitable trades
- **Max Drawdown**: Peak-to-trough decline
- **Profit Factor**: Gross profit / gross loss
- **Expectancy**: Average profit per trade
- **Calmar Ratio**: Annual return / Max drawdown
- **Alpha/Beta**: Risk-adjusted performance vs benchmark
- **Information Ratio**: Excess return / Tracking error
- **Correlation Analysis**: Strategy correlation matrix and diversification metrics
- **Risk-Adjusted Returns**: Returns normalized by various risk measures

## Troubleshooting

### Common Issues

#### 1. Data Loading Issues
- **Issue**: "No data found for symbol"
- **Solution**: Verify data files exist in correct format
- **Check**: `./data/history/raw/1m/{SYMBOL}.csv`

#### 2. Memory Issues
- **Issue**: System running out of memory
- **Solution**: Reduce cache sizes in configuration
- **Config**: `MAX_COIN_CACHE_SIZE` in `.env`

#### 3. Configuration Errors
- **Issue**: Invalid parameter ranges
- **Solution**: Verify parameter bounds in hyperopt configuration
- **Check**: Parameter ranges in `HyperoptParameterSpace`

### Error Reporting
- Check log files in `./logs/` directory
- Enable verbose output with `--verbose` flag
- Review configuration files for missing values

### Support
- Review documentation in `./docs/` directory
- Check runner scripts for usage examples
- Examine test files for implementation examples

## Production Deployment

### 1. Setup
```bash
# Create production environment
cp .env.example .env.production
# Configure production settings including:
# - ML fusion parameters
# - Advanced risk management
# - Hyperopt optimization settings
# - Position sizing algorithms
# - Market regime detection thresholds
```

### 2. Configuration Parameters
The system uses configurable parameters instead of hardcoded values:
- **Position Sizing**: Configure through environment variables (Kelly fraction, ATR multiplier, volatility targets)
- **Risk Management**: Set risk thresholds via environment variables (max position size, drawdown limits, correlation limits)
- **ML Fusion**: Control ML model parameters via environment variables (model types, lookback periods, confidence thresholds)
- **Hyperopt**: Configure optimization parameters in environment (algorithm types, max evaluations, early stopping)

### 3. Monitoring
- Enable logging to file
- Set up alert notifications
- Monitor resource usage
- Track performance metrics
- Monitor ML model performance and retraining cycles

### 3. Backup Strategy
- Regular backup of results data
- Configuration version control
- Log rotation and archival

## Quality Assurance

### Testing Framework
- Unit tests: Individual component functionality
- Integration tests: Complete workflow validation
- End-to-end tests: Full system validation
- Performance tests: Load and stress testing

### Run Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_complete_orchestrator_workflow.py -v
python -m pytest tests/wfo_complete_pipeline_tests.py -v
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🏆 System Status

The lynxion-ets system is now fully validated and production-ready with enhanced capabilities:

- ✅ Complete WFO pipeline with 90/30/30 windows
- ✅ Data resampling: 1m → 5m/15m/30m/1h with zero-drift methodology
- ✅ Lookahead bias prevention through proper indicator shifting
- ✅ MTF synchronization (downsample → ffill → shift → align)
- ✅ Stop-loss priority > take-profit for longs
- ✅ Realistic backtesting with proper fees/slippage execution
- ✅ Peak-trough drawdown calculation
- ✅ Full hexagonal architecture compliance
- ✅ RETUNE integration preserved and enhanced
- ✅ Comprehensive testing suite with QA checklist
- ✅ **Sync Engine**: Gap-free 1-minute OHLCV sync for many symbols
- ✅ **Async Processing**: Network downloads + thread pool for local CPU work
- ✅ **Atomic Operations**: Safe file writes and deterministic gap-filling
- ✅ **Structured Logging**: JSON logs and cycle reports
- ✅ **On-demand Repair**: Watcher retune for priority repairs
- ✅ **Dynamic Configuration**: Environment-based settings and symbol routing
- ✅ **Multi-exchange Support**: Flexible exchange selection per symbol
- ✅ **Machine Learning Fusion**: ML-based signal fusion with Random Forest, Gradient Boosting, and Ensemble methods
- ✅ **Real Hyperopt Integration**: Actual hyperopt library integration with TPE, Random, and Annealing algorithms
- ✅ **Advanced Position Sizing**: Multiple algorithms (Kelly, ATR-based, Optimal F, Volatility-targeted) with configurable parameters
- ✅ **Dynamic Risk Management**: Market regime-aware risk adjustments and correlation-based position sizing
- ✅ **Configurable Parameters**: All previously hardcoded values now configurable via environment variables
- ✅ **Enhanced Performance Monitoring**: Comprehensive metrics with correlation analysis and risk-adjusted returns
- ✅ **Improved Architecture**: Base engine adapter to reduce code duplication and improve maintainability

The system follows institutional-grade standards and is ready for professional trading operations.