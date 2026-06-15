"""Cross-validation engine for validating strategy robustness in Walk-Forward Optimization."""

from typing import Dict, Any, List, Callable
import pandas as pd
import numpy as np
from domain.ports.backtest_ports import BacktestEnginePort
from application.walk_forward.sliding_window_splitter import SlidingWindowSplitter, WalkForwardWindow


class CrossValidationEngine:
    """Cross-validation engine for validating strategy robustness."""
    
    def __init__(self,
                 n_splits: int = 5,
                 min_train_size: int = 30,
                 test_size: int = 15,
                 *,
                 backtester_class: Callable[[], BacktestEnginePort]):
        """
        Initialize the cross-validation engine.
        
        Args:
            n_splits: Number of cross-validation splits
            min_train_size: Minimum training size for each fold
            test_size: Size of test set for each fold
            backtester_class: Backtester class to use for validation
        """
        self.n_splits = n_splits
        self.min_train_size = min_train_size
        self.test_size = test_size
        self.backtester_class = backtester_class
        
    def run_cross_validation(self,
                           data: pd.DataFrame,
                           strategy_func: Callable,
                           strategy_params: Dict[str, Any],
                           return_details: bool = False) -> Dict[str, Any]:
        """
        Run cross-validation on the given data with specified strategy.
        
        Args:
            data: DataFrame with OHLCV data
            strategy_func: Strategy function to test
            strategy_params: Parameters for the strategy
            return_details: Whether to return detailed results for each fold
            
        Returns:
            Dictionary with cross-validation results
        """
        if data.empty or len(data) < (self.min_train_size + self.test_size):
            return {
                'error': f'Insufficient data. Need at least {self.min_train_size + self.test_size} points',
                'cv_results': []
            }
        
        # Use time series split to preserve temporal order
        splitter = self._create_time_series_splits(data)
        
        fold_results = []
        
        for fold_num, (train_idx, test_idx) in enumerate(splitter):
            if len(test_idx) == 0:
                continue
                
            train_data = data.iloc[train_idx]
            test_data = data.iloc[test_idx]
            
            # Run backtest on training data
            train_results = self._run_single_backtest(train_data, strategy_func, strategy_params)
            
            # Run backtest on testing data  
            test_results = self._run_single_backtest(test_data, strategy_func, strategy_params)
            
            fold_result = {
                'fold': fold_num,
                'train_period': {
                    'start': train_data.index[0],
                    'end': train_data.index[-1],
                    'size': len(train_data)
                },
                'test_period': {
                    'start': test_data.index[0],
                    'end': test_data.index[-1],
                    'size': len(test_data)
                },
                'train_results': train_results,
                'test_results': test_results
            }
            
            fold_results.append(fold_result)
        
        return self._aggregate_cv_results(fold_results, return_details)
    
    def _create_time_series_splits(self, data: pd.DataFrame):
        """Create time series splits that preserve temporal order."""
        n_samples = len(data)
        indices = np.arange(n_samples)
        
        # Calculate split points to ensure minimum training size
        min_total_size = self.min_train_size + self.test_size
        if n_samples < min_total_size:
            raise ValueError(f"Insufficient data for cross-validation. Need at least {min_total_size} samples.")
        
        # Create overlapping or non-overlapping splits
        splits = []
        step_size = max(1, (n_samples - self.min_train_size - self.test_size) // (self.n_splits - 1) if self.n_splits > 1 else 1)
        
        start_idx = 0
        for i in range(self.n_splits):
            # Define training and test indices
            train_end_idx = min(start_idx + self.min_train_size + i * step_size, n_samples - self.test_size)
            test_start_idx = train_end_idx
            test_end_idx = min(test_start_idx + self.test_size, n_samples)
            
            if test_end_idx <= train_end_idx:
                break
                
            train_idx = indices[start_idx:train_end_idx]
            test_idx = indices[test_start_idx:test_end_idx]
            
            if len(train_idx) >= self.min_train_size and len(test_idx) >= self.test_size:
                splits.append((train_idx, test_idx))
            
            if test_end_idx >= n_samples:
                break
        
        return splits
    
    def _run_single_backtest(self, data: pd.DataFrame, strategy_func: Callable, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single backtest with the given strategy and parameters."""
        try:
            backtester = self.backtester_class()
            results = backtester.run_backtest(
                data=data,
                strategy_function=strategy_func,
                strategy_params=params
            )
            return results
        except Exception as e:
            return {
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 1.0,
                'error': str(e)
            }
    
    def _aggregate_cv_results(self, fold_results: List[Dict], return_details: bool) -> Dict[str, Any]:
        """Aggregate cross-validation results across all folds."""
        if not fold_results:
            return {'error': 'No valid cross-validation folds generated'}
        
        # Extract metrics from all folds
        train_returns = []
        test_returns = []
        train_sharpes = []
        test_sharpes = []
        train_drawdowns = []
        test_drawdowns = []
        train_win_rates = []
        test_win_rates = []
        train_profit_factors = []
        test_profit_factors = []
        
        for fold in fold_results:
            train_result = fold.get('train_results', {})
            test_result = fold.get('test_results', {})
            
            train_returns.append(train_result.get('total_return', 0))
            test_returns.append(test_result.get('total_return', 0))
            train_sharpes.append(train_result.get('sharpe_ratio', 0))
            test_sharpes.append(test_result.get('sharpe_ratio', 0))
            train_drawdowns.append(abs(train_result.get('max_drawdown', 0)))
            test_drawdowns.append(abs(test_result.get('max_drawdown', 0)))
            train_win_rates.append(train_result.get('win_rate', 0))
            test_win_rates.append(test_result.get('win_rate', 0))
            train_profit_factors.append(train_result.get('profit_factor', 1.0))
            test_profit_factors.append(test_result.get('profit_factor', 1.0))
        
        # Calculate aggregate metrics
        avg_train_return = np.mean(train_returns) if train_returns else 0
        avg_test_return = np.mean(test_returns) if test_returns else 0
        avg_train_sharpe = np.mean(train_sharpes) if train_sharpes else 0
        avg_test_sharpe = np.mean(test_sharpes) if test_sharpes else 0
        avg_train_drawdown = np.mean(train_drawdowns) if train_drawdowns else 0
        avg_test_drawdown = np.mean(test_drawdowns) if test_drawdowns else 0
        avg_train_win_rate = np.mean(train_win_rates) if train_win_rates else 0
        avg_test_win_rate = np.mean(test_win_rates) if test_win_rates else 0
        avg_train_pf = np.mean(train_profit_factors) if train_profit_factors else 0
        avg_test_pf = np.mean(test_profit_factors) if test_profit_factors else 0
        
        # Calculate overfitting metrics
        overfit_return = abs(avg_train_return - avg_test_return) if (avg_train_return != 0 or avg_test_return != 0) else 0
        overfit_sharpe = abs(avg_train_sharpe - avg_test_sharpe) if (avg_train_sharpe != 0 or avg_test_sharpe != 0) else 0
        overfit_win_rate = abs(avg_train_win_rate - avg_test_win_rate) if (avg_train_win_rate != 0 or avg_test_win_rate != 0) else 0
        
        results = {
            'total_folds': len(fold_results),
            'avg_train_return': float(avg_train_return),
            'avg_test_return': float(avg_test_return),
            'avg_train_sharpe': float(avg_train_sharpe),
            'avg_test_sharpe': float(avg_test_sharpe),
            'avg_train_drawdown': float(avg_train_drawdown),
            'avg_test_drawdown': float(avg_test_drawdown),
            'avg_train_win_rate': float(avg_train_win_rate),
            'avg_test_win_rate': float(avg_test_win_rate),
            'avg_train_profit_factor': float(avg_train_pf),
            'avg_test_profit_factor': float(avg_test_pf),
            'overfit_return': float(overfit_return),
            'overfit_sharpe': float(overfit_sharpe),
            'overfit_win_rate': float(overfit_win_rate),
            'cv_score': self._calculate_cv_score(avg_test_sharpe, avg_test_return, avg_test_win_rate),
            'robustness_score': self._calculate_robustness_score(test_sharpes, test_returns)
        }
        
        if return_details:
            results['fold_details'] = fold_results
        
        return results
    
    def _calculate_cv_score(self, avg_sharpe: float, avg_return: float, avg_win_rate: float) -> float:
        """Calculate a composite cross-validation score."""
        # Normalize values to 0-1 range
        normalized_sharpe = max(0, min(1, (avg_sharpe + 2) / 4))  # Assuming reasonable Sharpe range [-2, 2]
        normalized_return = max(0, min(1, avg_return + 0.5))  # Adjust based on expected return range
        normalized_win_rate = max(0, min(1, avg_win_rate))
        
        # Weighted combination (can be adjusted based on priorities)
        score = (normalized_sharpe * 0.5) + (normalized_return * 0.3) + (normalized_win_rate * 0.2)
        
        return float(score)
    
    def _calculate_robustness_score(self, sharpes: List[float], returns: List[float]) -> float:
        """Calculate robustness based on consistency across folds."""
        if len(sharpes) < 2:
            return 1.0  # Perfect robustness if only one fold
        
        # Robustness is inversely related to coefficient of variation
        sharpe_std = np.std(sharpes)
        sharpe_mean = np.mean(sharpes)
        
        if sharpe_mean == 0:
            # If mean is 0, robustness depends on how small the std is
            return float(max(0, 1 - sharpe_std))
        
        # Calculate coefficient of variation for sharpes
        cv_sharpe = sharpe_std / abs(sharpe_mean)
        # Lower CV means higher robustness (up to 1.0)
        robustness = max(0, min(1, 1 - cv_sharpe))
        
        return float(robustness)


class WalkForwardCrossValidation:
    """Cross-validation specifically designed to work with Walk-Forward optimization."""
    
    def __init__(self, 
                 cv_engine: CrossValidationEngine,
                 wfo_splitter: SlidingWindowSplitter):
        """
        Initialize WFO-specific cross-validation.
        
        Args:
            cv_engine: Cross-validation engine instance
            wfo_splitter: Walk-forward splitter instance
        """
        self.cv_engine = cv_engine
        self.wfo_splitter = wfo_splitter
    
    def validate_walk_forward_setup(self,
                                  data: pd.DataFrame,
                                  strategy_func: Callable,
                                  strategy_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the Walk-Forward setup with cross-validation.
        
        Args:
            data: Complete dataset to validate on
            strategy_func: Strategy function to test
            strategy_params: Parameters for the strategy
            
        Returns:
            Dictionary with validation results
        """
        # Perform cross-validation on the complete dataset
        cv_results = self.cv_engine.run_cross_validation(
            data=data,
            strategy_func=strategy_func,
            strategy_params=strategy_params,
            return_details=True
        )
        
        if 'error' in cv_results:
            return cv_results
        
        # Also validate the Walk-Forward split will work
        try:
            windows = self.wfo_splitter.split(data)
            wfo_validation = {
                'wfo_windows_available': len(windows),
                'first_window': {
                    'train_size': len(windows[0].train_data) if windows else 0,
                    'test_size': len(windows[0].test_data) if windows else 0
                } if windows else {}
            }
        except Exception as e:
            wfo_validation = {'wfo_error': str(e)}
        
        # Combine results
        validation_results = {
            'cross_validation': cv_results,
            'walk_forward_validation': wfo_validation,
            'overall_robustness': self._calculate_overall_robustness(cv_results, wfo_validation)
        }
        
        return validation_results
    
    def _calculate_overall_robustness(self, cv_results: Dict, wfo_validation: Dict) -> float:
        """Calculate overall robustness combining CV and WFO metrics."""
        cv_score = cv_results.get('cv_score', 0)
        cv_robustness = cv_results.get('robustness_score', 0)
        
        # If WFO validation failed, overall robustness is low
        if 'wfo_error' in wfo_validation:
            return 0.0
        
        wfo_windows = wfo_validation.get('wfo_windows_available', 0)
        
        # More WFO windows generally means more robust validation
        wfo_score = min(1.0, wfo_windows / 10.0)  # Cap at 10 windows = 1.0
        
        # Combine scores (can be weighted differently)
        overall_robustness = (cv_score * 0.4) + (cv_robustness * 0.3) + (wfo_score * 0.3)
        
        return float(overall_robustness)