"""
Signal Processing and Conflict Resolution System
Handles signal validation, conflict resolution, and weighting based on reliability.
"""
from typing import List, Dict, Optional, Tuple, Any
from domain.entities.trading_entities import Signal
from domain.value_objects import Symbol, Percentage
from shared.logger import EnhancedLogger
from datetime import datetime
import numpy as np


class SignalConflictResolver:
    """
    Resolves conflicts between multiple signals and applies weighting based on reliability.
    """
    
    def __init__(self):
        self.logger = EnhancedLogger("SignalConflictResolver")
        self.watcher_reliability_scores = {}  # Store reliability scores for each watcher
        self.signal_history = {}  # Track signal history for validation
        self.conflict_threshold = 0.1  # Threshold for considering signals conflicting
        
    def resolve_conflicts(self, signals: List[Signal]) -> Optional[Signal]:
        """
        Resolve conflicts between multiple signals and return the best one.
        
        Args:
            signals: List of incoming signals to resolve
            
        Returns:
            A single resolved signal or None if no clear winner
        """
        if not signals:
            return None
        
        if len(signals) == 1:
            return signals[0]
        
        # Group signals by symbol
        symbol_signals = {}
        for signal in signals:
            symbol_key = signal.symbol.value
            if symbol_key not in symbol_signals:
                symbol_signals[symbol_key] = []
            symbol_signals[symbol_key].append(signal)
        
        # Process each symbol separately
        resolved_signals = []
        for symbol_key, symbol_signal_list in symbol_signals.items():
            resolved = self._resolve_signals_for_symbol(symbol_signal_list)
            if resolved:
                resolved_signals.append(resolved)
        
        # For now, return the first resolved signal (in a real system, you might want to handle multiple symbols)
        return resolved_signals[0] if resolved_signals else None
    
    def _resolve_signals_for_symbol(self, signals: List[Signal]) -> Optional[Signal]:
        """Resolve conflicts for signals related to the same symbol."""
        if not signals:
            return None
        
        # First, check for conflicting signal types (BUY vs SELL)
        buy_signals = [s for s in signals if s.signal_type.name == 'BUY']
        sell_signals = [s for s in signals if s.signal_type.name == 'SELL']
        hold_signals = [s for s in signals if s.signal_type.name == 'HOLD' or s.signal_type.name == 'NEUTRAL']
        
        if not buy_signals and not sell_signals:
            # Only hold signals, return the one with highest confidence
            if hold_signals:
                return max(hold_signals, key=lambda s: float(s.confidence.value))
            return None
        
        # Calculate weighted confidence for each direction
        buy_weighted_confidence = self._calculate_weighted_confidence(buy_signals)
        sell_weighted_confidence = self._calculate_weighted_confidence(sell_signals)
        
        # If there's a clear winner (difference above threshold), return it
        confidence_diff = abs(buy_weighted_confidence - sell_weighted_confidence)
        
        if confidence_diff > self.conflict_threshold:
            if buy_weighted_confidence > sell_weighted_confidence:
                # Return the buy signal with highest weighted confidence
                best_buy = self._select_best_signal(buy_signals)
                self.logger.info(f"Selected BUY signal for {best_buy.symbol.value} based on weighted confidence")
                return best_buy
            else:
                # Return the sell signal with highest weighted confidence
                best_sell = self._select_best_signal(sell_signals)
                self.logger.info(f"Selected SELL signal for {best_sell.symbol.value} based on weighted confidence")
                return best_sell
        else:
            # Signals are too close, might want to return HOLD or use additional criteria
            self.logger.info(f"Signals too close for {signals[0].symbol.value}, considering HOLD or additional criteria")
            # For now, return the signal with highest original confidence
            return max(signals, key=lambda s: float(s.confidence.value))
    
    def _calculate_weighted_confidence(self, signals: List[Signal]) -> float:
        """Calculate weighted confidence based on watcher reliability."""
        if not signals:
            return 0.0
        
        total_weighted_confidence = 0.0
        total_weight = 0.0
        
        for signal in signals:
            # Get reliability weight for the source engine/watcher
            reliability_weight = self._get_reliability_weight(signal.source_engine or signal.strategy_name)
            
            confidence = float(signal.confidence.value)
            weighted_confidence = confidence * reliability_weight
            
            total_weighted_confidence += weighted_confidence
            total_weight += reliability_weight
        
        if total_weight > 0:
            return total_weighted_confidence / total_weight
        else:
            # If no reliability data, just average the confidences
            confidences = [float(s.confidence.value) for s in signals]
            return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _get_reliability_weight(self, source_engine: str) -> float:
        """Get reliability weight for a source engine/watcher."""
        # Default reliability is 1.0 if not tracked
        return self.watcher_reliability_scores.get(source_engine, 1.0)
    
    def _select_best_signal(self, signals: List[Signal]) -> Signal:
        """Select the best signal from a list based on weighted confidence."""
        if not signals:
            return None
        
        # Calculate weighted confidence for each signal
        weighted_signals = []
        for signal in signals:
            reliability_weight = self._get_reliability_weight(signal.source_engine or signal.strategy_name)
            confidence = float(signal.confidence.value)
            weighted_confidence = confidence * reliability_weight
            weighted_signals.append((signal, weighted_confidence))
        
        # Return the signal with highest weighted confidence
        best_signal, _ = max(weighted_signals, key=lambda x: x[1])
        return best_signal
    
    def update_watcher_reliability(self, watcher_name: str, performance_score: float):
        """Update the reliability score for a watcher based on performance."""
        # Use exponential moving average to update reliability
        current_score = self.watcher_reliability_scores.get(watcher_name, 1.0)
        # Use a decay factor to give more weight to recent performance
        decay_factor = 0.7
        new_score = decay_factor * performance_score + (1 - decay_factor) * current_score
        self.watcher_reliability_scores[watcher_name] = max(0.1, min(2.0, new_score))  # Clamp between 0.1 and 2.0
    
    def validate_signal(self, signal: Signal) -> Tuple[bool, str]:
        """
        Validate a signal based on various criteria.
        
        Returns:
            Tuple of (is_valid, reason_for_invalidity)
        """
        # Check if confidence is within valid range
        if not 0 <= float(signal.confidence.value) <= 1:
            return False, f"Invalid confidence value: {signal.confidence.value}"
        
        # Check if score is within reasonable range
        if not -1 <= signal.score <= 1:
            return False, f"Invalid score value: {signal.score}"
        
        # Check if signal is too old (more than 1 minute old)
        time_diff = (datetime.now() - signal.timestamp).total_seconds()
        if time_diff > 60:  # 1 minute threshold
            return False, f"Signal is too old: {time_diff} seconds"
        
        # Check for duplicate signals (same source, same symbol, similar timestamp)
        if self._is_duplicate_signal(signal):
            return False, "Duplicate signal detected"
        
        return True, "Valid signal"


class SignalValidator:
    """
    Enhanced signal validation system.
    """
    
    def __init__(self):
        self.conflict_resolver = SignalConflictResolver()
        self.logger = EnhancedLogger("SignalValidator")
        self.validation_rules = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default validation rules."""
        self.validation_rules = [
            self._validate_confidence_range,
            self._validate_score_range,
            self._validate_timestamp_freshness,
            self._validate_signal_type,
        ]
    
    def validate_signals(self, signals: List[Signal]) -> Tuple[List[Signal], List[Tuple[Signal, str]]]:
        """
        Validate a list of signals and return valid signals and invalid signals with reasons.
        
        Returns:
            Tuple of (valid_signals, invalid_signals_with_reasons)
        """
        valid_signals = []
        invalid_signals = []
        
        for signal in signals:
            is_valid, reason = self._validate_single_signal(signal)
            if is_valid:
                valid_signals.append(signal)
            else:
                invalid_signals.append((signal, reason))
        
        # If we have multiple valid signals, resolve conflicts
        if len(valid_signals) > 1:
            resolved_signal = self.conflict_resolver.resolve_conflicts(valid_signals)
            if resolved_signal:
                valid_signals = [resolved_signal]
            else:
                valid_signals = []  # No clear resolution
        
        return valid_signals, invalid_signals
    
    def _validate_single_signal(self, signal: Signal) -> Tuple[bool, str]:
        """Validate a single signal against all rules."""
        for rule in self.validation_rules:
            is_valid, reason = rule(signal)
            if not is_valid:
                return False, reason
        return True, "Valid signal"
    
    def _validate_confidence_range(self, signal: Signal) -> Tuple[bool, str]:
        """Validate that confidence is in [0, 1] range."""
        confidence = float(signal.confidence.value)
        if 0 <= confidence <= 1:
            return True, ""
        return False, f"Confidence {confidence} not in valid range [0, 1]"
    
    def _validate_score_range(self, signal: Signal) -> Tuple[bool, str]:
        """Validate that score is in [-1, 1] range."""
        score = signal.score
        if -1 <= score <= 1:
            return True, ""
        return False, f"Score {score} not in valid range [-1, 1]"
    
    def _validate_timestamp_freshness(self, signal: Signal) -> Tuple[bool, str]:
        """Validate that signal timestamp is not too old."""
        time_diff = (datetime.now() - signal.timestamp).total_seconds()
        if time_diff <= 60:  # 1 minute threshold
            return True, ""
        return False, f"Signal timestamp is {time_diff:.1f}s old, exceeds 60s limit"
    
    def _validate_signal_type(self, signal: Signal) -> Tuple[bool, str]:
        """Validate that signal type is valid."""
        valid_types = ['BUY', 'SELL', 'HOLD', 'NEUTRAL']
        if signal.signal_type.name in valid_types:
            return True, ""
        return False, f"Invalid signal type: {signal.signal_type.name}"
    
    def add_validation_rule(self, rule_func):
        """Add a custom validation rule."""
        self.validation_rules.append(rule_func)
    
    def get_reliability_weight(self, source_engine: str) -> float:
        """Get reliability weight for a source engine."""
        return self.conflict_resolver._get_reliability_weight(source_engine)
    
    def update_watcher_reliability(self, watcher_name: str, performance_score: float):
        """Update watcher reliability score."""
        self.conflict_resolver.update_watcher_reliability(watcher_name, performance_score)