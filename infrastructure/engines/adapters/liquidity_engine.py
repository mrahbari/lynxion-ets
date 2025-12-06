from ..base_engine import BaseEngine
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List, Tuple


class LiquidityEngine(BaseEngine):
    """Liquidity Engine - evaluates signals based on market liquidity conditions"""
    
    def __init__(self, name: str, lookback: int = 10, low_liquidity_threshold: float = 0.3, high_liquidity_threshold: float = 0.7):
        super().__init__(name)
        self.lookback = lookback
        self.low_liquidity_threshold = low_liquidity_threshold
        self.high_liquidity_threshold = high_liquidity_threshold
        self.bids: List[Tuple[float, float]] = []  # List of (price, volume) tuples
        self.asks: List[Tuple[float, float]] = []  # List of (price, volume) tuples
        self.liquidity_score_history: List[float] = []
        self.current_liquidity_score = 0.0
        self.avg_liquidity_score = 0.0
        
    def update_data(self, data: Dict):
        """Update with new market data (order book)"""
        if 'bids' in data and 'asks' in data:
            # Update order book
            self.bids = [(float(price), float(vol)) for price, vol in data['bids']]
            self.asks = [(float(price), float(vol)) for price, vol in data['asks']]
            
            # Calculate liquidity metrics
            liquidity_score = self.calculate_liquidity_score()
            self.liquidity_score_history.append(liquidity_score)
            if len(self.liquidity_score_history) > self.lookback * 3:
                self.liquidity_score_history.pop(0)
                
            self.current_liquidity_score = liquidity_score
            self.avg_liquidity_score = np.mean(self.liquidity_score_history) if self.liquidity_score_history else 0.5
            
    def calculate_liquidity_score(self) -> float:
        """Calculate a liquidity score from 0 to 1"""
        if not self.bids or not self.asks:
            return 0.0
            
        # Calculate total volume in the top levels
        top_bid_vol = sum(vol for _, vol in self.bids[:5])  # Top 5 bid levels
        top_ask_vol = sum(vol for _, vol in self.asks[:5])  # Top 5 ask levels
        
        # Calculate spread
        best_bid = self.bids[0][0] if self.bids else 1
        best_ask = self.asks[0][0] if self.asks else 1
        spread = (best_ask - best_bid) / best_bid if best_bid != 0 else 0
        
        # Calculate depth score (how much volume is available at good prices)
        total_top_volume = top_bid_vol + top_ask_vol
        avg_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 1
        dollar_depth = total_top_volume * avg_price
        
        # Combine spread and depth to create liquidity score
        # Lower spread and higher depth = higher liquidity
        spread_factor = max(0, 1 - spread * 100)  # Convert spread to factor (0-1), assuming 1% max spread
        depth_factor = min(1, np.log1p(dollar_depth / 10000) / 5)  # Logarithmic scaling for depth
        
        # Weighted combination (can be adjusted)
        liquidity_score = (spread_factor * 0.4) + (depth_factor * 0.6)
        
        return max(0.0, min(1.0, liquidity_score))  # Clamp between 0 and 1
        
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through liquidity analysis"""
        if not self.liquidity_score_history:
            # No liquidity data - return original signal with slightly reduced confidence for safety
            new_confidence = max(0.2, signal.confidence * 0.8)
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=new_confidence,
                score=signal.score * 0.8,
                strategy=f"{signal.strategy}_liquidity_filtered",
                timestamp=datetime.now(),
                metadata=signal.metadata
            )
            
        # Determine liquidity regime
        is_low_liquidity = self.current_liquidity_score < self.low_liquidity_threshold
        is_high_liquidity = self.current_liquidity_score > self.high_liquidity_threshold
        is_normal_liquidity = not is_low_liquidity and not is_high_liquidity
        
        # Adjust signal based on liquidity conditions
        if is_low_liquidity:
            # Low liquidity increases risk of slippage and poor fills
            # Reduce confidence significantly
            new_confidence = max(0.1, signal.confidence * 0.4)
            new_score = signal.score * 0.5
            
            # For buy signals, low liquidity might be particularly risky
            if signal.signal_type == SignalType.BUY:
                new_confidence *= 0.8  # Even more conservative for buy signals in low liquidity
        elif is_high_liquidity:
            # High liquidity is favorable for executing positions
            new_confidence = min(1.0, signal.confidence * 1.1)  # Slightly increase confidence
            new_score = signal.score * 1.1
        else:
            # Normal liquidity - adjust confidence based on how liquidity has changed
            if len(self.liquidity_score_history) > 1:
                prev_liquidity = self.liquidity_score_history[-2]
                if self.current_liquidity_score > prev_liquidity:
                    # Liquidity is improving - slightly increase confidence
                    new_confidence = min(1.0, signal.confidence * 1.05)
                    new_score = signal.score * 1.05
                elif self.current_liquidity_score < prev_liquidity:
                    # Liquidity is deteriorating - slightly reduce confidence
                    new_confidence = max(0.1, signal.confidence * 0.95)
                    new_score = signal.score * 0.95
                else:
                    # No change in liquidity
                    new_confidence = signal.confidence
                    new_score = signal.score
            else:
                # No previous liquidity data
                new_confidence = signal.confidence
                new_score = signal.score
                
        # For signals that require large position sizes, liquidity becomes even more critical
        if signal.metadata and signal.metadata.get('position_size', 1) > 1:
            # Large position signals should be more sensitive to liquidity
            if is_low_liquidity:
                new_confidence *= 0.7  # Reduce even further for large positions
            elif is_high_liquidity:
                new_confidence = min(1.0, new_confidence * 1.15)  # Boost for large positions in high liquidity
                
        # Generate enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy=f"{signal.strategy}_liquidity_filtered",
            timestamp=datetime.now(),
            metadata=signal.metadata or {}
        )
        
        # Add liquidity-specific metadata
        enhanced_signal.metadata.update({
            'original_confidence': signal.confidence,
            'current_liquidity_score': self.current_liquidity_score,
            'avg_liquidity_score': self.avg_liquidity_score,
            'liquidity_regime': self.get_liquidity_regime(),
            'bid_volume_top5': sum(vol for _, vol in self.bids[:5]) if self.bids else 0,
            'ask_volume_top5': sum(vol for _, vol in self.asks[:5]) if self.asks else 0
        })
        
        logger.debug(f"LiquidityEngine {self.name} processed signal: original={signal.signal_type}, "
                    f"liquidity_regime={self.get_liquidity_regime()}, "
                    f"new_conf={new_confidence:.3f}")
        
        # Add to history
        self.add_signal_to_history(enhanced_signal)
        
        return enhanced_signal
        
    def get_liquidity_regime(self) -> str:
        """Get current liquidity regime"""
        if self.current_liquidity_score < self.low_liquidity_threshold:
            return "low"
        elif self.current_liquidity_score > self.high_liquidity_threshold:
            return "high"
        else:
            return "normal"
            
    def get_liquidity_metrics(self) -> Dict:
        """Get current liquidity metrics"""
        return {
            'current_liquidity_score': self.current_liquidity_score,
            'avg_liquidity_score': self.avg_liquidity_score,
            'best_bid': self.bids[0][0] if self.bids else 0,
            'best_ask': self.asks[0][0] if self.asks else 0,
            'bid_ask_spread': ((self.asks[0][0] - self.bids[0][0]) / self.bids[0][0]) if self.bids and self.asks and self.bids[0][0] != 0 else 0,
            'total_top_bid_volume': sum(vol for _, vol in self.bids[:5]) if self.bids else 0,
            'total_top_ask_volume': sum(vol for _, vol in self.asks[:5]) if self.asks else 0,
            'regime': self.get_liquidity_regime()
        }