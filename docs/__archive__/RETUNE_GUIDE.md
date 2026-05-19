# Comprehensive Guide: Retune, Walk-Forward, and Optimized Backtesting

## Overview

This guide explains the three main processes for managing trading strategies in the automated trading system:

- **Retune**: Hyperparameter optimization for current market conditions
- **Walk-Forward Analysis**: Validation of strategy robustness over time
- **Optimized Backtesting**: Historical validation using optimized parameters

---

## 1. Retune Process

### Purpose
- Automatically optimize strategy parameters for current market conditions
- Maintains strategy performance as market regimes change
- Identifies optimal parameters using historical data

### How it Works
The retune process:
1. Downloads 1-day timeframe data for 6 months (180 days)
2. Runs hyperparameter optimization using specified algorithms
3. Validates results and saves optimal parameters
4. Updates strategy configuration for production use

### Usage
```bash
# Retune all symbols from WFO_COINS environment variable
python runner_retune.py --strategy crypto_breakout --evals 50 --days 90

# Retune specific symbols
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --evals 100 --days 180

# With validation and output
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT --evals 25 --days 120 --validate --output ./data/results/retune/results.json
```

python runner_retune.py --symbols BTCUSDT --evals 25 --days 120 --validate --output ./data/results/retune/results.json


### Parameters
- `--strategy`: Trading strategy to optimize (default: crypto_breakout)
- `--symbols`: List of symbols to retune (default: WFO_COINS from environment)
- `--evals`: Maximum number of hyperparameter optimization evaluations per symbol (default: 50)
- `--days`: Number of days of historical data to use (default: 90)
- `--validate`: Validate results after retuning
- `--output`: Save results to JSON file
- `--verbose`: Enable verbose output

### Configuration
- Parameters and their ranges defined in `shared/configurable_hyperopt.py`
- Optimization objectives: sharpe_ratio, profit_factor, max_drawdown, total_return, win_rate
- Constraints ensure parameter validity and realistic trading conditions

### Best Practices
- Run regularly or when market conditions change significantly
- Use 1-day timeframe data for stable parameter optimization
- Validate results before applying to live trading
- Monitor the optimization results for consistency across symbols

---

## 2. Walk-Forward Analysis

### Purpose
- Validates strategy robustness over different market conditions
- Tests how well a strategy adapts to changing market regimes
- Provides confidence in strategy performance for future periods

### How it Works
The walk-forward process:
1. Divides historical data into multiple time windows
2. Optimizes strategy parameters on training window
3. Tests parameters on out-of-sample validation window
4. Repeats across the entire time period
5. Aggregates results to assess overall strategy robustness

### Usage
```bash
# Run walk-forward analysis
python runner_walkforward.py --strategy crypto_breakout --symbols BTCUSDT --train-days 60 --test-days 15

# Multiple symbols with custom parameters
python runner_walkforward.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --train-days 90 --test-days 30 --evals 25
```

### Parameters
- `--strategy`: Trading strategy to analyze (default: crypto_breakout)
- `--symbols`: List of symbols to analyze (default: WFO_COINS from environment)
- `--train-days`: Number of days for training/optimization window
- `--test-days`: Number of days for testing/validation window
- `--evals`: Maximum optimization evaluations per training period
- `--start-date`: Start date for analysis (default: earliest available)
- `--end-date`: End date for analysis (default: today)

### Outputs
- Performance metrics across all time windows
- Consistency analysis of optimal parameters
- Drawdown and risk metrics
- Comparison to static parameter backtesting

### Best Practices
- Use longer training windows for more stable parameter optimization
- Ensure test windows are meaningful for the trading strategy timeframe
- Regular walk-forward analysis helps validate strategy adaptability
- Compare walk-forward results to standard backtesting to identify overfitting

---

## 3. Optimized Backtesting

### Purpose
- Historical validation of trading strategies with optimized parameters
- Performance analysis across extended historical periods
- Risk assessment and strategy validation

### How it Works
The optimized backtesting process:
1. Uses parameters from retune process (or manual optimization)
2. Simulates trading on historical data
3. Applies realistic trading conditions (slippage, fees, etc.)
4. Calculates comprehensive performance metrics
5. Generates detailed reports and visualizations

### Usage
```bash
# Standard optimized backtest
python runner_backtest.py --strategy crypto_breakout --symbols BTCUSDT --start 2023-01-01 --end 2023-12-31

# Backtest with optimized parameters
python runner_backtest.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --start 90d --end today --optimized

# Advanced backtesting with detailed reports
python runner_backtest.py --strategy crypto_breakout --symbols BTCUSDT --start 180d --end today --report --plot --output results/
```

### Parameters
- `--strategy`: Trading strategy to backtest (default: crypto_breakout)
- `--symbols`: List of symbols to backtest
- `--start`: Start date or relative period (e.g., "90d", "2023-01-01")
- `--end`: End date or relative period (default: today)
- `--optimized`: Use optimized parameters from retune process
- `--timeframe`: Data timeframe (default: depends on strategy)
- `--report`: Generate detailed performance report
- `--plot`: Generate performance charts
- `--output`: Output directory for results

### Performance Metrics
- Total return and annualized return
- Sharpe ratio and Sortino ratio
- Maximum drawdown and Calmar ratio
- Win rate and average profit/loss ratio
- Number of trades and trading frequency
- Risk-adjusted returns

### Best Practices
- Always use realistic trading conditions (fees, slippage, spread)
- Validate backtesting results with out-of-sample testing
- Compare against benchmark strategies or indices
- Ensure sufficient data for meaningful results
- Consider different market conditions during the testing period

---

## Integration and Workflow

### Recommended Workflow
1. **Data Synchronization**: Use `runner_resync.py` to ensure data is up-to-date
2. **Parameter Optimization**: Run `runner_retune.py` to optimize strategy parameters
3. **Validation**: Use `runner_walkforward.py` to validate strategy robustness
4. **Performance Assessment**: Run `runner_backtest.py` with optimized parameters for final validation
5. **Implementation**: Apply optimized parameters to live trading system

### Data Management
- All processes use data from `./data/history/processed/` directory
- 1-day timeframe data specifically stored in `./data/history/processed/1d/`
- Raw data maintained for aggregation to different timeframes
- Automatic cleanup based on retention policies

### Monitoring and Maintenance
- Regular monitoring of optimization results
- Tracking performance degradation over time
- Periodic revalidation of strategy parameters
- Documentation of parameter changes and reasoning

## Troubleshooting

### Common Issues
- **Insufficient Data**: Ensure adequate historical data is available
- **Optimization Failures**: Check data quality and parameter ranges
- **Performance Deterioration**: May indicate market regime change requiring re-optimization
- **Memory Issues**: Reduce the dataset size or optimize the process

### Error Handling
- All runners provide detailed logging and error messages
- Results saved to JSON files for post-mortem analysis
- Validation ensures data integrity before processing
- Graceful handling of missing or erroneous data points