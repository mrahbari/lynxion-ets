from typing import Dict, List, Optional, Tuple
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np
from collections import defaultdict, deque
import threading
import time


class FusionV3:
    """Fusion Engine v3 - Advanced signal fusion with regime awareness and ML weight adjustment"""
    
    def __init__(self, 
                 max_signals_history: int = 100,
                 confidence_threshold: float = 0.3,
                 regime_aware: bool = True,
                 ml_weighted: bool = True):
        self.max_signals_history = max_signals_history
        self.confidence_threshold = confidence_threshold
        self.regime_aware = regime_aware
        self.ml_weighted = ml_weighted
        
        # Signal storage
        self.signal_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))  # By strategy
        self.all_signals: deque = deque(maxlen=max_signals_history)
        
        # Regime tracking
        self.current_regime: str = "normal"
        self.regime_weights: Dict[str, float] = {}
        
        # ML weights by strategy and regime
        self.strategy_weights: Dict[str, float] = {}
        self.regime_strategy_weights: Dict[Tuple[str, str], float] = {}
        
        # Performance tracking
        self.strategy_performance: Dict[str, Dict] = defaultdict(lambda: {
            'total_signals': 0,
            'profitable_signals': 0,
            'total_pnl': 0.0,
            'avg_confidence': 0.0
        })
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
    def add_signal(self, signal: Signal):
        """Add a signal from an engine/watcher to the fusion engine"""
        with self.lock:
            # Add to strategy-specific buffer
            self.signal_buffer[signal.strategy].append(signal)
            
            # Add to general buffer
            self.all_signals.append(signal)
            
            # Update strategy performance tracking
            self.strategy_performance[signal.strategy]['total_signals'] += 1
            self.strategy_performance[signal.strategy]['avg_confidence'] = (
                self.strategy_performance[signal.strategy]['avg_confidence'] * 
                (self.strategy_performance[signal.strategy]['total_signals'] - 1) + 
                signal.confidence
            ) / self.strategy_performance[signal.strategy]['total_signals']
    
    def update_regime(self, regime: str):
        """Update the current market regime"""
        self.current_regime = regime
        logger.debug(f"FusionV3 regime updated to: {regime}")
    
    def update_strategy_performance(self, strategy: str, pnl: float):
        """Update the performance of a strategy"""
        with self.lock:
            perf = self.strategy_performance[strategy]
            perf['total_pnl'] += pnl
            if pnl > 0:
                perf['profitable_signals'] += 1
            
            # Update strategy weight based on performance
            win_rate = perf['profitable_signals'] / perf['total_signals'] if perf['total_signals'] > 0 else 0
            # Weight between 0.5 and 1.5 based on win rate
            self.strategy_weights[strategy] = 0.5 + win_rate
            
            # Update regime-strategy weight
            regime_strategy_key = (self.current_regime, strategy)
            self.regime_strategy_weights[regime_strategy_key] = 0.5 + win_rate
            
    def fusion_v3_core(self, 
                       time_window: int = 10, 
                       min_signals: int = 2, 
                       use_regime_weights: bool = True) -> Optional[Signal]:
        """Core fusion algorithm with regime awareness and ML weights"""
        with self.lock:
            if len(self.all_signals) < min_signals:
                return None
                
            # Get recent signals within time window
            recent_signals = self._get_recent_signals(time_window)
            
            if len(recent_signals) < min_signals:
                return None
            
            # Group signals by symbol
            symbol_signals = defaultdict(list)
            for signal in recent_signals:
                symbol_signals[signal.symbol].append(signal)
            
            # Process each symbol
            for symbol, signals in symbol_signals.items():
                if len(signals) < min_signals:
                    continue
                    
                # Perform fusion for this symbol
                fused_signal = self._fuse_signals(signals, use_regime_weights)
                
                if fused_signal:
                    logger.debug(f"FusionV3 generated fused signal for {symbol}: {fused_signal.signal_type} "
                                f"with score {fused_signal.score:.3f} and confidence {fused_signal.confidence:.3f}")
                    return fused_signal
                    
        return None
    
    def _get_recent_signals(self, time_window: int) -> List[Signal]:
        """Get signals from the last time_window seconds"""
        recent = []
        cutoff_time = datetime.now().timestamp() - time_window
        
        for signal in list(self.all_signals):
            if (datetime.now().timestamp() - signal.timestamp.timestamp()) <= time_window:
                recent.append(signal)
                
        return recent
    
    def _fuse_signals(self, signals: List[Signal], use_regime_weights: bool) -> Optional[Signal]:
        """Fuse a list of signals into a single meta-signal"""
        if not signals:
            return None
            
        # Calculate weighted scores by signal type
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        hold_signals = [s for s in signals if s.signal_type == SignalType.HOLD]
        
        # Calculate weighted scores for each type
        buy_score = self._calculate_weighted_score(buy_signals, use_regime_weights)
        sell_score = self._calculate_weighted_score(sell_signals, use_regime_weights)
        hold_score = self._calculate_weighted_score(hold_signals, use_regime_weights)
        
        # Determine the dominant signal type
        max_score = max(buy_score, sell_score, hold_score)
        
        if max_score < self.confidence_threshold:
            # If no strong signal, return None or HOLD
            return None
            
        # Determine signal type
        if buy_score == max_score:
            signal_type = SignalType.BUY
            final_score = buy_score
        elif sell_score == max_score:
            signal_type = SignalType.SELL
            final_score = -sell_score  # Negative for sell
        else:
            signal_type = SignalType.HOLD
            final_score = 0.0  # Hold has neutral score
            
        # Calculate overall confidence based on agreement among signals
        agreement = self._calculate_agreement(signals)
        base_confidence = max_score  # Use the maximum score as base confidence
        
        # Adjust confidence based on agreement and signal count
        confidence = base_confidence * (0.7 + 0.3 * agreement)  # Confidence between 70-100% of base
        
        # Create the fused signal
        fused_signal = Signal(
            symbol=signals[0].symbol,  # Use symbol from first signal (they should all be the same)
            signal_type=signal_type,
            confidence=min(1.0, confidence),
            score=final_score,
            strategy="FusionV3_Meta",
            timestamp=datetime.now(),
            metadata={
                'source_signals_count': len(signals),
                'buy_signals_count': len(buy_signals),
                'sell_signals_count': len(sell_signals),
                'hold_signals_count': len(hold_signals),
                'agreement_level': agreement,
                'regime': self.current_regime,
                'fusion_timestamp': datetime.now().isoformat()
            }
        )
        
        return fused_signal
    
    def _calculate_weighted_score(self, signals: List[Signal], use_regime_weights: bool) -> float:
        """Calculate weighted score for signals of the same type"""
        if not signals:
            return 0.0
            
        total_weighted_score = 0.0
        total_weights = 0.0
        
        for signal in signals:
            # Get base weight from signal confidence
            weight = signal.confidence
            
            # Apply strategy-specific weight if ML weighted is enabled
            if self.ml_weighted and signal.strategy in self.strategy_weights:
                weight *= self.strategy_weights[signal.strategy]
                
            # Apply regime-strategy weight if regime aware and enabled
            if use_regime_weights and self.regime_aware:
                regime_strategy_key = (self.current_regime, signal.strategy)
                if regime_strategy_key in self.regime_strategy_weights:
                    weight *= self.regime_strategy_weights[regime_strategy_key]
                    
            # Apply the weight
            total_weighted_score += signal.score * weight
            total_weights += weight
            
        if total_weights == 0:
            return 0.0
            
        return total_weighted_score / total_weights
    
    def _calculate_agreement(self, signals: List[Signal]) -> float:
        """Calculate agreement level among signals (0-1)"""
        if len(signals) < 2:
            return 1.0  # Perfect agreement if only one signal
            
        signal_types = [s.signal_type for s in signals]
        unique_types = set(signal_types)
        
        # If all signals are the same type, perfect agreement
        if len(unique_types) == 1:
            return 1.0
            
        # Count dominant type
        dominant_count = max(signal_types.count(t) for t in unique_types)
        
        # Agreement is dominant count over total count
        return dominant_count / len(signals)
    
    def get_signal_analytics(self) -> Dict:
        """Get analytics about the signals in the system"""
        with self.lock:
            total_signals = len(self.all_signals)
            strategy_counts = {}
            
            for signal in self.all_signals:
                strategy_counts[signal.strategy] = strategy_counts.get(signal.strategy, 0) + 1
                
            return {
                'total_signals': total_signals,
                'strategy_distribution': strategy_counts,
                'avg_signal_confidence': np.mean([s.confidence for s in self.all_signals]) if self.all_signals else 0,
                'current_regime': self.current_regime,
                'strategy_weights': self.strategy_weights.copy(),
                'regime_strategy_weights': self.regime_strategy_weights.copy(),
                'active_strategies_count': len(set(s.strategy for s in self.all_signals))
            }
    
    def reset_weights(self):
        """Reset all learned weights"""
        with self.lock:
            self.strategy_weights.clear()
            self.regime_strategy_weights.clear()
            logger.info("FusionV3 weights have been reset")