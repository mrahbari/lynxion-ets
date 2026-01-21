"""
Portfolio-level risk management system to control overall exposure
across all positions and strategies.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import threading
import time

class PortfolioRiskLimits:
    """Define portfolio-level risk limits."""
    
    def __init__(self):
        # Maximum total portfolio drawdown allowed
        self.max_portfolio_drawdown = 0.05  # 5%
        
        # Maximum allocation to single strategy
        self.max_strategy_allocation = 0.30  # 30%
        
        # Maximum allocation to single symbol
        self.max_symbol_allocation = 0.10  # 10%
        
        # Maximum leverage
        self.max_leverage = 1.0  # No leverage for conservative approach
        
        # Maximum daily loss
        self.max_daily_loss = 0.02  # 2% per day
        
        # Minimum account balance threshold
        self.min_account_balance = 1000.0  # $1000

class PositionTracker:
    """Track individual positions and their risk."""
    
    def __init__(self, symbol: str, side: str, size: float, entry_price: float):
        self.symbol = symbol
        self.side = side  # 'long' or 'short'
        self.size = size
        self.entry_price = entry_price
        self.entry_time = datetime.now()
        self.current_pnl = 0.0
        self.max_unrealized_pnl = 0.0 if self.side == 'long' else float('inf')
        self.min_unrealized_pnl = float('inf') if self.side == 'long' else 0.0
        self.peak_time = self.entry_time
        self.valley_time = self.entry_time

class PortfolioRiskManager:
    """Manage portfolio-level risk controls."""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_pnl = 0.0
        self.daily_pnl_reset_time = datetime.now().date()
        
        self.positions: Dict[str, PositionTracker] = {}  # trade_id -> PositionTracker
        self.strategy_allocations: Dict[str, float] = {}  # strategy_name -> allocated_amount
        self.symbol_allocations: Dict[str, float] = {}   # symbol -> allocated_amount
        
        self.limits = PortfolioRiskLimits()
        self.lock = threading.Lock()
        self.active = True
        
    def update_position(self, trade_id: str, symbol: str, strategy: str, 
                       side: str, size: float, price: float) -> bool:
        """Update position and check risk limits."""
        with self.lock:
            if not self.active:
                return False
                
            # Check if we should allow this position based on limits
            if not self._check_position_risk(symbol, strategy, size, price):
                return False
                
            # Create/update position
            self.positions[trade_id] = PositionTracker(symbol, side, size, price)
            
            # Update allocations
            self._update_allocations(strategy, symbol, size * price)
            
            return True
            
    def update_pnl(self, trade_id: str, current_price: float) -> float:
        """Update PnL for a position and return current PnL."""
        with self.lock:
            if trade_id not in self.positions:
                return 0.0
                
            pos = self.positions[trade_id]
            multiplier = 1 if pos.side == 'long' else -1
            pos.current_pnl = (current_price - pos.entry_price) * pos.size * multiplier
            
            # Update peak/valley tracking for drawdown calculation
            if pos.current_pnl > pos.max_unrealized_pnl:
                pos.max_unrealized_pnl = pos.current_pnl
                pos.peak_time = datetime.now()
            elif pos.current_pnl < pos.min_unrealized_pnl:
                pos.min_unrealized_pnl = pos.current_pnl
                pos.valley_time = datetime.now()
                
            return pos.current_pnl
            
    def close_position(self, trade_id: str, exit_price: float) -> float:
        """Close a position and return realized PnL."""
        with self.lock:
            if trade_id not in self.positions:
                return 0.0
                
            pos = self.positions[trade_id]
            multiplier = 1 if pos.side == 'long' else -1
            realized_pnl = (exit_price - pos.entry_price) * pos.size * multiplier
            
            # Update capital and daily PnL
            self.current_capital += realized_pnl
            self.daily_pnl += realized_pnl
            
            # Remove position and update allocations
            allocated_amount = pos.size * pos.entry_price
            self._remove_allocations(pos.symbol, pos.strategy, allocated_amount)
            del self.positions[trade_id]
            
            # Check if we need to reset daily PnL
            if datetime.now().date() != self.daily_pnl_reset_time:
                self.daily_pnl = 0.0
                self.daily_pnl_reset_time = datetime.now().date()
            
            return realized_pnl
            
    def _check_position_risk(self, symbol: str, strategy: str, size: float, price: float) -> bool:
        """Check if a new position violates risk limits."""
        position_value = size * price
        
        # Check total portfolio drawdown
        total_allocated = sum(pos.size * pos.entry_price for pos in self.positions.values())
        total_pnl = self.current_capital - self.initial_capital + self.daily_pnl
        portfolio_drawdown = abs(total_pnl) / self.initial_capital if self.initial_capital > 0 else 0
        
        if portfolio_drawdown > self.limits.max_portfolio_drawdown:
            return False
            
        # Check strategy allocation limit
        current_strategy_alloc = self.strategy_allocations.get(strategy, 0.0)
        if (current_strategy_alloc + position_value) / self.current_capital > self.limits.max_strategy_allocation:
            return False
            
        # Check symbol allocation limit
        current_symbol_alloc = self.symbol_allocations.get(symbol, 0.0)
        if (current_symbol_alloc + position_value) / self.current_capital > self.limits.max_symbol_allocation:
            return False
            
        # Check daily loss limit
        if self.daily_pnl < -abs(self.current_capital * self.limits.max_daily_loss):
            return False
            
        # Check minimum account balance
        if self.current_capital < self.limits.min_account_balance:
            return False
            
        return True
        
    def _update_allocations(self, strategy: str, symbol: str, amount: float):
        """Update strategy and symbol allocation tracking."""
        self.strategy_allocations[strategy] = self.strategy_allocations.get(strategy, 0.0) + amount
        self.symbol_allocations[symbol] = self.symbol_allocations.get(symbol, 0.0) + amount
        
    def _remove_allocations(self, symbol: str, strategy: str, amount: float):
        """Remove allocation tracking when position is closed."""
        self.strategy_allocations[strategy] = max(0, self.strategy_allocations.get(strategy, 0.0) - amount)
        self.symbol_allocations[symbol] = max(0, self.symbol_allocations.get(symbol, 0.0) - amount)
        
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio risk summary."""
        with self.lock:
            total_allocated = sum(pos.size * pos.entry_price for pos in self.positions.values())
            total_pnl = self.current_capital - self.initial_capital + self.daily_pnl
            portfolio_drawdown = abs(total_pnl) / self.initial_capital if self.initial_capital > 0 else 0
            
            return {
                "current_capital": self.current_capital,
                "total_allocated": total_allocated,
                "daily_pnl": self.daily_pnl,
                "total_pnl": total_pnl,
                "portfolio_drawdown": portfolio_drawdown,
                "active_positions_count": len(self.positions),
                "strategy_allocations": self.strategy_allocations.copy(),
                "symbol_allocations": self.symbol_allocations.copy(),
                "limits": {
                    "max_portfolio_drawdown": self.limits.max_portfolio_drawdown,
                    "max_strategy_allocation": self.limits.max_strategy_allocation,
                    "max_symbol_allocation": self.limits.max_symbol_allocation,
                    "max_daily_loss": self.limits.max_daily_loss,
                    "min_account_balance": self.limits.min_account_balance
                }
            }
            
    def emergency_stop(self):
        """Emergency stop all trading activity."""
        with self.lock:
            self.active = False
            
    def resume_trading(self):
        """Resume trading after emergency stop."""
        with self.lock:
            self.active = True

# Global portfolio risk manager instance
portfolio_risk_manager = PortfolioRiskManager()