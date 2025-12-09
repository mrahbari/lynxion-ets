"""
Application service for backtesting in the enterprise hedge fund trading system.
"""
from typing import List, Dict, Any
from domain.entities.trading_entities import Signal, Position
from domain.value_objects import Symbol, Money
from domain.ports.backtest_ports import (
    BacktestEnginePort, HistoricalDataProviderPort, BacktestMetricsPort
)
from shared.logger import logger


class BacktestExecutionService:
    """Application service for executing backtests"""
    
    def __init__(self,
                 backtest_engine_port: BacktestEnginePort,
                 historical_data_port: HistoricalDataProviderPort,
                 metrics_port: BacktestMetricsPort):
        self.backtest_engine = backtest_engine_port
        self.historical_data = historical_data_port
        self.metrics_calculator = metrics_port
    
    def run_strategy_backtest(self, 
                             symbol: Symbol,
                             start_date: str,
                             end_date: str,
                             initial_capital: float,
                             strategy_name: str = "DefaultStrategy") -> Dict[str, Any]:
        """Run a backtest for a specific strategy"""
        logger.info(f"Running backtest for {strategy_name} on {symbol.value}")
        
        # Execute the backtest
        results = self.backtest_engine.run_backtest(
            symbol, start_date, end_date, initial_capital
        )
        
        logger.info(f"Backtest completed for {strategy_name}. Total return: {results.get('total_return', 0):.2%}")
        return results
    
    def compare_strategies(self, 
                          symbol: Symbol,
                          start_date: str,
                          end_date: str,
                          initial_capital: float,
                          strategies: List[str]) -> Dict[str, Any]:
        """Compare performance of multiple strategies"""
        comparison_results = {}
        
        for strategy_name in strategies:
            logger.info(f"Running backtest for strategy: {strategy_name}")
            # In a real implementation, you'd need to switch strategies
            # For this example, we'll run the same engine with different parameters
            # that would affect strategy behavior
            results = self.run_strategy_backtest(
                symbol, start_date, end_date, initial_capital, strategy_name
            )
            comparison_results[strategy_name] = results
        
        logger.info(f"Strategy comparison completed for {len(strategies)} strategies")
        return comparison_results
    
    def validate_strategy_performance(self, 
                                    results: Dict[str, Any], 
                                    min_return_threshold: float = 0.0,
                                    max_drawdown_threshold: float = 0.1) -> bool:
        """Validate if strategy performance meets minimum requirements"""
        total_return = results.get('total_return', 0)
        max_drawdown = results.get('max_drawdown', 0)
        
        meets_return = total_return >= min_return_threshold
        meets_drawdown = max_drawdown <= max_drawdown_threshold
        
        is_valid = meets_return and meets_drawdown
        
        logger.info(f"Strategy validation: Return >= {min_return_threshold:.2%}: {meets_return}, "
                   f"Drawdown <= {max_drawdown_threshold:.2%}: {meets_drawdown}, "
                   f"Overall valid: {is_valid}")
        
        return is_valid


class BacktestOptimizationService:
    """Service for optimizing strategy parameters through backtesting"""
    
    def __init__(self, backtest_service: BacktestExecutionService):
        self.backtest_service = backtest_service
    
    def optimize_strategy_parameters(self,
                                   symbol: Symbol,
                                   start_date: str,
                                   end_date: str,
                                   initial_capital: float,
                                   strategy_name: str,
                                   parameter_ranges: Dict[str, tuple]) -> Dict[str, Any]:
        """Optimize strategy parameters through grid search"""
        logger.info(f"Optimizing parameters for {strategy_name}")
        
        best_params = {}
        best_score = float('-inf')
        best_results = {}
        
        # Simple grid search implementation
        # In a real system, this would be more sophisticated (genetic algorithms, etc.)
        import itertools
        
        # Generate parameter combinations
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        
        # Create combinations (for demonstration with limited combinations)
        param_combinations = []
        for i, values in enumerate(param_values):
            if isinstance(values, tuple) and len(values) == 3:  # (start, stop, step)
                param_combinations.append(list(self._frange(values[0], values[1], values[2])))
            else:
                param_combinations.append(values)
        
        # Limit to first 10 combinations to avoid too many tests
        combinations = list(itertools.product(*param_combinations))[:10]
        
        for i, combination in enumerate(combinations):
            param_dict = dict(zip(param_names, combination))
            
            # In a real system, you'd need to pass these parameters to the strategy
            # For now, we'll just log the attempt
            logger.info(f"Testing parameter combination {i+1}: {param_dict}")
            
            # Run backtest with these parameters
            # For this example, we'll use the same backtest and just record the parameters
            results = self.backtest_service.run_strategy_backtest(
                symbol, start_date, end_date, initial_capital, strategy_name
            )
            
            # Calculate score (e.g., Sharpe ratio or risk-adjusted return)
            score = self._calculate_optimization_score(results)
            
            if score > best_score:
                best_score = score
                best_params = param_dict.copy()
                best_results = results.copy()
        
        optimization_results = {
            'best_parameters': best_params,
            'best_score': best_score,
            'best_results': best_results,
            'total_combinations': len(combinations)
        }
        
        logger.info(f"Parameter optimization completed. Best score: {best_score:.4f}")
        return optimization_results
    
    def _frange(self, start, stop, step):
        """Helper function to create float ranges"""
        while start < stop:
            yield start
            start += step
    
    def _calculate_optimization_score(self, results: Dict[str, Any]) -> float:
        """Calculate score for optimization (e.g., Sharpe ratio, Calmar ratio, etc.)"""
        total_return = results.get('total_return', 0)
        max_drawdown = results.get('max_drawdown', 0.001)  # Avoid division by zero
        
        # Simple score: return / max_drawdown (Calmar ratio)
        score = total_return / max_drawdown if max_drawdown > 0 else total_return
        return score


class BacktestAnalyticsService:
    """Service for analyzing backtest results"""
    
    def __init__(self, metrics_port: BacktestMetricsPort):
        self.metrics_calculator = metrics_port
    
    def analyze_backtest_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze backtest results and generate insights"""
        trades = results.get('trades', [])
        
        analysis = {
            'performance_summary': self._summarize_performance(results),
            'risk_metrics': self._calculate_risk_metrics(results),
            'trade_analysis': self._analyze_trades(trades),
            'validation': self._validate_results(results)
        }
        
        return analysis
    
    def _summarize_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create performance summary"""
        return {
            'total_return': results.get('total_return', 0),
            'annualized_return': results.get('total_return', 0),  # Would be annualized in real system
            'total_trades': results.get('total_trades', 0),
            'win_rate': results.get('win_rate', 0),
            'sharpe_ratio': results.get('sharpe_ratio', 0)
        }
    
    def _calculate_risk_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk metrics"""
        return {
            'max_drawdown': results.get('max_drawdown', 0),
            'volatility': results.get('volatility', 0),  # Not calculated in our basic backtest
            'var': results.get('var', 0)  # Not calculated in our basic backtest
        }
    
    def _analyze_trades(self, trades: List[Dict]) -> Dict[str, Any]:
        """Analyze individual trades"""
        if not trades:
            return {'total_trades': 0}
        
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
        
        avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        }
    
    def _validate_results(self, results: Dict[str, Any]) -> Dict[str, bool]:
        """Validate results quality"""
        return {
            'min_trades_threshold_met': results.get('total_trades', 0) > 10,
            'positive_return': results.get('total_return', 0) > 0,
            'acceptable_drawdown': results.get('max_drawdown', 1) < 0.2  # Less than 20%
        }