# Strategy Documentation

## Available Trading Strategies

The system implements 9 trading strategies, each designed for specific market conditions and trading approaches:

### Core Strategies (`infrastructure/strategies/strategy_adapters.py`)

#### 1. **TrendFollowStrategyAdapter** 
- **Approach**: Identifies and follows market trends using moving average crossovers
- **Mechanism**: Compares short-term and long-term moving averages to detect trend direction
- **Indicators**: EMA/SMA, Price momentum, ATR (Average True Range)
- **Best Market Condition**: Trending markets with clear directional moves

#### 2. **MeanReversionStrategyAdapter**
- **Approach**: Seeks to profit from price corrections back to mean values
- **Mechanism**: Uses RSI and Bollinger Bands to identify overbought/oversold conditions
- **Indicators**: RSI (Relative Strength Index), Bollinger Bands, Support/Resistance levels
- **Best Market Condition**: Sideways/ranging markets with mean-reverting behavior

#### 3. **ScalpingStrategyAdapter**
- **Approach**: Captures small price movements in very short timeframes
- **Mechanism**: Uses fast/slow moving averages with momentum confirmation
- **Indicators**: Fast EMA/Slow EMA crossovers, RSI, Volume confirmation, Momentum
- **Best Market Condition**: High volatility markets with frequent price oscillations

#### 4. **BreakoutStrategyAdapter**
- **Approach**: Captures profits from price movements beyond support/resistance levels
- **Mechanism**: Identifies consolidation periods followed by strong directional moves
- **Indicators**: Support/Resistance, ATR, Volatility measures, Momentum
- **Best Market Condition**: Markets transitioning from consolidation to trending

### Specialized Strategies (`infrastructure/strategies/adapters/`)

#### 5. **LiquidityStrategyAdapter**
- **Approach**: Professional strategy combining multiple sophisticated market microstructure elements
- **Mechanism**: Analyzes liquidity levels, funding rate biases, and OI expansion to detect sweep opportunities
- **Indicators**: RSI, Bollinger Bands, Funding Rates, Open Interest, Volume analysis
- **Best Market Condition**: Crypto markets with high derivatives volume and funding payments

#### 6. **MTFTrendStrategyAdapter** (Multi-Timeframe Trend)
- **Approach**: Analyzes trends across multiple timeframes for higher probability signals
- **Mechanism**: Confirms trend alignment across different temporal scales with weighted confirmation
- **Indicators**: Multi-period EMAs, Cross-timeframe confirmation, Momentum
- **Best Market Condition**: Well-defined trends that align across multiple timeframes

#### 7. **OIFootprintStrategyAdapter** (Open Interest Footprint)
- **Approach**: Uses derivatives market dynamics to identify institutional positions and potential moves
- **Mechanism**: Analyzes the relationship between price, volume, and open interest changes
- **Indicators**: Open Interest changes, Volume analysis, Price-volume relationships
- **Best Market Condition**: Derivatives markets with significant volume differences

#### 8. **SweepScalperAdapter** (Liquidity Sweep Scalper)
- **Approach**: Targets liquidity sweep zones where market makers take orders from order books
- **Mechanism**: Identifies potential sweep areas using volatility and market structure analysis
- **Indicators**: Volatility measures, Support/Resistance, Volume spikes, Range analysis
- **Best Market Condition**: Markets with predictable liquidity zones and stop hunts

#### 9. **VWAPReversalStrategyAdapter** (Volume Weighted Average Price Reversal)
- **Approach**: Uses VWAP as a dynamic mean for mean reversion opportunities
- **Mechanism**: Identifies price excursions from VWAP with statistical significance
- **Indicators**: VWAP proxy, Bollinger Bands, Standard deviation, Price deviation measures
- **Best Market Condition**: Markets with high volume correlation and mean-reverting behavior

## Key Features

- **Real Technical Analysis**: All strategies incorporate genuine technical indicators rather than placeholder logic
- **Hexagonal Architecture**: All strategies implement domain ports for proper architecture separation
- **Market Data Processing**: Each strategy handles OHLCV market data appropriately
- **Risk Management**: All strategies include position sizing based on signal confidence
- **Signal Validity**: All strategies generate proper BUY/SELL/HOLD signals with confidence scoring
- **Performance Tracking**: Built-in logging and analysis for signal effectiveness
- **Modular Design**: Each strategy is isolated in its own file for maintainability

## Deployment Readiness

All strategies have been tested and verified to work with real market data without requiring hyperparameter optimization systems. This ensures they function with fixed parameters before any dynamic tuning systems are introduced.

The system architecture maintains proper isolation between:
- Domain layer (business logic)
- Application layer (use cases and orchestration)
- Infrastructure layer (adapters and external integrations)
- Interface layer (APIs and UIs)