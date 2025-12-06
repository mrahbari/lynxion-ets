from ..base_engine import BaseEngine
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List, Tuple


class OrderFlowEngine(BaseEngine):
    """Order Flow Engine - analyzes order flow patterns and market maker behavior"""
    
    def __init__(self, name: str, lookback: int = 20):
        super().__init__(name)
        self.lookback = lookback
        
        # Order book data
        self.bids: List[Tuple[float, float]] = []  # (price, volume)
        self.asks: List[Tuple[float, float]] = []  # (price, volume)
        
        # Order flow metrics
        self.bid_volume_history: List[float] = []
        self.ask_volume_history: List[float] = []
        self.order_flow_imbalance_history: List[float] = []
        self.aggressive_buy_volume = 0
        self.aggressive_sell_volume = 0
        
        # Calculated metrics
        self.current_imbalance = 0
        self.avg_imbalance = 0
        self.imbalance_trend = 0
        
    def update_data(self, data: Dict):
        """Update with new market data (order book and trades)"""
        if 'bids' in data and 'asks' in data:
            self.bids = [(float(price), float(vol)) for price, vol in data['bids']]
            self.asks = [(float(price), float(vol)) for price, vol in data['asks']]
            
            # Calculate total volumes
            bid_vol = sum(vol for _, vol in self.bids)
            ask_vol = sum(vol for _, vol in self.asks)
            
            self.bid_volume_history.append(bid_vol)
            self.ask_volume_history.append(ask_vol)
            
            if len(self.bid_volume_history) > self.lookback * 3:
                self.bid_volume_history.pop(0)
                self.ask_volume_history.pop(0)
                
            # Calculate order flow imbalance
            total_vol = bid_vol + ask_vol
            if total_vol > 0:
                imbalance = (bid_vol - ask_vol) / total_vol
            else:
                imbalance = 0
                
            self.order_flow_imbalance_history.append(imbalance)
            
            if len(self.order_flow_imbalance_history) > self.lookback * 3:
                self.order_flow_imbalance_history.pop(0)
                
            # Update calculated metrics
            self.current_imbalance = imbalance
            self.avg_imbalance = np.mean(self.order_flow_imbalance_history) if self.order_flow_imbalance_history else 0
            
            # Calculate imbalance trend
            if len(self.order_flow_imbalance_history) >= 2:
                recent_imbalances = self.order_flow_imbalance_history[-5:] if len(self.order_flow_imbalance_history) >= 5 else self.order_flow_imbalance_history
                x = np.arange(len(recent_imbalances))
                if len(x) > 1:
                    self.imbalance_trend = (len(x) * np.sum(x * recent_imbalances) - np.sum(x) * np.sum(recent_imbalances)) / \
                                          (len(x) * np.sum(x * x) - (np.sum(x)) ** 2) if len(x) * np.sum(x * x) - (np.sum(x)) ** 2 != 0 else 0
                else:
                    self.imbalance_trend = 0
            else:
                self.imbalance_trend = 0
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through order flow analysis"""
        if len(self.order_flow_imbalance_history) < 3:
            # Not enough order flow data - return original signal with slightly reduced confidence
            new_confidence = signal.confidence * 0.85
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=new_confidence,
                score=signal.score * 0.85,
                strategy=f"{signal.strategy}_orderflow_filtered",
                timestamp=datetime.now(),
                metadata=signal.metadata
            )
            
        # Determine if order flow supports the signal
        signal_aligned_with_flow = self.is_signal_aligned_with_flow(signal)
        
        # Calculate order flow strength
        flow_strength = abs(self.current_imbalance)
        
        # Adjust signal based on order flow alignment
        if signal_aligned_with_flow:
            # Signal aligns with order flow - increase confidence
            new_confidence = min(1.0, signal.confidence * (1.0 + flow_strength * 0.5))
            new_score = signal.score * (1.0 + flow_strength * 0.3)
        else:
            # Signal goes against order flow - decrease confidence
            new_confidence = max(0.1, signal.confidence * (1.0 - flow_strength * 0.4))
            new_score = signal.score * (1.0 - flow_strength * 0.3)
            
        # Consider the trend in order flow
        if abs(self.imbalance_trend) > 0.01:  # If there's a significant trend in order flow
            if self.imbalance_trend > 0 and signal.signal_type == SignalType.BUY:
                # Positive trend in imbalance supporting buy signal
                new_confidence = min(1.0, new_confidence * 1.1)
                new_score = new_score * 1.05
            elif self.imbalance_trend < 0 and signal.signal_type == SignalType.SELL:
                # Negative trend in imbalance supporting sell signal
                new_confidence = min(1.0, new_confidence * 1.1)
                new_score = new_score * 1.05
            elif self.imbalance_trend > 0 and signal.signal_type == SignalType.SELL:
                # Positive trend in imbalance opposing sell signal
                new_confidence = max(0.1, new_confidence * 0.95)
                new_score = new_score * 0.95
            elif self.imbalance_trend < 0 and signal.signal_type == SignalType.BUY:
                # Negative trend in imbalance opposing buy signal
                new_confidence = max(0.1, new_confidence * 0.95)
                new_score = new_score * 0.95
                
        # Generate enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy=f"{signal.strategy}_orderflow_filtered",
            timestamp=datetime.now(),
            metadata=signal.metadata or {}
        )
        
        # Add order flow-specific metadata
        enhanced_signal.metadata.update({
            'original_confidence': signal.confidence,
            'current_imbalance': self.current_imbalance,
            'avg_imbalance': self.avg_imbalance,
            'imbalance_trend': self.imbalance_trend,
            'flow_strength': flow_strength,
            'signal_aligned_with_flow': signal_aligned_with_flow,
            'bid_volume': sum(vol for _, vol in self.bids) if self.bids else 0,
            'ask_volume': sum(vol for _, vol in self.asks) if self.asks else 0
        })
        
        logger.debug(f"OrderFlowEngine {self.name} processed signal: original={signal.signal_type}, "
                    f"aligned={signal_aligned_with_flow}, flow_strength={flow_strength:.3f}, "
                    f"new_conf={new_confidence:.3f}")
        
        # Add to history
        self.add_signal_to_history(enhanced_signal)
        
        return enhanced_signal
        
    def is_signal_aligned_with_flow(self, signal: Signal) -> bool:
        """Check if the signal aligns with current order flow"""
        if signal.signal_type == SignalType.BUY:
            # Buy signal aligns if there's more buying pressure (positive imbalance)
            return self.current_imbalance > 0.1
        elif signal.signal_type == SignalType.SELL:
            # Sell signal aligns if there's more selling pressure (negative imbalance)
            return self.current_imbalance < -0.1
        else:  # HOLD
            # Hold signals are considered aligned if flow is balanced
            return abs(self.current_imbalance) <= 0.1
            
    def get_order_flow_regime(self) -> str:
        """Get current order flow regime"""
        if self.current_imbalance > 0.3:
            return "strong_bid_dominance"
        elif self.current_imbalance > 0.1:
            return "moderate_bid_dominance"
        elif self.current_imbalance < -0.3:
            return "strong_ask_dominance"
        elif self.current_imbalance < -0.1:
            return "moderate_ask_dominance"
        else:
            return "balanced"
            
    def get_order_flow_metrics(self) -> Dict:
        """Get current order flow metrics"""
        return {
            'current_imbalance': self.current_imbalance,
            'avg_imbalance': self.avg_imbalance,
            'imbalance_trend': self.imbalance_trend,
            'flow_regime': self.get_order_flow_regime(),
            'bid_volume': sum(vol for _, vol in self.bids) if self.bids else 0,
            'ask_volume': sum(vol for _, vol in self.asks) if self.asks else 0,
            'data_points': len(self.order_flow_imbalance_history)
        }