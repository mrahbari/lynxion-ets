# Hedge-Fund Walk-Forward Optimization (WFO) Pipeline

This document provides detailed instructions for using the enterprise-grade Walk-Forward Optimization pipeline designed for hedge-fund level trading system validation.

## 📋 Table of Contents
1. [Overview](#overview)
2. [Components](#components)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Testing Instructions](#testing-instructions)
7. [Results Interpretation](#results-interpretation)

## Overview

The Walk-Forward Optimization (WFO) pipeline provides institutional-grade strategy validation combining:
- Multi-asset, multi-timeframe analysis
- Hyperparameter optimization per asset & per Training Window
- Real Walk-Forward Optimization with Sliding Windows
- Robust Cross-Validation
- Parameter aggregation for robustness
- Comprehensive reporting: equity curves, ROI, drawdown, overfit index
- Ready for Live Trading integration

## Components

### Core Architecture (Hexagonal)
1. **Data Layer**: CSVHistoryLoader, TimeframeResampler, MultiTimeframeMerger
2. **Strategy Layer**: StrategyPort interface, RiskEnginePort interface
3. **Execution Layer**: MarketExecutor, RealisticBacktester 
4. **Optimization Layer**: HyperoptAdapter, MultiAssetOptimizer
5. **Walk-Forward Layer**: SlidingWindowSplitter, MultiAssetWalkForward
6. **Cross-Validation Layer**: CrossValidationEngine
7. **Visualization Layer**: WFVisualizer
8. **Orchestrator**: WFOOrchestrator

### Key Features
- **Sliding Window Logic**: Training 90 days, Testing 30 days, Sliding 30 days
- **Multi-Asset WFO**: Independent optimization per asset with parameter aggregation
- **Realistic Backtesting**: Slippage, fees, partial fills, order types
- **Cross-Validation**: Prevention of overfitting and robustness validation
- **Hexagonal Architecture**: Proper separation of concerns between domain, application, and infrastructure layers
- **Professional Reporting**: Complete metrics including Sharpe ratios, drawdown, consistency, overfit index
- **Environment Configuration**: All key parameters configurable via `.env` file

## Installation

```bash
# 1. Navigate to project directory
cd /path/to/hedge_fund

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Ensure data directory exists
mkdir -p ./data/{BTCUSDT,ETHUSDT,ADAUSDT,SOLUSDT}/
# Add your OHLCV data in CSV format: 1m.csv, 5m.csv, 1h.csv, 1d.csv

# 4. Create results directories
mkdir -p ./data/results/wfo
mkdir -p ./data/results/wfo/plots
```

## Configuration

### Configuration File Structure (JSON)
```json
{
  "data_path": "./data",
  "results_dir": "./data/results/wfo",
  "train_size": 90,      // Training window size in days
  "test_size": 30,       // Testing window size in days
  "step": 30,            // Sliding window step in days
  "performance_threshold": 0.1,   // Minimum Sharpe ratio
  "max_drawdown_threshold": 0.15, // Maximum allowed drawdown (15%)
  "max_evals": 50,       // Number of hyperopt evaluations
  "risk_config": {
    "initial_capital": 1000000,
    "fee_rate": 0.001,
    "slippage_factor": 0.0005,
    "max_risk_per_trade": 0.02,
    "max_position_size": 0.20,
    "max_drawdown_threshold": 0.15
  },
  "cv_config": {
    "n_splits": 5,
    "min_train_size": 30,
    "test_size": 15
  }
}
```

## Usage

### 1. Basic Usage Example
```python
from application.walk_forward.wfo_orchestrator import WFOOrchestrator

# Configuration
config = {
    "train_size": 90,
    "test_size": 30, 
    "step": 30,
    "performance_threshold": 0.1,
    "max_drawdown_threshold": 0.15,
    "max_evals": 30
}

# Initialize orchestrator
orchestrator = WFOOrchestrator(config)

# Run complete WFO pipeline
results = orchestrator.run_complete_wfo_pipeline(
    symbols=["BTCUSDT", "ETHUSDT"],  # Trading pairs to analyze
    strategy_name="crypto_breakout", # Your strategy name
    strategy_func=None               # Strategy function (optional)
)
```

### 2. Custom Strategy Integration
To integrate your own strategy:

```python
def my_custom_strategy(row, params):
    """
    Custom strategy function.
    Args:
        row: Pandas Series with OHLCV data for current candle
        params: Dict with optimized parameters
        
    Returns:
        int: 1 for buy, -1 for sell, 0 for hold
    """
    # Calculate indicators using values from 'row'
    sma_short = row.get('sma_' + str(int(params.get('short_ma_period', 10))), 0)
    sma_long = row.get('sma_' + str(int(params.get('long_ma_period', 20))), 0)
    rsi = row.get('rsi', 50)
    
    # Example strategy: MA crossover with RSI filter
    if sma_short > sma_long and rsi < params.get('rsi_oversold', 40):
        return 1  # Buy signal
    elif sma_short < sma_long and rsi > params.get('rsi_overbought', 60):
        return -1  # Sell signal
    else:
        return 0  # No signal

# Then use in WFO pipeline:
results = orchestrator.run_complete_wfo_pipeline(
    symbols=["BTCUSDT", "ETHUSDT"],
    strategy_name="my_custom_strategy", 
    strategy_func=my_custom_strategy
)
```

### 3. Command Line Usage
```bash
python -c "
from application.walk_forward.wfo_orchestrator import WFOOrchestrator

config = {
    'train_size': 90,
    'test_size': 30,
    'step': 30,
    'max_evals': 50
}

orchestrator = WFOOrchestrator(config)
results = orchestrator.run_complete_wfo_pipeline(
    symbols=['BTCUSDT', 'ETHUSDT'],
    strategy_name='crypto_breakout'
)
print('WFO completed:', results['timestamp'])
"
```

## Testing Instructions

### 1. Unit Testing Individual Components
Test each component separately:

```bash
# Test data loader
python -c "
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
loader = CSVHistoryLoaderAdapter('./data')
df = loader.load('BTCUSDT', '1d')
print(f'Loaded {len(df)} rows for BTCUSDT')
"

# Test sliding window splitter
python -c "
from application.walk_forward.sliding_window_splitter import SlidingWindowSplitter
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

dates = pd.date_range(end=datetime.now(), periods=200, freq='D')
sample_data = pd.DataFrame({
    'timestamp': dates,
    'open': np.random.rand(200) * 100,
    'high': np.random.rand(200) * 110, 
    'low': np.random.rand(200) * 90,
    'close': np.random.rand(200) * 100,
    'volume': np.random.rand(200) * 1000000
}).set_index('timestamp')

splitter = SlidingWindowSplitter(train_size=60, test_size=20, step=20)
windows = splitter.split(sample_data)
print(f'Created {len(windows)} walk-forward windows')
"
```

### 2. Integration Testing
Run the complete pipeline with sample data:

```bash
# Run complete pipeline with sample data
python -c "
from application.walk_forward.wfo_orchestrator import WFOOrchestrator
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create sample data for testing
dates = pd.date_range(end=datetime.now(), periods=300, freq='D')
btc_data = pd.DataFrame({
    'timestamp': dates,
    'open': 40000 + np.cumsum(np.random.randn(300) * 100),
    'high': 40000 + np.cumsum(np.random.randn(300) * 150),
    'low': 40000 + np.cumsum(np.random.randn(300) * 100),
    'close': 40000 + np.cumsum(np.random.randn(300) * 100),
    'volume': np.abs(np.random.randn(300)) * 1000000
}).set_index('timestamp')

# Note: You need real data files in ./data/BTCUSDT/1d.csv, ./data/ETHUSDT/1d.csv, etc.
# or set up a mock data loader

config = {
    'train_size': 60,
    'test_size': 20,
    'step': 20,
    'max_evals': 10,  # For quick test
    'performance_threshold': 0.05,
    'results_dir': './data/results/test_results'
}

try:
    orchestrator = WFOOrchestrator(config)
    # This would work with real data files
    print('WFO Orchestrator initialized successfully')
except Exception as e:
    print(f'Error initializing orchestrator: {e}')
"
```

### 3. Full System Test
```bash
# Run the test script that validates the complete pipeline
python test_complete_wfo_pipeline.py
```

### 4. Expected Output Verification
After running the pipeline, verify the output includes:
- Multi-asset WFO results
- Parameter stability metrics
- Cross-validation scores
- Overfit index < 1.0 (lower is better)
- Consistency score > 0.6 (higher is better)
- Sharpe ratio > 0.5 (higher is better)
- All results saved to `./data/results/wfo/`

## Results Interpretation

### Key Metrics
- **Avg Sharpe Ratio**: Measure of risk-adjusted return (target > 0.5)
- **Avg Total Return**: Average return across WFO periods  
- **Max Drawdown**: Maximum peak-to-trough decline (target < 0.15)
- **Pass Rate**: Percentage of periods passing thresholds (target > 0.6)
- **Parameter Stability**: Consistency of parameters across periods (target > 0.5)
- **Consistency Score**: Consistency of positive returns (target > 0.6)
- **Overfit Index**: Measure of overfitting (target < 1.0, lower is better)

### Performance Grades
- **A**: Excellent - Ready for live trading with small position sizes
- **B**: Good - Suitable for paper trading, monitor closely  
- **C**: Average - Needs further validation before live deployment
- **D**: Below Average - Significant improvements needed
- **F**: Poor - Strategy needs major revision

### Output Files
1. `wfo_report_{strategy}_{symbols}_{timestamp}.json` - Complete WFO analysis
2. `robust_params_{strategy}_{symbols}_{timestamp}.json` - Aggregate parameters
3. Various plot files in `./data/results/wfo/plots/` - Visualizations

## Troubleshooting

### Common Issues
1. **"Insufficient Data" Errors**: Ensure your data has sufficient historical points (at least train_size + test_size + buffer)
2. **"No Trades Executed"**: Check strategy logic and parameter ranges
3. **High Overfit Index**: Indicates potential overfitting - consider tighter parameter bounds
4. **Low Pass Rate**: Strategy may not be robust across different market regimes

### Logging
Check log files in `./logs/` for detailed debugging information.

## Next Steps

1. **Connect to Live Data**: Replace CSV data loader with live market data feeds
2. **Broker Integration**: Connect to live trading platform (Binance, Bybit, etc.)  
3. **Schedule WFO**: Set up periodic optimization (daily/weekly/monthly)
4. **Add Monitoring**: Implement alerts and live performance tracking
5. **Scale Multi-Asset**: Add more trading pairs and asset classes

---

**Note**: This pipeline implements institutional-grade Walk-Forward Optimization as used in real hedge funds. Proper validation of results is critical before any live trading implementation.