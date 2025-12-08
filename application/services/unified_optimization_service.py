"""Unified optimization service that can optimize parameters across different system components."""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd

from shared.logger import EnhancedLogger
from shared.optimization_service import OptimizationService
from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
from infrastructure.optimization.hyperopt_objective import HyperoptObjective
from infrastructure.optimization.advanced_optimization_service import AdvancedOptimizationService
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from shared.auto_drop_engine import CoinQualityFilter
from application.services.adaptive_retuning import PerformanceBasedRetuner


class UnifiedOptimizationService:
    """Service to optimize parameters across different system components."""
    
    def __init__(self, 
                 results_dir: str = "data/unified_optimization_results",
                 cache_dir: str = "data/unified_optimization_cache"):
        self.results_dir = Path(results_dir)
        self.cache_dir = Path(cache_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = EnhancedLogger("UnifiedOptimizationService")
        self.optimization_service = OptimizationService(results_dir, cache_dir)
        self.param_space = HyperoptParameterSpace()
        self.objective_handler = HyperoptObjective()
        self.advanced_optimization_service = AdvancedOptimizationService()
        
        # Component references for parameter optimization
        self.components = {}
        
    def register_component(self, name: str, component):
        """Register a system component that has parameters to optimize."""
        self.components[name] = component
        
    def optimize_strategy_params(self,
                               strategy_name: str,
                               data_dict: Dict[str, pd.DataFrame],
                               risk_config: Dict[str, Any],
                               max_evals: int = 100) -> Dict[str, Any]:
        """Optimize strategy-specific parameters."""
        # Get parameter space for the strategy
        param_space = self.param_space.get_space(strategy_name)
        
        if not param_space:
            self.logger.warning(f"No parameter space defined for strategy {strategy_name}, using generic space")
            param_space = self.param_space.get_space("generic")
        
        # Create objective function
        objective_fn = self.objective_handler.create_objective_function(
            data_dict, risk_config, optimization_objectives=['sharpe_ratio']
        )
        
        # Run optimization
        results = self.optimization_service.optimize(
            strategy_name=strategy_name,
            symbol="unified",  # Placeholder symbol
            indicators=[],  # Will be handled in the objective function
            price_changes=[],  # Will be handled in the objective function
            param_space=param_space,
            max_evals=max_evals
        )
        
        # Override with our own objective function
        from hyperopt import fmin, tpe, Trials, STATUS_OK
        trials = Trials()
        
        try:
            best = fmin(
                fn=objective_fn,
                space=param_space,
                algo=tpe.suggest,
                max_evals=max_evals,
                trials=trials
            )
            
            results = {
                'best_params': best,
                'trials': len(trials),
                'best_loss': trials.best_trial['result']['loss'],
                'component': 'strategy',
                'strategy': strategy_name
            }
            
        except Exception as e:
            self.logger.error(f"Strategy parameter optimization failed: {e}")
            results = {'error': str(e)}
        
        # Save results
        results_path = self.results_dir / f"strategy_{strategy_name}_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        return results
    
    def optimize_risk_params(self,
                           data_dict: Dict[str, pd.DataFrame],
                           initial_risk_manager: EnterpriseRiskManager,
                           max_evals: int = 50) -> Dict[str, Any]:
        """Optimize risk management parameters."""
        # Define parameter space for risk management
        from hyperopt import hp
        risk_param_space = {
            "max_portfolio_exposure": hp.uniform("max_portfolio_exposure", 50000, 500000),
            "max_position_exposure": hp.uniform("max_position_exposure", 25000, 250000),
            "max_risk_per_trade": hp.uniform("max_risk_per_trade", 0.001, 0.05),  # 0.1% to 5%
            "max_daily_loss_pct": hp.uniform("max_daily_loss_pct", 0.01, 0.10),  # 1% to 10%
            "max_drawdown_pct": hp.uniform("max_drawdown_pct", 0.05, 0.30),      # 5% to 30%
            "slippage_tolerance": hp.uniform("slippage_tolerance", 0.0001, 0.01), # 0.01% to 1%
            "max_correlation": hp.uniform("max_correlation", 0.5, 0.95)
        }
        
        # Create objective function that uses risk parameters
        def risk_objective(params):
            # Create a risk manager with these parameters
            temp_risk_manager = EnterpriseRiskManager(risk_config=params)
            
            # Create a mock objective function that evaluates risk-adjusted performance
            # This is simplified - in a real implementation, we would run actual backtests
            # with the risk parameters and evaluate the results
            score = 0
            
            # Simple scoring based on parameter values (in a real system, this would run actual backtests)
            # Higher max_risk_per_trade could lead to higher returns but also higher risk
            # We want to balance risk and return
            risk_score = params.get('max_risk_per_trade', 0.01) * 100  # Convert to percentage for score
            stability_score = (1 - params.get('max_drawdown_pct', 0.15) / 0.15) * 50  # Lower drawdown = higher score
            exposure_score = (params.get('max_portfolio_exposure', 100000) / 100000) * 10  # Higher exposure = higher score
            
            # Combine scores (this is a simplified approach)
            score = risk_score + stability_score + exposure_score
            
            return {'loss': -score, 'status': 'ok'}
        
        from hyperopt import fmin, tpe, Trials
        trials = Trials()
        
        try:
            best = fmin(
                fn=risk_objective,
                space=risk_param_space,
                algo=tpe.suggest,
                max_evals=max_evals,
                trials=trials
            )
            
            # Update the original risk manager with best parameters
            initial_risk_manager.update_from_params(best)
            
            results = {
                'best_params': best,
                'trials': len(trials),
                'best_loss': trials.best_trial['result']['loss'],
                'component': 'risk_management'
            }
            
        except Exception as e:
            self.logger.error(f"Risk parameter optimization failed: {e}")
            results = {'error': str(e)}
        
        # Save results
        results_path = self.results_dir / "risk_management_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        return results
    
    def optimize_auto_drop_params(self,
                                data_dict: Dict[str, pd.DataFrame],
                                initial_filter: CoinQualityFilter,
                                max_evals: int = 30) -> Dict[str, Any]:
        """Optimize auto-drop engine parameters."""
        # Define parameter space for auto-drop filters
        from hyperopt import hp
        filter_param_space = {
            "min_volume": hp.quniform("min_volume", 50000, 500000, 1000),
            "max_spread": hp.uniform("max_spread", 0.001, 0.01),
            "min_liquidity_score": hp.uniform("min_liquidity_score", 0.1, 0.8),
            "wash_trading_threshold": hp.uniform("wash_trading_threshold", 0.4, 0.8),
            "pump_dump_detector": hp.choice("pump_dump_detector", [True, False])
        }
        
        # Create objective function for auto-drop parameters
        def filter_objective(params):
            # This is a simplified approach - in a real implementation, 
            # we would evaluate the effectiveness of filtering parameters
            # based on backtest results with and without certain assets
            
            # Simple scoring based on filter parameters
            # More restrictive filters might lead to higher quality assets but fewer opportunities
            volume_score = (params.get('min_volume', 100000) - 50000) / 50000  # Higher min volume = more restrictive
            spread_score = (0.01 - params.get('max_spread', 0.003)) / 0.007   # Lower max spread = more restrictive
            liquidity_score = params.get('min_liquidity_score', 0.35) * 10     # Higher min liquidity = more restrictive
            wash_score = (0.8 - params.get('wash_trading_threshold', 0.65)) / 0.4  # Lower threshold = more restrictive
            
            # We want a balance - not too restrictive, not too loose
            score = (volume_score + spread_score + liquidity_score + wash_score) / 4
            
            return {'loss': -score, 'status': 'ok'}
        
        from hyperopt import fmin, tpe, Trials
        trials = Trials()
        
        try:
            best = fmin(
                fn=filter_objective,
                space=filter_param_space,
                algo=tpe.suggest,
                max_evals=max_evals,
                trials=trials
            )
            
            # Update the original filter with best parameters
            initial_filter.update_from_params(best)
            
            results = {
                'best_params': best,
                'trials': len(trials),
                'best_loss': trials.best_trial['result']['loss'],
                'component': 'auto_drop_engine'
            }
            
        except Exception as e:
            self.logger.error(f"Auto-drop parameter optimization failed: {e}")
            results = {'error': str(e)}
        
        # Save results
        results_path = self.results_dir / "auto_drop_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        return results
    
    def optimize_retuning_params(self,
                               initial_retuner: PerformanceBasedRetuner,
                               max_evals: int = 20) -> Dict[str, Any]:
        """Optimize auto-retuning parameters."""
        # Define parameter space for retuning
        from hyperopt import hp
        retuning_param_space = {
            "sharpe_ratio_threshold": hp.uniform("sharpe_ratio_threshold", 0.05, 0.5),
            "max_drawdown_threshold": hp.uniform("max_drawdown_threshold", -0.3, -0.05),  # Negative values
            "win_rate_threshold": hp.uniform("win_rate_threshold", 0.3, 0.6),
            "profit_factor_threshold": hp.uniform("profit_factor_threshold", 1.1, 2.0),
            "consecutive_loss_threshold": hp.quniform("consecutive_loss_threshold", 3, 10, 1),
            "performance_window": hp.quniform("performance_window", 10, 50, 1),
            "min_trades_for_evaluation": hp.quniform("min_trades_for_evaluation", 5, 25, 1),
            "performance_threshold": hp.uniform("performance_threshold", -0.5, 0.0),  # Negative values
            "retune_check_interval": hp.quniform("retune_check_interval", 1800, 14400, 1800),  # 0.5 to 4 hours
            "max_evals_per_retune": hp.quniform("max_evals_per_retune", 20, 100, 10)
        }
        
        # Create objective function for retuning parameters
        def retuning_objective(params):
            # This would evaluate how well the retuning parameters perform
            # For now, using a simple scoring system
            score = 0
            
            # Higher thresholds might mean more stable but less responsive system
            # We want to balance sensitivity and stability
            threshold_balance = (
                (params.get('sharpe_ratio_threshold', 0.15) - 0.1) * 5 +
                abs(params.get('max_drawdown_threshold', -0.15) + 0.1) * 5 +
                (params.get('win_rate_threshold', 0.4) - 0.3) * 5 +
                (params.get('profit_factor_threshold', 1.3) - 1.0) * 3
            )
            
            stability = (
                params.get('consecutive_loss_threshold', 5) / 10 +
                params.get('min_trades_for_evaluation', 10) / 20
            )
            
            score = threshold_balance + stability
            
            return {'loss': -score, 'status': 'ok'}
        
        from hyperopt import fmin, tpe, Trials
        trials = Trials()
        
        try:
            best = fmin(
                fn=retuning_objective,
                space=retuning_param_space,
                algo=tpe.suggest,
                max_evals=max_evals,
                trials=trials
            )
            
            # Update the original retuner with best parameters
            initial_retuner.update_from_params(best)
            
            results = {
                'best_params': best,
                'trials': len(trials),
                'best_loss': trials.best_trial['result']['loss'],
                'component': 'adaptive_retuning'
            }
            
        except Exception as e:
            self.logger.error(f"Retuning parameter optimization failed: {e}")
            results = {'error': str(e)}
        
        # Save results
        results_path = self.results_dir / "retuning_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        return results
    
    def optimize_all_components(self,
                              strategy_name: str,
                              data_dict: Dict[str, pd.DataFrame],
                              risk_manager: EnterpriseRiskManager,
                              auto_drop_filter: CoinQualityFilter,
                              retuner: PerformanceBasedRetuner,
                              max_evals_per_component: int = 50) -> Dict[str, Any]:
        """Optimize parameters for all system components."""
        self.logger.info("Starting unified optimization for all system components")
        
        results = {}
        
        # Optimize strategy parameters
        self.logger.info("Optimizing strategy parameters...")
        results['strategy'] = self.optimize_strategy_params(
            strategy_name, data_dict, risk_manager.get_optimizable_params(), max_evals_per_component
        )
        
        # Optimize risk parameters
        self.logger.info("Optimizing risk management parameters...")
        results['risk_management'] = self.optimize_risk_params(
            data_dict, risk_manager, max_evals_per_component // 2
        )
        
        # Optimize auto-drop parameters
        self.logger.info("Optimizing auto-drop engine parameters...")
        results['auto_drop'] = self.optimize_auto_drop_params(
            data_dict, auto_drop_filter, max_evals_per_component // 3
        )
        
        # Optimize retuning parameters
        self.logger.info("Optimizing adaptive retuning parameters...")
        results['retuning'] = self.optimize_retuning_params(
            retuner, max_evals_per_component // 4
        )

        # Save unified results
        results_path = self.results_dir / "unified_optimization_results.json"
        with open(results_path, 'w') as f:
            import json
            json.dump(results, f, indent=4)

        self.logger.info("Unified optimization completed")

        return results

    def optimize_strategy_params_advanced(self,
                                        strategy_name: str,
                                        data_dict: Dict[str, pd.DataFrame],
                                        risk_config: Dict[str, Any],
                                        max_evals: int = 100,
                                        use_ensemble: bool = True) -> Dict[str, Any]:
        """Advanced strategy parameter optimization with multiple algorithms or multi-objective."""
        # Get parameter space for the strategy
        param_space = self.param_space.get_space(strategy_name)

        if not param_space:
            self.logger.warning(f"No parameter space defined for strategy {strategy_name}, using generic space")
            param_space = self.param_space.get_space("generic")

        if use_ensemble:
            # Use ensemble of multiple algorithms
            results = self.advanced_optimization_service.optimize_with_multiple_algorithms(
                strategy_name=strategy_name,
                data_dict=data_dict,
                param_space=param_space,
                risk_config=risk_config,
                max_evals_per_algo=max_evals // 4 if max_evals >= 4 else 25,  # Distribute evaluations
                algorithms=['tpe', 'random', 'anneal']
            )
        else:
            # Use multi-objective optimization with early stopping
            results = self.advanced_optimization_service.multi_objective_optimize(
                data_dict=data_dict,
                param_space=param_space,
                risk_config=risk_config,
                max_evals=max_evals,
                objectives_weights={
                    'sharpe_ratio': 0.4,
                    'total_return': 0.25,
                    'max_drawdown': 0.25,  # Negative value, so higher is better
                    'win_rate': 0.1
                }
            )

        # Save results
        results_path = self.results_dir / f"strategy_{strategy_name}_advanced_results.json"
        with open(results_path, 'w') as f:
            import json
            json.dump(results, f, indent=4, default=str)  # default=str to handle datetime objects

        return results

    def optimize_with_early_stopping(self,
                                   strategy_name: str,
                                   data_dict: Dict[str, pd.DataFrame],
                                   risk_config: Dict[str, Any],
                                   max_evals: int = 100) -> Dict[str, Any]:
        """Strategy optimization with early stopping to prevent overfitting."""
        # Get parameter space for the strategy
        param_space = self.param_space.get_space(strategy_name)

        if not param_space:
            self.logger.warning(f"No parameter space defined for strategy {strategy_name}, using generic space")
            param_space = self.param_space.get_space("generic")

        # Use advanced optimization with early stopping
        results = self.advanced_optimization_service.optimize_with_early_stopping(
            data_dict=data_dict,
            param_space=param_space,
            risk_config=risk_config,
            max_evals=max_evals,
            early_stopping_rounds=15,
            min_improvement=0.0001
        )

        # Save results
        results_path = self.results_dir / f"strategy_{strategy_name}_early_stop_results.json"
        with open(results_path, 'w') as f:
            import json
            json.dump(results, f, indent=4, default=str)  # default=str to handle datetime objects

        return results