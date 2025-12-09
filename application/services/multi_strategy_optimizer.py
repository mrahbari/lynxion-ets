"""Multi-Strategy Optimization System with PyTorch CUDA acceleration."""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

from shared.optimization_service import OptimizationService, ParameterSpace
from shared.logger import EnhancedLogger
from shared.auto_drop import AutoDropEngine


class MultiStrategyOptimizer:
    """Manages optimization for multiple strategies simultaneously."""
    
    def __init__(self, 
                 optimization_service: OptimizationService,
                 max_workers: int = 4):
        self.optimization_service = optimization_service
        self.max_workers = max_workers
        self.logger = EnhancedLogger("MultiStrategyOptimizer")
        self.auto_drop = AutoDropEngine()
    
    def optimize_multiple_strategies(self, 
                                   strategies: List[str],
                                   symbol: str,
                                   data: pd.DataFrame,
                                   max_evals_per_strategy: int = 100) -> Dict[str, Any]:
        """Optimize multiple strategies in parallel."""
        self.logger.info(f"Starting multi-strategy optimization for {symbol} with strategies: {strategies}")
        
        results = {}
        
        # Prepare data once for all strategies
        indicators = self._prepare_indicators(data)
        price_changes = data['close'].pct_change().fillna(0).values
        
        # Run optimizations in parallel
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(strategies))) as executor:
            # Submit optimization tasks
            future_to_strategy = {}
            for strategy_name in strategies:
                param_space = ParameterSpace.get_space(strategy_name)
                
                future = executor.submit(
                    self._run_single_optimization,
                    strategy_name=strategy_name,
                    symbol=symbol,
                    indicators=indicators,
                    price_changes=price_changes,
                    param_space=param_space,
                    max_evals=max_evals_per_strategy
                )
                future_to_strategy[future] = strategy_name
            
            # Collect results
            for future in as_completed(future_to_strategy):
                strategy_name = future_to_strategy[future]
                try:
                    result = future.result()
                    results[strategy_name] = result
                    self.logger.info(f"Completed optimization for {strategy_name}")
                except Exception as e:
                    self.logger.error(f"Error optimizing {strategy_name}: {e}")
                    results[strategy_name] = {"error": str(e)}
        
        # Save multi-strategy results
        self._save_multi_strategy_results(symbol, results)
        
        return results
    
    def _run_single_optimization(self,
                                strategy_name: str,
                                symbol: str,
                                indicators: np.ndarray,
                                price_changes: np.ndarray,
                                param_space: Dict[str, Any],
                                max_evals: int) -> Dict[str, Any]:
        """Run single strategy optimization."""
        return self.optimization_service.optimize(
            strategy_name=strategy_name,
            symbol=symbol,
            indicators=indicators,
            price_changes=price_changes,
            param_space=param_space,
            max_evals=max_evals
        )
    
    def _prepare_indicators(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare indicator matrix for GPU evaluation."""
        try:
            # Calculate basic indicators
            rsi_values = self._calculate_rsi(df['close'])
            ema_fast_values = df['close'].ewm(span=10).mean()
            ema_slow_values = df['close'].ewm(span=21).mean()
            atr_values = self._calculate_atr(df)
            
            # Stack indicators into matrix
            indicators = pd.concat([
                rsi_values,
                ema_fast_values,
                ema_slow_values,
                atr_values
            ], axis=1).fillna(0).values
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error preparing indicators: {e}")
            # Return a simple matrix if calculation fails
            return df[['open', 'high', 'low', 'close']].fillna(0).pct_change().fillna(0).values
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    def _save_multi_strategy_results(self, symbol: str, results: Dict[str, Any]) -> None:
        """Save multi-strategy results to file."""
        results_dir = Path("data/optimization_results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_path = results_dir / f"multi_strategy_{symbol}_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=4, default=str)
    
    def rank_strategies_by_performance(self, strategy_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank strategies by their optimization performance."""
        ranked = []
        
        for strategy_name, result in strategy_results.items():
            if 'error' not in result and 'best_loss' in result:
                ranked.append({
                    'strategy_name': strategy_name,
                    'performance_score': -result['best_loss'],  # Negative loss = positive performance
                    'trials': result.get('trials', 0),
                    'best_params': result.get('best_params', {})
                })
        
        # Sort by performance score (descending)
        ranked.sort(key=lambda x: x['performance_score'], reverse=True)
        return ranked


class StrategyFusionEngine:
    """Fuses multiple strategy signals using learned weights."""
    
    def __init__(self):
        self.logger = EnhancedLogger("StrategyFusionEngine")
        self.strategy_weights = {}
    
    def calculate_fused_signal(self, 
                              strategy_signals: Dict[str, float], 
                              strategy_weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate fused signal from multiple strategy outputs."""
        if not strategy_signals:
            return 0.0
        
        # Use provided weights or equal weights
        if strategy_weights is None:
            equal_weight = 1.0 / len(strategy_signals)
            weights = {name: equal_weight for name in strategy_signals.keys()}
        else:
            weights = strategy_weights
        
        # Calculate weighted average
        total_weight = sum(weights.get(name, 0) for name in strategy_signals.keys())
        if total_weight == 0:
            return 0.0
        
        fused_signal = sum(
            strategy_signals.get(name, 0) * weights.get(name, 0)
            for name in strategy_signals.keys()
        ) / total_weight
        
        return fused_signal
    
    def learn_optimal_weights(self, 
                             backtest_results: Dict[str, Any],
                             market_regime: str = "neutral") -> Dict[str, float]:
        """Learn optimal strategy weights based on backtest performance."""
        weights = {}
        
        for strategy_name, results in backtest_results.items():
            # Calculate performance score based on multiple metrics
            if 'error' not in results:
                # This is a simplified weight calculation based on loss
                # In practice you'd use more sophisticated metrics
                performance_score = -results.get('best_loss', 0)  # Negative loss = positive performance
                # Add other metrics like Sharpe ratio, max drawdown, etc.
                weights[strategy_name] = max(0, performance_score)  # Only positive weights
            else:
                weights[strategy_name] = 0.0  # Zero weight for failed optimizations
        
        # Normalize weights so they sum to 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            normalized_weights = {k: v / total_weight for k, v in weights.items()}
        else:
            # Equal weights if all have zero performance
            equal_weight = 1.0 / len(weights) if len(weights) > 0 else 0
            normalized_weights = {k: equal_weight for k in weights.keys()}
        
        self.strategy_weights = normalized_weights
        return normalized_weights


class AdaptiveStrategySelector:
    """Selects the best strategy based on market conditions and performance."""
    
    def __init__(self):
        self.logger = EnhancedLogger("AdaptiveStrategySelector")
        self.performance_history = {}
    
    def select_best_strategy(self, 
                           available_strategies: List[str],
                           market_conditions: Dict[str, Any],
                           strategy_performances: Dict[str, float]) -> str:
        """Select the best strategy based on current market conditions."""
        if not available_strategies:
            return "default"
        
        # Default to first strategy if no performance data
        if not strategy_performances:
            return available_strategies[0]
        
        # Sort strategies by performance
        sorted_strategies = sorted(
            available_strategies,
            key=lambda s: strategy_performances.get(s, 0),
            reverse=True
        )
        
        # Return the strategy with best performance
        return sorted_strategies[0]
    
    def update_performance_history(self, 
                                 strategy_name: str, 
                                 performance: float) -> None:
        """Update performance history for a strategy."""
        if strategy_name not in self.performance_history:
            self.performance_history[strategy_name] = []
        
        self.performance_history[strategy_name].append(performance)
        
        # Keep only recent performance history (last 20 entries)
        if len(self.performance_history[strategy_name]) > 20:
            self.performance_history[strategy_name] = self.performance_history[strategy_name][-20:]
    
    def get_strategy_performance_trend(self, strategy_name: str) -> str:
        """Get trend for a strategy's performance (improving, declining, stable)."""
        if strategy_name not in self.performance_history:
            return "neutral"
        
        history = self.performance_history[strategy_name]
        if len(history) < 2:
            return "neutral"
        
        recent_avg = np.mean(history[-5:]) if len(history) >= 5 else np.mean(history)
        earlier_avg = np.mean(history[:5]) if len(history) >= 5 else np.mean(history)
        
        if recent_avg > earlier_avg * 1.1:
            return "improving"
        elif recent_avg < earlier_avg * 0.9:
            return "declining"
        else:
            return "stable"