"""
Profitability Enhancement Techniques for the Hedge Fund Trading System.
Implements variance reduction, expectancy compounding, selective trade filtering, 
capital efficiency improvements, and signal timing refinement.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


class ProfitabilityEnhancer:
    """
    Comprehensive profitability enhancement system with:
    - Variance reduction techniques
    - Expectancy compounding
    - Selective trade filtering
    - Capital efficiency improvements
    - Signal timing refinement
    """

    def __init__(self,
                 min_signal_strength_threshold: float = 0.3,
                 max_correlation_threshold: float = 0.7,
                 volatility_filter_threshold: float = 0.03,
                 trend_confirmation_bars: int = 3,
                 minimum_sample_size: int = 20,
                 confidence_boost_threshold: float = 0.7,
                 efficiency_target: float = 0.85):

        self.min_signal_strength_threshold = min_signal_strength_threshold
        self.max_correlation_threshold = max_correlation_threshold
        self.volatility_filter_threshold = volatility_filter_threshold
        self.trend_confirmation_bars = trend_confirmation_bars
        self.minimum_sample_size = minimum_sample_size
        self.confidence_boost_threshold = confidence_boost_threshold
        self.efficiency_target = efficiency_target

        # Track performance metrics
        self.trade_history: List[Dict[str, Any]] = []
        self.signal_quality_history: Dict[str, List[float]] = {}
        self.timing_efficiency: Dict[str, float] = {}
        self.variance_reduction_stats: Dict[str, Dict[str, float]] = {}

    def apply_variance_reduction(self, returns: List[float], window: int = 20) -> List[float]:
        """
        Apply variance reduction techniques to trading returns.
        
        Methods:
        1. Rolling mean adjustment
        2. Outlier filtering
        3. Smoothing
        """
        if len(returns) < window:
            return returns

        # Method 1: Rolling mean adjustment
        rolling_means = pd.Series(returns).rolling(window=window, center=True).mean()
        adjusted_returns = [r - rm if not pd.isna(rm) else r for r, rm in zip(returns, rolling_means)]

        # Method 2: Outlier filtering using IQR
        Q1 = np.percentile(adjusted_returns, 25)
        Q3 = np.percentile(adjusted_returns, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        filtered_returns = [r if lower_bound <= r <= upper_bound else np.clip(r, lower_bound, upper_bound)
                            for r in adjusted_returns]

        # Method 3: Smoothing with EWMA
        series = pd.Series(filtered_returns)
        smoothed = series.ewm(alpha=0.3).mean()

        # Store variance reduction stats
        original_var = np.var(returns) if returns else 0
        reduced_var = np.var(smoothed.dropna()) if not smoothed.empty else 0
        reduction_ratio = (original_var - reduced_var) / original_var if original_var != 0 else 0

        self.variance_reduction_stats['overall'] = {
            'original_variance': original_var,
            'reduced_variance': reduced_var,
            'reduction_ratio': reduction_ratio,
            'window': window
        }

        return smoothed.fillna(0).tolist()

    def compound_expectancy(self,
                            base_expectancy: float,
                            confidence: float,
                            market_regime_factor: float = 1.0) -> float:
        """
        Compound expectancy based on multiple factors.
        
        Formula: base_expectancy * confidence_factor * regime_factor
        """
        # Confidence-based amplification
        confidence_factor = 0.5 + (confidence * 0.5)  # Maps 0-1 to 0.5-1.0

        # Regime-based adjustment
        regime_factor = max(0.5, min(1.5, market_regime_factor))

        compounded_expectancy = base_expectancy * confidence_factor * regime_factor

        return compounded_expectancy

    def selective_trade_filter(self,
                               signal_strength: float,
                               correlation_with_portfolio: float,
                               market_volatility: float,
                               trend_strength: float,
                               regime_confidence: float,
                               recent_performance: float) -> bool:
        """
        Apply selective trade filtering based on multiple criteria.
        """
        # Filter 1: Signal strength
        if signal_strength < self.min_signal_strength_threshold:
            return False

        # Filter 2: Correlation with portfolio
        if correlation_with_portfolio > self.max_correlation_threshold:
            return False

        # Filter 3: Market volatility (avoid extremely volatile conditions)
        if market_volatility > self.volatility_filter_threshold:
            return False

        # Filter 4: Trend confirmation
        if abs(trend_strength) < 0.1:  # Weak trend
            return False

        # Filter 5: Regime confidence
        if regime_confidence < 0.5:
            return False

        # Filter 6: Recent performance (avoid trading when performance is poor)
        if recent_performance < -0.05:  # If recent performance is worse than -5%
            return False

        return True

    def improve_capital_efficiency(self,
                                   position_size: float,
                                   portfolio_value: float,
                                   volatility: float,
                                   correlation_factor: float,
                                   regime_factor: float) -> float:
        """
        Improve capital efficiency by optimizing position sizing.
        """
        # Calculate efficiency multiplier
        volatility_efficiency = max(0.5,
                                    min(1.5, 1.0 / (1.0 + volatility * 10)))  # Lower volatility = higher efficiency
        correlation_efficiency = max(0.5, min(1.2, 1.0 - correlation_factor))  # Lower correlation = higher efficiency
        regime_efficiency = max(0.8, min(1.2, regime_factor))  # Regime-appropriate sizing

        efficiency_multiplier = (volatility_efficiency * correlation_efficiency * regime_efficiency)

        # Apply efficiency target
        optimal_size = position_size * efficiency_multiplier
        max_efficient_size = portfolio_value * self.efficiency_target / 10  # 10% max per position as example

        return min(optimal_size, max_efficient_size)

    def refine_signal_timing(self,
                             entry_signal_time: datetime,
                             market_data: pd.DataFrame,
                             lookback_bars: int = 5) -> Dict[str, Any]:
        """
        Refine signal timing using market microstructure analysis.
        """
        if len(market_data) < lookback_bars:
            return {'refined_time': entry_signal_time, 'timing_quality': 0.5, 'refinement_reason': 'insufficient_data'}

        # Get recent data
        recent_data = market_data.tail(lookback_bars)

        # Calculate volume-weighted average price for timing refinement
        vwap = (recent_data['close'] * recent_data['volume']).sum() / recent_data['volume'].sum() if recent_data[
                                                                                                         'volume'].sum() > 0 else \
        recent_data['close'].iloc[-1]

        # Calculate momentum in recent bars
        momentum = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]

        # Calculate volatility in recent bars
        recent_returns = recent_data['close'].pct_change().dropna()
        volatility = recent_returns.std() if len(recent_returns) > 1 else 0.01

        # Determine optimal timing based on microstructure
        if momentum > 0.02 and volatility < 0.02:  # Strong momentum, low volatility
            timing_quality = 0.9
            refinement_reason = "strong_momentum_low_volatility"
        elif momentum < -0.02 and volatility < 0.02:  # Strong reversal, low volatility
            timing_quality = 0.85
            refinement_reason = "strong_reversal_low_volatility"
        elif volatility > 0.03:  # High volatility - delay entry
            timing_quality = 0.4
            refinement_reason = "high_volatility_delay"
        else:  # Normal conditions
            timing_quality = 0.7
            refinement_reason = "normal_conditions"

        # Adjust timing based on quality
        if timing_quality < 0.6:  # Poor timing conditions
            refined_time = entry_signal_time + timedelta(minutes=5)  # Delay entry
        elif timing_quality > 0.8:  # Excellent timing conditions
            refined_time = entry_signal_time  # Immediate entry
        else:  # Good timing conditions
            refined_time = entry_signal_time + timedelta(minutes=1)  # Slight delay to confirm

        return {
            'refined_time': refined_time,
            'timing_quality': timing_quality,
            'refinement_reason': refinement_reason,
            'vwap': vwap,
            'momentum': momentum,
            'volatility': volatility
        }

    def calculate_improved_expectancy(self,
                                      win_rate: float,
                                      avg_win: float,
                                      avg_loss: float,
                                      signal_confidence: float,
                                      regime_confidence: float,
                                      correlation_adjustment: float = 1.0) -> float:
        """
        Calculate improved expectancy with all enhancement factors.
        """
        # Base expectancy
        base_expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        # Apply enhancement factors
        confidence_boost = 0.5 + (signal_confidence * 0.3) + (regime_confidence * 0.2)  # Weight signal confidence more
        correlation_penalty = max(0.5, 1.0 - correlation_adjustment)  # Reduce expectancy if highly correlated

        improved_expectancy = base_expectancy * confidence_boost * correlation_penalty

        return improved_expectancy

    def optimize_trade_frequency(self,
                                 current_frequency: float,
                                 market_volatility: float,
                                 strategy_performance: float,
                                 correlation_with_other_strategies: float) -> float:
        """
        Optimize trade frequency based on market conditions.
        """
        # Adjust frequency based on volatility (higher volatility = fewer trades)
        volatility_factor = max(0.3, min(1.0, 1.0 - (market_volatility / 0.05)))

        # Adjust based on strategy performance (poor performance = fewer trades)
        performance_factor = max(0.5, min(1.2, 1.0 + strategy_performance))

        # Adjust based on correlation (high correlation = fewer trades)
        correlation_factor = max(0.6, min(1.0, 1.0 - correlation_with_other_strategies))

        optimized_frequency = current_frequency * volatility_factor * performance_factor * correlation_factor

        return max(0.1, min(2.0, optimized_frequency))  # Keep within reasonable bounds

    def enhance_portfolio_allocation(self,
                                     strategy_returns: Dict[str, List[float]],
                                     correlation_matrix: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Enhance portfolio allocation using risk parity and diversification.
        """
        if not strategy_returns:
            return {}

        # Calculate individual strategy volatilities
        strategy_vols = {}
        for strategy, returns in strategy_returns.items():
            if returns:
                strategy_vols[strategy] = np.std(returns)
            else:
                strategy_vols[strategy] = 0.02  # Default volatility

        # If no correlation matrix provided, assume moderate correlations
        if correlation_matrix is None:
            n = len(strategy_returns)
            correlation_matrix = np.eye(n)
            strategies = list(strategy_returns.keys())
            for i in range(n):
                for j in range(i + 1, n):
                    correlation_matrix[i][j] = 0.3  # Moderate correlation
                    correlation_matrix[j][i] = 0.3

        # Calculate risk parity weights
        weights = {}
        total_inverse_risk = sum(1.0 / max(vol, 0.001) for vol in strategy_vols.values())

        for strategy, vol in strategy_vols.items():
            weight = (1.0 / max(vol, 0.001)) / total_inverse_risk
            weights[strategy] = weight

        # Apply diversification adjustment based on correlation
        for i, strategy in enumerate(strategy_returns.keys()):
            if i < len(correlation_matrix):
                avg_correlation = np.mean([correlation_matrix[i][j] for j in range(len(correlation_matrix)) if i != j])
                # Reduce weight if strategy is highly correlated with others
                weights[strategy] *= max(0.5, 1.0 - avg_correlation)

        # Renormalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            for strategy in weights:
                weights[strategy] /= total_weight
        else:
            # Equal weights if all volatilities are zero
            equal_weight = 1.0 / len(strategy_returns) if strategy_returns else 0
            weights = {strategy: equal_weight for strategy in strategy_returns.keys()}

        return weights

    def calculate_sharpe_improvement(self,
                                     original_returns: List[float],
                                     enhanced_returns: List[float]) -> Dict[str, float]:
        """
        Calculate improvement in Sharpe ratio after applying enhancements.
        """
        if not original_returns or not enhanced_returns:
            return {'original_sharpe': 0, 'enhanced_sharpe': 0, 'improvement': 0}

        # Calculate original Sharpe
        orig_mean = np.mean(original_returns)
        orig_std = np.std(original_returns) if len(original_returns) > 1 else 1
        original_sharpe = (
                                      orig_mean - 0.02 / 252) / orig_std if orig_std != 0 else 0  # Assuming 2% annual risk-free rate

        # Calculate enhanced Sharpe
        enh_mean = np.mean(enhanced_returns)
        enh_std = np.std(enhanced_returns) if len(enhanced_returns) > 1 else 1
        enhanced_sharpe = (enh_mean - 0.02 / 252) / enh_std if enh_std != 0 else 0

        improvement = enhanced_sharpe - original_sharpe

        return {
            'original_sharpe': original_sharpe,
            'enhanced_sharpe': enhanced_sharpe,
            'improvement': improvement,
            'improvement_percentage': (improvement / abs(original_sharpe) * 100) if original_sharpe != 0 else 0
        }

    def record_trade_outcome(self,
                             strategy_name: str,
                             signal_strength: float,
                             entry_time: datetime,
                             exit_time: datetime,
                             pnl: float,
                             expectancy: float,
                             applied_enhancements: List[str]):
        """
        Record trade outcome for continuous improvement.
        """
        trade_record = {
            'strategy': strategy_name,
            'signal_strength': signal_strength,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'pnl': pnl,
            'expectancy': expectancy,
            'applied_enhancements': applied_enhancements,
            'duration': (exit_time - entry_time).total_seconds() / 3600  # Duration in hours
        }

        self.trade_history.append(trade_record)

        # Update signal quality history
        if strategy_name not in self.signal_quality_history:
            self.signal_quality_history[strategy_name] = []
        self.signal_quality_history[strategy_name].append(signal_strength)

    def get_enhancement_effectiveness(self) -> Dict[str, Any]:
        """
        Get effectiveness metrics for all enhancement techniques.
        """
        if not self.trade_history:
            return {
                'variance_reduction_stats': self.variance_reduction_stats,
                'total_trades': 0,
                'average_signal_quality': 0,
                'enhancement_usage': {}
            }

        # Calculate average signal quality by strategy
        avg_signal_quality = {}
        for strategy, qualities in self.signal_quality_history.items():
            avg_signal_quality[strategy] = np.mean(qualities) if qualities else 0

        # Count enhancement usage
        all_enhancements = []
        for trade in self.trade_history:
            all_enhancements.extend(trade['applied_enhancements'])

        enhancement_usage = {}
        for enh in all_enhancements:
            enhancement_usage[enh] = enhancement_usage.get(enh, 0) + 1

        # Calculate overall effectiveness
        total_pnl = sum(trade['pnl'] for trade in self.trade_history)
        avg_pnl = total_pnl / len(self.trade_history) if self.trade_history else 0

        return {
            'variance_reduction_stats': self.variance_reduction_stats,
            'total_trades': len(self.trade_history),
            'average_signal_quality': avg_signal_quality,
            'enhancement_usage': enhancement_usage,
            'total_pnl': total_pnl,
            'average_pnl': avg_pnl,
            'best_performing_enhancements': sorted(enhancement_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        }


class IntegratedProfitabilitySystem:
    """
    Integrated system that combines all profitability enhancement techniques.
    """

    def __init__(self):
        self.enhancer = ProfitabilityEnhancer()
        self.active_filters = {
            'variance_reduction': True,
            'selective_filtering': True,
            'capital_efficiency': True,
            'timing_refinement': True
        }

    def process_signal(self,
                       signal_data: Dict[str, Any],
                       market_data: pd.DataFrame,
                       portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a trading signal through all profitability enhancement techniques.
        """
        processed_signal = signal_data.copy()

        enhancements_applied = []

        # 1. Apply selective trade filtering
        if self.active_filters['selective_filtering']:
            should_trade = self.enhancer.selective_trade_filter(
                signal_strength=signal_data.get('signal_strength', 0.5),
                correlation_with_portfolio=portfolio_data.get('correlation', 0.3),
                market_volatility=market_data['close'].pct_change().std() if len(market_data) > 1 else 0.02,
                trend_strength=signal_data.get('trend_strength', 0.1),
                regime_confidence=signal_data.get('regime_confidence', 0.6),
                recent_performance=portfolio_data.get('recent_performance', 0.02)
            )

            if not should_trade:
                processed_signal['filtered_out'] = True
                processed_signal['filter_reason'] = 'failed_selective_filter'
                return processed_signal

            enhancements_applied.append('selective_filtering')

        # 2. Improve capital efficiency
        if self.active_filters['capital_efficiency']:
            original_size = signal_data.get('position_size', 1.0)
            enhanced_size = self.enhancer.improve_capital_efficiency(
                position_size=original_size,
                portfolio_value=portfolio_data.get('portfolio_value', 100000),
                volatility=market_data['close'].pct_change().std() if len(market_data) > 1 else 0.02,
                correlation_factor=portfolio_data.get('correlation', 0.3),
                regime_factor=signal_data.get('regime_factor', 1.0)
            )

            processed_signal['enhanced_position_size'] = enhanced_size
            enhancements_applied.append('capital_efficiency')

        # 3. Refine signal timing
        if self.active_filters['timing_refinement']:
            timing_refinement = self.enhancer.refine_signal_timing(
                entry_signal_time=signal_data.get('signal_time', datetime.now()),
                market_data=market_data
            )

            processed_signal['refined_entry_time'] = timing_refinement['refined_time']
            processed_signal['timing_quality'] = timing_refinement['timing_quality']
            processed_signal['timing_refinement'] = timing_refinement['refinement_reason']
            enhancements_applied.append('timing_refinement')

        # 4. Compound expectancy
        base_expectancy = signal_data.get('base_expectancy', 0.02)
        confidence = signal_data.get('confidence', 0.6)
        regime_factor = signal_data.get('regime_factor', 1.0)

        enhanced_expectancy = self.enhancer.compound_expectancy(
            base_expectancy=base_expectancy,
            confidence=confidence,
            market_regime_factor=regime_factor
        )

        processed_signal['enhanced_expectancy'] = enhanced_expectancy
        enhancements_applied.append('expectancy_compounding')

        # Record applied enhancements
        processed_signal['applied_enhancements'] = enhancements_applied

        return processed_signal

    def optimize_portfolio_allocation(self,
                                      strategy_returns: Dict[str, List[float]],
                                      correlation_matrix: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Optimize portfolio allocation using enhancement techniques.
        """
        return self.enhancer.enhance_portfolio_allocation(
            strategy_returns=strategy_returns,
            correlation_matrix=correlation_matrix
        )

    def evaluate_enhancement_impact(self,
                                    original_returns: List[float],
                                    enhanced_returns: List[float]) -> Dict[str, Any]:
        """
        Evaluate the impact of enhancements on performance.
        """
        return self.enhancer.calculate_sharpe_improvement(original_returns, enhanced_returns)


# Global instance
profitability_enhancer = ProfitabilityEnhancer()
integrated_profitability_system = IntegratedProfitabilitySystem()
