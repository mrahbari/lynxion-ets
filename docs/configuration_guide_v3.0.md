# Configuration Guide - Version 3.0

## Overview
This document details all the configurable parameters for the trading system, with a focus on the enhanced watcher configuration that allows for better customization and optimization.

## Environment Variables

### Historical Candle Watcher Configuration
The historical candle watcher now uses environment variables for all key parameters:

#### Confidence Thresholds
- `WATCHER_MIN_CONFIDENCE_THRESHOLD` (default: 0.15)
  - Minimum confidence threshold for watcher observations
  - Lower values allow more observations to be generated

- `WATCHER_MAX_CONFIDENCE_WITH_PATTERNS` (default: 0.3)
  - Maximum confidence when specific patterns are detected
  - Controls how strongly pattern-based signals are weighted

- `WATCHER_MIN_PRICE_CHANGE_THRESHOLD` (default: 0.0005)
  - Minimum price change threshold to generate basic observations (0.05%)
  - Controls sensitivity to basic price movements

- `WATCHER_MAX_CONFIDENCE_WITH_MOVEMENT` (default: 0.35)
  - Maximum confidence with basic price movement
  - Caps confidence for simple trend observations

- `WATCHER_NEUTRAL_CONFIDENCE` (default: 0.1)
  - Confidence for neutral market conditions
  - Very low confidence for neutral observations

#### Weight Parameters
- `WATCHER_PATTERN_WEIGHT` (default: 0.4)
  - Weight given to pattern strength in confidence calculation
  - Controls influence of candlestick patterns

- `WATCHER_MOMENTUM_WEIGHT` (default: 0.3)
  - Weight given to momentum strength in confidence calculation
  - Controls influence of momentum analysis

#### Volatility Adjustments
- `WATCHER_HIGH_VOLATILITY_BOOST` (default: 0.2)
  - Additional confidence boost for high volatility regime
  - Increases confidence during high volatility periods

- `WATCHER_LOW_VOLATILITY_BOOST` (default: 0.05)
  - Additional confidence boost for low volatility regime
  - Provides slight boost during low volatility periods

- `WATCHER_NORMAL_VOLATILITY_BOOST` (default: 0.1)
  - Additional confidence boost for normal volatility regime
  - Standard boost during normal market conditions

#### General Parameters
- `WATCHER_MIN_CONFIDENCE_WHEN_SIGNALS_DETECTED` (default: 0.15)
  - Minimum confidence when any signals are detected
  - Ensures some confidence when signals exist

- `WATCHER_MAX_CONFIDENCE_CAP` (default: 0.95)
  - Maximum confidence cap
  - Prevents overconfidence in any signal

- `WATCHER_MOMENTUM_LOOKBACK_PERIOD` (default: 10)
  - Number of candles to look back for momentum calculation
  - Controls momentum analysis window

- `WATCHER_MOMENTUM_SENSITIVITY_FACTOR` (default: 10.0)
  - Sensitivity factor for momentum strength calculation
  - Controls how momentum strength is amplified

## Configuration Tuning Guide

### For More Aggressive Trading
To increase the frequency of trade signals:
```
WATCHER_MIN_CONFIDENCE_THRESHOLD=0.10
WATCHER_MIN_PRICE_CHANGE_THRESHOLD=0.0002
WATCHER_PATTERN_WEIGHT=0.3
WATCHER_MOMENTUM_WEIGHT=0.4
```

### For More Conservative Trading
To decrease the frequency of trade signals:
```
WATCHER_MIN_CONFIDENCE_THRESHOLD=0.25
WATCHER_MIN_PRICE_CHANGE_THRESHOLD=0.0010
WATCHER_MAX_CONFIDENCE_WITH_PATTERNS=0.25
WATCHER_MAX_CONFIDENCE_WITH_MOVEMENT=0.25
```

### For High Volatility Markets
To adapt to high volatility conditions:
```
WATCHER_HIGH_VOLATILITY_BOOST=0.3
WATCHER_MOMENTUM_LOOKBACK_PERIOD=15
WATCHER_MOMENTUM_SENSITIVITY_FACTOR=8.0
```

### For Low Volatility Markets
To adapt to low volatility conditions:
```
WATCHER_LOW_VOLATILITY_BOOST=0.1
WATCHER_MIN_PRICE_CHANGE_THRESHOLD=0.0003
WATCHER_PATTERN_WEIGHT=0.5
```

## Impact on System Behavior

### Signal Generation
- Lower `WATCHER_MIN_CONFIDENCE_THRESHOLD` values increase the number of signals generated
- Higher `WATCHER_PATTERN_WEIGHT` values emphasize technical patterns over momentum
- Higher `WATCHER_MOMENTUM_WEIGHT` values emphasize momentum over patterns

### Risk Management
- The configuration parameters work with the existing risk management system
- Lower thresholds may increase trade frequency but should still respect risk limits
- All orders still go through the proper risk validation in the Strategy layer

### Performance
- More sensitive configurations may increase processing load
- The system maintains early-exit logic to optimize processing efficiency
- Proper configuration can balance signal quality with processing overhead

## Monitoring Configuration Changes

After changing these parameters:
1. Restart the trading system to apply new configurations
2. Monitor the logs for observation generation frequency
3. Check that the proper architecture flow is maintained (Watcher → Engine → Fusion → Strategy → Broker)
4. Verify that risk management is still functioning properly
5. Adjust parameters iteratively based on performance results

## Troubleshooting

### If No Observations Are Generated
- Check that `WATCHER_MIN_CONFIDENCE_THRESHOLD` is not set too high
- Verify that `WATCHER_MIN_PRICE_CHANGE_THRESHOLD` is appropriate for current market conditions
- Ensure data is flowing properly to the watchers

### If Too Many Weak Signals Are Generated
- Increase `WATCHER_MIN_CONFIDENCE_THRESHOLD`
- Increase `WATCHER_MIN_PRICE_CHANGE_THRESHOLD`
- Reduce `WATCHER_MOMENTUM_SENSITIVITY_FACTOR`

### If System Is Too Slow
- Check that lookback periods are not set too high
- Monitor CPU and memory usage
- Consider reducing the number of symbols being monitored simultaneously