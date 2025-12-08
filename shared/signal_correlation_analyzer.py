"""
Signal correlation analyzer for the enterprise hedge fund trading system.
Provides sophisticated analysis of signal relationships and portfolio allocation based on correlation.
"""
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
from shared.logger import logger


class SignalCorrelationAnalyzer:
    """Analyzes correlations between different trading signals and strategies"""
    
    def __init__(self):
        self.correlation_cache: Dict[str, pd.DataFrame] = {}
        self.signal_history: Dict[str, List[Tuple[datetime, float, str]]] = {}  # strategy -> [(time, signal_value, symbol)]
    
    def add_signal_data(self, strategy_name: str, timestamp: datetime, signal_value: float, symbol: str):
        """Add signal data point for correlation analysis"""
        if strategy_name not in self.signal_history:
            self.signal_history[strategy_name] = []
        
        self.signal_history[strategy_name].append((timestamp, signal_value, symbol))
        
        # Keep only recent data to prevent memory issues
        if len(self.signal_history[strategy_name]) > 10000:  # Keep last 10,000 signals
            self.signal_history[strategy_name] = self.signal_history[strategy_name][-5000:]
    
    def calculate_pairwise_correlation(self, strategy1: str, strategy2: str, 
                                     lookback_period: int = 100) -> Optional[float]:
        """Calculate correlation between two strategies' signals"""
        if strategy1 not in self.signal_history or strategy2 not in self.signal_history:
            return None
        
        # Get signal histories
        hist1 = self.signal_history[strategy1][-lookback_period:]
        hist2 = self.signal_history[strategy2][-lookback_period:]
        
        # Align timestamps
        timestamps1 = [(ts, val) for ts, val, _ in hist1]
        timestamps2 = [(ts, val) for ts, val, _ in hist2]
        
        # Create a common timeline
        all_timestamps = set(ts for ts, _ in timestamps1) & set(ts for ts, _ in timestamps2)
        if len(all_timestamps) < 2:
            return None
        
        # Align signals by timestamp
        ts1_dict = dict(timestamps1)
        ts2_dict = dict(timestamps2)
        
        aligned_s1 = [ts1_dict[ts] for ts in sorted(all_timestamps)]
        aligned_s2 = [ts2_dict[ts] for ts in sorted(all_timestamps)]
        
        if len(aligned_s1) < 2:
            return None
        
        # Calculate correlation
        correlation = np.corrcoef(aligned_s1, aligned_s2)[0, 1]
        return float(correlation) if not np.isnan(correlation) else 0.0
    
    def calculate_correlation_matrix(self, strategy_names: List[str], 
                                   lookback_period: int = 100) -> pd.DataFrame:
        """Calculate correlation matrix for multiple strategies"""
        n = len(strategy_names)
        corr_matrix = np.eye(n)  # Initialize with identity matrix (diagonal = 1)
        
        for i in range(n):
            for j in range(i+1, n):
                corr = self.calculate_pairwise_correlation(
                    strategy_names[i], 
                    strategy_names[j], 
                    lookback_period
                )
                
                if corr is not None:
                    corr_matrix[i, j] = corr
                    corr_matrix[j, i] = corr
        
        # Create DataFrame with strategy names
        return pd.DataFrame(corr_matrix, index=strategy_names, columns=strategy_names)
    
    def calculate_distance_matrix(self, strategy_names: List[str], 
                                lookback_period: int = 100) -> pd.DataFrame:
        """Calculate distance matrix based on correlations (1 - |correlation|)"""
        corr_matrix = self.calculate_correlation_matrix(strategy_names, lookback_period)
        # Convert correlation to distance: higher correlation = lower distance
        distance_matrix = 1 - np.abs(corr_matrix)
        return pd.DataFrame(distance_matrix, index=strategy_names, columns=strategy_names)
    
    def cluster_strategies(self, strategy_names: List[str], 
                         n_clusters: int = 3, 
                         lookback_period: int = 100) -> Dict[str, int]:
        """Cluster strategies based on signal correlation"""
        distance_matrix = self.calculate_distance_matrix(strategy_names, lookback_period)
        
        # Convert to condensed distance matrix for scipy
        condensed_distances = pdist(distance_matrix.values)
        
        # Perform hierarchical clustering
        linkage_matrix = linkage(condensed_distances, method='ward')
        
        # Assign clusters
        cluster_labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust')
        
        # Return dictionary mapping strategy names to cluster IDs
        return {name: int(cluster_labels[i]) for i, name in enumerate(strategy_names)}
    
    def calculate_diversification_score(self, strategy_weights: Dict[str, float], 
                                      lookback_period: int = 100) -> float:
        """Calculate diversification score based on strategy weights and correlations"""
        strategy_names = list(strategy_weights.keys())
        weights = np.array([strategy_weights[name] for name in strategy_names])
        
        # Calculate correlation matrix
        corr_matrix = self.calculate_correlation_matrix(strategy_names, lookback_period)
        
        # Calculate weighted average correlation (diagonal is 1, so we exclude it)
        weighted_corr = 0.0
        total_weight = 0.0
        
        for i in range(len(strategy_names)):
            for j in range(len(strategy_names)):
                if i != j:  # Exclude self-correlation
                    pair_weight = weights[i] * weights[j]
                    weighted_corr += pair_weight * corr_matrix.iloc[i, j]
                    total_weight += pair_weight
        
        if total_weight == 0:
            return 1.0  # Fully diversified if no pairs
        
        # Diversification score: 1 - average weighted correlation
        avg_weighted_corr = weighted_corr / total_weight
        diversification_score = max(0.0, 1.0 - abs(avg_weighted_corr))  # Ensure non-negative
        
        return diversification_score
    
    def get_uncorrelated_strategy_pairs(self, strategy_names: List[str], 
                                      threshold: float = 0.3, 
                                      lookback_period: int = 100) -> List[Tuple[str, str, float]]:
        """Get pairs of strategies with correlation below threshold"""
        pairs = []
        n = len(strategy_names)
        
        for i in range(n):
            for j in range(i+1, n):
                corr = self.calculate_pairwise_correlation(
                    strategy_names[i], 
                    strategy_names[j], 
                    lookback_period
                )
                
                if corr is not None and abs(corr) < threshold:
                    pairs.append((strategy_names[i], strategy_names[j], corr))
        
        return pairs
    
    def analyze_signal_concordance(self, strategy1: str, strategy2: str, 
                                 lookback_period: int = 100) -> Dict[str, float]:
        """Analyze how often two strategies agree on signal direction"""
        if strategy1 not in self.signal_history or strategy2 not in self.signal_history:
            return {}
        
        hist1 = self.signal_history[strategy1][-lookback_period:]
        hist2 = self.signal_history[strategy2][-lookback_period:]
        
        # Create timeline mapping
        ts1_dict = {(ts, symbol): val for ts, val, symbol in hist1}
        ts2_dict = {(ts, symbol): val for ts, val, symbol in hist2}
        
        # Find common timestamps and symbols
        common_keys = set(ts1_dict.keys()) & set(ts2_dict.keys())
        
        if len(common_keys) < 2:
            return {}
        
        same_direction = 0
        total_comparisons = 0
        
        for ts_symbol in common_keys:
            val1 = ts1_dict[ts_symbol]
            val2 = ts2_dict[ts_symbol]
            
            # Check if both signals are in the same direction (both positive or both negative)
            if (val1 >= 0) == (val2 >= 0):
                same_direction += 1
            total_comparisons += 1
        
        return {
            'concordance_ratio': same_direction / total_comparisons if total_comparisons > 0 else 0,
            'total_comparisons': total_comparisons,
            'same_direction_count': same_direction,
            'opposite_direction_count': total_comparisons - same_direction
        }


class EnhancedSignalFusionService:
    """Enhanced signal fusion service with correlation-aware combining"""
    
    def __init__(self):
        self.correlation_analyzer = SignalCorrelationAnalyzer()
        self.fusion_weights = {}  # Strategy -> weight
        self.diversification_enabled = True
    
    def add_signal_for_analysis(self, strategy_name: str, timestamp: datetime, 
                               signal_value: float, symbol: str):
        """Add signal data for correlation analysis"""
        self.correlation_analyzer.add_signal_data(strategy_name, timestamp, signal_value, symbol)
    
    def fuse_signals_with_diversification(self, signals: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Fuse signals while considering diversification"""
        if not signals:
            return None
        
        # Group signals by symbol
        symbol_signals = {}
        for signal in signals:
            symbol = signal.get('symbol', 'UNKNOWN')
            if symbol not in symbol_signals:
                symbol_signals[symbol] = []
            symbol_signals[symbol].append(signal)
        
        results = {}
        for symbol, symbol_signals_list in symbol_signals.items():
            if not symbol_signals_list:
                continue
            
            # Extract strategy names
            strategy_names = [s.get('strategy_name', 'unknown') for s in symbol_signals_list]
            
            # Calculate diversification score if we have multiple strategies
            if len(strategy_names) > 1 and self.diversification_enabled:
                # Create temporary weights (initially equal)
                temp_weights = {name: 1.0/len(strategy_names) for name in strategy_names}
                div_score = self.correlation_analyzer.calculate_diversification_score(temp_weights)
                
                # Adjust weights based on diversification (reduce weight for highly correlated strategies)
                if div_score < 0.5:  # Low diversification
                    # Calculate individual strategy correlations and adjust weights
                    weights = self._adjust_weights_for_diversification(strategy_names)
                else:
                    # Equal weights if well-diversified
                    weights = {name: 1.0/len(strategy_names) for name in strategy_names}
            else:
                # Equal weights if not diversified or single strategy
                weights = {name: 1.0/len(strategy_names) for name in strategy_names}
            
            # Weighted fusion of signal values
            total_weighted_value = 0
            total_weight = 0
            
            for signal in symbol_signals_list:
                strategy_name = signal.get('strategy_name', 'unknown')
                signal_value = signal.get('value', 0)
                weight = weights.get(strategy_name, 1.0/len(strategy_names))
                
                total_weighted_value += signal_value * weight
                total_weight += weight
            
            if total_weight > 0:
                fused_value = total_weighted_value / total_weight
                results[symbol] = {
                    'symbol': symbol,
                    'fused_value': fused_value,
                    'diversification_score': div_score if 'div_score' in locals() else 1.0,
                    'weights_used': weights,
                    'original_signals_count': len(symbol_signals_list)
                }
        
        # Return the first result (in a real system you might return all)
        return list(results.values())[0] if results else None
    
    def _adjust_weights_for_diversification(self, strategy_names: List[str]) -> Dict[str, float]:
        """Adjust weights based on strategy diversification"""
        if len(strategy_names) <= 1:
            return {name: 1.0 for name in strategy_names}
        
        # Calculate correlation matrix
        corr_matrix = self.correlation_analyzer.calculate_correlation_matrix(strategy_names)
        
        # Simple approach: reduce weight for strategies that are highly correlated with others
        weights = {}
        for strategy in strategy_names:
            # Calculate average correlation of this strategy with all others
            other_corrs = [corr_matrix.loc[strategy, s] for s in strategy_names if s != strategy]
            avg_corr = np.mean(np.abs(other_corrs)) if other_corrs else 0
            
            # Weight inversely proportional to average correlation
            weight = max(0.1, 1.0 - avg_corr)  # Minimum weight of 0.1
            weights[strategy] = weight
        
        # Normalize weights to sum to 1
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        
        return weights


# Global instances
signal_correlation_analyzer = SignalCorrelationAnalyzer()
enhanced_fusion_service = EnhancedSignalFusionService()