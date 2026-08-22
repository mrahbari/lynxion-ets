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
* [Prospective Validation & Live Execution Plan](#prospective-validation--live-execution-plan)
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
* **Enhanced Risk Management**: Comprehensive risk controls with regime-adaptive, correlation-aware, drawdown-sensitive, and volatility-normalized features
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
* **Probabilistic Position Sizing**: Evidence-weighted approach with fusion confidence, regime accuracy, and correlation exposure factors
* **Advanced SL/TP Logic**: Volatility-normalized and structure-aware stop loss/take profit levels with regime-adaptive adjustments
* **Adaptive Fusion Weighting**: Performance-adaptive, correlation-penalizing, stability-rewarding, and noise-suppressing features
* **Advanced Regime Classification**: Confidence scoring, veto mechanisms, maturity tracking, and confusion matrix feedback
* **Intelligent Strategy Selection**: Performance-ranking, risk-adjustment, and regime-compatibility with promotion/demotion/suspension rules
* **Profitability Enhancement**: Variance reduction, expectancy compounding, selective trade filtering, capital efficiency improvements, and signal timing refinement
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
* **Engine (`EngineService`)**: Canonical engine layer — interprets raw market observations into signals
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
Watcher  --->  Engine (EngineService)  --->  Fusion  --->  Strategy  --->  Risk  --->  Broker

  Watcher   :  domain-specific market analysis; emits raw market observations
  Engine    :  EngineService interprets each observation into an InterpretedSignal (canonical engine layer)
  Fusion    :  adaptive weighting + signal aggregation (diversity, explainability, conflict resolution)
  Strategy  :  strategy selection + execution intent
  Risk      :  ATR-based stops/sizing + portfolio risk controls + kill-switch
  Broker    :  order execution + monitoring
```

For a detailed diagram and walkthrough of the event-driven signal flow, refer to the [System Architecture Flow](docs/architecture_flow.md) document.

### Workflow Components

* **Watcher Layer**: Owns domain-specific market analysis (trend, volatility, liquidity, order-flow, regime); emits raw market observations; health monitoring, auto-restart, signal validation, symbol filtering
* **Engine Layer** (`EngineService`): The single canonical engine — interprets each raw market observation into an `InterpretedSignal`. The legacy multi-engine signal-filter chain was retired in E3 and physically removed in E8 (see the Engine System note below).
* **Fusion Layer**: Adaptive weighting and signal aggregation — diversity metrics, explainability, conflict resolution
* **Strategy Layer**: Strategy selection and execution intent; health monitoring, auto-restart, performance tracking
* **Risk Layer**: ATR-based stop-loss/take-profit and position sizing, portfolio risk controls, kill-switch
* **Broker Layer**: Order execution and monitoring

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

All strategies inherit from `BaseStrategyAdapter` (implementing `StrategyPort`) and are fully isolated with enhanced monitoring, dynamic setup scoring, and management capabilities. Strategies operate downstream of `Engine` $\rightarrow$ `Fusion`, taking fused signals or setup engine candidates and converting them into validated `ExecutionIntent` objects with dynamic ATR-based SL/TP levels.

**Base Class Features**
* `BaseStrategyAdapter`: Provides standard technical indicators (`calculate_ema`, `calculate_rsi`, `calculate_atr`), risk parameter management, cooldown tracking, and intent discipline.
* **Dynamic Confidence Scaling**: Confidence is dynamically mapped from candidate setup score ($Score \in [-1, 1]$) into $[0.50, 0.95]$ via $Conf = \min(0.95, \max(0.50, 0.60 + 0.35 \cdot |Score|))$.

**Available Strategies & Their Internal Logic**

1. **TrendFollowStrategyAdapter** (`trend_following`)
   * **Logic**: Moving Average (EMA) Crossover with Momentum & Volume Confirmation.
   * **Mechanism**: Evaluates fast EMA (10/20) against slow EMA (50/200). Generates `BUY` when fast EMA crosses above slow EMA with positive price momentum and ATR above minimum threshold. Generates `SELL` on bearish crossovers.
   * **Risk/Exit**: ATR-based Stop Loss ($1.5 \times \text{ATR}$) and Take Profit ($2.0\text{--}3.0 \times \text{ATR}$).

2. **MeanReversionStrategyAdapter** (`mean_reversion`)
   * **Logic**: Relative Strength Index (RSI) + Bollinger Bands Reversion.
   * **Mechanism**: Monitors price relative to 20-period 2.0$\sigma$ Bollinger Bands and 14-period RSI. Triggers `BUY` when price pierces the lower Bollinger Band with oversold RSI ($< 35$), targeting reversion to the middle SMA. Triggers `SELL` when price pierces upper band with overbought RSI ($> 65$).
   * **Risk/Exit**: SL set beyond recent swing high/low; TP set at middle Bollinger Band (SMA/POC).

3. **BreakoutStrategyAdapter** (`breakout` / `crypto_breakout`)
   * **Logic**: Consolidation Channel & Volume Expansion Breakout.
   * **Mechanism**: Identifies tight consolidation channels over a lookback window. Triggers `BUY` when price breaks above N-period resistance with volume exceeding $1.5\times$ moving average volume. Triggers `SELL` when breaking below support.
   * **Risk/Exit**: SL placed inside consolidation channel; TP set at multi-R expansion level.

4. **DonchianBreakoutStrategyAdapter** (`donchian_breakout`)
   * **Logic**: Donchian Channel High/Low Channel Expansion.
   * **Mechanism**: Computes N-period highest high and lowest low (Donchian Channels). Triggers `BUY` on fresh break of upper channel; triggers `SELL` on break of lower channel.
   * **Risk/Exit**: ATR-scaled stop loss and channel width expansion profit targets.

5. **LiquidityStrategyAdapter** (`liquidity`)
   * **Logic**: Liquidity Pool Sweep & Stop-Hunt Reversal.
   * **Mechanism**: Detects stop-loss sweeps beyond key equal highs/lows or liquidity pools. Triggers `BUY` when price sweeps below support and immediately reclaims the level within the bar (false breakdown / spring). Triggers `SELL` when price sweeps above resistance and rejects (upthrust).
   * **Risk/Exit**: Tight SL placed beyond sweep wick low/high; TP targeted at opposing liquidity pool.

6. **MTFTrendStrategyAdapter** (`mtf_trend`)
   * **Logic**: Multi-Timeframe Trend Consensus Alignment.
   * **Mechanism**: Evaluates trend direction across multiple timeframes (15m, 1h, 4h). Triggers `BUY` only when short, medium, and long timeframes align in unanimous bullish consensus. Triggers `SELL` on unanimous bearish consensus.
   * **Risk/Exit**: Filters out conflicting market regimes; ATR trailing stop.

7. **OIFootprintStrategyAdapter** (`oi_footprint`)
   * **Logic**: Open Interest ($\Delta\text{OI}$) Delta & Volume Footprint Analysis.
   * **Mechanism**: Analyzes Open Interest changes combined with price action:
     * *Long Accumulation* (Price $\uparrow$ + OI $\uparrow$): Bullish continuation signal.
     * *Short Accumulation* (Price $\downarrow$ + OI $\uparrow$): Bearish continuation signal.
     * *Long Liquidation Flush* (Price $\downarrow$ + OI $\downarrow$): Reversal buy setup.
     * *Short Squeeze* (Price $\uparrow$ + OI $\downarrow$): Reversal sell setup.
   * **Risk/Exit**: Structure-based SL beyond liquidation candle extreme; TP set at high-volume nodes.

8. **ShortTermReversalStrategyAdapter** (`short_term_reversal`)
   * **Logic**: Micro-structure Overextension & VWAP Deviation Scalping.
   * **Mechanism**: Monitors short-term price spikes that extend beyond $3\sigma$ standard deviation boundaries from short-term VWAP/EMA. Generates counter-trend scalp signals when volume and tick intensity show exhaustion.
   * **Risk/Exit**: Tight ATR stop loss; TP set back at short-term VWAP mean.

9. **SweepScalperAdapter** (`sweep_scalper`)
   * **Logic**: Order Flow Sweep & Liquidity Vacuum Scalping.
   * **Mechanism**: Intercepts WebSocket order book sweeps. Identifies aggressive market order series eating through multiple price levels. Emits rapid momentum scalp signals or fade signals when large limit absorption orders appear.
   * **Risk/Exit**: Very short holding time; tight tick-based stop loss.

10. **VWAPReversalStrategyAdapter** (`vwap_reversal`)
    * **Logic**: Session VWAP Deviation & Value Area Reversion.
    * **Mechanism**: Computes Session VWAP and Standard Deviation Bands ($\pm 1\sigma, \pm 2\sigma, \pm 3\sigma$) alongside Value Area High (VAH), Value Area Low (VAL), and Point of Control (POC). Triggers `BUY` when price extends below $-2\sigma / -3\sigma$ VWAP or VAL with bullish candle confirmation. Triggers `SELL` above $+2\sigma / +3\sigma$ VWAP or VAH.
    * **Risk/Exit**: SL set outside extreme deviation band; TP set at Session VWAP / POC.

11. **VolatilityBreakoutStrategy** (`volatility_breakout`)
    * **Logic**: Volatility Squeeze (Bollinger inside Keltner) & Expansion Breakout.
    * **Mechanism**: Identifies periods where Bollinger Bands contract inside Keltner Channels (volatility squeeze). Triggers signals when price breaks out of the channel with expanding ATR.
    * **Risk/Exit**: Dynamic Keltner Channel stop loss and trailing ATR profit targets.

---

### Strategy Management System

* `StrategyManager` – Comprehensive strategy lifecycle management, health monitoring, dynamic registration, and performance-ranked capital allocation (`PerformanceRankedStrategySelector`).
* `StrategyHealthMonitor` – Real-time performance tracking (win rate, Sharpe, drawdown, expectancy) with auto-restart upon runtime failure.
* Dynamic registration and resource optimization.

### Signal Processing System

* `SignalConflictResolver` – Advanced conflict resolution algorithms for opposing strategy signals.
* `SignalValidator` – Comprehensive signal validation with reliability weighting.
* Adaptive signal weighting based on historical watcher accuracy.

### Engine System

* **`EngineService`** is the single, canonical engine layer. It transforms each raw `MarketObservation` emitted by a watcher into an `InterpretedSignal` (direction, strength, confidence) that Fusion consumes.
* Exposed to the rest of the system behind `EnginePort` via the pure-delegation `EngineServiceAdapter` — not a per-signal engine chain.

> **Retired in E3/E8 — legacy multi-engine chain.** The old "signal-filter chain" engines (`TrendEngine`, `VolatilityEngine`, `CorrelationEngine`, `OrderFlowEngine`, `LiquidityEngine`, `MLWeightEngine`, `ATRRiskEngine`, `RegimeEngine`) were never wired into the live path and were physically removed in E8. Their responsibilities now live in the layers that actually own them: **Watchers** (domain-specific market analysis), **Fusion** (adaptive weighting / aggregation), **Risk** (ATR & risk controls) and the **regime classifier**. **Correlation / pairs (cointegration) trading is deferred to a future backlog epic.**

### Fusion System

* `FusionService` / `AdvancedFusionWeighting` – Adaptive weighting and signal aggregation with diversity metrics.
* Enhanced explainability and conflict resolution.
* Market regime awareness and correlation adjustment.

### Watcher System

The Watcher layer **owns domain-specific market analysis**. Each watcher runs independently, monitors market streams, and emits raw `MarketObservation` objects into the pipeline (which `EngineService` then interprets into signals).

**Available Watchers & Their Internal Logic**

1. **HistoricalCandleWatcherAdapter** (`historical_candle`)
   * **Logic**: Candlestick Pattern Recognition & Price Action Analysis.
   * **Mechanism**: Analyzes historical OHLCV candle buffers for key candlestick patterns: Doji (indecision), Bullish/Bearish Engulfing (reversal), Hammer / Inverted Hammer, Spinning Tops, and Small Body candles using adaptive body-to-wick ratio thresholds.
   * **Observation**: Emits candle pattern type, trend context, and pattern confidence score.

2. **MarketPulseWatcher** (`market_pulse`)
   * **Logic**: Multi-Indicator Sentiment & Momentum Pulse Analysis.
   * **Mechanism**: Combines momentum, trend, and volume sub-scores using RSI (overbought $>65$, oversold $<35$), MACD histogram crossovers, and volume spike detection ($>1.5\times$ avg volume).
   * **Observation**: Emits composite `market_pulse` observation with direction, momentum score, and volume surge flags.

3. **VolatilityWatcher** (`volatility`)
   * **Logic**: Volatility Regime & ATR Expansion/Compression Detection.
   * **Mechanism**: Calculates Average True Range (ATR) and price standard deviation over lookback windows. Classifies market into `high` (expansion threshold $>1.5\times$ avg), `low` (compression threshold $<0.5\times$ avg), or `normal` volatility regimes.
   * **Observation**: Emits `volatility_expansion` or `volatility_compression` observations with regime magnitude and confidence.

4. **TrendMTFWatcher** (`trend_mtf`)
   * **Logic**: Multi-Timeframe Trend Direction & Alignment Analysis.
   * **Mechanism**: Computes price trend direction and slope across 3 distinct windows (short e.g. 5 periods, medium e.g. 15 periods, long e.g. 30 periods). Calculates trend alignment score across all timeframes.
   * **Observation**: Emits `trend_positive`, `trend_negative`, or `trend_neutral` observations with alignment consistency metric.

5. **AnomalyMLWatcher** (`anomaly_ml`)
   * **Logic**: Statistical & Machine Learning Anomaly Detection.
   * **Mechanism**: Normalizes price, volume, and volatility features (Z-score standardization). Uses statistical outlier detection / Isolation Forest scoring to identify unusual price spikes, flash dumps, or abnormal volume surges exceeding threshold ($>0.6$).
   * **Observation**: Emits `anomaly_detected` observation with anomaly magnitude and cooldown tracking.

6. **OrderFlowWSWatcher** (`orderflow_ws`)
   * **Logic**: Real-Time Order Book Imbalance & WebSocket Trade Flow Delta.
   * **Mechanism**: Processes live WebSocket order book depth and trade executions. Computes aggressive buy volume vs aggressive sell volume, order book bid/ask volume imbalance, and tick flow direction.
   * **Observation**: Emits `order_flow_imbalance` or `order_flow_neutral` observations with buy/sell delta ratio.

7. **CMCScreener** (`cmc_screener`)
   * **Logic**: Market-Wide CoinMarketCap Screener & Universe Observation.
   * **Mechanism**: Queries CoinMarketCap API for top crypto assets. Filters by 24h volume, price momentum, market cap rank, and volume surges to evaluate market-wide breadth and select top universe candidates.
   * **Observation**: Emits `universe_screening` observations detailing top volume gainers and market sentiment.

8. **FundingRateWatcher** (`funding_rate`)
   * **Logic**: Perpetual Contract Funding Rate & Position Crowding Analysis.
   * **Mechanism**: Tracks 8-hour perpetual funding rates. Identifies extreme positive funding ($>0.5\%\text{--}1.0\%$, indicating heavy long crowding) or extreme negative funding ($<-0.5\%$, indicating heavy short crowding).
   * **Observation**: Emits `funding_rate_extreme` observations highlighting short/long squeeze conditions.

9. **LiquidityWatcher** (`liquidity`)
   * **Logic**: Order Book Depth & Liquidity Density Analysis.
   * **Mechanism**: Evaluates order book bid/ask depth score, bid-ask spread percentage, and liquidity ratio across top order book levels to detect thin liquidity or thick wall absorption.
   * **Observation**: Emits `high_liquidity` or `low_liquidity` observations with depth score and spread metrics.

10. **TickWatcherAdapter** (`tick`)
    * **Logic**: Micro-Structure Tick Intensity & Imbalance Tracking.
    * **Mechanism**: Analyzes tick-by-tick price changes, tick sizes, and tick directions (up-tick vs down-tick). Calculates tick intensity (ticks per second) and tick imbalance ratio.
    * **Observation**: Emits `high_tick_intensity` or `tick_imbalance` observations for micro-structure scalping.

### Complete Workflow Integration

* **Watcher → Engine → Fusion → Strategy → Broker** flow with full monitoring.
* End-to-end error isolation, auto-restart health management, and performance tracking across all system components.
* `WatcherManager` and `StrategyManager` for centralized lifecycle management.
* Adaptive threshold adjustments based on market conditions.

### Enhanced System Components

The system now includes advanced enhancements across all core components:

#### Advanced Risk Management
* **Regime-Adaptive Risk**: Risk parameters automatically adjust based on market regime detection
* **Correlation-Aware Positioning**: Risk allocation considers correlation with existing positions
* **Drawdown-Sensitive Controls**: Risk scales down during drawdown periods to preserve capital
* **Volatility-Normalized Position Sizing**: Position sizes adjust based on asset volatility levels

#### Probabilistic Position Sizing
* **Evidence-Weighted Approach**: Position sizes based on multiple evidence sources (fusion confidence, regime accuracy, strategy expectancy)
* **Mathematical Formula**: Position_Size = (Portfolio_Equity * Base_Risk * Confidence_Product * Regime_Adjustment * Correlation_Penalty) / Risk_Distance
* **Dynamic Adjustment**: Sizes adjust based on real-time market conditions and performance

#### Advanced SL/TP Logic
* **Volatility-Normalized Levels**: Stop loss and take profit levels adjust based on ATR and volatility
* **Structure-Aware Placement**: Levels consider support/resistance levels for optimal placement
* **Regime-Adaptive Distances**: SL/TP distances vary based on market regime (trending vs ranging vs volatile)
* **Priority-Based Execution**: Stop loss takes priority over take profit for simultaneous hits to preserve capital
* **Realistic Market Dynamics**: Proper handling of simultaneous SL/TP hits with realistic order execution priority
* **Market Structure Validation**: Ensures SL/TP levels respect key technical levels (support/resistance)
* **Dynamic Trailing Stops**: ATR-based trailing stops that adapt to market volatility
* **Realistic Level Validation**: Comprehensive validation ensuring SL/TP levels are achievable and reasonable

#### Adaptive Fusion Weighting
* **Performance-Adaptive Weights**: Signal weights update based on recent performance
* **Correlation-Penalizing**: Highly correlated signals receive reduced weights to promote diversification
* **Stability Rewards**: Consistent performers receive bonus weights
* **Noise Suppression**: Volatile signals receive reduced weights to suppress noise

#### Advanced Regime Classification
* **Confidence Scoring**: Each regime classification includes confidence level
* **Veto Mechanisms**: Low-confidence classifications are vetoed to prevent poor decisions
* **Maturity Tracking**: System tracks how long a regime has persisted
* **Recalibration Logic**: System adjusts classification based on prediction accuracy
* **Confusion Matrix Feedback**: Performance feedback improves future classifications

#### Intelligent Strategy Selection
* **Performance-Ranking**: Strategies ranked by risk-adjusted returns and recent performance
* **Regime Compatibility**: Strategies matched to current market regime
* **Risk-Adjusted Selection**: Selection considers risk-adjusted returns, not just raw returns
* **Promotion/Demotion Rules**: Underperforming strategies are demoted, top performers promoted
* **Suspension Mechanisms**: Poor-performing strategies are temporarily suspended

#### Profitability Enhancement Techniques
* **Variance Reduction**: Techniques to reduce return volatility while maintaining returns
* **Expectancy Compounding**: Multiple factors combine to enhance expected returns
* **Selective Trade Filtering**: Only high-probability trades are executed
* **Capital Efficiency Improvements**: Better utilization of available capital
* **Signal Timing Refinement**: Optimal entry/exit timing based on market microstructure

---

## Prerequisites

* Python **3.10+**
* **Redis Server** (required for caching and IPC)
* pip
* 8GB RAM recommended (for optimization)
* Exchange API keys (optional for backtesting)

---

## Installation

```bash
git clone git@github.com:mrahbari/lynxion-ets.git
cd lynxion-ets

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install core dependencies
pip install --upgrade pip setuptools
pip install -r requirements.txt

# Critical: Install pydantic (required for configuration) 
# and fix hyperopt compatibility by downgrading setuptools
pip install pydantic pydantic-settings
pip install "setuptools<70.0.0"
```

---

## Environment Setup

1. **Configure Environment Variables**:
```bash
cp .env.example .env
```
Edit `.env` to include your exchange API keys and Redis URL (default: `redis://localhost:6379/0`).

2. **Ensure Redis is Running**:
The system requires a running Redis instance.
```bash
# On Linux/Ubuntu:
sudo service redis-server start
# Or using Docker:
docker run -d -p 6379:6379 redis
```

---

## Quick Verification

Before running the full system, verify your configuration and dependencies:

```bash
# Activate venv if not already active
source venv/bin/activate

# Run the config-test mode
python run_trading_system.py --mode config-test
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

The system supports 11 specialized strategies defined in the StrategyType enum, each optimized for its design timeframe:

* **Sweep Scalper (`sweep_scalper`)** [Timeframe: `1m`] – Sweeping liquidity strategy
* **Scalping (`scalping`)** [Timeframe: `1m` / `5m`] – Short-term quick profit strategy
* **Liquidity (`liquidity`)** [Timeframe: `5m`] – Based on liquidity and volume patterns
* **VWAP Reversal (`vwap_reversal`)** [Timeframe: `5m`] – VWAP-based reversal strategy
* **Breakout (`breakout`)** [Timeframe: `15m`] – Identifies resistance/support breakouts
* **Volatility Breakout (`volatility_breakout`)** [Timeframe: `15m`] – Captures price movements during volatility expansion
* **MTF Trend (`mtf_trend`)** [Timeframe: `15m`] – Multi-timeframe trend following (using `5m`, `15m`, and `1h` inputs)
* **Trend Following (`trend_following`)** [Timeframe: `1h`] – Follows trending market movements
* **Mean Reversion (`mean_reversion`)** [Timeframe: `1h`] – Bets on price returning to mean
* **OI Footprint (`oi_footprint`)** [Timeframe: `1h`] – Order interest footprint analysis
* **Momentum (`momentum`)** [Timeframe: `1h`] – Capitalizes on momentum patterns and rate of change

Additionally, the system includes the `crypto_breakout` strategy [Timeframe: `15m`] for compatibility with existing examples.

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

### Comprehensive Integration Testing

The system includes comprehensive integration tests to validate all enhanced components:

```bash
python tests/integration_tests.py
```

This test suite validates:

1. **Adaptive Risk Manager**: Regime-adaptive, correlation-aware, drawdown-sensitive, and volatility-normalized features
2. **Probabilistic Position Sizing**: Evidence-weighted approach with fusion confidence and regime accuracy
3. **Advanced SL/TP Logic**: Volatility-normalized and structure-aware stop loss/take profit levels
4. **Adaptive Fusion Weighting**: Performance-adaptive, correlation-penalizing, stability-rewarding, and noise-suppressing features
5. **Advanced Regime Classification**: Confidence scoring, veto mechanisms, maturity tracking, and confusion matrix feedback
6. **Intelligent Strategy Selection**: Performance-ranking, risk-adjustment, and regime-compatibility with promotion/demotion/suspension rules
7. **Profitability Enhancement**: Variance reduction, expectancy compounding, selective trade filtering, capital efficiency improvements, and signal timing refinement
8. **End-to-End Integration**: Complete workflow validation from signal generation to position management

The integration tests ensure all components work together seamlessly and maintain the high standards required for institutional-grade trading systems.

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
python runner_history_download.py --start 30d --end today --timeframes 1m

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
python runner_multitimeframe_update.py --symbols BTCUSDT --timeframes 5m 15m 30m 1h 4h 1d

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

### Forensic Logging Configuration

The system includes forensic-grade structured logging for complete trade traceability and post-trade analysis:

* `FORENSIC_LOGGING_ENABLED=true/false` - Enable/disable forensic logging (default: true)
  - When enabled: Creates detailed JSON logs in `logs/forensic.log` for each trade
  - When disabled: No forensic logging overhead for performance optimization
  - Controlled via environment variable or code parameter

**Forensic Logging Structure:**
The system captures the complete trading workflow from market perception to final PnL:

```
Watcher → Engine → Fusion → Strategy → Broker → Trade Close
```

Each layer logs structured data with a unique trade ID for complete traceability.

**Performance Considerations:**
- All forensic logging is now controlled by the `FORENSIC_LOGGING_ENABLED` environment variable
- No special execution path required - forensic logging works in all modes
- When `FORENSIC_LOGGING_ENABLED=false`: Zero logging overhead for production performance
- When `FORENSIC_LOGGING_ENABLED=true`: Detailed audit trail for analysis and optimization
- Logs are written to `logs/forensic.log` in JSON format for easy parsing and analysis

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

**ModuleNotFoundError: No module named 'pkg_resources'**

* This is caused by `setuptools` version 70+. Run `pip install "setuptools<70.0.0"` to fix.

**ModuleNotFoundError: No module named 'pydantic'**

* Run `pip install pydantic pydantic-settings` to ensure the configuration system can load.

Logs are available in `logs/`.

---

## Prospective Validation & Live Execution Plan

### 1. Forensic Audit & Cohort Breakdown
During the live prospective validation cohort ($N=100$ trades on BingX VST):
- **Headline Performance ($N=92$)**: 20 Wins / 72 Losses (21.7% Win Rate), Net Realized PnL: `-$111.34 VST`.
- **Forensic Diagnosis**:
  - **Pre-Fix XMR Protective Unwind Defect**: 47 trades, 0 wins, **`-$107.57 VST`** (95% of total losses). Caused by unformatted conditional order precision on BingX triggering repeated protective unwinds with legacy cooldown bypass.
  - **Non-Anomaly Organic Performance (23 Symbols)**: 45 trades, 20 wins, 25 losses, **`+$1.36 VST` (Net Positive Profitability, 47.6% Win Rate)**.

### 2. Live Risk & Position Management Architecture
- **Active Position Trailing Stop Engine (`infrastructure/risk/active_position_manager.py`)**:
  - **Breakeven Protection**: Automatically moves Stop Loss to Entry + 0.1% fee buffer at **+5.0% ROE** (+0.5% price move at 10x leverage).
  - **Dynamic Trailing Stop**: Automatically trails Stop Loss 0.5% behind peak high-water mark price at **+10.0% ROE** (+1.0% price move at 10x leverage), locking in profits.
  - **Clean Single-Exit Execution**: Elimination of partial-closing friction and minimum lot-size constraints.
- **Universal Fail-Closed Cooldown Gate (`infrastructure/risk/symbol_cooldown_gate.py`)**:
  - **60-Minute Lockout**: Enforced on ANY stop-loss exit, negative PnL exit, or protective unwind.
  - **15-Minute Spacing Window**: Enforced even on profitable Take Profit exits to prevent rapid re-entry churn.
  - **Zero Hardcoded Symbols**: 100% dynamic across all 34 perpetual pairs.

### 3. Execution Plan Summary
1. **Complete Cohort 1 ($N = 100$) Audit**:
   - Complete remaining trades to reach $N = 100$ milestone and publish official validation report with dual forensic views (All-Inclusive Raw vs Non-Anomaly Organic Baseline).
2. **Deploy Dynamic 24-Hour Symbol Health Gate**:
   - Automatic 24-hour circuit breaker on any asset experiencing 2 consecutive protective unwinds or rapid losses within 2 hours.
3. **Launch Clean Prospective Cohort 2 ($N = 100$)**:
   - Benchmark the true unpolluted equity curve under the upgraded trailing stop and cooldown engine.

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