"""
Performance optimization utilities for the Hedge Fund trading system.
Implements HRP, Kelly criterion, volatility targeting, and other optimizations.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import warnings
warnings.filterwarnings('ignore')

try:
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.covariance import LedoitWolf
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class HighFrequencyPerformanceOptimizer:
    """Optimizations for high-frequency trading workloads."""
    
    def precompute_indicators_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Precompute indicators using vectorized NumPy operations."""
        result_df = df.copy()
        
        # Precompute rolling windows once for efficiency
        close_20 = df['close'].rolling(20, min_periods=1)
        close_50 = df['close'].rolling(50, min_periods=1)
        high_14 = df['high'].rolling(14, min_periods=1)
        low_14 = df['low'].rolling(14, min_periods=1)
        close_14 = df['close'].rolling(14, min_periods=1)
        
        # Vectorized moving averages
        result_df['sma_20'] = close_20.mean()
        result_df['sma_50'] = close_50.mean()
        
        # Vectorized RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
        
        rs = gain / (loss + 1e-10)  # Add small epsilon to avoid division by zero
        rsi = 100 - (100 / (1 + rs))
        result_df['rsi'] = rsi
        
        # Vectorized ATR calculation
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        result_df['atr'] = pd.Series(tr).rolling(14).mean()
        
        # Vectorized Bollinger Bands
        bb_middle = close_20.mean()
        bb_std = close_20.std()
        result_df['bb_middle'] = bb_middle
        result_df['bb_upper'] = bb_middle + (bb_std * 2)
        result_df['bb_lower'] = bb_middle - (bb_std * 2)
        
        # Shift all indicators to prevent lookahead bias
        columns_to_shift = ['rsi', 'sma_20', 'sma_50', 'atr', 'bb_middle', 'bb_upper', 'bb_lower']
        for col in columns_to_shift:
            if col in result_df:
                result_df[col] = result_df[col].shift(1)
        
        return result_df
    
    def vectorized_sl_tp_check(self, positions: List[Dict], current_data: pd.Series) -> List[Dict]:
        """Vectorized SL/TP check for faster execution."""
        if not positions:
            return []
        
        # Convert positions to arrays for vectorization
        prices = np.array([pos['entry_price'] for pos in positions])
        sizes = np.array([pos['size'] for pos in positions])
        directions = np.array([pos['direction'] for pos in positions])
        sl_prices = np.array([pos['stop_loss'] for pos in positions])
        tp_prices = np.array([pos['take_profit'] for pos in positions])
        
        current_high = current_data['high']
        current_low = current_data['low']
        
        # Vectorized checking
        if len(directions) > 0:
            # For long positions (direction == 1), check if low <= SL or high >= TP
            long_mask = directions == 1
            short_mask = directions == -1
            
            # Initialize exit conditions
            sl_triggered = np.zeros_like(prices, dtype=bool)
            tp_triggered = np.zeros_like(prices, dtype=bool)
            
            if np.any(long_mask):
                sl_mask = long_mask & (current_low <= sl_prices)
                tp_mask = long_mask & (current_high >= tp_prices)
                sl_triggered |= sl_mask
                tp_triggered |= tp_mask
            
            if np.any(short_mask):
                sl_mask = short_mask & (current_high >= sl_prices)
                tp_mask = short_mask & (current_low <= tp_prices)
                sl_triggered |= sl_mask
                tp_triggered |= tp_mask
        
        # Handle simultaneous triggers with priority (SL > TP for longs, TP > SL for shorts)
        simultaneous = sl_triggered & tp_triggered
        if np.any(simultaneous):
            for i in np.where(simultaneous)[0]:
                pos_idx = i
                entry = positions[pos_idx]['entry_price']
                
                if directions[pos_idx] == 1:  # Long position
                    # SL priority > TP priority for longs
                    if abs(sl_prices[pos_idx] - entry) <= abs(tp_prices[pos_idx] - entry):
                        # Keep SL triggered, cancel TP
                        tp_triggered[pos_idx] = False
                    else:
                        # Keep TP triggered, cancel SL
                        sl_triggered[pos_idx] = False
                else:  # Short position
                    # For shorts, the priority depends on implementation, but generally TP > SL
                    if abs(tp_prices[pos_idx] - entry) <= abs(sl_prices[pos_idx] - entry):
                        # Keep TP triggered, cancel SL
                        sl_triggered[pos_idx] = False
                    else:
                        # Keep SL triggered, cancel TP
                        tp_triggered[pos_idx] = False

        # Create list of triggered positions
        triggered_exits = []
        for i, (sl_trig, tp_trig) in enumerate(zip(sl_triggered, tp_triggered)):
            if sl_trig or tp_trig:
                exit_type = 'SL' if sl_trig else 'TP'
                exit_price = sl_prices[i] if sl_trig else tp_prices[i]
                
                triggered_exits.append({
                    'position_idx': i,
                    'exit_type': exit_type,
                    'exit_price': exit_price,
                    'original_position': positions[i]
                })
        
        return triggered_exits


class HierarchicalRiskParity:
    """Hierarchical Risk Parity portfolio optimization."""
    
    def __init__(self):
        pass
    
    def calculate_allocation(self, returns_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate HRP allocation based on hierarchical clustering."""
        if not HAS_SKLEARN:
            # Fallback to inverse variance if sklearn not available
            variances = returns_df.var()
            weights = 1.0 / variances
            weights = weights / weights.sum()
            return weights.to_dict()
        
        # Standardize returns
        returns = returns_df.fillna(0).values
        
        # Calculate correlation matrix
        correl = np.corrcoef(returns.T)
        correl = np.nan_to_num(correl, nan=0.0)
        
        # Hierarchical clustering
        distances = np.sqrt(2 * (1 - correl))
        
        # Perform clustering (this is a simplified version)
        n_clusters = min(len(returns_df.columns), max(2, len(returns_df.columns) // 2))
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters, 
            metric='precomputed', 
            linkage='single'
        )
        
        cluster_labels = clustering.fit_predict(distances)
        
        # Calculate risk parity within clusters and between clusters
        # This is a simplified HRP implementation
        cov_matrix = LedoitWolf().fit(returns).covariance_
        
        # Risk parity weights
        n = cov_matrix.shape[0]
        weights = np.ones(n) / n
        
        # Iteratively adjust weights to achieve risk parity
        for _ in range(50):  # Max iterations
            risk_contribution = weights * (cov_matrix @ weights) / (weights @ cov_matrix @ weights)
            target_risk = np.sum(risk_contribution) / len(risk_contribution)
            weights = weights * np.sqrt(target_risk / risk_contribution)
            weights = weights / np.sum(weights)  # Normalize
        
        # Convert back to dict
        assets = returns_df.columns.tolist()
        allocation = {asset: float(w) for asset, w in zip(assets, weights)}
        
        return allocation


class KellyCriterionSizer:
    """Kelly Criterion and Half-Kelly position sizing."""
    
    def calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly fraction: K = (bp - q) / b
        where b = avg_win / avg_loss (win/loss ratio)
              p = win_rate
              q = 1 - win_rate
        """
        if avg_loss == 0:
            return 1.0  # If no losses, bet everything (theoretical)
        
        b = avg_win / avg_loss if avg_loss != 0 else 0
        p = win_rate
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b if b != 0 else 0
        
        # Return half-kelly to be more conservative
        half_kelly = kelly_fraction / 2
        return max(0, min(half_kelly, 1.0))  # Clamp between 0 and 1


class VolatilityTargeter:
    """Volatility targeting for position sizing."""
    
    def calculate_volatility_based_size(self, 
                                     current_price: float, 
                                     atr: float, 
                                     target_volatility: float = 0.15,  # 15% annual
                                     portfolio_value: float = 100000) -> float:
        """
        Calculate position size based on volatility targeting.
        """
        # Calculate daily volatility (assuming 252 trading days)
        daily_volatility = target_volatility / np.sqrt(252)
        
        # Size based on risk budget
        risk_budget = portfolio_value * daily_volatility
        
        # Size based on expected volatility (using ATR as proxy)
        expected_move = atr
        position_size = risk_budget / expected_move if expected_move > 0 else 0
        
        return position_size


class AdvancedRegimeDetector:
    """Advanced market regime detection."""
    
    def detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect market regime based on multiple factors:
        - Volatility regime (low/normal/high)
        - Trend regime (trending/reverting)
        - Volatility-regime correlation
        """
        if df.empty:
            return {
                'volatility_regime': 'low',
                'trend_regime': 'neutral',
                'correlation_regime': 'low',
                'risk_level': 1.0
            }
        
        # Calculate volatility regime (based on ATR)
        atr_values = df['atr'].fillna(0).tail(30).values
        avg_atr = np.mean(atr_values) if len(atr_values) > 0 else 0
        recent_atr = atr_values[-1] if len(atr_values) > 0 else 0
        
        # Define volatility thresholds based on historical ATR
        if len(atr_values) > 10:
            historical_avg = np.mean(atr_values)
            current_vs_hist = recent_atr / (historical_avg + 1e-10)
            
            if current_vs_hist > 1.5:
                volatility_regime = 'high'
                volatility_factor = 1.5
            elif current_vs_hist < 0.7:
                volatility_regime = 'low'
                volatility_factor = 0.5
            else:
                volatility_regime = 'normal'
                volatility_factor = 1.0
        else:
            volatility_regime = 'normal'
            volatility_factor = 1.0
        
        # Calculate trend regime (based on price action)
        closes = df['close'].tail(50).pct_change().dropna().values
        if len(closes) > 10:
            # Measure trend strength with autocorrelation
            autocorr = np.corrcoef(closes[:-1], closes[1:])[0, 1] if len(closes) > 1 else 0
            autocorr = 0 if np.isnan(autocorr) else autocorr
            
            if autocorr > 0.3:
                trend_regime = 'trending'
                trend_factor = 0.8  # Trending strategies work better
            elif autocorr < -0.1:
                trend_regime = 'reverting'
                trend_factor = 1.2  # Mean reversion strategies work better
            else:
                trend_regime = 'neutral'
                trend_factor = 1.0
        else:
            trend_regime = 'neutral'
            trend_factor = 1.0
        
        # Overall risk level considering both regimes
        risk_level = volatility_factor * trend_factor
        
        return {
            'volatility_regime': volatility_regime,
            'trend_regime': trend_regime,
            'correlation_regime': 'medium',  # Simplified for now
            'risk_level': risk_level,
            'volatility_factor': volatility_factor,
            'trend_factor': trend_factor
        }


class PortfolioOptimizer:
    """Main portfolio optimization class combining all techniques."""
    
    def __init__(self):
        self.hrp = HierarchicalRiskParity()
        self.kelly = KellyCriterionSizer()
        self.vol_targeter = VolatilityTargeter()
        self.regime_detector = AdvancedRegimeDetector()
    
    def optimize_allocation(self, 
                          returns_data: pd.DataFrame,
                          performance_metrics: Dict[str, Any],
                          market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Combine all optimization techniques for portfolio allocation.
        """
        # HRP allocation based on return correlations
        hrp_allocation = self.hrp.calculate_allocation(returns_data)
        
        # Kelly sizing based on performance
        win_rate = performance_metrics.get('win_rate', 0.5)
        avg_win = abs(performance_metrics.get('avg_positive_return', 0.02))
        avg_loss = abs(performance_metrics.get('avg_negative_return', 0.015))
        
        kelly_size = self.kelly.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
        
        # Volatility adjustment based on market data
        current_price = market_data['close'].iloc[-1] if not market_data.empty else 100
        current_atr = market_data['atr'].iloc[-1] if 'atr' in market_data.columns and not market_data.empty else 1
        portfolio_value = performance_metrics.get('portfolio_value', 100000)
        
        vol_adjusted_size = self.vol_targeter.calculate_volatility_based_size(
            current_price, current_atr, portfolio_value=portfolio_value
        )
        
        # Regime adjustment
        regime_info = self.regime_detector.detect_regime(market_data)
        regime_adjustment = regime_info.get('risk_level', 1.0)
        
        # Combine all factors
        final_allocation = {}
        for asset, base_weight in hrp_allocation.items():
            # Adjust allocation based on regime and sizing
            adjusted_weight = base_weight * regime_adjustment * kelly_size if kelly_size > 0 else base_weight
            
            final_allocation[asset] = min(adjusted_weight, 0.2)  # Limit to 20% per asset
        
        return {
            'allocation': final_allocation,
            'position_size': min(kelly_size * 0.8, 0.1),  # Conservative sizing
            'regime_info': regime_info,
            'risk_adjustment': regime_adjustment
        }