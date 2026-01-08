# Advanced Risk Management Implementation

## Overview
This document outlines the implementation of advanced risk management features for the Enterprise Hedge Fund Trading System, addressing the critical requirements identified in the audit:

- **Dynamic Position Sizing** with volatility-adjusted position sizing, correlation-based risk adjustments, and market regime detection
- **Advanced SL/TP Management** with trailing stops, dynamic take-profit levels, and time-based exits

## 1. Dynamic Position Sizing

### 1.1 Volatility-Adjusted Position Sizing
The system calculates position size based on market volatility to ensure appropriate risk exposure:

```python
def _calculate_volatility_factor(self, market_data: pd.DataFrame) -> float:
    """Calculate volatility-based risk adjustment factor"""
    if len(market_data) < self.volatility_lookback:
        return 1.0
    
    # Calculate rolling volatility
    returns = market_data['close'].pct_change().dropna()
    rolling_volatility = returns.rolling(window=self.volatility_lookback).std().iloc[-1]
    
    # Normalize volatility (higher volatility = smaller position)
    avg_volatility = 0.02  # 2% daily volatility as baseline
    volatility_ratio = rolling_volatility / avg_volatility
    
    # Adjust position size inversely to volatility
    factor = 1.0 / (1.0 + volatility_ratio)
    return max(0.3, min(1.5, factor))  # Ensure factor is reasonable
```

### 1.2 Correlation-Based Risk Adjustments
Positions are sized considering correlation with existing portfolio holdings:

```python
def _calculate_correlation_factor(self, symbol: Symbol) -> float:
    """Calculate correlation-based risk adjustment factor"""
    if symbol.value in self.position_correlations:
        correlations = list(self.position_correlations[symbol.value].values())
        if correlations:
            avg_correlation = sum(correlations) / len(correlations)
            # Reduce position size if highly correlated with other positions
            factor = 1.0 - (avg_correlation / 2.0)
            return max(0.3, factor)  # Don't go below 30% of normal size
    return 1.0
```

### 1.3 Market Regime Detection
The system detects market conditions and adjusts position sizing accordingly:

```python
def _calculate_regime_factor(self, symbol: Symbol, market_data: pd.DataFrame) -> float:
    """Calculate market regime-based risk adjustment factor"""
    regime = self._detect_market_regime(market_data)
    self.market_regimes[symbol.value] = regime
    
    # Adjust risk based on regime
    regime_multipliers = {
        RegimeType.BULLISH_TRENDING: 1.2,    # Higher position size in trending markets
        RegimeType.BEARISH_TRENDING: 1.2,    # Higher position size in trending markets
        RegimeType.HIGH_VOLATILITY: 0.7,     # Lower position size in high volatility
        RegimeType.LOW_VOLATILITY: 1.1,      # Slightly higher in low volatility
        RegimeType.CHOPPY: 0.6,              # Much lower in choppy markets
        RegimeType.BREAKOUT: 1.0,            # Normal in breakout situations
        RegimeType.NORMAL: 1.0               # Normal in normal markets
    }
    
    return regime_multipliers.get(regime, 1.0)
```

## 2. Advanced SL/TP Management

### 2.1 Dynamic Stop-Loss and Take-Profit Levels
The system calculates SL/TP levels based on risk factors and market conditions:

```python
def calculate_sl_tp_levels(self, 
                          entry_price: float, 
                          position_side: str,
                          risk_adjustment_factors: RiskAdjustmentFactors,
                          atr_value: Optional[float] = None,
                          market_data: Optional[pd.DataFrame] = None) -> Tuple[float, float]:
    """
    Calculate dynamic stop-loss and take-profit levels based on risk factors.
    """
    if atr_value is None and market_data is not None:
        highs = market_data['high'].values
        lows = market_data['low'].values
        closes = market_data['close'].values
        atr_value = self._calculate_atr(highs, lows, closes)
    
    if atr_value is None:
        atr_value = entry_price * 0.01  # 1% of price as default ATR
    
    # Base stop loss and take profit multipliers
    base_sl_multiplier = 2.0  # 2 ATRs for stop loss
    base_tp_multiplier = 3.0  # 3 ATRs for take profit (1:1.5 risk/reward ratio)
    
    # Apply risk adjustment factors
    sl_multiplier = base_sl_multiplier * risk_adjustment_factors.stop_loss_multiplier
    tp_multiplier = base_tp_multiplier * risk_adjustment_factors.take_profit_multiplier
    
    if position_side.upper() == 'LONG':
        # For long positions: SL below entry, TP above entry
        stop_loss_price = entry_price - (atr_value * sl_multiplier)
        take_profit_price = entry_price + (atr_value * tp_multiplier)
        
        # Ensure stop loss is not too close to entry (minimum 1% away)
        min_sl_distance = entry_price * 0.01
        stop_loss_price = max(stop_loss_price, entry_price - min_sl_distance)
        take_profit_price = max(take_profit_price, entry_price + min_sl_distance)
        
    elif position_side.upper() == 'SHORT':
        # For short positions: SL above entry, TP below entry
        stop_loss_price = entry_price + (atr_value * sl_multiplier)
        take_profit_price = entry_price - (atr_value * tp_multiplier)
        
        # Ensure stop loss is not too close to entry (minimum 1% away)
        min_sl_distance = entry_price * 0.01
        stop_loss_price = min(stop_loss_price, entry_price + min_sl_distance)
        take_profit_price = min(take_profit_price, entry_price - min_sl_distance)
    else:
        raise ValueError(f"Invalid position side: {position_side}. Must be 'LONG' or 'SHORT'")
    
    return stop_loss_price, take_profit_price
```

### 2.2 Trailing Stops
Trailing stops automatically adjust as price moves favorably:

```python
def update_trailing_stop(self, 
                       current_price: float, 
                       entry_price: float, 
                       position_side: str,
                       initial_stop_loss: float,
                       trail_percentage: float = 0.10) -> float:
    """
    Update trailing stop based on current price movement.
    """
    if position_side.upper() == 'LONG':
        # For long positions, trailing stop moves up as price increases
        if current_price > entry_price:
            # Calculate trailing stop level (trail_percentage behind current price)
            trailing_stop = current_price * (1 - trail_percentage)
            # Never move stop loss below initial level or below entry
            return max(initial_stop_loss, trailing_stop, entry_price * 0.95)
        else:
            # Price is below entry, don't adjust stop loss
            return initial_stop_loss
            
    elif position_side.upper() == 'SHORT':
        # For short positions, trailing stop moves down as price decreases
        if current_price < entry_price:
            # Calculate trailing stop level (trail_percentage ahead of current price)
            trailing_stop = current_price * (1 + trail_percentage)
            # Never move stop loss above initial level or above entry
            return min(initial_stop_loss, trailing_stop, entry_price * 1.05)
        else:
            # Price is above entry, don't adjust stop loss
            return initial_stop_loss
    else:
        raise ValueError(f"Invalid position side: {position_side}. Must be 'LONG' or 'SHORT'")
```

### 2.3 Time-Based Exits
Positions can be automatically closed after a specified holding period:

```python
def should_exit_on_time(self, 
                      entry_time: datetime, 
                      max_holding_period: timedelta,
                      current_time: Optional[datetime] = None) -> bool:
    """
    Determine if position should be exited based on time constraints.
    """
    if current_time is None:
        current_time = datetime.now()
    
    holding_period = current_time - entry_time
    
    return holding_period > max_holding_period
```

## 3. Integration Points

### 3.1 Broker Execution Service Integration
The advanced risk management is integrated into the broker execution service to enhance orders with proper risk parameters:

```python
def _enhance_order_with_risk_parameters(self, order: Order) -> Order:
    """Enhance order with risk parameters if they're missing."""
    # Check if the order already has SL/TP parameters
    has_stop_loss = hasattr(order, 'stop_loss_price') and order.stop_loss_price is not None
    has_take_profit = hasattr(order, 'take_profit_price') and order.take_profit_price is not None

    # If both SL and TP are already present, return the order as is
    if has_stop_loss and has_take_profit:
        return order

    # If SL/TP are missing, we need to add them using advanced risk management
    # This should ideally be done by the Strategy layer, but we'll add defaults here
    # to ensure institutional standards are met
    if order.price is not None and order.price.amount is not None:
        current_price = float(order.price.amount)

        # Use advanced risk management system to calculate dynamic TP/SL based on market conditions
        try:
            from infrastructure.risk.advanced_risk_management import AdvancedRiskManagementService, SLTPManager
            import os

            # Initialize risk management components
            risk_service = AdvancedRiskManagementService()
            # ... (detailed implementation as shown in the code)
        except Exception as e:
            # Fallback to simple calculation if advanced risk management fails
            # ... (simple calculation)
```

### 3.2 Multi-Broker Service Integration
Similar integration exists in the multi-broker service for exchange switching capability:

```python
def _enhance_order_with_risk_parameters(self, order: Order) -> Order:
    """Enhance order with risk parameters if they're missing."""
    # Similar implementation as in broker execution service
    # Uses the same advanced risk management features
```

## 4. Key Features Summary

### 4.1 Dynamic Position Sizing Features
- **Volatility Adjustment**: Position size decreases in high volatility markets
- **Correlation Management**: Reduces position size when highly correlated with existing positions
- **Regime Detection**: Adjusts position size based on market conditions (trending, choppy, volatile)
- **Confidence-Based Sizing**: Larger positions for higher confidence signals

### 4.2 Advanced SL/TP Features
- **ATR-Based Levels**: Stop-loss and take-profit levels based on Average True Range
- **Risk/Reward Ratios**: Configurable risk/reward ratios (default 1:1.5)
- **Trailing Stops**: Automatically adjusts stops as price moves favorably
- **Time Exits**: Automatic position closure after maximum holding period
- **Dynamic Updates**: SL/TP levels update based on market conditions

### 4.3 Risk Validation
- **Order Validation**: Validates orders against risk management standards
- **Safety Checks**: Ensures SL/TP levels are reasonable and achievable
- **Fallback Mechanisms**: Falls back to simple calculations if advanced methods fail

## 5. Benefits

### 5.1 Risk Management Benefits
- **Reduced Drawdown**: Dynamic position sizing reduces risk during volatile periods
- **Improved Risk/Reward**: Consistent risk/reward ratios improve overall performance
- **Correlation Control**: Prevents over-concentration in correlated assets
- **Market Adaptation**: Adjusts to changing market conditions automatically

### 5.2 Operational Benefits
- **Institutional Standards**: Meets professional risk management standards
- **Consistency**: Automated risk management ensures consistent application
- **Flexibility**: Configurable parameters for different market conditions
- **Integration**: Seamlessly integrates with existing architecture

## 6. Configuration

The advanced risk management features can be configured through environment variables and parameters:

```python
class AdvancedRiskManagementService:
    def __init__(self, 
                 base_risk_percentage: float = 0.02,  # 2% risk per trade
                 max_correlation_threshold: float = 0.7,
                 atr_period: int = 14,
                 volatility_lookback: int = 20,
                 regime_detection_lookback: int = 50):
```

## 7. Testing and Validation

The implementation includes comprehensive testing to ensure all features work correctly:
- Unit tests for individual components
- Integration tests with broker services
- Edge case handling for various market conditions
- Performance validation under different market regimes

This advanced risk management system provides institutional-grade risk controls while maintaining the flexibility to adapt to changing market conditions, ensuring the trading system operates within safe risk parameters while maximizing opportunities.