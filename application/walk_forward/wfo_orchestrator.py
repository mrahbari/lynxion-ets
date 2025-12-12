"""Walk-Forward Optimization orchestrator - connects all components for a complete WFO pipeline."""

from typing import Dict, Any, List, Callable
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Import our custom components
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter as CSVHistoryLoader
from application.walk_forward.sliding_window_splitter import SlidingWindowSplitter
from application.walk_forward.hyperopt_adapter import MultiAssetHyperoptAdapter
from application.walk_forward.cross_validation_engine import CrossValidationEngine
from infrastructure.backtest.adapters.walk_forward import WalkForwardAnalyzer
from infrastructure.backtest.realistic_backtester import RealisticBacktester
from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
from shared.logger import logger
import json


class WFOOrchestrator:
    """Orchestrates the complete Walk-Forward Optimization pipeline."""

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the WFO orchestrator.

        Args:
            config: Configuration dictionary with all required parameters
        """
        self.config = config or {}

        # Initialize components
        self.data_loader = CSVHistoryLoader(self.config.get('data_path', './data'))
        self.splitter = SlidingWindowSplitter(
            train_size=self.config.get('train_size', 90),
            test_size=self.config.get('test_size', 30),
            step=self.config.get('step', 30)
        )
        self.hyperopt_adapter = MultiAssetHyperoptAdapter(
            risk_config=self.config.get('risk_config', {}),
            max_evals=self.config.get('max_evals', 50)
        )
        self.cv_engine = CrossValidationEngine(
            n_splits=self.config.get('cv_n_splits', 5),
            min_train_size=self.config.get('cv_min_train_size', 30),
            test_size=self.config.get('cv_test_size', 15)
        )

        # Corrected initialization with proper config format
        wfo_configs = {
            'train_size': self.config.get('train_size', 90),
            'test_size': self.config.get('test_size', 30),
            'step': self.config.get('step', 30),
            'performance_threshold': self.config.get('performance_threshold', 0.1),
            'max_drawdown_threshold': self.config.get('max_drawdown_threshold', 0.15)
        }
        self.wfo_analyzer = WalkForwardAnalyzer(wfo_configs)

        # Set up output directories
        self.results_dir = Path(self.config.get('results_dir', './data/results/wfo'))
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def run_complete_wfo_pipeline(self, 
                                symbols: List[str],
                                strategy_name: str,
                                strategy_func: Callable = None) -> Dict[str, Any]:
        """
        Run the complete Walk-Forward Optimization pipeline.
        
        Args:
            symbols: List of trading symbols to analyze
            strategy_name: Name of the strategy to optimize
            strategy_func: Strategy function to use
            
        Returns:
            Dictionary with complete WFO results
        """
        logger.info(f"Starting complete WFO pipeline for symbols: {symbols}, strategy: {strategy_name}")
        
        # Step 1: Load data
        logger.info("Step 1: Loading historical data...")
        data_dict = self._load_data(symbols)
        if not data_dict:
            return {'error': 'Failed to load data', 'results': {}}
        
        # Step 2: Validate data sufficiency for WFO
        logger.info("Step 2: Validating data for WFO...")
        validation_results = self._validate_data_for_wfo(data_dict)
        if not validation_results.get('all_symbols_valid', False):
            return {'error': 'Insufficient data for WFO', 'validation': validation_results}
        
        # Step 3: Determine parameter space for hyperparameter optimization
        logger.info("Step 3: Setting up hyperparameter space...")
        param_space = self._get_parameter_space(strategy_name)

        # Step 4: Cross-validation to assess strategy robustness
        logger.info("Step 4: Running cross-validation...")
        cv_results = self._run_cross_validation(data_dict, strategy_func, param_space)

        # Step 5: Multi-asset hyperparameter optimization
        logger.info("Step 5: Running multi-asset hyperparameter optimization...")
        multi_asset_params = self.hyperopt_adapter.optimize(
            multi_asset_data=data_dict,
            parameter_space=param_space
        )

        # Step 6: Aggregate parameters across assets for robustness
        logger.info("Step 6: Aggregating parameters across assets...")
        robust_params = self.hyperopt_adapter.aggregate_parameters(multi_asset_params)

        # Step 7: Run Walk-Forward Analysis
        logger.info("Step 7: Running Walk-Forward Analysis...")
        wfo_results = self.wfo_analyzer.run_walk_forward_analysis(
            data=data_dict,
            strategy_optimizer=lambda df: robust_params  # Use robust params for WFO
        )

        # Step 8: Generate comprehensive report
        logger.info("Step 8: Generating comprehensive report...")
        comprehensive_report = self._generate_comprehensive_report(
            cv_results, multi_asset_params, robust_params, wfo_results
        )

        # Step 9: Save results
        logger.info("Step 9: Saving results...")
        self._save_results(comprehensive_report, symbols, strategy_name)

        final_results = {
            'timestamp': datetime.now().isoformat(),
            'symbols': symbols,
            'strategy_name': strategy_name,
            'data_validation': validation_results,
            'cross_validation_results': cv_results,
            'multi_asset_optimization': multi_asset_params,
            'robust_parameters': robust_params,
            'walk_forward_results': wfo_results,
            'comprehensive_report': comprehensive_report
        }

        logger.info("WFO pipeline completed successfully!")
        return final_results
    
    def _load_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Load historical data for specified symbols."""
        data_dict = {}
        for symbol in symbols:
            try:
                df = self.data_loader.load(symbol=symbol)
                if not df.empty:
                    data_dict[symbol] = df
                    logger.info(f"Loaded {len(df)} rows for {symbol}")
                else:
                    logger.warning(f"No data loaded for {symbol}")
            except Exception as e:
                logger.error(f"Error loading data for {symbol}: {e}")
        
        return data_dict
    
    def _validate_data_for_wfo(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate that the data is sufficient for Walk-Forward Analysis."""
        validation_results = {}
        
        all_valid = True
        for symbol, df in data_dict.items():
            try:
                validation = self.splitter.validate_split(df)
                validation_results[symbol] = validation
                if not validation['has_sufficient_data']:
                    all_valid = False
                    logger.warning(f"Insufficient data for {symbol}: {validation}")
            except Exception as e:
                logger.error(f"Error validating data for {symbol}: {e}")
                validation_results[symbol] = {'error': str(e)}
                all_valid = False
        
        return {
            'all_symbols_valid': all_valid,
            'individual_validations': validation_results
        }
    
    def _get_parameter_space(self, strategy_name: str) -> Dict[str, Any]:
        """Get the parameter space for hyperparameter optimization."""
        # Use the existing HyperoptParameterSpace from infrastructure
        param_space_handler = HyperoptParameterSpace()
        return param_space_handler.get_space(strategy_name)
    
    def _run_cross_validation(self, 
                            data_dict: Dict[str, pd.DataFrame], 
                            strategy_func: Callable, 
                            param_space: Dict[str, Any]) -> Dict[str, Any]:
        """Run cross-validation on the strategy and data."""
        # For now, we'll run cross-validation on a single representative dataset
        # In practice, you might want to run this for each symbol or aggregated
        cv_results = {}
        
        for symbol, df in data_dict.items():
            if len(df) > 100:  # Ensure sufficient data
                # Use CrossValidationEngine for validation rather than WalkForwardCrossValidation
                # which isn't properly imported in this file
                default_params = {k: v.get('min', 1) if hasattr(v, 'get') else 1
                                for k, v in param_space.items()}

                try:
                    # Run cross-validation on this dataset
                    cv_result = self.cv_engine.run_cross_validation(
                        data=df,
                        strategy_func=strategy_func or self._default_strategy_function,
                        strategy_params=default_params,
                        return_details=True
                    )
                    cv_results[symbol] = cv_result
                except Exception as e:
                    logger.error(f"Error in CV for {symbol}: {e}")
                    cv_results[symbol] = {'error': str(e)}
                    
        return cv_results
    
    def _default_strategy_function(self, row, params):
        """Default strategy function for use when none is provided."""
        # This is a simple example - in practice, this would be the actual strategy logic
        return 0  # No signal
    
    def _generate_comprehensive_report(self, 
                                     cv_results: Dict, 
                                     multi_asset_params: Dict, 
                                     robust_params: Dict, 
                                     wfo_results: Dict) -> Dict[str, Any]:
        """Generate a comprehensive report from all analysis results."""
        
        # Calculate key metrics
        total_assets = wfo_results.get('total_assets_analyzed', 0)
        total_periods = wfo_results.get('total_periods', 0)
        avg_sharpe = wfo_results.get('avg_sharpe_ratio', 0)
        avg_return = wfo_results.get('avg_total_return', 0)
        avg_drawdown = wfo_results.get('avg_max_drawdown', 0)
        pass_rate = wfo_results.get('pass_rate', 0)
        param_stability = wfo_results.get('parameter_stability', 0)
        
        # Calculate consistency
        consistency_score = wfo_results.get('statistical_significance', {}).get('consistency_score', 0)
        overfit_index = wfo_results.get('statistical_significance', {}).get('overfit_index', float('inf'))
        
        # Determine overall grade
        grade = self._calculate_overall_grade(
            avg_sharpe=avg_sharpe, pass_rate=pass_rate, param_stability=param_stability,
            consistency_score=consistency_score, overfit_index=overfit_index
        )

        report = {
            'summary_metrics': {
                'total_assets_analyzed': total_assets,
                'total_walk_forward_periods': total_periods,
                'average_sharpe_ratio': avg_sharpe,
                'average_total_return': avg_return,
                'average_max_drawdown': avg_drawdown,
                'pass_rate': pass_rate,  # Percentage of periods that passed thresholds
                'parameter_stability_score': param_stability,
                'consistency_score': consistency_score,
                'overfit_index': overfit_index
            },
            'performance_grade': grade,
            'robust_parameters': robust_params,
            'multi_asset_optimization_summary': {
                'assets': list(multi_asset_params.keys()),
                'parameter_ranges': self._get_parameter_ranges(multi_asset_params)
            },
            'cross_validation_summary': self._summarize_cv_results(cv_results),
            'walk_forward_analysis_summary': {
                'total_periods': total_periods,
                'successful_periods': int(total_periods * pass_rate) if total_periods > 0 else 0,
                'success_rate_percentage': pass_rate * 100
            },
            'recommendations': self._generate_recommendations(
                avg_sharpe=avg_sharpe, pass_rate=pass_rate, param_stability=param_stability,
                consistency_score=consistency_score, overfit_index=overfit_index
            )
        }

        return report

    def _calculate_overall_grade(self, avg_sharpe: float, pass_rate: float, param_stability: float,
                               consistency_score: float, overfit_index: float) -> str:
        """Calculate an overall performance grade (A-F)."""
        # Normalize scores to 0-100 range
        sharpe_score = max(0, min(100, (avg_sharpe + 2) * 25))  # Sharpe of 2.0 = 100 points
        pass_rate_score = pass_rate * 100
        param_stability_score = param_stability * 100
        consistency_score_score = consistency_score * 100
        
        # For overfit index, lower is better (inverse score)
        overfit_score = max(0, 100 - (overfit_index * 50))  # Normalize to 0-100
        
        # Calculate weighted average (weights can be adjusted)
        weighted_avg = (
            sharpe_score * 0.3 +
            pass_rate_score * 0.2 +
            param_stability_score * 0.2 +
            consistency_score_score * 0.2 +
            overfit_score * 0.1
        )
        
        # Convert to letter grade
        if weighted_avg >= 90:
            return 'A'
        elif weighted_avg >= 80:
            return 'B'
        elif weighted_avg >= 70:
            return 'C'
        elif weighted_avg >= 60:
            return 'D'
        else:
            return 'F'
    
    def _get_parameter_ranges(self, multi_asset_params: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Get the range of each parameter across all assets."""
        if not multi_asset_params:
            return {}
        
        param_ranges = {}
        all_keys = set()
        
        # Collect all parameter keys
        for params in multi_asset_params.values():
            all_keys.update(params.keys())
        
        # Calculate min and max for each parameter
        for key in all_keys:
            values = []
            for params in multi_asset_params.values():
                if key in params and params[key] is not None:
                    try:
                        values.append(float(params[key]))
                    except (ValueError, TypeError):
                        continue

            if values:
                param_ranges[key] = {
                    'min': float(min(values)),
                    'max': float(max(values)),
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values))
                }

        return param_ranges
    
    def _summarize_cv_results(self, cv_results: Dict) -> Dict[str, Any]:
        """Summarize cross-validation results."""
        if not cv_results:
            return {'summary': 'No CV results available'}
        
        # Extract metrics from CV results
        cv_scores = []
        robustness_scores = []
        
        for asset_results in cv_results.values():
            if isinstance(asset_results, dict) and 'cross_validation' in asset_results:
                cv_score = asset_results['cross_validation'].get('cv_score', 0)
                robustness_score = asset_results['cross_validation'].get('robustness_score', 0)
                cv_scores.append(cv_score)
                robustness_scores.append(robustness_score)
        
        return {
            'average_cv_score': float(np.mean(cv_scores)) if cv_scores else 0,
            'average_robustness_score': float(np.mean(robustness_scores)) if robustness_scores else 0,
            'total_assets_cv_tested': len(cv_scores)
        }
    
    def _generate_recommendations(self, avg_sharpe, pass_rate, param_stability, consistency_score, overfit_index):
        """Generate recommendations based on the results."""
        recommendations = []
        
        # Sharpe ratio recommendation
        if avg_sharpe < 0.5:
            recommendations.append("Sharpe ratio is low (< 0.5). Consider strategy improvements or risk management.")
        elif avg_sharpe > 1.5:
            recommendations.append("Very high Sharpe ratio detected (> 1.5). Verify for potential overfitting.")
        
        # Pass rate recommendation
        if pass_rate < 0.6:
            recommendations.append("Pass rate is low (< 60%). Strategy may not be robust across different market conditions.")
        
        # Parameter stability recommendation
        if param_stability < 0.5:
            recommendations.append("Parameter stability is low (< 50%). Parameters vary significantly across periods.")
        
        # Consistency recommendation
        if consistency_score < 0.6:
            recommendations.append("Consistency score is low (< 60%). Strategy performance is inconsistent across periods.")
        
        # Overfit index recommendation
        if overfit_index > 1:
            recommendations.append("High overfit index detected (> 1). Strategy may be overfitted to historical data.")
        
        # General recommendation
        if avg_sharpe >= 0.5 and pass_rate >= 0.6 and param_stability >= 0.5:
            recommendations.append("Strategy shows promising results. Consider paper trading before live implementation.")
        
        return recommendations
    
    def _save_results(self, results: Dict[str, Any], symbols: List[str], strategy_name: str):
        """Save the results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive report
        report_file = self.results_dir / f"wfo_report_{strategy_name}_{'_'.join(symbols)}_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # Save robust parameters separately for easy access
        if 'robust_parameters' in results:
            params_file = self.results_dir / f"robust_params_{strategy_name}_{'_'.join(symbols)}_{timestamp}.json"
            with open(params_file, 'w') as f:
                json.dump({
                    'timestamp': results.get('timestamp', datetime.now().isoformat()),
                    'strategy': strategy_name,
                    'symbols': symbols,
                    'robust_parameters': results['robust_parameters']
                }, f, indent=2, default=str)

        logger.info(f"Results saved to {report_file}")