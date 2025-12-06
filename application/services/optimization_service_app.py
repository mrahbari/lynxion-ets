"""Application service for optimization using hexagonal architecture."""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from domain.ports.optimization_ports import IOptimizationService, IDataLoader
from shared.optimization_service import OptimizationService, ParameterSpace
from shared.logger import EnhancedLogger
from shared.auto_drop import AutoDropEngine


class OptimizationAppService(IOptimizationService):
    """Application service for strategy optimization."""
    
    def __init__(self, 
                 data_loader: IDataLoader,
                 optimization_service: OptimizationService):
        self.data_loader = data_loader
        self.optimization_service = optimization_service
        self.auto_drop = AutoDropEngine()
        self.logger = EnhancedLogger("OptimizationAppService")
    
    def optimize_strategy(self, strategy_name: str, data: pd.DataFrame, 
                         parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize strategy parameters with data preprocessing."""
        try:
            self.logger.info(f"Starting optimization for {strategy_name}")
            
            # Prepare data for GPU evaluation
            indicators = self._prepare_indicators(data)
            price_changes = data['close'].pct_change().fillna(0).values
            
            # Get parameter space for strategy
            param_space = ParameterSpace.get_space(strategy_name)
            
            # Get max_evals from parameters or default
            max_evals = parameters.get('max_evals', 100)
            symbol = parameters.get('symbol', 'UNKNOWN')
            
            # Run optimization
            results = self.optimization_service.optimize(
                strategy_name=strategy_name,
                symbol=symbol,
                indicators=indicators,
                price_changes=price_changes,
                param_space=param_space,
                max_evals=max_evals
            )
            
            if 'error' not in results:
                # Cache the results
                self.optimization_service.cache_parameters(
                    strategy_name, symbol, results['best_params']
                )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in optimize_strategy: {e}")
            return {'error': str(e)}
    
    def get_optimized_parameters(self, strategy_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get previously optimized parameters."""
        return self.optimization_service.load_cached_results(strategy_name, symbol)
    
    def save_optimized_parameters(self, strategy_name: str, symbol: str, 
                                parameters: Dict[str, Any]) -> None:
        """Save optimized parameters."""
        self.optimization_service.cache_parameters(strategy_name, symbol, parameters)
    
    def _prepare_indicators(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare indicator matrix for GPU evaluation."""
        try:
            # Calculate basic indicators that can be used by GPU evaluator
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


class AutoRetuneService:
    """Service for automatic re-tuning of strategies."""
    
    def __init__(self, 
                 optimization_service: OptimizationAppService,
                 data_loader: IDataLoader,
                 performance_threshold: float = 0.1):
        self.optimization_service = optimization_service
        self.data_loader = data_loader
        self.performance_threshold = performance_threshold
        self.logger = EnhancedLogger("AutoRetuneService")
    
    def should_retune(self, strategy_name: str, symbol: str, 
                     current_performance: float) -> bool:
        """Check if strategy needs re-tuning based on performance."""
        # Load previous best parameters and performance
        cached_results = self.optimization_service.get_optimized_parameters(
            strategy_name, symbol
        )
        
        if not cached_results or 'best_params' not in cached_results:
            # First time optimization needed
            return True
        
        # Compare current performance with historical best
        # If performance has dropped significantly, trigger re-tuning
        historical_best = cached_results.get('best_loss', float('inf'))
        
        # If performance has significantly degraded, retune
        if abs(current_performance - historical_best) > self.performance_threshold:
            self.logger.info(f"Performance degradation detected. Retuning required for {strategy_name} on {symbol}")
            return True
        
        return False
    
    def run_auto_retune(self, strategy_name: str, symbol: str, 
                       data: pd.DataFrame) -> Dict[str, Any]:
        """Run automatic re-tuning if needed."""
        self.logger.info(f"Checking auto-retune for {strategy_name} on {symbol}")
        
        # For now, we'll run optimization regardless of performance
        # In a real system, you'd implement proper performance tracking
        return self.optimization_service.optimize_strategy(
            strategy_name=strategy_name,
            data=data,
            parameters={'symbol': symbol, 'max_evals': 50}  # Fewer evals for auto-retune
        )