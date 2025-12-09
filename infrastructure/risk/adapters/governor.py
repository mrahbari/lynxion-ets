from typing import Dict, List, Optional
from shared.types import Order, Signal, Position, Balance
from shared.logger import logger
from datetime import datetime, timedelta
import numpy as np


class RiskGovernor:
    """Central risk management system for all trading activities"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Risk parameters
        self.max_portfolio_risk = config.get('max_portfolio_risk', 0.02)  # 2% max portfolio risk
        self.max_position_risk = config.get('max_position_risk', 0.01)   # 1% max single position risk
        self.max_drawdown = config.get('max_drawdown', 0.15)             # 15% max drawdown
        self.max_correlation = config.get('max_correlation', 0.7)        # 0.7 max correlation between positions
        self.max_leverage = config.get('max_leverage', 1.0)              # 1x max leverage (no leverage)
        
        # Tracking state
        self.current_positions: Dict[str, Position] = {}
        self.current_balances: Dict[str, Balance] = {}
        self.trade_history = []
        self.daily_pnl = 0
        self.period_start_balance = 0
        self.max_capital_exposure = 0
        self.total_capital = config.get('initial_capital', 100000)
        
        # Timestamps
        self.start_time = datetime.now()
        self.daily_reset_time = datetime.combine(datetime.now().date(), datetime.min.time()).replace(hour=0, minute=0, second=0)
        
        # Asset-specific risk limits
        self.asset_risk_limits: Dict[str, float] = config.get('asset_risk_limits', {})
        self.asset_correlation_limits: Dict[str, float] = config.get('asset_correlation_limits', {})
    
    def assess_order_risk(self, order: Order, current_price: float) -> Dict:
        """Assess risk for a potential order"""
        risk_assessment = {
            'approved': True,
            'reasons': [],
            'adjusted_size': order.quantity,
            'risk_score': 0.0,
            'position_impact': {}
        }
        
        # Check if we're within daily PnL limits
        if hasattr(self, 'daily_pnl') and self.config.get('max_daily_loss'):
            max_daily_loss = self.config['max_daily_loss']
            if self.daily_pnl <= -max_daily_loss * self.total_capital:
                risk_assessment['approved'] = False
                risk_assessment['reasons'].append(f"Daily loss limit exceeded: {self.daily_pnl:.2f} vs limit {-max_daily_loss * self.total_capital:.2f}")
                return risk_assessment
        
        # Calculate potential position size risk
        potential_value = order.quantity * current_price
        portfolio_risk = potential_value / self.total_capital
        
        if portfolio_risk > self.max_position_risk:
            risk_assessment['approved'] = False
            risk_assessment['reasons'].append(f"Position risk exceeds limit: {portfolio_risk:.3f} > {self.max_position_risk}")
            # Suggest adjusted position size
            max_position_value = self.max_position_risk * self.total_capital
            risk_assessment['adjusted_size'] = min(order.quantity, max_position_value / current_price)
        
        # Check asset-specific limits
        if order.symbol in self.asset_risk_limits:
            asset_limit = self.asset_risk_limits[order.symbol]
            # Calculate current exposure to this asset
            current_asset_exposure = sum(
                pos.quantity * pos.entry_price 
                for pos in self.current_positions.values() 
                if pos.symbol == order.symbol
            )
            potential_asset_exposure = current_asset_exposure + potential_value
            
            if potential_asset_exposure / self.total_capital > asset_limit:
                risk_assessment['approved'] = False
                risk_assessment['reasons'].append(f"Asset exposure limit exceeded for {order.symbol}")
        
        # Calculate risk score (0-1)
        risk_assessment['risk_score'] = min(1.0, portfolio_risk / self.max_position_risk)
        
        return risk_assessment
    
    def validate_order(self, order: Order, current_price: float) -> bool:
        """Validate an order against risk parameters"""
        assessment = self.assess_order_risk(order, current_price)
        return assessment['approved']
    
    def update_position(self, position: Position):
        """Update the system with a new position"""
        if position.quantity == 0:
            if position.symbol in self.current_positions:
                del self.current_positions[position.symbol]
        else:
            self.current_positions[position.symbol] = position
            
        # Update max capital exposure
        total_exposure = sum(pos.quantity * pos.entry_price for pos in self.current_positions.values())
        self.max_capital_exposure = max(self.max_capital_exposure, total_exposure)
    
    def update_balance(self, balance: Balance):
        """Update balance information"""
        self.current_balances[balance.asset] = balance
        if balance.asset.upper() == 'USD' or balance.asset.upper() == 'USDT':
            self.total_capital = balance.total
    
    def calculate_portfolio_correlation(self) -> float:
        """Calculate overall portfolio correlation"""
        if len(self.current_positions) < 2:
            return 0.0
            
        # In a real system, you'd calculate correlations between all assets
        # For now, return a mock value based on position count
        return min(0.8, len(self.current_positions) * 0.1)
    
    def check_kill_switch_conditions(self) -> bool:
        """Check if any kill switch conditions are met"""
        # Check drawdown
        if self.period_start_balance > 0:
            current_drawdown = (self.period_start_balance - self.total_capital) / self.period_start_balance
            if current_drawdown > self.max_drawdown:
                logger.warning(f"Kill switch activated: Drawdown of {current_drawdown:.3f} exceeds limit {self.max_drawdown}")
                return True
        
        # Check portfolio correlation
        portfolio_corr = self.calculate_portfolio_correlation()
        if portfolio_corr > self.max_correlation:
            logger.warning(f"Kill switch activated: Portfolio correlation {portfolio_corr:.3f} exceeds limit {self.max_correlation}")
            return True
        
        # Check leverage
        total_exposure = sum(pos.quantity * pos.entry_price for pos in self.current_positions.values())
        if total_exposure > 0 and self.total_capital > 0:
            leverage = total_exposure / self.total_capital
            if leverage > self.max_leverage:
                logger.warning(f"Kill switch activated: Leverage {leverage:.3f} exceeds limit {self.max_leverage}")
                return True
        
        return False
    
    def process_fill(self, fill_data: Dict):
        """Process fill information and update risk metrics"""
        # Update daily PnL
        symbol = fill_data.get('symbol', '')
        price = fill_data.get('price', 0)
        quantity = fill_data.get('quantity', 0)
        side = fill_data.get('side', '')
        fees = fill_data.get('fees', 0)
        
        # Update trade history
        self.trade_history.append(fill_data)
        
        # Calculate profit for the fill if it closes a position
        # This is a simplified calculation
        if symbol in self.current_positions:
            existing_pos = self.current_positions[symbol]
            
            # Calculate PnL if this fill closes or reduces the position
            if (side == 'SELL' and existing_pos.side == 'LONG') or (side == 'BUY' and existing_pos.side == 'SHORT'):
                # This fill is closing the position
                pnl = (price - existing_pos.entry_price) * quantity
                if side == 'BUY':  # Closing short position
                    pnl = (existing_pos.entry_price - price) * quantity
                
                # Update daily PnL
                self.daily_pnl += pnl - fees
                logger.info(f"Position closed: {symbol}, PnL: {pnl:.2f}, fees: {fees:.2f}")
    
    def reset_daily_metrics(self):
        """Reset daily metrics"""
        if datetime.now().date() != self.daily_reset_time.date():
            self.daily_pnl = 0
            self.daily_reset_time = datetime.combine(datetime.now().date(), datetime.min.time())
    
    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics"""
        total_exposure = sum(pos.quantity * pos.entry_price for pos in self.current_positions.values())
        current_leverage = total_exposure / self.total_capital if self.total_capital > 0 else 0
        portfolio_correlation = self.calculate_portfolio_correlation()
        
        # Calculate unrealized PnL
        unrealized_pnl = 0
        for pos in self.current_positions.values():
            # This is simplified; in reality you'd need current market prices
            current_price = pos.entry_price * 1.01  # Placeholder
            pos_pnl = (current_price - pos.entry_price) * pos.quantity
            if pos.side == 'SHORT':
                pos_pnl = -pos_pnl
            unrealized_pnl += pos_pnl
        
        return {
            'total_capital': self.total_capital,
            'total_exposure': total_exposure,
            'current_leverage': current_leverage,
            'max_leverage': self.max_leverage,
            'portfolio_correlation': portfolio_correlation,
            'max_correlation': self.max_correlation,
            'daily_pnl': self.daily_pnl,
            'unrealized_pnl': unrealized_pnl,
            'position_count': len(self.current_positions),
            'active_positions': list(self.current_positions.keys()),
            'current_drawdown': (self.period_start_balance - self.total_capital) / self.period_start_balance if self.period_start_balance > 0 else 0,
            'max_drawdown': self.max_drawdown
        }
    
    def adjust_position_size(self, symbol: str, base_size: float, current_price: float) -> float:
        """Adjust position size based on risk constraints"""
        # Calculate the risk of the proposed position
        position_value = base_size * current_price
        position_risk = position_value / self.total_capital
        
        # Apply position risk limit
        if position_risk > self.max_position_risk:
            adjusted_value = self.max_position_risk * self.total_capital
            base_size = adjusted_value / current_price
        
        # Check portfolio risk limit
        total_exposure = sum(pos.quantity * pos.entry_price for pos in self.current_positions.values())
        new_total_exposure = total_exposure + position_value
        
        if new_total_exposure / self.total_capital > self.max_portfolio_risk:
            max_exposure = self.max_portfolio_risk * self.total_capital - total_exposure
            if max_exposure > 0:
                base_size = min(base_size, max_exposure / current_price)
            else:
                base_size = 0  # Don't allow any position
        
        return max(0, base_size)  # Don't allow negative position size