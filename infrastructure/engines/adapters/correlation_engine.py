from ..base_engine import BaseEngine
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List


class CorrelationEngine(BaseEngine):
    """Correlation Engine - analyzes correlations between assets and adjusts signals accordingly"""
    
    def __init__(self, name: str, lookback: int = 30, correlation_threshold: float = 0.7):
        super().__init__(name)
        self.lookback = lookback
        self.correlation_threshold = correlation_threshold  # Threshold for high correlation
        
        # Price history for the main symbol and correlated symbols
        self.price_history: List[float] = []
        self.correlated_assets: Dict[str, List[float]] = {}  # Symbol -> price history
        self.correlation_matrix: Dict[str, float] = {}  # Symbol -> correlation coefficient
        self.cointegration_tests: Dict[str, bool] = {}  # Symbol -> cointegration result
        
        # Current values
        self.primary_asset = ""
        self.related_assets = []
        
    def update_data(self, data: Dict):
        """Update with new market data for the primary asset"""
        if 'close' in data and 'symbol' in data:
            symbol = data['symbol']
            
            # Update primary asset history
            if symbol == self.primary_asset or not self.primary_asset:
                if not self.primary_asset:
                    self.primary_asset = symbol
                self.price_history.append(float(data['close']))
                if len(self.price_history) > self.lookback * 3:
                    self.price_history.pop(0)
            
            # Update correlated assets if provided
            if 'correlated_assets' in data:
                for corr_symbol, corr_price in data['correlated_assets'].items():
                    if corr_symbol not in self.correlated_assets:
                        self.correlated_assets[corr_symbol] = []
                    self.correlated_assets[corr_symbol].append(float(corr_price))
                    if len(self.correlated_assets[corr_symbol]) > self.lookback * 3:
                        self.correlated_assets[corr_symbol].pop(0)
        
        # Update correlations if we have enough data
        if len(self.price_history) >= 10:
            self.update_correlations()
    
    def update_correlations(self):
        """Update correlation coefficients with other assets"""
        if len(self.price_history) < 10:
            return
            
        # Calculate correlations with each correlated asset
        for symbol, asset_prices in self.correlated_assets.items():
            if len(asset_prices) < 10:
                continue
                
            # Use the overlapping portion of the histories
            min_len = min(len(self.price_history), len(asset_prices))
            if min_len < 10:
                continue
                
            primary_prices = np.array(self.price_history[-min_len:])
            asset_prices = np.array(asset_prices[-min_len:])
            
            # Calculate correlation coefficient
            if np.std(primary_prices) == 0 or np.std(asset_prices) == 0:
                correlation = 0.0
            else:
                correlation_matrix = np.corrcoef(primary_prices, asset_prices)
                correlation = correlation_matrix[0, 1]
                
            self.correlation_matrix[symbol] = correlation
            
            # Perform a simplified cointegration test
            # In practice, you'd use more sophisticated tests like Engle-Granger
            self.cointegration_tests[symbol] = self.test_cointegration(primary_prices, asset_prices)
    
    def test_cointegration(self, prices1: np.ndarray, prices2: np.ndarray) -> bool:
        """Simplified cointegration test - in practice, use Engle-Granger or Johansen test"""
        # Calculate the spread between the two price series
        spread = prices1 - prices2
        
        # Check if the spread is stationary (a simple heuristic)
        # In a real implementation, you would use statistical tests like ADF
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        
        # If the spread doesn't deviate too far from its mean relative to its volatility, 
        # we might consider the series cointegrated
        current_deviation = abs(spread[-1] - spread_mean)
        return current_deviation < 2 * spread_std  # Simplified check
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through correlation analysis"""
        if not self.correlation_matrix or len(self.price_history) < 10:
            # Not enough correlation data - return original signal
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                score=signal.score,
                strategy=f"{signal.strategy}_correlation_filtered",
                timestamp=datetime.now(),
                metadata=signal.metadata
            )
            
        # Calculate how the signal aligns with correlated assets
        alignment_score = self.calculate_alignment_score(signal)
        
        # Adjust signal based on correlation
        base_confidence = signal.confidence
        base_score = signal.score
        
        # Determine if we should increase or decrease confidence based on correlations
        correlation_factor = 1.0
        
        # Find highly correlated assets that support the signal
        supporting_correlations = 0
        opposing_correlations = 0
        
        for symbol, correlation in self.correlation_matrix.items():
            if abs(correlation) < self.correlation_threshold:
                continue  # Only consider highly correlated assets
                
            # Check if we have recent signal data for this symbol (would come from elsewhere in a full system)
            # For this example, we'll simulate based on price movement direction
            if len(self.correlated_assets.get(symbol, [])) >= 2:
                recent_change = (self.correlated_assets[symbol][-1] - self.correlated_assets[symbol][-2]) / self.correlated_assets[symbol][-2]
                
                # Determine if this asset's movement supports the signal
                if signal.signal_type == SignalType.BUY and recent_change > 0:
                    supporting_correlations += abs(correlation)
                elif signal.signal_type == SignalType.SELL and recent_change < 0:
                    supporting_correlations += abs(correlation)
                elif (signal.signal_type == SignalType.BUY and recent_change < 0) or (signal.signal_type == SignalType.SELL and recent_change > 0):
                    opposing_correlations += abs(correlation)
        
        # Apply correlation adjustment
        net_correlation_support = supporting_correlations - opposing_correlations
        
        if net_correlation_support > 0.1:
            # Positive correlation support - increase confidence
            correlation_factor = min(1.3, 1.0 + net_correlation_support * 0.5)
        elif net_correlation_support < -0.1:
            # Negative correlation support - decrease confidence
            correlation_factor = max(0.7, 1.0 + net_correlation_support * 0.5)
        else:
            # Neutral correlation - slight adjustment
            correlation_factor = 1.0
            
        new_confidence = max(0.05, min(1.0, base_confidence * correlation_factor))
        new_score = base_score * correlation_factor
        
        # Additional adjustment for cointegrated pairs
        cointegrated_support = 0
        for symbol, is_cointegrated in self.cointegration_tests.items():
            if is_cointegrated and symbol in self.correlation_matrix:
                correlation = self.correlation_matrix[symbol]
                if abs(correlation) > self.correlation_threshold:
                    # Check if this cointegrated asset supports the signal (simplified)
                    if len(self.correlated_assets.get(symbol, [])) >= 2:
                        recent_change = (self.correlated_assets[symbol][-1] - self.correlated_assets[symbol][-2]) / self.correlated_assets[symbol][-2]
                        if (signal.signal_type == SignalType.BUY and recent_change > 0) or (signal.signal_type == SignalType.SELL and recent_change < 0):
                            cointegrated_support += abs(correlation) * 0.1
        
        new_confidence = min(1.0, new_confidence + cointegrated_support)
        new_score = new_score + cointegrated_support
        
        # Generate enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy=f"{signal.strategy}_correlation_filtered",
            timestamp=datetime.now(),
            metadata=signal.metadata or {}
        )
        
        # Add correlation-specific metadata
        enhanced_signal.metadata.update({
            'original_confidence': signal.confidence,
            'correlation_factor': correlation_factor,
            'alignment_score': alignment_score,
            'supporting_correlations': supporting_correlations,
            'opposing_correlations': opposing_correlations,
            'cointegrated_support': cointegrated_support,
            'correlation_assets_count': len(self.correlation_matrix),
            'average_correlation': np.mean(list(self.correlation_matrix.values())) if self.correlation_matrix else 0
        })
        
        logger.debug(f"CorrelationEngine {self.name} processed signal: original={signal.signal_type}, "
                    f"corr_factor={correlation_factor:.3f}, "
                    f"new_conf={new_confidence:.3f}")
        
        # Add to history
        self.add_signal_to_history(enhanced_signal)
        
        return enhanced_signal
        
    def calculate_alignment_score(self, signal: Signal) -> float:
        """Calculate how well the signal aligns with correlated assets (-1 to 1)"""
        if not self.correlation_matrix:
            return 0.0
            
        alignment_sum = 0
        weight_sum = 0
        
        for symbol, correlation in self.correlation_matrix.items():
            if len(self.correlated_assets.get(symbol, [])) >= 2:
                # Calculate recent price change direction
                recent_change = (self.correlated_assets[symbol][-1] - self.correlated_assets[symbol][-2]) / self.correlated_assets[symbol][-2]
                
                # Determine if the direction aligns with the signal
                if (signal.signal_type == SignalType.BUY and recent_change > 0) or \
                   (signal.signal_type == SignalType.SELL and recent_change < 0):
                    alignment = 1  # Aligned
                elif (signal.signal_type == SignalType.BUY and recent_change < 0) or \
                     (signal.signal_type == SignalType.SELL and recent_change > 0):
                    alignment = -1  # Opposing
                else:
                    alignment = 0  # Neutral
                    
                # Weight by correlation strength
                alignment_sum += alignment * abs(correlation)
                weight_sum += abs(correlation)
        
        if weight_sum == 0:
            return 0.0
            
        return alignment_sum / weight_sum
        
    def add_correlated_asset(self, symbol: str, initial_price: float):
        """Add a new asset to monitor for correlations"""
        self.correlated_assets[symbol] = [initial_price]
        
    def get_correlations(self) -> Dict[str, float]:
        """Get current correlation matrix"""
        return self.correlation_matrix.copy()
        
    def get_cointegration_tests(self) -> Dict[str, bool]:
        """Get results of cointegration tests"""
        return self.cointegration_tests.copy()