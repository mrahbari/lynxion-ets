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

```bash
python runner_backtest.py --strategy crypto_breakout --start 90d --end today --report
```

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
python runner_history_download.py --start 90d --end today --timeframes 1m
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