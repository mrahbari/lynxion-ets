# Advanced Crypto Strategies Documentation

## Overview
This document describes the advanced crypto strategies added to the trading system. These professional-grade strategies are designed specifically for cryptocurrency markets and include sophisticated features like multi-timeframe analysis, liquidity detection, funding rate bias, and orderbook analysis.

## Strategies

### 1. Crypto Liquidity Strategy (`CryptoLiquidity`)

**Description**: A comprehensive strategy combining multiple crypto-specific signals including liquidity sweeps, funding rate bias, open interest expansion, CVD divergences, and multi-timeframe trend confirmation.

**Key Features**:
- Liquidity sweep detection
- Funding rate bias analysis
- Open Interest expansion/contraction
- CVD (Cumulative Volume Delta) divergences
- Multi-timeframe trend confirmation
- Volatility regime filtering

**Configuration Parameters**:
- `min_oi_trend` (default: 0.04): Minimum Open Interest trend threshold
- `max_funding_bias` (default: 0.005): Maximum funding rate for bias detection
- `cvd_divergence_strength` (default: 2.0): Strength threshold for CVD divergences

**Hyperopt Space**:
```python
{
    "min_oi_trend": hp.uniform("min_oi_trend", 0.01, 0.10),
    "max_funding_bias": hp.uniform("max_funding_bias", 0.001, 0.01),
    "cvd_divergence_strength": hp.uniform("cvd_divergence_strength", 1.0, 6.0)
}
```

### 2. MTF Trend Strategy (`CryptoMTFTrend`)

**Description**: Multi-timeframe trend following strategy that combines signals from multiple timeframes (3m, 15m, 1h, 4h, 1D) with configurable weighting.

**Key Features**:
- Multi-timeframe analysis (3m, 15m, 1h, 4h, 1D)
- Weighted signal aggregation
- Fast/slow EMA trend detection
- Flexible timeframe weighting

**Configuration Parameters**:
- `trend_period` (default: 50): Base period for trend calculation
- `tf_weights` (default): Timeframe weights for signal aggregation

**Hyperopt Space**:
```python
{
    "trend_period": hp.choice("trend_period", [30, 50, 80])
}
```

### 3. VWAP Reversal Strategy (`CryptoVWAPReversal`)

**Description**: VWAP-based reversal strategy that identifies mean reversion opportunities around Volume Weighted Average Price levels.

**Key Features**:
- VWAP calculation with configurable lookback
- Standard deviation bands for reversal signals
- Multi-timeframe VWAP analysis (default: 15m)

**Configuration Parameters**:
- `lookback` (default: 200): VWAP lookback period
- `std_mult` (default: 2.0): Standard deviation multiplier for bands

**Hyperopt Space**:
```python
{
    "lookback": hp.quniform("lookback", 100, 400, 10),
    "std_mult": hp.uniform("std_mult", 1.0, 4.0)
}
```

### 4. OI Footprint Strategy (`CryptoOIFootprint`)

**Description**: Open Interest and volume footprint analysis strategy that identifies institutional accumulation/distribution patterns.

**Key Features**:
- Open Interest expansion analysis
- CVD (Cumulative Volume Delta) tracking
- Volume footprint pattern recognition
- Multi-timeframe confirmation (default: 3m)

**Configuration Parameters**:
- `oi_expansion` (default: 0.05): Open Interest expansion threshold
- `delta_strength` (default: 5): CVD strength threshold

**Hyperopt Space**:
```python
{
    "oi_expansion": hp.uniform("oi_expansion", 0.02, 0.10),
    "delta_strength": hp.uniform("delta_strength", 2, 10)
}
```

### 5. Liquidity Sweep Scalper (`CryptoSweepScalper`)

**Description**: High-frequency scalping strategy focused on detecting and trading liquidity sweeps in crypto markets.

**Key Features**:
- Liquidity sweep detection algorithms
- Multiple timeframes supported (default: 3m)
- Risk management around key levels
- Configurable killzone trading hours

**Configuration Parameters**:
- `killzone` (default: ["UTC-13:00", "UTC-01:00"]): High-activity trading hours
- `lookback` (default: 4): Lookback period for sweep detection

**Hyperopt Space**:
```python
{
    "lookback": hp.choice("lookback", [3, 4, 5])
}
```

## Installation and Setup

The strategies are implemented as separate files in the adapters directory and can be used with the hyperopt optimization system:

```python
from infrastructure.strategies.adapters.crypto_liquidity_strategy_adapter import CryptoLiquidityStrategyAdapter
from infrastructure.strategies.adapters.crypto_mtf_trend_strategy_adapter import CryptoMTFTrendStrategyAdapter
from infrastructure.strategies.adapters.crypto_vwap_reversal_strategy_adapter import CryptoVWAPReversalStrategyAdapter
from infrastructure.strategies.adapters.crypto_oi_footprint_strategy_adapter import CryptoOIFootprintStrategyAdapter
from infrastructure.strategies.adapters.crypto_sweep_scalper_adapter import CryptoSweepScalperAdapter

# Example usage
strategy = CryptoLiquidityStrategyAdapter(config={
    "min_oi_trend": 0.05,
    "max_funding_bias": 0.008
})
```

## Hyperopt Integration

All crypto strategies are fully integrated with the hyperparameter optimization system:

```python
from infrastructure.optimization.hyperopt_space import parameter_space

# Get parameter space for any strategy
space = parameter_space.get_space("CryptoLiquidity")
```

## Testing

Each strategy comes with comprehensive unit tests:

- Test initialization with default and custom configurations
- Test signal generation
- Test method-specific functionality
- Validate hexagonal architecture compliance

Run the tests:
```bash
python -m pytest tests/infrastructure/test_strategy_adapters.py -k "Crypto" -v
```

## Architecture Compliance

All strategies follow the hexagonal architecture pattern:
- Implement the `StrategyPort` interface
- Inherit from `BaseStrategyAdapter`
- Use proper dependency injection
- Maintain separation of concerns
- Follow existing code patterns

## Risk Considerations

⚠️ **Important**: Crypto strategies involve additional risks including:
- Higher volatility exposure
- Funding rate costs/earnings
- Liquidation risks
- Market structure differences
- Regulatory considerations

Always backtest thoroughly before live trading and implement proper risk management.