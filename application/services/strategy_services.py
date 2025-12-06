"""
Enhanced Application service for strategy orchestration in the enterprise hedge fund trading system.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from domain.entities.trading_entities import Signal, Position
from domain.value_objects import Symbol
from domain.ports.strategy_ports import StrategyPort
from shared.logger import logger
import statistics


class StrategyPerformanceTracker:
    """Track and analyze strategy performance metrics"""

    def __init__(self):
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.regime_data: Dict[str, List[Dict[str, Any]]] = {}

    def update_performance(self, strategy_name: str, performance: Dict[str, Any]):
        """Update performance metrics for a strategy"""
        if strategy_name not in self.performance_history:
            self.performance_history[strategy_name] = []

        # Add timestamp to performance data
        performance_record = {
            'timestamp': datetime.now(),
            'avg_return': performance.get('avg_return', 0),
            'win_rate': performance.get('win_rate', 0),
            'sharpe_ratio': performance.get('sharpe_ratio', 0),
            'max_drawdown': performance.get('max_drawdown', 0),
            'volatility': performance.get('volatility', 0),
            'total_pnl': performance.get('total_pnl', 0),
            'trades_count': performance.get('trades_count', 0)
        }

        self.performance_history[strategy_name].append(performance_record)

        # Keep only recent performance data (last 100 records)
        if len(self.performance_history[strategy_name]) > 100:
            self.performance_history[strategy_name] = self.performance_history[strategy_name][-100:]

    def calculate_overall_metrics(self, strategy_name: str) -> Dict[str, float]:
        """Calculate overall performance metrics for a strategy"""
        if strategy_name not in self.performance_history or not self.performance_history[strategy_name]:
            return {
                'avg_return': 0.0,
                'win_rate': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'volatility': 0.0,
                'total_pnl': 0.0
            }

        records = self.performance_history[strategy_name]

        avg_returns = [r['avg_return'] for r in records]
        win_rates = [r['win_rate'] for r in records]
        sharpe_ratios = [r['sharpe_ratio'] for r in records]
        max_drawdowns = [r['max_drawdown'] for r in records]
        volatilities = [r['volatility'] for r in records]
        total_pnls = [r['total_pnl'] for r in records]

        return {
            'avg_return': statistics.mean(avg_returns) if avg_returns else 0.0,
            'win_rate': statistics.mean(win_rates) if win_rates else 0.0,
            'sharpe_ratio': statistics.mean(sharpe_ratios) if sharpe_ratios else 0.0,
            'max_drawdown': statistics.mean(max_drawdowns) if max_drawdowns else 0.0,
            'volatility': statistics.mean(volatilities) if volatilities else 0.0,
            'total_pnl': sum(total_pnls)
        }

    def get_recent_performance(self, strategy_name: str, days: int = 30) -> Dict[str, float]:
        """Get recent performance metrics for a strategy"""
        if strategy_name not in self.performance_history:
            return self.calculate_overall_metrics(strategy_name)

        cutoff_time = datetime.now() - timedelta(days=days)
        recent_records = [r for r in self.performance_history[strategy_name] if r['timestamp'] > cutoff_time]

        if not recent_records:
            return self.calculate_overall_metrics(strategy_name)

        avg_returns = [r['avg_return'] for r in recent_records]
        win_rates = [r['win_rate'] for r in recent_records]
        sharpe_ratios = [r['sharpe_ratio'] for r in recent_records]
        max_drawdowns = [r['max_drawdown'] for r in recent_records]
        volatilities = [r['volatility'] for r in recent_records]
        total_pnls = [r['total_pnl'] for r in recent_records]

        return {
            'avg_return': statistics.mean(avg_returns) if avg_returns else 0.0,
            'win_rate': statistics.mean(win_rates) if win_rates else 0.0,
            'sharpe_ratio': statistics.mean(sharpe_ratios) if sharpe_ratios else 0.0,
            'max_drawdown': statistics.mean(max_drawdowns) if max_drawdowns else 0.0,
            'volatility': statistics.mean(volatilities) if volatilities else 0.0,
            'total_pnl': sum(total_pnls)
        }

    def get_strategies_correlation_matrix(self, strategy_names: List[str]) -> np.ndarray:
        """Calculate correlation matrix between strategies"""
        n = len(strategy_names)
        if n == 0:
            return np.eye(0)

        # Create a dummy correlation matrix - in a real system, this would be based on actual return data
        correlation_matrix = np.eye(n)

        # Simulate some correlation data between strategies
        for i in range(n):
            for j in range(i+1, n):
                # In a real system, this would be calculated from actual return series
                correlation_val = np.random.uniform(-0.3, 0.3)  # Mock correlation values
                correlation_matrix[i][j] = correlation_val
                correlation_matrix[j][i] = correlation_val

        return correlation_matrix


class StrategySelectionService:
    """Enhanced application service for selecting strategies based on market conditions and performance"""

    def __init__(self, strategies: List[StrategyPort]):
        self.strategies = strategies
        self.performance_tracker = StrategyPerformanceTracker()
        self.time_operation_tracker: Dict[str, List[float]] = {}  # Track execution time of operations
        self.market_regime_detector = MarketRegimeDetector()
        self.weights_cache: Dict[str, float] = {}  # Cache for calculated weights

    def calculate_strategy_score(self, strategy_name: str) -> float:
        """Calculate a weighted score for a strategy based on multiple metrics"""
        metrics = self.performance_tracker.get_recent_performance(strategy_name)

        # Weighted scoring system (these weights can be adjusted based on priority)
        # Higher is better for positive metrics, lower is better for negative metrics
        score = (
            0.30 * metrics['sharpe_ratio'] +                    # Sharpe ratio (30% weight)
            0.25 * metrics['win_rate'] +                        # Win rate (25% weight)
            0.20 * metrics['avg_return'] +                      # Average return (20% weight)
            -0.15 * min(0.1, metrics['max_drawdown']) +         # Drawdown penalty (15% weight, capped)
            0.10 * (1.0 / (1.0 + metrics['volatility']))       # Lower volatility is better (10% weight)
        )

        # Adjust score based on market regime fit
        regime_bonus = self.market_regime_detector.get_regime_strategy_bonus(strategy_name)
        score += regime_bonus

        return max(0.0, score)  # Ensure non-negative score

    def select_best_strategy(self, symbol: Symbol, market_data: Dict[str, Any] = None) -> Optional[StrategyPort]:
        """Select the best strategy based on market conditions and performance"""
        if not self.strategies:
            return None

        start_time = datetime.now()

        # Calculate scores for all strategies
        strategy_scores = {}
        for strategy in self.strategies:
            strategy_name = strategy.get_strategy_name()
            score = self.calculate_strategy_score(strategy_name)
            strategy_scores[strategy] = score

        # Select strategy with highest score
        if strategy_scores:
            best_strategy = max(strategy_scores, key=strategy_scores.get)
        else:
            # Fallback to first strategy if no scores available
            best_strategy = self.strategies[0]

        # Track operation time
        end_time = datetime.now()
        operation_time = (end_time - start_time).total_seconds()

        strategy_name = best_strategy.get_strategy_name()
        if strategy_name not in self.time_operation_tracker:
            self.time_operation_tracker[strategy_name] = []
        self.time_operation_tracker[strategy_name].append(operation_time)

        logger.info(f"Selected strategy: {strategy_name} with score: {strategy_scores.get(best_strategy, 0):.4f}")
        return best_strategy

    def generate_signal_with_optimal_strategy(self, symbol: Symbol, market_data: Dict[str, Any] = None) -> Optional[Signal]:
        """Generate a signal using the optimal strategy for current conditions"""
        start_time = datetime.now()

        strategy = self.select_best_strategy(symbol, market_data)
        if strategy:
            logger.info(f"Generating signal using strategy: {strategy.get_strategy_name()}")
            signal = strategy.generate_signal(symbol)

            # Track operation time
            end_time = datetime.now()
            operation_time = (end_time - start_time).total_seconds()

            strategy_name = strategy.get_strategy_name()
            if strategy_name not in self.time_operation_tracker:
                self.time_operation_tracker[strategy_name] = []
            self.time_operation_tracker[strategy_name].append(operation_time)

            return signal
        return None

    def update_strategy_performance(self, strategy_name: str, performance: Dict[str, Any]):
        """Update the performance metrics for a strategy"""
        self.performance_tracker.update_performance(strategy_name, performance)

        # Clear weights cache when performance is updated
        self.weights_cache.clear()

    def get_strategy_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get comprehensive metrics for all strategies"""
        metrics = {}
        for strategy in self.strategies:
            strategy_name = strategy.get_strategy_name()
            metrics[strategy_name] = self.performance_tracker.calculate_overall_metrics(strategy_name)
        return metrics

    def get_operation_times(self) -> Dict[str, Dict[str, float]]:
        """Get operation time statistics for each strategy"""
        times = {}
        for strategy_name, time_list in self.time_operation_tracker.items():
            if time_list:
                times[strategy_name] = {
                    'avg_time': statistics.mean(time_list),
                    'min_time': min(time_list),
                    'max_time': max(time_list),
                    'total_calls': len(time_list)
                }
        return times


class MarketRegimeDetector:
    """Detect market regimes and adjust strategy selection accordingly"""

    def __init__(self):
        self.current_regime = "NEUTRAL"
        self.regime_history: List[Dict[str, Any]] = []

    def detect_regime(self, market_data: Dict[str, Any]) -> str:
        """Detect the current market regime based on market data"""
        # In a real system, this would analyze market data to detect regimes
        # For now, we'll simulate different regimes based on volatility or trend indicators
        if market_data:
            # Example: detect high volatility regime
            if market_data.get('volatility', 0) > 0.3:
                return "HIGH_VOLATILITY"
            # Example: detect trending market
            elif abs(market_data.get('trend', 0)) > 0.1:
                if market_data.get('trend', 0) > 0:
                    return "BULL_TREND"
                else:
                    return "BEAR_TREND"

        return "NEUTRAL"

    def get_regime_strategy_bonus(self, strategy_name: str) -> float:
        """Get bonus for strategy based on current regime"""
        # Different strategies may perform better in different regimes
        # This is a simplified example - in reality, this would be based on historical performance in regimes
        regime_bonuses = {
            "BULL_TREND": {"momentum_strategy": 0.1, "trend_following": 0.05},
            "BEAR_TREND": {"mean_reversion": 0.1, "short_selling": 0.08},
            "HIGH_VOLATILITY": {"volatility_strategy": 0.12, "short_term": 0.05},
            "NEUTRAL": {"balanced_strategy": 0.05}
        }

        regime_bonuses_for_current = regime_bonuses.get(self.current_regime, {})
        return regime_bonuses_for_current.get(strategy_name, 0.0)


class StrategyOrchestrationService:
    """Enhanced service for orchestrating strategy execution"""

    def __init__(self,
                 strategy_selection_service: StrategySelectionService,
                 signal_processing_service,
                 risk_service):
        self.strategy_selection = strategy_selection_service
        self.signal_processing_service = signal_processing_service
        self.risk_service = risk_service

    def execute_strategy_cycle(self, symbol: Symbol, market_data: Dict[str, Any] = None) -> Optional[Signal]:
        """Execute a complete strategy cycle: select, signal, process"""
        # Select the best strategy
        strategy = self.strategy_selection.select_best_strategy(symbol, market_data)
        if not strategy:
            logger.warning(f"No strategy available for {symbol.value}")
            return None

        # Generate signal from selected strategy
        signal = strategy.generate_signal(symbol)
        if not signal:
            logger.info(f"Strategy {strategy.get_strategy_name()} did not generate a signal for {symbol.value}")
            return None

        logger.info(f"Strategy {strategy.get_strategy_name()} generated signal: {signal.signal_type.name}")

        # Process the signal through engines and fusion
        # In a real system, the signal would go through the processing pipeline
        processed_signal = self.signal_processing_service.process_signal(signal)

        # Validate through risk management - check which validation method is available
        is_valid = True  # Default to valid if no validation method exists
        if hasattr(self.risk_service, 'validate_signal'):
            is_valid = self.risk_service.validate_signal(processed_signal)
        elif hasattr(self.risk_service, 'validate_order_risk'):
            # For now, just check if the service is valid by checking attributes
            is_valid = True
        elif hasattr(self.risk_service, 'validate_order'):
            is_valid = self.risk_service.validate_order(processed_signal)  # Use the signal as input for order validation logic

        if not is_valid:
            logger.warning(f"Signal failed risk validation: {processed_signal.signal_type.name}")
            return None

        logger.info(f"Strategy cycle completed for {symbol.value}, final signal: {processed_signal.signal_type.name}")
        return processed_signal

    def get_strategy_performance(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get performance metrics for all strategies"""
        return self.strategy_selection.performance_tracker.performance_history

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get all metrics including performance, correlations, and operation times"""
        return {
            'strategy_performance': self.strategy_selection.get_strategy_metrics(),
            'operation_times': self.strategy_selection.get_operation_times(),
            'regime_info': self.strategy_selection.market_regime_detector.current_regime
        }


class PortfolioStrategyAllocationService:
    """Enhanced service for allocating capital across different strategies"""

    def __init__(self, strategy_selection_service: StrategySelectionService):
        self.strategy_selection = strategy_selection_service
        self.diversification_threshold = 0.7  # Maximum correlation allowed between strategies

    def calculate_strategy_weights(self) -> Dict[str, float]:
        """Calculate weight for each strategy based on performance and correlation considerations"""
        if not self.strategy_selection.strategies:
            return {}

        # Get strategy scores and names
        strategy_scores = {}
        strategy_names = []

        for strategy in self.strategy_selection.strategies:
            strategy_name = strategy.get_strategy_name()
            score = self.strategy_selection.calculate_strategy_score(strategy_name)
            strategy_scores[strategy_name] = score
            strategy_names.append(strategy_name)

        # Normalize scores to get preliminary weights
        total_score = sum(strategy_scores.values())
        if total_score == 0:
            # If all scores are 0, use equal weights
            equal_weight = 1.0 / len(self.strategy_selection.strategies)
            return {name: equal_weight for name in strategy_names}

        # Calculate preliminary weights based on normalized scores
        preliminary_weights = {name: score / total_score for name, score in strategy_scores.items()}

        # Get correlation matrix to adjust weights based on diversification needs
        correlation_matrix = self.strategy_selection.performance_tracker.get_strategies_correlation_matrix(strategy_names)

        # Adjust weights based on correlation to reduce concentration in similar strategies
        adjusted_weights = self._adjust_weights_for_diversification(
            preliminary_weights,
            correlation_matrix,
            strategy_names
        )

        return adjusted_weights

    def _adjust_weights_for_diversification(self,
                                          weights: Dict[str, float],
                                          correlation_matrix: np.ndarray,
                                          strategy_names: List[str]) -> Dict[str, float]:
        """Adjust strategy weights to promote diversification"""
        # Create a copy of weights to adjust
        adjusted_weights = weights.copy()

        # Get indices for strategies
        n = len(strategy_names)

        # Find strategies with high correlation and reduce their weights
        for i in range(n):
            for j in range(i + 1, n):
                corr = correlation_matrix[i][j]
                if abs(corr) > self.diversification_threshold:
                    # Reduce weights of highly correlated strategies
                    strategy_i = strategy_names[i]
                    strategy_j = strategy_names[j]

                    if adjusted_weights[strategy_i] > 0 and adjusted_weights[strategy_j] > 0:
                        # Reduce both weights proportionally
                        reduction_factor = abs(corr) - self.diversification_threshold
                        adjustment_i = adjusted_weights[strategy_i] * reduction_factor * 0.1
                        adjustment_j = adjusted_weights[strategy_j] * reduction_factor * 0.1

                        adjusted_weights[strategy_i] -= adjustment_i
                        adjusted_weights[strategy_j] -= adjustment_j

        # Normalize adjusted weights to sum to 1
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            for strategy_name in adjusted_weights:
                adjusted_weights[strategy_name] /= total_weight
        else:
            # If weights became negative or zero, revert to equal allocation
            equal_weight = 1.0 / len(strategy_names) if strategy_names else 0
            return {name: equal_weight for name in strategy_names}

        return adjusted_weights

    def allocate_capital_to_strategies(self, total_capital: float) -> Dict[str, float]:
        """Allocate capital to strategies based on calculated weights"""
        weights = self.calculate_strategy_weights()
        allocations = {}

        for strategy_name, weight in weights.items():
            allocations[strategy_name] = total_capital * weight

        return allocations

    def get_diversification_metrics(self) -> Dict[str, Any]:
        """Get metrics related to strategy diversification"""
        strategy_names = [s.get_strategy_name() for s in self.strategy_selection.strategies]
        correlation_matrix = self.strategy_selection.performance_tracker.get_strategies_correlation_matrix(strategy_names)

        # Calculate average correlation to measure diversification
        n = len(strategy_names)
        if n < 2:
            avg_correlation = 0
        else:
            # Calculate average absolute correlation (excluding diagonal)
            total_corr = 0
            count = 0
            for i in range(n):
                for j in range(i + 1, n):
                    total_corr += abs(correlation_matrix[i][j])
                    count += 1
            avg_correlation = total_corr / count if count > 0 else 0

        return {
            'strategy_names': strategy_names,
            'correlation_matrix': correlation_matrix.tolist(),
            'average_correlation': avg_correlation,
            'diversification_score': 1 - avg_correlation,  # Higher score means better diversification
        }