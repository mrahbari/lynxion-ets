"""Auto-Retune system that automatically re-optimizes strategies based on market conditions."""

from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
import time

from shared.logger import EnhancedLogger
from shared.optimization_service import OptimizationService, ParameterSpace
from application.services.multi_strategy_optimizer import MultiStrategyOptimizer
from domain.ports.optimization_ports import IDataLoader
from shared.auto_drop import AutoDropEngine


class AutoRetuneScheduler:
    """Schedules auto-retuning based on time intervals and market conditions."""
    
    def __init__(self, 
                 optimization_service: OptimizationService,
                 data_loader: IDataLoader,
                 check_interval: int = 3600,  # Check every hour
                 timeframes_to_check: List[str] = ["1h", "4h"]):
        self.optimization_service = optimization_service
        self.data_loader = data_loader
        self.check_interval = check_interval
        self.timeframes_to_check = timeframes_to_check
        self.logger = EnhancedLogger("AutoRetuneScheduler")
        self.auto_drop = AutoDropEngine()
        
        # Track last retune times
        self.last_retune_times = {}
    
    def start_scheduled_retuning(self, 
                                symbols: List[str], 
                                strategies: List[str],
                                max_evals: int = 50) -> None:
        """Start the scheduled auto-retuning loop."""
        self.logger.info("Starting scheduled auto-retuning...")
        
        while True:
            try:
                self.logger.info("Checking for auto-retuning opportunities...")
                
                for symbol in symbols:
                    for strategy in strategies:
                        # Check if retuning is needed
                        if self.should_retune(symbol, strategy):
                            self.logger.info(f"Retuning needed for {strategy} on {symbol}")
                            
                            # Load data and run retuning
                            for timeframe in self.timeframes_to_check:
                                data = self.data_loader.load_historical_data(
                                    symbol=symbol,
                                    timeframe=timeframe,
                                    limit=1000
                                )
                                
                                if not data.empty:
                                    # Run single strategy optimization
                                    self._run_single_strategy_retune(
                                        strategy, symbol, data, max_evals
                                    )
                                    break  # Use first available timeframe
                            
                            # Update last retune time
                            key = f"{symbol}_{strategy}"
                            self.last_retune_times[key] = datetime.now()
                
                self.logger.info(f"Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Auto-retuning stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in auto-retune scheduler: {e}")
                time.sleep(self.check_interval)
    
    def should_retune(self, symbol: str, strategy: str) -> bool:
        """Check if retuning is needed for a strategy on a symbol."""
        # Check if enough time has passed since last retune
        key = f"{symbol}_{strategy}"
        last_retune = self.last_retune_times.get(key)
        
        if last_retune:
            time_since_last = datetime.now() - last_retune
            # Retune at most once per day for each strategy-symbol pair
            if time_since_last < timedelta(hours=24):
                return False
        
        # For now, we'll retune if it's been more than 1 day
        # In a real system, you'd check performance degradation
        return True
    
    def _run_single_strategy_retune(self, 
                                  strategy: str, 
                                  symbol: str, 
                                  data: pd.DataFrame,
                                  max_evals: int) -> Dict[str, Any]:
        """Run retuning for a single strategy."""
        try:
            # Use the existing optimization service
            indicators = self._prepare_indicators(data)
            price_changes = data['close'].pct_change().fillna(0).values
            param_space = ParameterSpace.get_space(strategy)
            
            results = self.optimization_service.optimize(
                strategy_name=strategy,
                symbol=symbol,
                indicators=indicators,
                price_changes=price_changes,
                param_space=param_space,
                max_evals=max_evals
            )
            
            self.logger.info(f"Retuning completed for {strategy} on {symbol}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in single strategy retune: {e}")
            return {"error": str(e)}
    
    def _prepare_indicators(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare indicator matrix for optimization."""
        try:
            from shared.optimization_service import OptimizationService
            service = OptimizationService()
            return service._prepare_indicators(df)
        except:
            # Fallback indicator preparation
            return df[['open', 'high', 'low', 'close']].fillna(0).pct_change().fillna(0).values


class PerformanceBasedRetune:
    """Triggers retuning based on strategy performance degradation."""
    
    def __init__(self, 
                 performance_threshold: float = 0.15,  # 15% degradation triggers retune
                 min_trades_for_evaluation: int = 20):
        self.performance_threshold = performance_threshold
        self.min_trades_for_evaluation = min_trades_for_evaluation
        self.logger = EnhancedLogger("PerformanceBasedRetune")
        self.performance_history = {}
    
    def should_trigger_retune(self, 
                            strategy_name: str, 
                            symbol: str, 
                            current_metrics: Dict[str, float]) -> bool:
        """Check if current metrics indicate need for retuning."""
        key = f"{strategy_name}_{symbol}"
        
        # If no historical data, don't trigger retune
        if key not in self.performance_history:
            self.performance_history[key] = []
            return False
        
        # Need minimum number of metrics to evaluate
        if len(self.performance_history[key]) < self.min_trades_for_evaluation:
            return False
        
        # Calculate baseline performance (average of historical values)
        historical_values = self.performance_history[key]
        baseline = sum(historical_values) / len(historical_values)
        
        # Check if current performance is significantly worse
        current_performance = current_metrics.get('sharpe_ratio', 0)
        
        if baseline > 0 and current_performance < baseline * (1 - self.performance_threshold):
            self.logger.info(f"Performance degradation detected for {strategy_name} on {symbol}. "
                           f"Baseline: {baseline}, Current: {current_performance}")
            return True
        
        # Add current metric to history
        self.performance_history[key].append(current_performance)
        
        # Keep only recent history
        if len(self.performance_history[key]) > 100:  # Keep last 100 values
            self.performance_history[key] = self.performance_history[key][-50:]
        
        return False
    
    def update_performance(self, 
                          strategy_name: str, 
                          symbol: str, 
                          metrics: Dict[str, float]) -> None:
        """Update performance metrics for a strategy."""
        key = f"{strategy_name}_{symbol}"
        if key not in self.performance_history:
            self.performance_history[key] = []
        
        # Add the key performance metric (e.g., Sharpe ratio)
        performance_metric = metrics.get('sharpe_ratio', 0)
        self.performance_history[key].append(performance_metric)


class MarketRegimeBasedRetune:
    """Triggers retuning based on market regime changes."""
    
    def __init__(self):
        self.logger = EnhancedLogger("MarketRegimeBasedRetune")
        self.last_regime = {}
        self.regime_change_threshold = 0.3  # Significant regime change threshold
    
    def should_trigger_retune(self, 
                            symbol: str, 
                            current_regime: Dict[str, float]) -> bool:
        """Check if market regime change indicates need for retuning."""
        if symbol not in self.last_regime:
            self.last_regime[symbol] = current_regime
            return False
        
        last_regime = self.last_regime[symbol]
        
        # Calculate regime change magnitude
        change_magnitude = 0
        for key in current_regime:
            if key in last_regime:
                change_magnitude += abs(current_regime[key] - last_regime[key])
        
        # Normalize by number of regime indicators
        if len(current_regime) > 0:
            avg_change = change_magnitude / len(current_regime)
        else:
            avg_change = 0
        
        # Update last regime
        self.last_regime[symbol] = current_regime
        
        # Trigger retune if change is significant
        if avg_change > self.regime_change_threshold:
            self.logger.info(f"Market regime change detected for {symbol}, "
                           f"magnitude: {avg_change}")
            return True
        
        return False


class VolatilityBasedRetune:
    """Triggers retuning based on volatility changes."""
    
    def __init__(self, volatility_threshold: float = 0.5):
        self.volatility_threshold = volatility_threshold
        self.logger = EnhancedLogger("VolatilityBasedRetune")
        self.volatility_history = {}
        self.volatility_window = 20  # Look at last 20 periods
    
    def should_trigger_retune(self, symbol: str, current_volatility: float) -> bool:
        """Check if volatility change indicates need for retuning."""
        if symbol not in self.volatility_history:
            self.volatility_history[symbol] = []
        
        # Add current volatility
        self.volatility_history[symbol].append(current_volatility)
        
        # Keep only recent history
        if len(self.volatility_history[symbol]) > self.volatility_window:
            self.volatility_history[symbol] = self.volatility_history[symbol][-self.volatility_window:]
        
        # If not enough data, don't trigger
        if len(self.volatility_history[symbol]) < 5:
            return False
        
        # Calculate average volatility
        avg_vol = sum(self.volatility_history[symbol]) / len(self.volatility_history[symbol])
        
        # Check if current volatility is significantly different
        volatility_ratio = current_volatility / (avg_vol + 1e-8)  # Avoid division by zero
        
        if volatility_ratio > (1 + self.volatility_threshold) or volatility_ratio < (1 - self.volatility_threshold):
            self.logger.info(f"Volatility change detected for {symbol}. "
                           f"Avg: {avg_vol}, Current: {current_volatility}")
            return True
        
        return False


class AutoRetuneManager:
    """Main manager that coordinates all auto-retuning triggers."""
    
    def __init__(self,
                 multi_strategy_optimizer: MultiStrategyOptimizer,
                 data_loader: IDataLoader,
                 performance_checker: PerformanceBasedRetune,
                 regime_checker: MarketRegimeBasedRetune,
                 volatility_checker: VolatilityBasedRetune):
        self.multi_strategy_optimizer = multi_strategy_optimizer
        self.data_loader = data_loader
        self.performance_checker = performance_checker
        self.regime_checker = regime_checker
        self.volatility_checker = volatility_checker
        self.logger = EnhancedLogger("AutoRetuneManager")
        
        # Track when last optimization was done
        self.last_optimization_time = {}
    
    def evaluate_retune_needed(self, 
                             strategy: str, 
                             symbol: str,
                             current_metrics: Dict[str, Any],
                             market_data: pd.DataFrame) -> bool:
        """Evaluate if retuning is needed using multiple criteria."""
        # Check performance degradation
        performance_trigger = self.performance_checker.should_trigger_retune(
            strategy_name=strategy,
            symbol=symbol,
            current_metrics=current_metrics
        )
        
        # Check market regime changes
        regime_data = self._extract_regime_data(market_data)
        regime_trigger = self.regime_checker.should_trigger_retune(
            symbol=symbol,
            current_regime=regime_data
        )
        
        # Check volatility changes
        volatility = self._calculate_volatility(market_data)
        volatility_trigger = self.volatility_checker.should_trigger_retune(
            symbol=symbol,
            current_volatility=volatility
        )
        
        # Use OR logic: if any trigger is activated, retune
        needs_retune = performance_trigger or regime_trigger or volatility_trigger
        
        if needs_retune:
            self.logger.info(f"Auto-retune triggered for {strategy} on {symbol}. "
                           f"Reasons - Performance: {performance_trigger}, "
                           f"Regime: {regime_trigger}, Volatility: {volatility_trigger}")
        
        return needs_retune
    
    def _extract_regime_data(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract market regime indicators from data."""
        if len(df) < 10:
            return {"trend_strength": 0, "volatility": 0, "momentum": 0}
        
        close_prices = df['close']
        
        # Trend strength (correlation of prices with time)
        time_axis = list(range(len(close_prices)))
        trend_strength = abs(pd.Series(close_prices).corr(pd.Series(time_axis)))
        
        # Volatility (std of returns)
        returns = close_prices.pct_change().fillna(0)
        volatility = returns.std()
        
        # Momentum (rate of change)
        momentum = (close_prices.iloc[-1] - close_prices.iloc[-10]) / close_prices.iloc[-10] if len(close_prices) >= 10 else 0
        
        return {
            "trend_strength": trend_strength,
            "volatility": volatility,
            "momentum": momentum
        }
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate volatility from price data."""
        if len(df) < 2:
            return 0
        
        returns = df['close'].pct_change().fillna(0)
        return returns.std()
    
    def run_retune(self, 
                   strategies: List[str], 
                   symbol: str, 
                   data: pd.DataFrame,
                   max_evals: int = 50) -> Dict[str, Any]:
        """Run the actual retuning process."""
        self.logger.info(f"Running auto-retune for {symbol} with strategies: {strategies}")
        
        # Use multi-strategy optimizer to retune all strategies
        results = self.multi_strategy_optimizer.optimize_multiple_strategies(
            strategies=strategies,
            symbol=symbol,
            data=data,
            max_evals_per_strategy=max_evals
        )
        
        # Update last optimization time
        for strategy in strategies:
            key = f"{symbol}_{strategy}"
            self.last_optimization_time[key] = datetime.now()
        
        return results