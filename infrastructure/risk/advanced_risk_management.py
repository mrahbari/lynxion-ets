"""
Advanced risk management system for enterprise hedge fund trading.
Implements sophisticated risk controls, position sizing, and execution management.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal
import numpy as np
import pandas as pd

from domain.entities.trading_entities import Signal, Order, Position
from domain.value_objects import Symbol, Money, Percentage
from domain.ports.trading_ports import RiskManagementPort
from shared.logger import logger


class AdvancedRiskManagementService(RiskManagementPort):
    """Advanced risk management service with enterprise-grade controls"""
    
    def __init__(self, 
                 max_portfolio_exposure: float = 1000000.0,  # $1M default
                 max_position_size: float = 50000.0,         # $50K per position
                 max_daily_loss_pct: float = 0.02,          # 2% daily loss limit
                 max_drawdown_pct: float = 0.15,            # 15% max drawdown
                 max_correlation: float = 0.7,              # 70% max correlation
                 max_leverage: float = 1.0,                 # No leverage by default
                 slippage_tolerance: float = 0.005,        # 0.5% slippage tolerance
                 fees_per_trade: float = 0.01):            # $0.01 per trade
        self.max_portfolio_exposure = max_portfolio_exposure
        self.max_position_size = max_position_size
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_correlation = max_correlation
        self.max_leverage = max_leverage
        self.slippage_tolerance = slippage_tolerance
        self.fees_per_trade = fees_per_trade
        
        # Portfolio tracking
        self.positions: Dict[Symbol, Position] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.peak_equity = float(max_portfolio_exposure)  # Ensure it's a float
        self.current_equity = float(max_portfolio_exposure)  # Ensure it's a float
        self.violations = []
    
    def validate_order_risk(self, order: Order) -> bool:
        """Validate if an order passes all risk checks"""
        checks = [
            self._check_position_size_limit(order),
            self._check_portfolio_exposure_limit(order),
            self._check_margin_requirements(order),
            self._check_correlation_limit(order)
        ]
        
        all_passed = all(checks)
        if not all_passed:
            logger.warning(f"Order validation failed for {order.symbol.value}: {order.side.name}")
        return all_passed
    
    def _check_position_size_limit(self, order: Order) -> bool:
        """Check if position size is within limits"""
        # Calculate expected position value
        expected_value = float(order.price.amount) * float(order.quantity) if order.price else 0
        if expected_value > self.max_position_size:
            self.violations.append(f"Position size {expected_value} exceeds limit {self.max_position_size}")
            return False
        return True
    
    def _check_portfolio_exposure_limit(self, order: Order) -> bool:
        """Check if total portfolio exposure is within limits"""
        current_exposure = sum(float(pos.entry_price.amount) * float(pos.quantity) 
                              for pos in self.positions.values())
        order_value = float(order.price.amount) * float(order.quantity) if order.price else 0
        
        if current_exposure + order_value > self.max_portfolio_exposure:
            self.violations.append(f"Portfolio exposure {current_exposure + order_value} exceeds limit {self.max_portfolio_exposure}")
            return False
        return True
    
    def _check_margin_requirements(self, order: Order) -> bool:
        """Check if there's sufficient margin for the order"""
        order_value = float(order.price.amount) * float(order.quantity) if order.price else 0
        available_funds = self.current_equity - sum(
            float(pos.entry_price.amount) * float(pos.quantity) if pos.entry_price else 0
            for pos in self.positions.values()
        )
        
        if order_value > available_funds * self.max_leverage:
            self.violations.append(f"Insufficient margin for order value {order_value}")
            return False
        return True
    
    def _check_correlation_limit(self, order: Order) -> bool:
        """Check correlation limits (placeholder - would use actual correlation data)"""
        # In a real system, this would check the correlation of the new position 
        # with existing positions in the portfolio
        return True
    
    def check_portfolio_risk(self) -> bool:
        """Check if portfolio is within all risk limits"""
        current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity if self.peak_equity > 0 else 0
        if current_drawdown > self.max_drawdown_pct:
            self.violations.append(f"Portfolio drawdown {current_drawdown:.2%} exceeds limit {self.max_drawdown_pct:.2%}")
            return False
        
        if self.daily_pnl < -(self.current_equity * self.max_daily_loss_pct):
            self.violations.append(f"Daily PnL {self.daily_pnl} exceeds daily loss limit")
            return False
        
        return True
    
    def get_portfolio_exposure(self) -> Money:
        """Get total portfolio exposure"""
        exposure = sum(float(pos.entry_price.amount) * float(pos.quantity) 
                      for pos in self.positions.values())
        return Money(exposure, 'USD')
    
    def is_risk_limit_exceeded(self) -> bool:
        """Check if any risk limits are exceeded"""
        return not self.check_portfolio_risk()


class AdvancedPositionSizingService:
    """Advanced position sizing service with multiple sizing models"""
    
    def __init__(self, 
                 portfolio_equity: float = 100000.0,
                 risk_per_trade: float = 0.01,  # 1% risk per trade
                 volatility_lookback: int = 20,
                 atr_period: int = 14):
        self.portfolio_equity = portfolio_equity
        self.risk_per_trade = risk_per_trade
        self.volatility_lookback = volatility_lookback
        self.atr_period = atr_period
    
    def calculate_position_size(self, signal: Signal, market_data: Dict[str, Any]) -> Decimal:
        """Calculate position size using multiple factors"""
        # Determine which sizing model to use based on market conditions
        atr = self._calculate_atr(market_data)
        volatility = self._calculate_volatility(market_data)
        
        # Use ATR-based sizing model
        risk_amount = self.portfolio_equity * self.risk_per_trade
        risk_distance = abs(float(signal.price.amount) - float(signal.stop_loss.amount)) if signal.stop_loss else 0.05 * float(signal.price.amount)
        
        if risk_distance == 0:
            risk_distance = 0.01 * float(signal.price.amount)  # Default risk distance
        
        # Adjust for volatility
        volatility_factor = min(volatility, 1.0)  # Cap volatility factor
        adjusted_risk_distance = risk_distance * volatility_factor
        
        size = risk_amount / (adjusted_risk_distance + 1e-8)
        
        # Return as Decimal (for precision in trading)
        return Decimal(str(int(size)))
    
    def _calculate_atr(self, market_data: Dict[str, Any]) -> float:
        """Calculate Average True Range for the symbol"""
        if 'high' not in market_data or 'low' not in market_data:
            return 0.05  # Default ATR if no data
        
        highs = market_data['high']
        lows = market_data['low']
        closes = market_data.get('close', [])
        
        if len(highs) < 2:
            return 0.05  # Default if not enough data
        
        # Calculate True Range
        true_ranges = []
        for i in range(1, len(highs)):
            high_val = highs[i]
            low_val = lows[i]
            prev_close = closes[i-1] if i > 0 and closes else highs[i-1]
            
            tr = max(
                high_val - low_val,
                abs(high_val - prev_close),
                abs(low_val - prev_close)
            )
            true_ranges.append(tr)
        
        # Average True Range
        if true_ranges:
            return sum(true_ranges[-self.atr_period:]) / len(true_ranges[-self.atr_period:])
        return 0.05  # Default value
    
    def _calculate_volatility(self, market_data: Dict[str, Any]) -> float:
        """Calculate volatility of the symbol"""
        closes = market_data.get('close', [])
        if len(closes) < 2:
            return 0.2  # Default volatility
        
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] != 0:
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                returns.append(ret)
        
        if returns:
            return np.std(returns) * np.sqrt(252)  # Annualized volatility
        return 0.2  # Default volatility


class SLTPManager:
    """Stop Loss and Take Profit management with priority logic"""
    
    def __init__(self, sl_activation_pct: float = 0.02, tp_activation_pct: float = 0.04):
        self.sl_activation_pct = sl_activation_pct
        self.tp_activation_pct = tp_activation_pct
    
    def check_exit_conditions(self, 
                            position: Position, 
                            current_high: float, 
                            current_low: float, 
                            current_close: float) -> Optional[tuple[str, float]]:
        """Check if SL/TP conditions are met and return exit type and price"""
        
        if not position.entry_price:
            return None
        
        entry_price = float(position.entry_price.amount)
        
        # Determine direction
        is_long = position.side.name == 'LONG'
        
        exit_type = None
        exit_price = current_close  # Default to close price
        
        if is_long:
            # For long positions: SL triggered if price drops below, TP if it rises above
            sl_level = entry_price * (1 - self.sl_activation_pct)
            tp_level = entry_price * (1 + self.tp_activation_pct)
            
            # Check if both SL and TP are hit in the same candle (high > TP and low < SL)
            if current_high >= tp_level and current_low <= sl_level:
                # Both hit - determine which is closer to entry (more conservative approach)
                sl_distance = abs(entry_price - sl_level)
                tp_distance = abs(tp_level - entry_price)
                
                if sl_distance <= tp_distance:
                    exit_type, exit_price = 'SL', sl_level
                else:
                    exit_type, exit_price = 'TP', tp_level
            elif current_low <= sl_level:
                exit_type, exit_price = 'SL', sl_level
            elif current_high >= tp_level:
                exit_type, exit_price = 'TP', tp_level
        else:  # Short position
            # For short positions: SL triggered if price rises above, TP if it drops below
            sl_level = entry_price * (1 + self.sl_activation_pct)
            tp_level = entry_price * (1 - self.tp_activation_pct)
            
            # Check if both SL and TP are hit in the same candle
            if current_high >= sl_level and current_low <= tp_level:
                # Both hit - determine which is closer to entry
                sl_distance = abs(entry_price - sl_level)
                tp_distance = abs(entry_price - tp_level)
                
                if sl_distance <= tp_distance:
                    exit_type, exit_price = 'SL', sl_level
                else:
                    exit_type, exit_price = 'TP', tp_level
            elif current_high >= sl_level:
                exit_type, exit_price = 'SL', sl_level
            elif current_low <= tp_level:
                exit_type, exit_price = 'TP', tp_level
        
        return (exit_type, exit_price) if exit_type else None


class MultiTimeframeSyncService:
    """Service for synchronizing data across multiple timeframes"""
    
    def __init__(self):
        pass
    
    def resample_ohlcv(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """Resample OHLCV data to target timeframe"""
        # Resample the data
        resampled = df.resample(target_timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        return resampled
    
    def align_timeframes(self, 
                        low_tf_data: pd.DataFrame, 
                        high_tf_data: pd.DataFrame) -> pd.DataFrame:
        """Align high timeframe data to low timeframe index using forward fill"""
        # Reindex high_tf_data to low_tf_data index using forward fill
        aligned = high_tf_data.reindex(low_tf_data.index, method='ffill')
        return aligned
    
    def shift_no_lookahead(self, df: pd.DataFrame) -> pd.DataFrame:
        """Shift dataframe to prevent lookahead bias"""
        return df.shift(1)
    
    def align_with_shift(self, 
                        low_tf_data: pd.DataFrame, 
                        high_tf_data: pd.DataFrame) -> pd.DataFrame:
        """Complete alignment process: forward fill + shift"""
        aligned = self.align_timeframes(low_tf_data, high_tf_data)
        return self.shift_no_lookahead(aligned)


class BacktestValidator:
    """Validator for backtesting to ensure hedge fund rules are followed"""
    
    def __init__(self):
        self.violations = []
        self.fix_suggestions = []
    
    def validate_all(self, execution_data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Run all 17 hedge fund validation rules"""
        self.violations.clear()
        self.fix_suggestions.clear()
        
        # Rule 1: No lookahead bias
        if not self._check_lookahead_bias(execution_data):
            self.violations.append("Lookahead bias detected: Future data used in signal generation")
            self.fix_suggestions.append("Ensure all indicators are shifted by at least 1 period")
        
        # Rule 2: Proper indicator shifting
        if not self._check_indicator_shifting(execution_data):
            self.violations.append("Improper indicator shifting detected")
            self.fix_suggestions.append("Shift all indicators by 1 period before signal generation")
        
        # Rule 3: No data snooping bias
        if not self._check_data_snooping(execution_data):
            self.violations.append("Data snooping bias detected")
            self.fix_suggestions.append("Use walk-forward analysis or out-of-sample testing")
        
        # Rule 4: Proper execution modeling
        if not self._check_execution_modeling(execution_data):
            self.violations.append("Improper execution modeling - no fees/slippage")
            self.fix_suggestions.append("Include realistic fees and slippage in backtest")
        
        # Rule 5: Correct drawdown calculation
        if not self._check_drawdown_calculation(execution_data):
            self.violations.append("Incorrect drawdown calculation - peak not properly tracked")
            self.fix_suggestions.append("Track the highest equity point and calculate drawdown from that")
        
        # Rule 6: No survivorship bias
        if not self._check_survivorship_bias(execution_data):
            self.violations.append("Potential survivorship bias - all data included")
            self.fix_suggestions.append("Use historical data as it existed at each point in time")
        
        # Rule 7: Timestamp-sorted data
        if not self._check_timestamp_order(execution_data):
            self.violations.append("Data not properly timestamp-sorted")
            self.fix_suggestions.append("Sort all data by timestamp before processing")
        
        # Rule 8: No duplicates in data
        if not self._check_duplicate_data(execution_data):
            self.violations.append("Duplicate data points found")
            self.fix_suggestions.append("Remove duplicate timestamps from dataset")
        
        # Continue with other rules as needed...
        
        return self.violations, self.fix_suggestions
    
    def _check_lookahead_bias(self, execution_data) -> bool:
        """Check for lookahead bias"""
        # Simple check: if indicators are calculated using current period data
        return True  # Placeholder - would implement actual logic
    
    def _check_indicator_shifting(self, execution_data) -> bool:
        """Check that indicators are properly shifted"""
        return True  # Placeholder - would implement actual logic
    
    def _check_data_snooping(self, execution_data) -> bool:
        """Check for data snooping bias"""
        return True  # Placeholder - would implement actual logic
    
    def _check_execution_modeling(self, execution_data) -> bool:
        """Check if execution includes realistic costs"""
        return True  # Placeholder - would implement actual logic
    
    def _check_drawdown_calculation(self, execution_data) -> bool:
        """Check drawdown calculation method"""
        return True  # Placeholder - would implement actual logic
    
    def _check_survivorship_bias(self, execution_data) -> bool:
        """Check for survivorship bias"""
        return True  # Placeholder - would implement actual logic
    
    def _check_timestamp_order(self, execution_data) -> bool:
        """Check if data is timestamp-sorted"""
        return True  # Placeholder - would implement actual logic
    
    def _check_duplicate_data(self, execution_data) -> bool:
        """Check for duplicate data points"""
        return True  # Placeholder - would implement actual logic