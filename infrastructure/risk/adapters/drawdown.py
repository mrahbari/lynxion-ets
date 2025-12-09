from typing import Dict, List
from shared.types import Signal, Order
from shared.logger import logger
from datetime import datetime, timedelta
import numpy as np


class DrawdownManager:
    """Manages and limits drawdown risk"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Drawdown parameters
        self.max_drawdown_limit = config.get('max_drawdown_limit', 0.15)  # 15% max drawdown
        self.max_drawdown_rolling = config.get('max_drawdown_rolling', 0.10)  # 10% max rolling drawdown
        self.max_drawdown_duration = config.get('max_drawdown_duration', timedelta(days=30))  # Max duration in drawdown
        self.drawdown_recovery_factor = config.get('drawdown_recovery_factor', 0.5)  # Scale back risk by 50% after drawdown
        
        # Portfolio tracking
        self.initial_portfolio_value = config.get('initial_portfolio_value', 100000)
        self.current_portfolio_value = self.initial_portfolio_value
        self.peak_portfolio_value = self.initial_portfolio_value
        self.drawdown_start_value = self.initial_portfolio_value
        
        # Rolling drawdown tracking
        self.rolling_window = config.get('rolling_window', timedelta(days=30))
        self.value_history: List[Dict] = []  # List of {'value': float, 'timestamp': datetime}
        
        # Drawdown history
        self.drawdown_periods: List[Dict] = []  # List of {'start': value, 'end': value, 'peak': value, 'trough': value, 'duration': timedelta}
        self.current_drawdown_start = None
        
        # Risk scaling
        self.risk_multiplier = 1.0  # Multiplier applied to position sizes based on drawdown state
        
        # Alert thresholds
        self.alert_thresholds = config.get('alert_thresholds', [0.05, 0.10, 0.15])  # 5%, 10%, 15% drawdown alerts
    
    def update_portfolio_value(self, new_value: float):
        """Update the current portfolio value"""
        old_value = self.current_portfolio_value
        self.current_portfolio_value = new_value
        
        # Update peak value
        if new_value > self.peak_portfolio_value:
            self.peak_portfolio_value = new_value
            # If we're recovering from drawdown, update multiplier
            if self.risk_multiplier < 1.0:
                self.risk_multiplier = min(1.0, self.risk_multiplier + 0.05)  # Slowly increase risk after recovery
        
        # Add to history for rolling calculations
        self.value_history.append({
            'value': new_value,
            'timestamp': datetime.now()
        })
        
        # Clean old history entries outside the rolling window
        cutoff_time = datetime.now() - self.rolling_window
        self.value_history = [v for v in self.value_history if v['timestamp'] > cutoff_time]
        
        # Check for drawdown and update state
        self._check_drawdown_state()
    
    def _check_drawdown_state(self):
        """Check if we're in drawdown and update state"""
        current_drawdown = self.get_current_drawdown()
        
        # Check for alert thresholds
        for threshold in sorted(self.alert_thresholds, reverse=True):
            if current_drawdown >= threshold and current_drawdown - 0.01 < threshold:
                logger.warning(f"Drawdown alert: Current drawdown is {current_drawdown:.3f}, threshold {threshold}")
        
        # Check if we're entering a drawdown period
        if current_drawdown > 0.01 and self.current_drawdown_start is None:
            self.current_drawdown_start = datetime.now()
            self.drawdown_start_value = self.peak_portfolio_value
            logger.info(f"Entered drawdown period. Peak value: {self.drawdown_start_value}, Current value: {self.current_portfolio_value}")
        
        # Check if we're exiting a drawdown period
        if current_drawdown <= 0.001 and self.current_drawdown_start is not None:
            # Record the completed drawdown period
            if self.drawdown_start_value > self.current_portfolio_value:
                drawdown_period = {
                    'start': self.current_drawdown_start,
                    'end': datetime.now(),
                    'peak': self.drawdown_start_value,
                    'trough': self.current_portfolio_value,
                    'max_value': max(self.drawdown_start_value, 
                                   max(v['value'] for v in self.value_history 
                                       if v['timestamp'] >= self.current_drawdown_start) if self.value_history else self.drawdown_start_value)
                }
                self.drawdown_periods.append(drawdown_period)
            
            self.current_drawdown_start = None
            logger.info(f"Exited drawdown period. Recovered to peak value: {self.current_portfolio_value}")
    
    def is_drawdown_limit_exceeded(self) -> bool:
        """Check if drawdown limits are exceeded"""
        current_drawdown = self.get_current_drawdown()
        rolling_drawdown = self.get_rolling_drawdown()
        
        if current_drawdown > self.max_drawdown_limit:
            logger.error(f"Maximum drawdown limit exceeded: {current_drawdown:.3f} > {self.max_drawdown_limit}")
            return True
        
        if rolling_drawdown > self.max_drawdown_rolling:
            logger.error(f"Maximum rolling drawdown limit exceeded: {rolling_drawdown:.3f} > {self.max_drawdown_rolling}")
            return True
        
        # Check drawdown duration if applicable
        if (self.current_drawdown_start and 
            datetime.now() - self.current_drawdown_start > self.max_drawdown_duration):
            logger.error(f"Maximum drawdown duration exceeded: {datetime.now() - self.current_drawdown_start} > {self.max_drawdown_duration}")
            return True
        
        return False
    
    def get_current_drawdown(self) -> float:
        """Calculate the current drawdown from the peak"""
        if self.peak_portfolio_value == 0:
            return 0.0
        return max(0, (self.peak_portfolio_value - self.current_portfolio_value) / self.peak_portfolio_value)
    
    def get_rolling_drawdown(self) -> float:
        """Calculate the drawdown within the rolling window"""
        if not self.value_history:
            return 0.0
        
        # Find the peak value within the history
        peak_in_window = max(v['value'] for v in self.value_history)
        current_in_window = self.value_history[-1]['value']
        
        if peak_in_window == 0:
            return 0.0
        
        return max(0, (peak_in_window - current_in_window) / peak_in_window)
    
    def adjust_risk_for_drawdown(self) -> float:
        """Adjust risk based on current drawdown state"""
        current_drawdown = self.get_current_drawdown()
        
        # If in significant drawdown, reduce risk
        if current_drawdown > self.max_drawdown_limit * 0.7:  # 70% of limit
            self.risk_multiplier = max(0.1, self.risk_multiplier - 0.1)  # Reduce risk further
        elif current_drawdown > self.max_drawdown_limit * 0.4:  # 40% of limit
            self.risk_multiplier = max(0.3, self.risk_multiplier - 0.05)  # Reduce risk somewhat
        elif current_drawdown > 0.01:  # In any drawdown
            self.risk_multiplier = max(0.7, self.risk_multiplier - 0.02)  # Slightly reduce risk
        
        # Ensure multiplier doesn't go too low
        self.risk_multiplier = max(0.1, self.risk_multiplier)
        
        return self.risk_multiplier
    
    def should_restrict_trading(self) -> bool:
        """Determine if trading should be restricted due to drawdown"""
        return self.is_drawdown_limit_exceeded()
    
    def apply_drawdown_risk_adjustment(self, signal: Signal, original_position_size: float) -> float:
        """Apply drawdown-based risk adjustment to a position size"""
        adjusted_size = original_position_size * self.adjust_risk_for_drawdown()
        
        # Log the adjustment if significant
        if self.risk_multiplier < 0.8:
            logger.info(f"Position size reduced due to drawdown: {original_position_size:.4f} -> {adjusted_size:.4f} "
                       f"(multiplier: {self.risk_multiplier:.3f})")
        
        return adjusted_size
    
    def get_drawdown_report(self) -> Dict:
        """Get a comprehensive drawdown report"""
        return {
            'current_drawdown': self.get_current_drawdown(),
            'rolling_drawdown': self.get_rolling_drawdown(),
            'max_drawdown_limit': self.max_drawdown_limit,
            'max_rolling_drawdown_limit': self.max_drawdown_rolling,
            'peak_value': self.peak_portfolio_value,
            'current_value': self.current_portfolio_value,
            'total_return': (self.current_portfolio_value - self.initial_portfolio_value) / self.initial_portfolio_value,
            'risk_multiplier': self.risk_multiplier,
            'in_drawdown': self.current_drawdown_start is not None,
            'drawdown_start': self.current_drawdown_start,
            'drawdown_duration': (datetime.now() - self.current_drawdown_start) if self.current_drawdown_start else timedelta(0),
            'drawdown_periods_count': len(self.drawdown_periods),
            'largest_drawdown_period': max([abs((p['peak'] - p['trough']) / p['peak']) for p in self.drawdown_periods], default=0) if self.drawdown_periods else 0
        }
    
    def reset_drawdown_tracking(self, initial_value: float = None):
        """Reset all drawdown tracking"""
        if initial_value is not None:
            self.initial_portfolio_value = initial_value
            self.current_portfolio_value = initial_value
        
        self.peak_portfolio_value = self.current_portfolio_value
        self.drawdown_start_value = self.current_portfolio_value
        self.value_history.clear()
        self.drawdown_periods.clear()
        self.current_drawdown_start = None
        self.risk_multiplier = 1.0
        
        logger.info("Drawdown tracking reset")
    
    def get_recovery_status(self) -> Dict:
        """Get information about recovery from drawdown"""
        recovery_status = {
            'has_recovered': False,
            'recovery_percentage': 0.0,
            'distance_from_peak': 0.0
        }
        
        if self.peak_portfolio_value > 0:
            recovery_percentage = (self.current_portfolio_value - (self.peak_portfolio_value * (1 - self.max_drawdown_limit))) / (self.peak_portfolio_value * self.max_drawdown_limit) if self.max_drawdown_limit > 0 else 0
            distance_from_peak = (self.peak_portfolio_value - self.current_portfolio_value) / self.peak_portfolio_value
            
            recovery_status['recovery_percentage'] = max(0.0, recovery_percentage)
            recovery_status['distance_from_peak'] = distance_from_peak
            recovery_status['has_recovered'] = self.current_portfolio_value >= self.peak_portfolio_value * (1 - self.max_drawdown_limit * 0.1)  # 90% of max drawdown limit
        
        return recovery_status