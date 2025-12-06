from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from domain.value_objects import Symbol
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List


class LiquidityWatcher(BaseWatcher):
    """Liquidity Watcher - analyzes market liquidity conditions"""
    
    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 20):
        super().__init__(name, symbol, broker_service, target_broker)
        self.lookback = lookback
        
        # Order book data
        self.bids = []
        self.asks = []
        self.spread_history = []
        self.depth_history = []
        self.liquidity_score_history = []
        
        # Liquidity metrics
        self.avg_spread = 0
        self.liquidity_ratio = 0  # Ratio of bid/ask volume
        self.depth_score = 0  # Measure of order book depth
        
        # Thresholds
        self.low_liquidity_threshold = 0.3
        self.high_liquidity_threshold = 0.7
        self.spread_threshold_factor = 2.0  # Factor to determine abnormal spreads
        
    def update_data(self, data: Dict):
        """Update with new market data (order book)"""
        if 'bids' in data and 'asks' in data:
            # Store bid and ask levels
            self.bids = [(float(price), float(vol)) for price, vol in data['bids']]
            self.asks = [(float(price), float(vol)) for price, vol in data['asks']]
            
            # Calculate spread
            if self.bids and self.asks:
                best_bid = self.bids[0][0]
                best_ask = self.asks[0][0]
                spread = best_ask - best_bid
                spread_pct = spread / best_bid if best_bid != 0 else 0
                
                self.spread_history.append(spread_pct)
                if len(self.spread_history) > self.lookback * 2:
                    self.spread_history.pop(0)
                    
                # Calculate average spread
                if self.spread_history:
                    self.avg_spread = np.mean(self.spread_history)
                    
            # Calculate order book depth
            depth_score = self.calculate_depth_score()
            self.depth_history.append(depth_score)
            if len(self.depth_history) > self.lookback * 2:
                self.depth_history.pop(0)
                
            # Calculate liquidity score
            liquidity_score = self.calculate_liquidity_score()
            self.liquidity_score_history.append(liquidity_score)
            if len(self.liquidity_score_history) > self.lookback * 2:
                self.liquidity_score_history.pop(0)
                
    def calculate_depth_score(self) -> float:
        """Calculate a score based on order book depth"""
        if not self.bids or not self.asks:
            return 0.0
            
        # Calculate total volume in top levels
        top_bid_volume = sum(vol for _, vol in self.bids[:5])  # Top 5 bid levels
        top_ask_volume = sum(vol for _, vol in self.asks[:5])  # Top 5 ask levels
        
        # Calculate depth score based on available liquidity
        total_top_volume = top_bid_volume + top_ask_volume
        
        if total_top_volume == 0:
            return 0.0
            
        # Calculate average price level to normalize volume
        avg_price = (self.bids[0][0] + self.asks[0][0]) / 2 if self.bids and self.asks else 1.0
        
        # Normalize the volume by price (to get dollar value)
        total_dollar_depth = (top_bid_volume + top_ask_volume) * avg_price
        
        # Return a score proportional to the depth (capped to reasonable range)
        # Using logarithmic scaling to prevent extreme scores for very deep books
        depth_score = min(1.0, np.log1p(total_dollar_depth / 10000) / 5.0)  # Adjust scaling factor as needed
        
        return depth_score
        
    def calculate_liquidity_score(self) -> float:
        """Calculate overall liquidity score"""
        if not self.spread_history or not self.depth_history:
            return 0.0
            
        # Calculate spread-based liquidity (inverse - lower spread = higher liquidity)
        current_spread = self.spread_history[-1] if self.spread_history else 0
        avg_spread = np.mean(self.spread_history) if self.spread_history else 0.001  # Default to 0.1%
        
        if avg_spread == 0:
            avg_spread = 0.001
            
        spread_liquidity = max(0, 1 - (current_spread / avg_spread))
        
        # Calculate depth-based liquidity
        current_depth = self.depth_history[-1] if self.depth_history else 0
        avg_depth = np.mean(self.depth_history) if self.depth_history else 0.1
        
        # Combine spread and depth liquidity scores
        combined_liquidity = (spread_liquidity * 0.6) + (current_depth * 0.4)
        
        # Normalize to -1 to 1 range
        return combined_liquidity * 2 - 1  # Convert from 0-1 to -1-1 range
        
    def analyze(self, symbol: Symbol) -> Signal:
        """Analyze liquidity conditions and return a signal"""
        if len(self.liquidity_score_history) < 5:
            return None
            
        current_liquidity = self.liquidity_score_history[-1]
        avg_liquidity = np.mean(self.liquidity_score_history)
        
        # Determine if liquidity is low, normal, or high
        is_low_liquidity = current_liquidity < self.low_liquidity_threshold
        is_high_liquidity = current_liquidity > self.high_liquidity_threshold
        
        # Calculate signal based on liquidity conditions
        if is_low_liquidity:
            # Low liquidity: potentially dangerous to trade, suggest hold
            signal_type = SignalType.HOLD
            confidence = 0.8  # High confidence in hold during low liquidity
        elif is_high_liquidity:
            # High liquidity: favorable conditions, but don't signal direction
            # without other factors
            signal_type = SignalType.HOLD
            confidence = 0.3  # Lower confidence in hold during high liquidity (other factors may apply)
        else:
            # Normal liquidity: hold, unless other factors suggest otherwise
            signal_type = SignalType.HOLD
            confidence = 0.5  # Medium confidence
            
        # Score represents liquidity level (-1 for very low, +1 for very high)
        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=current_liquidity,
            strategy=self.name,
            timestamp=datetime.now()
        )
        
        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"LiquidityWatcher {self.name} generated signal: {signal_type} with liquidity score {current_liquidity:.3f}")
            
        return signal
        
    def get_liquidity_regime(self) -> str:
        """Get current liquidity regime"""
        if not self.liquidity_score_history:
            return "unknown"
            
        current_liquidity = self.liquidity_score_history[-1]
        
        if current_liquidity < self.low_liquidity_threshold:
            return "low"
        elif current_liquidity > self.high_liquidity_threshold:
            return "high"
        else:
            return "normal"
            
    def get_liquidity_metrics(self) -> Dict:
        """Get current liquidity metrics"""
        if not self.liquidity_score_history:
            return {}
            
        current = self.liquidity_score_history[-1]
        avg_liquidity = np.mean(self.liquidity_score_history) if self.liquidity_score_history else 0
        current_spread = self.spread_history[-1] if self.spread_history else 0
        avg_spread = np.mean(self.spread_history) if self.spread_history else 0
        
        return {
            'current_liquidity_score': current,
            'average_liquidity_score': avg_liquidity,
            'current_spread_pct': current_spread,
            'average_spread_pct': avg_spread,
            'current_depth_score': self.depth_history[-1] if self.depth_history else 0,
            'regime': self.get_liquidity_regime(),
            'data_points': len(self.liquidity_score_history)
        }