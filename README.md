# Lynx Hedge Fund Trading System

## Overview

This is an enterprise-grade hedge fund trading system implementing modern software architecture patterns with advanced optimization capabilities. The system follows hexagonal architecture principles and includes comprehensive optimization with hyperopt integration. The system implements the full workflow: **Watcher → Engine → Fusion → Strategy → Broker** with auto-retune capabilities.

## Key Features

- Hexagonal Architecture (Clean Architecture)
- Advanced Hyperparameter Optimization with Hyperopt
- Live Trading Capabilities
- Comprehensive Risk Management
- Auto-Retune System
- Auto-Detection System with Market Monitoring
- Dynamic Symbol Discovery and Selection
- Multi-Asset Support (Crypto, FX, Metals, Indices)
- Realistic Backtesting with Slippage/Fees
- Live Dashboard with Performance Monitoring
- Automated Retuning Capabilities

## 🚀 Complete System Manual

### **System Overview**

Your Hedge Fund trading system is built on **hexagonal architecture** following enterprise-grade standards. The core workflow:

```
Watcher → Engine → Fusion → Strategy → Broker
  ↓         ↓        ↓        ↓        ↓
Market    Risk    Signal   Strategy  Live Execution
Data      Aware   Fusion   Scalper   & Risk Control
Monitor   Engine  Service  w/Retune  w/Alerts
```

### **Auto-Detection System**

The system features an auto-detection capability that enables fully autonomous trading operations. The system continuously monitors markets, identifies opportunities based on technical conditions and market states, and automatically executes appropriate strategies with proper risk management.

**Key Capabilities:**
- **Continuous Market Monitoring**: Multiple watcher types (MarketPulse, Volatility, TrendMTF, AnomalyML, OrderFlow, CMC) continuously scan the markets for opportunities
- **CMC Market Intelligence**: Integrates with CoinMarketCap API to analyze market sentiment, identify high-growth potential coins, and detect crash-risk assets
- **Dynamic Symbol Discovery**: Automatically identifies and monitors the most promising trading symbols using CMC data and market screening (BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, ADA/USDT) based on market conditions
- **Intelligent Strategy Selection**: Dynamically chooses the most appropriate strategy (momentum, trend-following, mean-reversion, volatility-based, order-flow, CMC sentiment) based on detected opportunities
- **Automated Execution**: Executes trades automatically when opportunities meet predefined criteria and confidence thresholds
- **Comprehensive Risk Management**: All automated trades are subject to real-time risk controls, position sizing, and monitoring
- **Multi-Timeframe Analysis**: Analyzes market conditions across multiple timeframes (1h, 4h, 1d) for robust signal generation
- **Signal Fusion**: Combines signals from multiple watcher types using intelligent fusion algorithms
- **Market Regime Detection**: Automatically adapts strategy selection based on current market conditions and volatility regimes

**Usage:**
```bash
# Run in auto-detection mode with auto-discovered symbols
python run_trading_system.py --mode production --auto-detect

# Run in auto-detection mode with specific symbols
python run_trading_system.py --mode production --auto-detect --symbols BTC/USDT,ETH/USDT

# Run in auto-detection mode with risk configuration
python run_trading_system.py --mode production --auto-detect --symbols BTC/USDT,ETH/USDT --max-evals 50
```

**Auto-Detection Architecture:**
```
Watcher → Engine → Fusion → Strategy → Broker
  ↓         ↓        ↓        ↓        ↓
Market    Risk    Signal   Strategy  Live Execution
Data      Aware   Fusion   Scalper   & Risk Control
Monitor   Engine  Service  w/Retune  w/Alerts
```

The auto-detection mode implements the complete workflow where watchers continuously monitor market conditions, engines process signals with risk awareness, fusion services combine multiple signals, strategies execute trades, and brokers handle live execution with comprehensive risk controls.

### **Setup & Configuration**

#### **Environment Setup**
```bash
# 1. Clone and navigate to project
cd /path/to/hedge_fund

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create necessary directories
mkdir -p logs data/cache data/results data/coin_history_cache data/optimization_results

# 4. Copy and configure .env file
cp .env.example .env
```

#### **Configuration File (`config/hyperopt_autotune_config.json`)**
```json
{
  "data": {
    "cache_dir": "data/cache",
    "coin_history_cache_dir": "data/coin_history_cache",
    "results_db_path": "data/results.db",
    "results_storage_dir": "data/results_storage",
    "max_cache_age_hours": 24,
    "max_coin_cache_size": 50
  },
  
  "optimization": {
    "max_evals": 100,
    "algorithm": "tpe",
    "early_stopping_rounds": 20,
    "validation_split": 0.2,
    "objective_metric": "sharpe_ratio"
  },
  
  "trading": {
    "initial_capital": 1000000,
    "fee_rate": 0.001,
    "slippage_factor": 0.0005,
    "max_risk_per_trade": 0.02,
    "max_position_size": 0.20,
    "max_drawdown_threshold": -0.15,
    "max_leverage": 10.0
  },
  
  "retune": {
    "enabled": true,
    "interval_hours": 6,
    "performance_threshold": 0.15,
    "evals_per_retune": 20
  },
  
  "live_trading": {
    "enabled": false,
    "broker_api_key": "",
    "broker_secret": "",
    "demo_mode": true
  }
}
```

### **Backtesting**

#### **Single Strategy Backtest**
```bash
# Run backtest for a specific strategy and symbol
python run_trading_system.py --mode backtest \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --timeframe 1h \
  --days-back 90 \
  --use-optimized-params
```

#### **Batch Backtesting**
```bash
# Backtest a strategy for a single symbol (multi-symbol backtesting coming soon)
# Current implementation only processes a single symbol
python run_trading_system.py --mode backtest \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --timeframe 1h \
  --days-back 90
```

**Note**: The current implementation only backtests for a single symbol. Multi-symbol backtesting functionality is planned for future releases.

#### **Backtest with Custom Parameters**
```bash
python run_trading_system.py --mode backtest \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --config "application/configs/backtest_config.json"
```

#### **Custom Backtest Configuration**
```json
{
  "strategy": "crypto_breakout",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "initial_capital": 100000,
  "fee_rate": 0.001,
  "slippage_factor": 0.0005,
  "parameters": {
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "atr_period": 14,
    "atr_multiplier": 2.0,
    "position_size": 0.1
  },
  "risk_config": {
    "max_risk": 0.02,
    "stop_loss_atr": 2.0,
    "take_profit_atr": 3.0
  }
}
```

### **Coin History Updates**

#### **Automatic History Updates**
```bash
# Update coin history automatically (this runs continuously)
python run_coin_updater.py --update-all --interval-minutes 60
```

#### **Manual History Update**
```bash
# Update specific coins
python run_coin_updater.py --coins BTC,ETH,SOL --update-hours 24
```

#### **Update Script Options**
```bash
# Update with specific settings
python run_coin_updater.py \
  --coins BTC/USDT,ETH/USDT \
  --timeframes 1m,5m,15m,1h,4h,1d \
  --update-days 365 \
  --force-update \
  --verify-data
```

#### **Coin Updater Configuration**
```json
{
  "data": {
    "coin_cache_dir": "data/coin_history_cache",
    "max_cache_age_hours": 24,
    "max_cache_size": 50,
    "default_timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
  },
  "update": {
    "batch_size": 10,
    "request_delay": 0.1,
    "retries": 3,
    "verify_checksums": true
  },
  "sources": {
    "primary_exchange": "binance",
    "backup_exchanges": ["bybit", "kucoin"],
    "api_keys": {
      "binance": "your_binance_api_key"
    }
  }
}
```

### **Hyperparameter Optimization**

#### **Single Strategy Optimization**
```bash
# Optimize a specific strategy
python run_trading_system.py --mode optimize \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --timeframe 1h \
  --max-evals 100 \
  --days-back 30
```

#### **Multi-Strategy Optimization**
```bash
# Optimize a strategy for a single symbol (multi-symbol optimization coming soon)
# Current implementation only processes the first symbol provided
python run_trading_system.py --mode optimize \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --timeframe 1h \
  --max-evals 100
```

**Note**: The current implementation only optimizes for a single symbol. Multi-symbol optimization functionality is planned for future releases.

#### **Advanced Hyperopt Features**

##### **Custom Hyperopt Space**
```python
# Define custom parameter space in hyperopt_space.py
from hyperopt import hp
from shared.utils import Range

space = {
    # Trend parameters
    'fast_ma': hp.quniform('fast_ma', 5, 30, 1),
    'slow_ma': hp.quniform('slow_ma', 20, 120, 1),
    
    # Momentum parameters  
    'rsi_period': hp.quniform('rsi_period', 5, 30, 1),
    'rsi_overbought': hp.quniform('rsi_overbought', 60, 90, 1),
    'rsi_oversold': hp.quniform('rsi_oversold', 10, 40, 1),
    
    # Volatility parameters
    'atr_period': hp.quniform('atr_period', 5, 40, 1),
    'atr_multiplier_sl': hp.uniform('atr_multiplier_sl', 1.0, 5.0),
    'atr_multiplier_tp': hp.uniform('atr_multiplier_tp', 1.0, 8.0),
    
    # Position sizing parameters
    'risk_per_trade': hp.uniform('risk_per_trade', 0.001, 0.05),
    'max_position_size': hp.uniform('max_position_size', 0.01, 0.5),
    
    # Execution parameters
    'signal_smoothing': hp.uniform('signal_smoothing', 0.1, 1.0),
    'min_volume_filter': hp.uniform('min_volume_filter', 0, 5),
    
    # Advanced parameters
    'dynamic_risk_weight': hp.uniform('dynamic_risk_weight', 0.1, 2.0),
    'volatility_position_scale': hp.uniform('volatility_position_scale', 0.1, 3.0)
}
```

##### **Objective Function with Multiple Metrics**
```python
def hyperopt_objective(params, data_dict, risk_config):
    """
    Custom objective function combining multiple metrics
    """
    total_score = 0
    
    for asset_name, df in data_dict.items():
        # Run backtest with parameters
        result = run_backtest_with_params(df, params)
        
        # Calculate multiple performance metrics
        sharpe = result.get('sharpe_ratio', 0)
        win_rate = result.get('win_rate', 0)
        total_return = result.get('total_return', 0)
        max_drawdown = abs(result.get('max_drawdown', 0))
        profit_factor = result.get('profit_factor', 1.0)
        
        # Weighted scoring formula
        score = (
            sharpe * 2.0 +           # Sharpe ratio weight (most important)
            win_rate * 0.5 +         # Win rate contribution
            total_return * 5.0 +     # Total return contribution
            -max_drawdown * 3.0 +    # Drawdown penalty (negative = larger penalty)
            profit_factor * 0.5      # Profit factor contribution
        )
        
        # Apply constraints to prevent overfitting
        if result.get('total_trades', 0) < 10:
            score -= 100  # Heavy penalty for strategies with too few trades
            
        total_score += score
    
    return {'loss': -total_score, 'status': 'ok'}
```

### **Hyperopt with Constraints**
```bash
# Run hyperopt with performance constraints
python run_trading_system.py --mode optimize \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --max-evals 150 \
  --constraints "min_trades=20,min_sharpe=0.5,max_drawdown=0.1"
```

### **Hyperopt Results Analysis**
```bash
# View optimization results
python -c "
from shared.results_tracker import ResultsTracker
tracker = ResultsTracker()
results = tracker.get_hyperopt_results('crypto_breakout', 'BTC/USDT', limit=10)
for result in results:
    print(f'Params: {result[\"parameters\"]}')
    print(f'Sharpe: {result[\"sharpe_ratio\"]}')
    print(f'Return: {result[\"total_return\"]}')
    print('---')
"
```

### **Auto-Retune System**

#### **Auto-Retune Modes**

##### **Scheduled Auto-Retune**
```bash
# Run system with automatic re-tuning every 6 hours
python run_trading_system.py --mode production \
  --retune-interval-hours 6 \
  --evals-per-retune 20 \
  --performance-threshold 0.15
```

##### **Continuous Auto-Retune**
```bash
# Start continuous monitoring and re-tuning
python run_auto_retune.py --continuous \
  --check-interval-minutes 60 \
  --performance-metrics "sharpe_ratio,win_rate,max_drawdown" \
  --retune-threshold -0.10
```

### **Auto-Retune Configuration**
```json
{
  "auto_retune": {
    "enabled": true,
    "interval_hours": 6,
    "evals_per_cycle": 20,
    "performance_threshold": -0.05,
    "minimum_trades": 10,
    "retraining_window_days": 30,
    "validation_split": 0.2,
    
    "trigger_conditions": {
      "sharpe_decline": 0.2,
      "drawdown_exceeded": -0.10,
      "win_rate_drop": 0.40,
      "profit_factor_deterioration": 0.2
    },
    
    "safety_filters": {
      "maximum_evaluations": 50,
      "minimum_improvement": 0.01,
      "consecutive_failure_limit": 3,
      "time_between_runs_minutes": 30
    }
  }
}
```

### **Auto-Retune Monitoring**
```bash
# Monitor auto-retune performance
python -c "
from shared.auto_retune_manager import AutoRetuneManager
manager = AutoRetuneManager()
status = manager.get_retune_status()
print(f'Next retune in: {status[\"next_retune\"]}')
print(f'Last performance: {status[\"last_performance\"]}')
print(f'Active strategies: {status[\"active_strategies\"]}')
"
```

### **Live Trading Setup**

#### **Demo Mode (Simulated Trading)**
```bash
# Test live trading in demo mode
python run_trading_system.py --mode production \
  --demo-mode \
  --strategy crypto_breakout \
  --symbols BTC/USDT,ETH/USDT \
  --max-position-size 0.05 \
  --risk-per-trade 0.01
```

#### **Live Trading Configuration**
```json
{
  "live_trading": {
    "enabled": true,
    "broker": {
      "name": "binance",
      "api_key": "your_live_api_key",
      "secret": "your_live_secret",
      "sandbox_mode": false,
      "timeout": 30
    },
    "risk_management": {
      "max_daily_loss": 0.02,
      "max_position_size": 0.10,
      "max_leverage": 5.0,
      "max_correlation": 0.6,
      "max_drawdown": -0.15,
      "max_trades_per_day": 50
    },
    "execution": {
      "order_types": ["limit", "market", "stop_loss"],
      "slippage_tolerance": 0.005,
      "min_order_size": 10,
      "max_order_size": 100000
    },
    "monitoring": {
      "alert_frequency_minutes": 5,
      "email_notifications": true,
      "telegram_notifications": true,
      "alert_webhook_url": "https://your-alert-webhook.com"
    }
  }
}
```

#### **Live Trading Startup**
```bash
# Start live trading with full functionality
python run_trading_system.py --mode production \
  --live-trading \
  --strategy crypto_breakout \
  --symbols BTC/USDT,ETH/USDT,SOL/USDT,XRP/USDT \
  --timeframe 5m \
  --config "live_trading_config.json"
```

**Note on Strategy Selection and Watchers**:
While the current implementation takes strategies and symbols as command-line parameters, in a fully automated setup, the system's Watcher components would monitor market conditions and recommend optimal strategies and instruments to the Orchestrator. The Orchestrator would then execute those recommendations automatically. The parameterized approach provides manual control for initial deployment and testing phases, but could be replaced with automated instrument and strategy selection in future implementations.

#### **Watcher-Based Strategy Activation**
```bash
# In a fully automated setup, the system would run with automated strategy selection
python run_trading_system.py --mode production \
  --live-trading \
  --auto-select-strategy \
  --watcher-monitoring \
  --timeframe 5m \
  --config "live_trading_config.json"
```

In this mode, the system would:
- Continuously monitor market conditions via Watcher components
- Automatically select appropriate strategies based on market opportunity detection
- Dynamically allocate capital across detected opportunities
- Apply appropriate risk management per strategy and symbol

### **System Architecture & Component Roles**

#### **Watcher Components**
Watchers continuously monitor market data and generate signals based on predefined conditions. They are responsible for:
- Real-time market data analysis
- Opportunity identification
- Strategy recommendation based on market patterns
- Risk threshold monitoring

#### **Orchestrator Components**
The orchestrator manages strategy execution and coordinates between different system components. Its responsibilities include:
- Receiving recommendations from watchers
- Managing strategy lifecycle (start/stop/reconfigure)
- Coordinating execution engines
- Applying risk management rules

#### **Current Implementation vs Future State**
- **Current**: Strategies and symbols are configured via command line parameters for predictable and controlled operation
- **Future State**: Watchers would automatically recommend strategies/symbols to orchestrators based on market opportunities
- **Architecture Flexibility**: The hexagonal architecture allows for easy transition between these modes

### **Safety Checks Before Going Live**
```python
# Pre-flight safety check
python -c "
from shared.safety_checker import SafetyChecker
checker = SafetyChecker()
issues = checker.perform_pre_flight_check()
if issues:
    print('❌ Safety issues found:')
    for issue in issues:
        print(f'  - {issue}')
else:
    print('✅ All safety checks passed!')
"
```

### **Monitoring & Dashboard**

#### **Live Dashboard Access**
```bash
# Start monitoring dashboard
python run_dashboard.py --port 8050
# Then visit: http://localhost:8050
```

#### **Dashboard Features**
- Real-time P&L tracking
- Strategy performance metrics
- Risk exposure monitoring
- Trade execution logs
- Auto-retune status
- Market data visualization

#### **API Access to Metrics**
```bash
# Get current system status
curl http://localhost:8050/api/status

# Get strategy performance
curl http://localhost:8050/api/performance/crypto_breakout

# Get risk metrics
curl http://localhost:8050/api/risk/overview
```

#### **Automated Reports**
```bash
# Generate daily performance report
python run_reports.py --report daily --output reports/daily_$(date +%Y%m%d).pdf

# Generate weekly strategy comparison
python run_reports.py --report weekly_comparison --output reports/weekly_$(date +%Y%m%d).pdf

# Generate risk report
python run_reports.py --report risk_summary --output reports/risk_$(date +%Y%m%d).pdf
```

### **Risk Management**

#### **Risk Configuration**
```json
{
  "risk_management": {
    "portfolio": {
      "max_total_exposure": 1.0,
      "max_correlation_between_assets": 0.6,
      "max_daily_loss": 0.02,
      "max_total_drawdown": -0.15
    },
    "position": {
      "max_position_size": 0.20,
      "max_leverage": 10.0,
      "max_stop_distance": 0.10,
      "min_atr_multiplier": 1.0
    },
    "strategy": {
      "max_drawdown": -0.15,
      "min_sharpe_ratio": 0.3,
      "min_win_rate": 0.45,
      "max_consecutive_losses": 5
    },
    "execution": {
      "max_slippage": 0.005,
      "max_order_iceberg_ratio": 0.1,
      "min_time_between_orders": 10,
      "max_daily_orders": 100
    }
  }
}
```

#### **Risk Monitoring Commands**
```bash
# Check current risk exposure
python -c "
from shared.risk_monitor import RiskMonitor
monitor = RiskMonitor()
exposure = monitor.get_portfolio_exposure()
print(f'Current exposure: {exposure[\"total_exposure\"]:.2%}')
print(f'Drawdown: {exposure[\"current_drawdown\"]:.2%}')
print(f'Leverage: {exposure[\"current_leverage\"]:.2f}x')
"

# Run risk scan
python run_risk_scan.py --scan-type comprehensive
```

#### **Emergency Controls**
```bash
# Emergency stop all trading
python run_emergency_control.py --action stop-all --reason "emergency_stop"

# Cancel all open orders
python run_emergency_control.py --action cancel-orders --reason "risk_limit_exceeded"

# Liquidate positions
python run_emergency_control.py --action liquidate --reason "system_issue"
```

### **Troubleshooting**

#### **Common Issues & Solutions**

##### **Issue: "No Trades Executed"**
```bash
# Solution: Check signal generation
python run_trading_system.py --mode debug \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --debug-level signals
```

##### **Issue: "Optimization Taking Too Long"**
```bash
# Solution: Reduce max_evals and use parameter constraints
python run_trading_system.py --mode optimize \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --max-evals 50 \
  --trials-limit 500
```

##### **Issue: "Memory Issues"**
```bash
# Solution: Enable memory optimization
python run_trading_system.py --mode production \
  --memory-optimize \
  --garbage-collect-interval 1000
```

#### **Debugging Commands**
```bash
# Verbose logging
python run_trading_system.py --verbose --log-level DEBUG

# System health check
python run_health_check.py --deep-check

# Strategy validation
python run_validation.py --validate-strategy crypto_breakout
```

#### **Log Analysis**
```bash
# View recent errors
tail -f logs/trading_system_*.log | grep ERROR

# View performance metrics
grep "Performance Metrics" logs/trading_system_*.log | tail -10
```

### **Production Deployment**

#### **Docker Deployment**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Expose ports
EXPOSE 8050

CMD ["python", "run_production_system.py", "--mode", "production"]
```

#### **Systemd Service (Linux)**
```ini
[Unit]
Description=Hedge Fund Trading System
After=network.target

[Service]
Type=simple
User=trading
WorkingDirectory=/path/to/hedge_fund
ExecStart=/usr/bin/python3 run_trading_system.py --mode production
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### **Supervisor Configuration**
```ini
[program:hedge_fund]
command=python run_trading_system.py --mode production
directory=/path/to/hedge_fund
user=trading
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/hedge_fund.log
```

#### **Environment Variables**
```bash
# Production environment variables
export HEDGE_FUND_ENV="production"
export DATABASE_URL="postgresql://user:pass@localhost/hedge_fund"
export REDIS_URL="redis://localhost:6379/0"
export LOG_LEVEL="INFO"
export ENABLE_LIVE_TRADING="true"
export BROKER_API_KEY="your_production_key"
export BROKER_SECRET="your_production_secret"
```

### **Quick Start Examples**

#### **1. Basic Backtest**
```bash
python run_trading_system.py --mode backtest --strategy crypto_breakout --symbol BTC/USDT
```

#### **2. Optimize and Backtest**
```bash
python run_trading_system.py --mode optimize --strategy crypto_breakout --symbol BTC/USDT --max-evals 50
python run_trading_system.py --mode backtest --strategy crypto_breakout --symbol BTC/USDT --use-optimized-params
```

#### **3. Auto-Retune Production**
```bash
python run_trading_system.py --mode production --retune-enabled --retune-interval 6 --demo-mode
```

#### **4. Live Trading (TEST FIRST!)**
```bash
python run_trading_system.py --mode production --live-trading --strategy crypto_breakout --demo-mode --max-position-size 0.01
```

### **⚠️ Important Warnings & Safety Notes**

1. **Test in Demo Mode First**: Always test strategies with demo accounts before going live
2. **Start Small**: Begin with small position sizes and gradually increase
3. **Monitor Closely**: Monitor the system actively during the first week of live trading
4. **Have Emergency Plans**: Know how to stop trading immediately if needed
5. **Backup Configurations**: Regularly backup your optimized parameters
6. **Check Market Conditions**: Some strategies may not work during volatile market conditions
7. **Update Dependencies**: Keep your system and dependencies updated

### **Performance Optimization Tips**

1. **Batch Processing**: Use batch processing for large datasets
2. **Caching**: Enable data caching for frequently accessed data
3. **Threading**: Use appropriate threading for I/O operations
4. **Database Indexing**: Ensure proper indexing for results databases
5. **Memory Management**: Use generators for large datasets to avoid memory issues
6. **GPU Acceleration**: Enable GPU acceleration if using complex ML models

## License

MIT