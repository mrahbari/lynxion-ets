from typing import Dict, List, Optional
from shared.types import Signal, Order
from shared.logger import logger
from datetime import datetime
import numpy as np


class KellyCriterion:
    """Implements the Kelly Criterion for position sizing"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Kelly criterion parameters
        self.kelly_fraction = config.get('kelly_fraction', 0.5)  # Use half Kelly to be conservative
        self.max_position_size = config.get('max_position_size', 0.1)  # Max 10% of capital
        self.min_edge_threshold = config.get('min_edge_threshold', 0.05)  # Minimum edge threshold
        self.min_confidence_threshold = config.get('min_confidence_threshold', 0.6)  # Minimum confidence threshold
        
        # Historical data for calculating win rate and payoff ratio
        self.outcomes: List[Dict] = []  # List of {'outcome': 1 for win, -1 for loss, 'pnl': actual_pnl, 'confidence': signal_confidence}
        self.lookback_window = config.get('lookback_window', 100)  # Number of trades to consider
        
        # Asset-specific Kelly parameters
        self.asset_kelly_params: Dict[str, Dict] = {}
        
    def calculate_kelly_position_size(self, signal: Signal, current_price: float, account_balance: float) -> float:
        """Calculate position size using Kelly Criterion"""
        # Calculate Kelly percentage
        kelly_pct = self._calculate_kelly_percentage(signal)
        
        if kelly_pct <= 0:
            # If Kelly suggests negative or zero position, don't trade
            return 0.0
        
        # Apply Kelly fraction for more conservative sizing
        adjusted_kelly_pct = kelly_pct * self.kelly_fraction
        
        # Apply maximum position size limit
        adjusted_kelly_pct = min(adjusted_kelly_pct, self.max_position_size)
        
        # Calculate position size in dollars
        position_value = account_balance * adjusted_kelly_pct
        
        # Calculate position size in units
        position_size = position_value / current_price if current_price > 0 else 0
        
        logger.debug(f"Kelly calculation for {signal.symbol}: raw_pct={kelly_pct:.4f}, "
                    f"adjusted_pct={adjusted_kelly_pct:.4f}, position_size={position_size:.4f}")
        
        return max(0, position_size)  # Ensure non-negative size
    
    def _calculate_kelly_percentage(self, signal: Signal) -> float:
        """Calculate Kelly percentage based on win rate and payoff ratio"""
        # Get historical performance for this signal type or strategy
        win_rate, avg_win, avg_loss = self._get_historical_performance(signal)
        
        if win_rate is None or avg_win is None or avg_loss is None:
            # If no historical data, use signal confidence as a proxy for edge
            if signal.confidence < self.min_confidence_threshold:
                return 0.0
            
            # Use a conservative estimate when no historical data
            win_rate = max(0.5, signal.confidence)  # Conservative win rate estimate
            avg_win = 0.01  # Average 1% winners
            avg_loss = 0.01  # Average 1% losers
        
        if avg_loss == 0:
            return self.max_position_size  # If no losses, could go all in, but limit to max
        
        # Kelly formula: K = (bp - q) / b
        # b = net odds received on the wager (avg_win / avg_loss)
        # p = probability of winning (win_rate)
        # q = probability of losing (1 - win_rate)
        
        b = avg_win / avg_loss if avg_loss != 0 else 1
        p = win_rate
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # Only trade if there's a positive edge
        edge = b * p - q
        if edge <= self.min_edge_threshold:
            return 0.0
        
        return max(0, kelly_fraction)
    
    def _get_historical_performance(self, signal: Signal) -> tuple:
        """Get historical performance for the given signal"""
        # Filter outcomes for this strategy or signal type
        relevant_outcomes = [
            outcome for outcome in self.outcomes
            if (outcome.get('strategy') == signal.strategy or 
                outcome.get('symbol') == signal.symbol)
        ]
        
        if not relevant_outcomes:
            # If no strategy-specific data, try to use general data
            relevant_outcomes = self.outcomes[-self.lookback_window:]
        
        if not relevant_outcomes:
            # No historical performance data
            return None, None, None
        
        # Calculate win rate and average win/loss ratio
        wins = [o for o in relevant_outcomes if o['pnl'] > 0]
        losses = [o for o in relevant_outcomes if o['pnl'] <= 0]
        
        win_rate = len(wins) / len(relevant_outcomes) if relevant_outcomes else 0
        avg_win = np.mean([abs(o['pnl']) for o in wins]) if wins else 0
        avg_loss = np.mean([abs(o['pnl']) for o in losses]) if losses else 0
        
        return win_rate, avg_win, avg_loss
    
    def update_performance_history(self, signal: Signal, pnl: float, realized: bool = True):
        """Update performance history with new trade results"""
        if not realized:
            # Don't update for unrealized P&L
            return
        
        outcome = {
            'timestamp': datetime.now(),
            'pnl': pnl,
            'is_win': pnl > 0,
            'confidence': signal.confidence,
            'strategy': getattr(signal, 'strategy', ''),
            'symbol': signal.symbol,
        }
        
        self.outcomes.append(outcome)
        
        # Maintain lookback window
        if len(self.outcomes) > self.lookback_window:
            self.outcomes.pop(0)
    
    def get_expected_value(self, signal: Signal) -> float:
        """Calculate expected value of a trade based on Kelly parameters"""
        win_rate, avg_win, avg_loss = self._get_historical_performance(signal)
        
        if win_rate is None or avg_win is None or avg_loss is None:
            return 0.0
        
        expected_value = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        return expected_value
    
    def get_kelly_advice(self, signal: Signal) -> Dict:
        """Get comprehensive Kelly Criterion advice for a signal"""
        win_rate, avg_win, avg_loss = self._get_historical_performance(signal)
        
        advice = {
            'should_trade': True,
            'position_size': 0,
            'kelly_percentage': 0,
            'expected_value': 0,
            'edge': 0,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'trades_analyzed': len(self.outcomes),
            'min_edge_threshold': self.min_edge_threshold,
            'min_confidence_threshold': self.min_confidence_threshold
        }
        
        if win_rate is not None and avg_win is not None and avg_loss is not None:
            # Calculate edge
            edge = (avg_win * win_rate) - (avg_loss * (1 - win_rate))
            
            # Check if signal meets minimum thresholds
            if signal.confidence < self.min_confidence_threshold:
                advice['should_trade'] = False
                advice['position_size'] = 0
            elif edge < self.min_edge_threshold:
                advice['should_trade'] = False
                advice['position_size'] = 0
            else:
                # Calculate Kelly percentage
                b = avg_win / avg_loss if avg_loss != 0 else 1
                p = win_rate
                q = 1 - p
                
                kelly_pct = max(0, (b * p - q) / b)
                kelly_pct = min(kelly_pct, self.max_position_size) * self.kelly_fraction
                advice['kelly_percentage'] = kelly_pct
                advice['position_size'] = kelly_pct
                advice['edge'] = edge
                advice['expected_value'] = edge
        
        return advice
    
    def reset_performance_history(self):
        """Reset the performance history"""
        self.outcomes.clear()
        logger.info("Kelly Criterion performance history reset")
    
    def get_performance_summary(self) -> Dict:
        """Get a summary of performance used for Kelly calculations"""
        if not self.outcomes:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'win_loss_ratio': 0,
                'total_pnl': 0
            }
        
        wins = [o for o in self.outcomes if o['pnl'] > 0]
        losses = [o for o in self.outcomes if o['pnl'] <= 0]
        
        total_pnl = sum(o['pnl'] for o in self.outcomes)
        win_rate = len(wins) / len(self.outcomes) if self.outcomes else 0
        avg_win = np.mean([o['pnl'] for o in wins]) if wins else 0
        avg_loss = abs(np.mean([o['pnl'] for o in losses])) if losses else 0
        win_loss_ratio = avg_win / avg_loss if avg_loss != 0 else float('inf')
        
        return {
            'total_trades': len(self.outcomes),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_loss_ratio': win_loss_ratio,
            'total_pnl': total_pnl
        }