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

### Layers

* **Domain** – Core entities, strategies, and business rules
* **Application** – Use cases and orchestration logic
* **Infrastructure** – Exchanges, brokers, storage, APIs
* **Shared** – Configuration, utilities, logging

---

## System Components

### Strategy System

All strategies inherit from a shared base adapter and are fully isolated.

**Base**

* `BaseStrategyAdapter`
* Technical indicators: RSI, EMA, SMA, Bollinger Bands, ATR, momentum, volume

**Available Strategies**

* **TrendFollowStrategyAdapter** – MA crossovers with momentum confirmation
* **MeanReversionStrategyAdapter** – RSI + Bollinger Bands
* **ScalpingStrategyAdapter** – Fast MA crossovers with volume confirmation
* **BreakoutStrategyAdapter** – Consolidation and breakout detection
* **LiquidityStrategyAdapter** – Liquidity sweeps and market structure
* **MTFTrendStrategyAdapter** – Multi-timeframe trend alignment
* **OIFootprintStrategyAdapter** – Open Interest & volume analysis
* **SweepScalperAdapter** – Stop-hunt and volatility expansion
* **VWAPReversalStrategyAdapter** – VWAP-based mean reversion

### Strategy Execution Flow

1. Market data ingestion (OHLCV)
2. Technical analysis
3. Signal generation (BUY / SELL / HOLD)
4. Confidence scoring (0.0 – 1.0)
5. Position sizing (default 2% risk)
6. Order creation
7. Broker execution
8. Trade monitoring

✅ All strategies are production-ready and compatible with BingX VST testing.

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
python runner_history_download.py --start 365d --end today
```

---

## Recommended Workflow

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