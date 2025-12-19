# Lynxion ETS - Advanced Automated Trading System

A sophisticated cryptocurrency trading system with automated hyperparameter optimization, walk-forward analysis, and multi-timeframe data processing using hexagonal architecture.

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Running the System](#running-the-system)
- [Runner Instructions](#runner-instructions)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Project Overview

Lynxion ETS (Exchange Trading System) is an advanced cryptocurrency trading platform designed for systematic algorithmic trading. The system focuses on:

- **Automated Parameter Optimization**: Continuously tunes trading strategies for changing market conditions
- **Data Integrity**: Ensures complete and accurate historical data across multiple timeframes
- **Strategy Validation**: Validates strategies through walk-forward analysis and backtesting
- **Multi-Exchange Support**: Designed to work with multiple cryptocurrency exchanges
- **Risk Management**: Built-in risk controls and performance monitoring

The system is built using modern software engineering practices with a focus on scalability, maintainability, and performance.

## Architecture

The system follows **Hexagonal Architecture** (also known as Ports and Adapters) to create a clean separation between business logic and infrastructure concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Interface     │    │   Application    │    │   Infrastructure│
│   Layer         │    │   Layer          │    │   Layer         │
│                 │    │                  │    │                 │
│ Users/External  │◄──►│ Use Cases &      │◄──►│ External APIs   │
│ Systems         │    │ Business Rules   │    │ (Exchanges,     │
│                 │    │                  │    │ Databases, etc.)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         └───────────────────────┼────────────────────────┘
                                 │
                        ┌──────────────────┐
                        │    Domain        │
                        │    Layer         │
                        │                  │
                        │ Core Business    │
                        │ Logic & Entities │
                        └──────────────────┘
```

**Key Components:**
- **Domain Layer**: Core business entities, trading strategies, and domain services
- **Application Layer**: Use cases, business rules implementation, and orchestration
- **Infrastructure Layer**: External adapters (exchanges, databases, file systems)
- **Shared Components**: Common utilities, configuration, and logging

## Features

- **Multi-exchange support** (Binance, BingX, MEXC, Phemex)
- **Automated hyperparameter optimization** (retuning)
- **Walk-forward analysis** for strategy validation
- **Multi-timeframe data processing**
- **Realistic backtesting** with slippage and fees
- **Hexagonal architecture** for clean separation of concerns
- **Continuous data synchronization**

## Architecture

The system follows hexagonal architecture with the following layers:
- **Domain**: Core business logic and entities
- **Application**: Use cases and business rules
- **Infrastructure**: External services and adapters
- **Shared**: Common utilities and cross-cutting concerns

## Prerequisites

- Python 3.10+
- Pip package manager
- Exchange API credentials (for live trading, optional for backtesting)
- At least 4GB RAM for optimization processes

## Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd lynxion-ets
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install additional dependencies if needed**
```bash
pip install pandas numpy hyperopt
```

## Environment Setup

1. **Copy the example environment file**
```bash
cp .env.example .env
```

2. **Edit the `.env` file** with your exchange credentials (for live trading):
```bash
# Exchange API credentials
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
BINGX_API_KEY=your_bingx_api_key
BINGX_SECRET_KEY=your_bingx_secret_key

# WFO Configuration
WFO_COINS=BTCUSDT,ETHUSDT,BNBUSDT,ADAUSDT,XRPUSDT,SOLUSDT
```

3. **Configure coins for optimization** in `WFO_COINS` (comma-separated list)

## Running the System

### System Runners

### Strategy Components

#### Core Infrastructure Base Class (`infrastructure/strategies/strategy_adapters.py`)

- **BaseStrategyAdapter** - Contains core functionality and technical analysis methods (RSI, EMA, SMA, Bollinger Bands, ATR, etc.)

#### Individual Strategy Files (Properly Isolated in `infrastructure/strategies/adapters/`)

All strategies are now properly isolated in individual files within the adapters directory:

1. **TrendFollowStrategyAdapter** - Trend following strategy using moving average crossovers, trend strength analysis, and momentum confirmation to identify and follow market trends. Generates BUY signals when short-term MA crosses above long-term MA with positive momentum, SELL when opposite. Technical indicators: EMA, trend strength, momentum, ATR for volatility adjustment.

2. **MeanReversionStrategyAdapter** - Mean reversion strategy utilizing RSI and Bollinger Bands to identify overbought/oversold conditions for counter-trend opportunities. Generates BUY signals when price is below lower Bollinger Band and RSI is oversold (<30), SELL when above upper band and overbought (>70). Technical indicators: RSI, Bollinger Bands, momentum analysis.

3. **ScalpingStrategyAdapter** - Scalping strategy using fast moving average crossovers and momentum indicators for short-term profit opportunities with volume confirmation. Uses 5-period MA crossing 10-period MA with momentum validation and volume spike confirmation. Technical indicators: Fast/slow EMA, momentum, RSI, volume analysis.

4. **BreakoutStrategyAdapter** - Breakout strategy detecting consolidation periods followed by strong directional moves using support/resistance and volatility analysis. Identifies tight consolidation patterns that break with volume. Technical indicators: Support/resistance detection, consolidation analysis, volatility measures, momentum confirmation.

5. **LiquidityStrategyAdapter** - Liquidity sweep detection strategy combining technical analysis with market microstructure indicators to identify major player positioning. Looks for price action near liquidity levels. Technical indicators: RSI, Bollinger Bands, potential sweep zones, volume analysis.

6. **MTFTrendStrategyAdapter** - Multi-timeframe trend confirmation strategy analyzing different timeframes simultaneously to validate trend direction with higher reliability. Confirms trend alignment across multiple timeframes. Technical indicators: Multiple EMAs across different timeframes, trend alignment, momentum.

7. **OIFootprintStrategyAdapter** - Open Interest and volume footprint analysis strategy detecting institutional positioning shifts and market sentiment changes. Analyzes volume-interest relationships. Technical indicators: Volume analysis, momentum, market condition assessment.

8. **SweepScalperAdapter** - Liquidity sweep scalping strategy identifying potential stop hunt zones and market maker positions for quick profit opportunities. Focuses on volatility expansion and sweep detection. Technical indicators: Range analysis, volatility measurement, potential sweep zones.

9. **VWAPReversalStrategyAdapter** - VWAP-based mean reversion strategy using volume-weighted average price as dynamic equilibrium point for reversion trades. Identifies price deviations from VWAP equivalent. Technical indicators: VWAP proxy, price deviation analysis, statistical bands.

#### Strategy-Broker Integration Workflow

All strategies follow a standardized workflow for signal generation and order placement:

1. **Market Data Processing** - Each strategy receives and buffers market data (OHLCV)
2. **Technical Analysis** - Real indicators (RSI, EMAs, Bollinger Bands, ATR) analyze market conditions
3. **Signal Generation** - BUY/SELL/HOLD signals generated with confidence scoring (0.0-1.0)
4. **Position Sizing** - Size calculated based on signal confidence and risk parameters (2% per trade default)
5. **Order Creation** - Properly structured Order objects created from signals
6. **Broker Connection** - Ready to connect with BingX VST test account via broker adapter
7. **Execution** - Orders placed on exchange with tracking and management

#### Verification Status

- ✅ All 9 strategies generating real signals with technical analysis
- ✅ All strategies properly isolated in individual files
- ✅ All strategies have position sizing and risk management
- ✅ All strategies compatible with BingX broker integration
- ✅ Hexagonal architecture maintained throughout
- ✅ Ready for live testing on BingX VST account

#### Strategy Descriptions

- **TrendFollowStrategyAdapter**: Identifies and follows market trends using moving average crossovers, trend strength analysis, and momentum confirmation. Generates BUY signals when short-term MA crosses above long-term MA with positive momentum, SELL when opposite.

- **MeanReversionStrategyAdapter**: Exploits mean-reverting price behavior using RSI and Bollinger Bands. Generates BUY signals when price is oversold (RSI < 30) and below lower Bollinger Band, SELL when overbought (RSI > 70) and above upper Bollinger Band.

- **ScalpingStrategyAdapter**: Captures small price movements using fast MA crossovers and momentum. Optimized for high-frequency, short-term opportunities with volume confirmation. Generates signals when fast MA crosses slow MA with momentum confirmation.

- **BreakoutStrategyAdapter**: Detects consolidation periods followed by breakout moves. Identifies resistant support/resistance levels and generates signals when price breaks these levels with volume confirmation and momentum.

- **LiquidityStrategyAdapter**: Advanced strategy combining liquidity sweeps, funding rates, OI expansion, and CVD divergences with multi-timeframe confirmation for professional market structure analysis.

- **MTFTrendStrategyAdapter**: Uses multiple timeframes simultaneously to confirm trend direction, reducing false signals by ensuring alignment across different periods.

- **OIFootprintStrategyAdapter**: Analyzes Open Interest and volume data to detect institutional positioning and market sentiment shifts for early trend identification.

- **SweepScalperAdapter**: Seeks to capitalize on liquidity sweeps by identifying levels where market makers take orders from the order book.

- **VWAPReversalStrategyAdapter**: Uses Volume Weighted Average Price as a mean reference for mean reversion opportunities when price deviates significantly from VWAP.

### System Runners

The system includes several specialized runners for different operational tasks:

#### 1. **Main Trading System (`run_trading_system.py`)**

The primary entry point for the trading system that can orchestrate multiple processes and coordinate system operations.

```bash
# Run the main trading system with default configurations
python run_trading_system.py

# Run with specific configuration
python run_trading_system.py --config custom_config.json
```

#### 2. **Main Hexagonal Container (`main_hexagonal_container.py`)**

The hexagonal architecture container that wires up all system components using dependency injection.

```bash
# Initialize the hexagonal container (typically imported by other modules)
python main_hexagonal_container.py
```

#### 3. **Data Synchronization (`runner_resync.py`)**

Synchronize historical data for all configured symbols and timeframes. This orchestrates the entire data pipeline.

```bash
# Full resync (download + timeframes + retune validation)
python runner_resync.py --all

# Download historical data only
python runner_resync.py --download

# Process timeframes only
python runner_resync.py --timeframes

# Run retune validation only
python runner_resync.py --retune

# Process specific symbols
python runner_resync.py --all --symbols BTCUSDT ETHUSDT

# Process only specific coins from WFO_COINS environment variable
python runner_resync.py --download --timeframes
```

**Options:**
- `--all`: Run all processes (download, timeframes, retune)
- `--download`: Run download and sync process
- `--timeframes`: Process timeframes from raw data
- `--retune`: Run retune process to validate and repair data
- `--symbols SYMBOL1 SYMBOL2`: Process specific symbols

#### 4. **Hyperparameter Optimization (`runner_retune.py`)**

Automatically optimize strategy parameters for current market conditions using 1-day timeframe data for stable optimization.

```bash
# Retune all WFO_COINS symbols (from environment)
python runner_retune.py --strategy crypto_breakout --evals 50 --days 90

# Retune specific symbols
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --evals 100 --days 180

# With validation and output file
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT --evals 25 --days 120 --validate --output results.json

# Minimal test run
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT --evals 5 --days 30
```

**Options:**
- `--strategy`: Strategy name to retune (default: crypto_breakout)
- `--symbols SYMBOL1 SYMBOL2`: Specific symbols to retune (default: from WFO_COINS env var)
- `--evals`: Maximum number of hyperopt evaluations per symbol (default: 50)
- `--days`: Number of days of historical data to use (default: 90)
- `--output`: Output file to save results (JSON format)
- `--validate`: Validate results after retuning
- `--verbose`: Enable verbose output

#### 5. **Historical Data Downloader (`runner_history_download.py`)**

Download historical market data for multiple symbols and timeframes from exchanges.

```bash
# Download 1 year of data for all configured symbols
python runner_history_download.py --start 365d --end today

# Download specific timeframes for specific coins
python runner_history_download.py --start 2023-01-01 --end 2023-12-31 --symbols BTCUSDT ETHUSDT --timeframes 1m 5m 15m

# Download long-term 1-day data (recommended for retuning)
python runner_history_download.py --start 730d --end today --timeframes 1d --symbols BTCUSDT ETHUSDT

# With validation
python runner_history_download.py --start 30d --end today --validate
```

**Options:**
- `--start`: Start date in YYYY-MM-DD format or relative (e.g., "30d", "90d")
- `--end`: End date in YYYY-MM-DD format or "today" (default: today)
- `--symbols SYMBOL1 SYMBOL2`: Specific symbols to download (default: from WFO_COINS env var)
- `--timeframes`: Timeframes to download (default: 1m 5m 15m 30m 1h 4h 1d)
- `--exchange`: Exchange to download from (default: binance)
- `--output`: Output file to save results (JSON format)
- `--validate`: Validate data integrity after download

#### 6. **Walk-Forward Analysis (`runner_walkforward.py`)**

Validate strategy robustness over different market conditions using walk-forward methodology.

```bash
# Run walk-forward analysis with default parameters
python runner_walkforward.py --strategy crypto_breakout --symbols BTCUSDT --train-days 60 --test-days 15

# Multi-symbol walk-forward analysis
python runner_walkforward.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --train-days 90 --test-days 30 --evals 25
```

**Options:**
- `--strategy`: Trading strategy to analyze (default: crypto_breakout)
- `--symbols SYMBOL1 SYMBOL2`: List of symbols to analyze (default: WFO_COINS from environment)
- `--train-days`: Number of days for training/optimization window
- `--test-days`: Number of days for testing/validation window
- `--evals`: Maximum optimization evaluations per training period
- `--start-date`: Start date for analysis (default: earliest available)
- `--end-date`: End date for analysis (default: today)

#### 7. **Backtesting (`runner_backtest.py`)**

Run historical backtesting with optimized parameters and realistic trading simulation.

```bash
# Standard backtest
python runner_backtest.py --strategy crypto_breakout --symbols BTCUSDT --start 2023-01-01 --end 2023-12-31

# Backtest with optimized parameters
python runner_backtest.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --start 90d --end today --optimized

# Advanced backtesting with reports
python runner_backtest.py --strategy crypto_breakout --symbols BTCUSDT --start 180d --end today --report --plot --output results/
```

**Options:**
- `--strategy`: Trading strategy to backtest (default: crypto_breakout)
- `--symbols SYMBOL1 SYMBOL2`: List of symbols to backtest
- `--start`: Start date or relative period (e.g., "90d", "2023-01-01")
- `--end`: End date or relative period (default: today)
- `--optimized`: Use optimized parameters from retune process
- `--timeframe`: Data timeframe (default: depends on strategy)
- `--report`: Generate detailed performance report
- `--plot`: Generate performance charts
- `--output`: Output directory for results

#### 8. **Multi-timeframe Update (`runner_multitimeframe_update.py`)**

Update multiple timeframes for existing data, converting raw data to processed timeframes.

```bash
# Update all configured timeframes for all symbols
python runner_multitimeframe_update.py

# Update for specific symbols
python runner_multitimeframe_update.py --symbols BTCUSDT ETHUSDT
```

## Recommended Workflow

### Daily Operations:
1. **Update data**: `python runner_resync.py --download --timeframes`
2. **Monitor performance**: Check results and reports
3. **Trigger retuning if needed**: `python runner_retune.py --symbols BTCUSDT ETHUSDT --evals 25`

### Weekly Operations:
1. **Full resync**: `python runner_resync.py --all`
2. **Strategy validation**: `python runner_walkforward.py --symbols BTCUSDT --train-days 60 --test-days 15`

### Monthly Operations:
1. **Comprehensive backtesting**: `python runner_backtest.py --start 90d --end today --report`
2. **Parameter validation**: `python runner_retune.py --evals 100 --days 180`

## Configuration

### WFO Configuration Options

In your `.env` file, configure the following options:

- `WFO_COINS`: Comma-separated list of coins to optimize (e.g., `BTCUSDT,ETHUSDT,BNBUSDT`)
- `WFO_TRAIN_SIZE`: Training window size in days (default: 90)
- `WFO_TEST_SIZE`: Testing window size in days (default: 30)
- `WFO_MAX_EVALS`: Maximum hyperopt evaluations per asset (default: 50)
- `WFO_SYNC_DAYS`: Full refresh interval in days (default: 180)

### Strategy Configuration

The system uses configurable hyperopt with parameter ranges and constraints. You can customize strategy parameters in:
- `shared/configurable_hyperopt.py`
- Strategy-specific configuration files in `configs/hyperopt_configs/`

## Data Directory Structure

```
data/
├── history/
│   ├── raw/           # Raw 1-minute data
│   └── processed/     # Processed timeframes (5m, 15m, 30m, 1h, 4h, 1d, etc.)
├── results/           # Backtest and optimization results
├── reports/           # Generated reports and charts
└── cache/             # Temporary cached data
```

## Troubleshooting

### Common Issues:

1. **"Insufficient data for symbol"**: 
   - Usually occurs when using small `--days` values
   - The system requires at least 20 rows of data for optimization
   - Solution: Use larger `--days` values (30+ days recommended)

2. **API Rate Limits**:
   - Add delays between requests in configuration
   - Use exchange testnet for development

3. **Memory Issues During Optimization**:
   - Reduce the number of symbols processed simultaneously
   - Lower the number of evaluations (`--evals`)

4. **Missing Data Files**:
   - Run `runner_history_download.py` to download missing data
   - Check internet connection and exchange API status

### Error Reporting:
- Check log files in `logs/` directory
- Use `--verbose` flag for detailed output
- Verify exchange API keys are correct

## Maintenance

### Regular Maintenance Tasks:

1. **Clean old data files** (monthly):
   ```bash
   # The system automatically manages retention with configured settings
   ```

2. **Update dependencies** (quarterly):
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **Review optimization results** (weekly):
   - Check `data/hyperopt_results/` directory
   - Review parameter stability across time periods

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the maintainers.

---

**Note**: This system is designed for educational and research purposes. Trading cryptocurrencies involves substantial risk. Always test strategies thoroughly before using with real funds.