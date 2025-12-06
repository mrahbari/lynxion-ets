python run_trading_system.py --mode backtest --strategy crypto_breakout --symbol BTC/USDT --timeframe 1h --days-back 90 --use-opti… │
 │                                                                                                                                              │
 │    🚀 Starting Production Trading Orchestrator in backtest mode...                                                                           │
 │    📊 Running production orchestrator with sample data...                                                                                    │
 │    Dash is running on http://0.0.0.0:8050/                                                                                                   │
 │                                                                                                                                              │
 │     * Serving Flask app 'infrastructure.adapters.live_dashboard'                                                                             │
 │     * Debug mode: off                                                                                                                        │
 │    /usr/local/lib/python3.9/dist-packages/hyperopt/atpe.py:19: UserWarning: pkg_resources is deprecated as an API. See                       │
 │    https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as                      │
 │    2025-11-30. Refrain from using this package or pin to Setuptools<81.                                                                      │
 │      import pkg_resources                                                                                                                    │
 │    2025-12-06 11:15:36,420 - INFO - ProductionTradingOrchestrator - Initializing Production Trading Orchestrator...                          │
 │    2025-12-06 11:15:36,422 - INFO - ProductionTradingOrchestrator - Auto-retune monitoring started                                           │
 │    2025-12-06 11:15:36,422 - INFO - ProductionTradingOrchestrator - Risk monitoring started                                                  │
 │    2025-12-06 11:15:36,423 - INFO - LiveDashboardAdapter - Starting dashboard server on port 8050                                            │
 │    2025-12-06 11:15:36,423 - INFO - ProductionTradingOrchestrator - Performance monitoring started                                           │
 │    2025-12-06 11:15:36,423 - INFO - ProductionTradingOrchestrator - Started 4 background services                                            │
 │    2025-12-06 11:15:36,424 - INFO - ProductionTradingOrchestrator - Production Trading Orchestrator initialized successfully                 │
 │    2025-12-06 11:15:36,425 - INFO - ProductionTradingOrchestrator - Added strategy crypto_breakout for symbols: []                           │
 │    2025-12-06 11:15:36,425 - INFO - ProductionTradingOrchestrator - Starting production trading for strategy: crypto_breakout                │
 │    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.                    │
 │     * Running on all addresses (0.0.0.0)                                                                                                     │
 │     * Running on http://127.0.0.1:8050                                                                                                       │
 │     * Running on http://192.168.8.17:8050  
 
 
 
 Run one by one and try to fix them:
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
# Backtest multiple symbols
python run_trading_system.py --mode backtest \
  --strategy crypto_breakout \
  --symbols BTC/USDT,ETH/USDT,SOL/USDT \
  --timeframe 1h \
  --days-back 180
```

#### **Backtest with Custom Parameters**
```bash
python run_trading_system.py --mode backtest \
  --strategy crypto_breakout \
  --symbol BTC/USDT \
  --config "custom_backtest_config.json"
```
