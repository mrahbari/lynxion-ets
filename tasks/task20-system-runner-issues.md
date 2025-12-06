
 
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
# Optimize multiple strategies for different symbols
python run_trading_system.py --mode optimize \
  --strategy crypto_breakout \
  --symbols BTC/USDT,ETH/USDT,SOL/USDT \
  --timeframe 1h \
  --max-evals 200
```