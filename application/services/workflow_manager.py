"""Joint workflows connecting hyperopt, backtesting, and decision making."""

from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

from shared.logger import EnhancedLogger
from shared.configurable_hyperopt import ConfigurableHyperoptOptimizer, HyperoptConfig
from infrastructure.data.coin_history_service import CoinHistoryService
from infrastructure.results_tracking.results_tracker import ResultsTracker
from application.services.adaptive_retuning import AdaptiveRetuningManager


class HyperoptBacktestWorkflow:
    """
    Implements joint workflows for hyperopt and backtesting:
    - hyperopt → backtest → decision
    - backtest → hyperopt → backtest
    - Fully automated pipelines
    """
    
    def __init__(self,
                 hyperopt_optimizer: ConfigurableHyperoptOptimizer,
                 coin_history_service: CoinHistoryService,
                 results_tracker: ResultsTracker,
                 adaptive_retuner: AdaptiveRetuningManager):
        self.hyperopt_optimizer = hyperopt_optimizer
        self.coin_history_service = coin_history_service
        self.results_tracker = results_tracker
        self.adaptive_retuner = adaptive_retuner
        self.logger = EnhancedLogger("HyperoptBacktestWorkflow")
    
    def hyperopt_backtest_decision_workflow(self,
                                          strategy_name: str,
                                          symbol: str,
                                          timeframe: str = "1h",
                                          hyperopt_config: Dict[str, Any] = None,
                                          backtest_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the hyperopt → backtest → decision workflow.
        
        This workflow:
        1. Runs hyperparameter optimization
        2. Backtests the optimized parameters
        3. Makes a decision based on results
        """
        self.logger.info(f"Starting hyperopt → backtest → decision workflow for {strategy_name} {symbol}")
        
        workflow_result = {
            "workflow": "hyperopt_backtest_decision",
            "strategy": strategy_name,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "steps": {},
            "decision": None,
            "final_parameters": None
        }
        
        try:
            # Step 1: Fetch historical data
            data = self.coin_history_service.fetch_historical_data(symbol, timeframe)
            if data is None or data.empty:
                raise Exception(f"Failed to fetch data for {symbol}")
            
            self.logger.info(f"Fetched {len(data)} candles for {symbol}")
            workflow_result["steps"]["data_fetch"] = {
                "status": "completed",
                "data_points": len(data),
                "timeframe": timeframe
            }
            
            # Step 2: Run hyperparameter optimization
            self.logger.info("Starting hyperparameter optimization...")
            opt_results = self.hyperopt_optimizer.optimize_with_config(
                strategy_name=strategy_name,
                data=data,
                symbol=symbol,
                custom_config=hyperopt_config
            )
            
            if "error" in opt_results:
                raise Exception(f"Hyperopt failed: {opt_results['error']}")
            
            workflow_result["steps"]["hyperopt"] = {
                "status": "completed",
                "results": opt_results
            }
            
            # Step 3: Backtest optimized parameters
            self.logger.info("Starting backtest with optimized parameters...")
            backtest_results = self._run_backtest_with_parameters(
                strategy_name=strategy_name,
                symbol=symbol,
                data=data,
                parameters=opt_results["best_params"],
                config=backtest_config
            )
            
            workflow_result["steps"]["backtest"] = {
                "status": "completed",
                "results": backtest_results
            }
            
            # Save both results to tracker
            hyperopt_id = self.results_tracker.save_hyperopt_result(
                strategy_name=strategy_name,
                symbol=symbol,
                parameters=opt_results["best_params"],
                best_value=opt_results["best_value"],
                trials_completed=opt_results["trials_completed"],
                optimization_objective=opt_results["optimization_objective"]
            )
            
            backtest_id = self.results_tracker.save_backtest_result(
                strategy_name=strategy_name,
                symbol=symbol,
                parameters=opt_results["best_params"],
                total_return=backtest_results.get("total_return", 0),
                sharpe_ratio=backtest_results.get("sharpe_ratio", 0),
                max_drawdown=backtest_results.get("max_drawdown", 0),
                win_rate=backtest_results.get("win_rate", 0),
                total_trades=backtest_results.get("total_trades", 0),
                profit_factor=backtest_results.get("profit_factor", 0)
            )
            
            # Link the results
            run_id = f"hb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{strategy_name}_{symbol}"
            self.results_tracker.link_hyperopt_and_backtest(
                run_id=run_id,
                strategy_name=strategy_name,
                symbol=symbol,
                hyperopt_result_id=hyperopt_id,
                backtest_result_id=backtest_id,
                workflow_type="hyperopt_backtest_decision"
            )
            
            # Step 4: Make decision based on results
            decision = self._make_decision_from_results(
                hyperopt_results=opt_results,
                backtest_results=backtest_results
            )
            
            workflow_result["decision"] = decision
            workflow_result["final_parameters"] = opt_results["best_params"]
            
            self.logger.info(f"Workflow completed for {strategy_name} {symbol}, decision: {decision['action']}")
            
            return workflow_result
            
        except Exception as e:
            self.logger.error(f"Error in hyperopt → backtest → decision workflow: {e}")
            workflow_result["error"] = str(e)
            workflow_result["status"] = "failed"
            return workflow_result
    
    def backtest_hyperopt_backtest_workflow(self,
                                          strategy_name: str,
                                          symbol: str,
                                          timeframe: str = "1h",
                                          initial_parameters: Dict[str, Any] = None,
                                          hyperopt_config: Dict[str, Any] = None,
                                          backtest_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the backtest → hyperopt → backtest workflow.
        
        This workflow:
        1. Backtests with initial parameters
        2. Runs hyperparameter optimization based on results
        3. Backtests with optimized parameters
        """
        self.logger.info(f"Starting backtest → hyperopt → backtest workflow for {strategy_name} {symbol}")
        
        workflow_result = {
            "workflow": "backtest_hyperopt_backtest",
            "strategy": strategy_name,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "steps": {},
            "comparison": None,
            "final_parameters": None
        }
        
        try:
            # Step 1: Fetch historical data
            data = self.coin_history_service.fetch_historical_data(symbol, timeframe)
            if data is None or data.empty:
                raise Exception(f"Failed to fetch data for {symbol}")
            
            workflow_result["steps"]["data_fetch"] = {
                "status": "completed",
                "data_points": len(data),
                "timeframe": timeframe
            }
            
            # Step 2: Initial backtest with provided or default parameters
            initial_params = initial_parameters or self._get_default_parameters(strategy_name)
            self.logger.info("Running initial backtest...")
            
            initial_backtest_results = self._run_backtest_with_parameters(
                strategy_name=strategy_name,
                symbol=symbol,
                data=data,
                parameters=initial_params,
                config=backtest_config
            )
            
            workflow_result["steps"]["initial_backtest"] = {
                "status": "completed",
                "results": initial_backtest_results,
                "parameters": initial_params
            }
            
            # Step 3: Run hyperparameter optimization
            self.logger.info("Running hyperparameter optimization...")
            opt_results = self.hyperopt_optimizer.optimize_with_config(
                strategy_name=strategy_name,
                data=data,
                symbol=symbol,
                custom_config=hyperopt_config
            )
            
            if "error" in opt_results:
                raise Exception(f"Hyperopt failed: {opt_results['error']}")
            
            workflow_result["steps"]["hyperopt"] = {
                "status": "completed",
                "results": opt_results
            }
            
            # Step 4: Backtest with optimized parameters
            self.logger.info("Running final backtest with optimized parameters...")
            final_backtest_results = self._run_backtest_with_parameters(
                strategy_name=strategy_name,
                symbol=symbol,
                data=data,
                parameters=opt_results["best_params"],
                config=backtest_config
            )
            
            workflow_result["steps"]["final_backtest"] = {
                "status": "completed",
                "results": final_backtest_results,
                "parameters": opt_results["best_params"]
            }
            
            # Save all results to tracker
            initial_bt_id = self.results_tracker.save_backtest_result(
                strategy_name=strategy_name,
                symbol=symbol,
                parameters=initial_params,
                total_return=initial_backtest_results.get("total_return", 0),
                sharpe_ratio=initial_backtest_results.get("sharpe_ratio", 0),
                max_drawdown=initial_backtest_results.get("max_drawdown", 0),
                win_rate=initial_backtest_results.get("win_rate", 0),
                total_trades=initial_backtest_results.get("total_trades", 0),
                profit_factor=initial_backtest_results.get("profit_factor", 0),
                notes="Initial backtest before hyperopt"
            )
            
            hyperopt_id = self.results_tracker.save_hyperopt_result(
                strategy_name=strategy_name,
                symbol=symbol,
                parameters=opt_results["best_params"],
                best_value=opt_results["best_value"],
                trials_completed=opt_results["trials_completed"],
                optimization_objective=opt_results["optimization_objective"]
            )
            
            final_bt_id = self.results_tracker.save_backtest_result(
                strategy_name=strategy_name,
                symbol=symbol,
                parameters=opt_results["best_params"],
                total_return=final_backtest_results.get("total_return", 0),
                sharpe_ratio=final_backtest_results.get("sharpe_ratio", 0),
                max_drawdown=final_backtest_results.get("max_drawdown", 0),
                win_rate=final_backtest_results.get("win_rate", 0),
                total_trades=final_backtest_results.get("total_trades", 0),
                profit_factor=final_backtest_results.get("profit_factor", 0),
                notes="Final backtest after hyperopt"
            )
            
            # Link the results
            run_id = f"bhb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{strategy_name}_{symbol}"
            self.results_tracker.link_hyperopt_and_backtest(
                run_id=run_id,
                strategy_name=strategy_name,
                symbol=symbol,
                hyperopt_result_id=hyperopt_id,
                backtest_result_id=final_bt_id,
                workflow_type="backtest_hyperopt_backtest"
            )
            
            # Step 5: Compare results and provide insights
            comparison = self._compare_backtest_results(
                initial_backtest_results,
                final_backtest_results
            )
            
            workflow_result["comparison"] = comparison
            workflow_result["final_parameters"] = opt_results["best_params"]
            
            self.logger.info(f"Workflow completed for {strategy_name} {symbol}, "
                           f"improvement: {comparison.get('improvement_percentage', 0):.2f}%")
            
            return workflow_result
            
        except Exception as e:
            self.logger.error(f"Error in backtest → hyperopt → backtest workflow: {e}")
            workflow_result["error"] = str(e)
            workflow_result["status"] = "failed"
            return workflow_result
    
    def automated_pipeline_workflow(self,
                                  strategy_name: str,
                                  symbols: List[str],
                                  timeframe: str = "1h",
                                  pipeline_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a fully automated pipeline workflow for multiple symbols.
        
        This workflow:
        1. For each symbol, runs either hyperopt → backtest → decision
        2. Or backtest → hyperopt → backtest, depending on configuration
        3. Collects and aggregates results
        """
        self.logger.info(f"Starting automated pipeline for {strategy_name} on {len(symbols)} symbols")
        
        pipeline_result = {
            "workflow": "automated_pipeline",
            "strategy": strategy_name,
            "symbols": symbols,
            "timestamp": datetime.now().isoformat(),
            "individual_results": {},
            "aggregated_results": {},
            "summary": {}
        }
        
        successful_runs = 0
        failed_runs = 0
        
        for symbol in symbols:
            try:
                # Determine which workflow to run based on config
                workflow_type = pipeline_config.get("workflow_type", "hyperopt_backtest_decision")
                
                if workflow_type == "backtest_hyperopt_backtest":
                    result = self.backtest_hyperopt_backtest_workflow(
                        strategy_name=strategy_name,
                        symbol=symbol,
                        timeframe=timeframe,
                        initial_parameters=pipeline_config.get("initial_parameters"),
                        hyperopt_config=pipeline_config.get("hyperopt_config"),
                        backtest_config=pipeline_config.get("backtest_config")
                    )
                else:
                    result = self.hyperopt_backtest_decision_workflow(
                        strategy_name=strategy_name,
                        symbol=symbol,
                        timeframe=timeframe,
                        hyperopt_config=pipeline_config.get("hyperopt_config"),
                        backtest_config=pipeline_config.get("backtest_config")
                    )
                
                pipeline_result["individual_results"][symbol] = result
                
                if result.get("error") is None:
                    successful_runs += 1
                else:
                    failed_runs += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing {symbol} in pipeline: {e}")
                pipeline_result["individual_results"][symbol] = {"error": str(e)}
                failed_runs += 1
        
        # Aggregate results
        pipeline_result["summary"] = {
            "total_symbols": len(symbols),
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": successful_runs / len(symbols) if symbols else 0
        }
        
        self.logger.info(f"Pipeline completed: {successful_runs} successful, {failed_runs} failed")
        
        return pipeline_result
    
    def _run_backtest_with_parameters(self,
                                    strategy_name: str,
                                    symbol: str,
                                    data: pd.DataFrame,
                                    parameters: Dict[str, Any],
                                    config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run a backtest with given parameters.
        This is a mock implementation - in reality would connect to actual backtesting system.
        """
        # Mock backtest implementation
        # In a real system, this would run the actual strategy backtest
        self.logger.info(f"Running mock backtest for {strategy_name} {symbol}")
        
        # Calculate mock performance metrics
        import numpy as np
        
        # Generate mock returns based on parameters and market data
        np.random.seed(abs(hash(symbol + strategy_name)) % (2**32))
        base_return = 0.0001  # 0.01% daily base return
        volatility = 0.02  # 2% daily volatility
        
        # Adjust based on parameters
        risk_multiplier = parameters.get('risk_per_trade', 0.02) / 0.02
        atr_multiplier = parameters.get('atr_multiplier', 2.0) / 2.0
        
        # Generate mock returns
        num_periods = len(data) if len(data) > 0 else 100
        returns = np.random.normal(base_return * risk_multiplier, volatility * atr_multiplier, num_periods)
        
        # Calculate backtest metrics
        total_return = np.sum(returns)
        cumulative_returns = np.cumprod(1 + returns) - 1
        final_equity = 1 + cumulative_returns[-1] if len(cumulative_returns) > 0 else 1
        
        # Sharpe ratio (risk-adjusted return)
        if np.std(returns) != 0:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(365)  # Annualized
        else:
            sharpe_ratio = 0
            
        # Max drawdown
        cumulative = np.concatenate([[0], np.cumprod(1 + returns)])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        # Win rate
        win_rate = np.sum(returns > 0) / len(returns) if len(returns) > 0 else 0
        
        # Profit factor
        gains = returns[returns > 0]
        losses = returns[returns < 0]
        profit_factor = np.sum(gains) / abs(np.sum(losses)) if np.sum(losses) != 0 else float('inf')
        
        results = {
            "total_return": float(total_return),
            "final_equity": float(final_equity),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "total_trades": len(returns),
            "parameters_used": parameters,
            "symbol": symbol,
            "strategy": strategy_name,
            "data_points": num_periods
        }
        
        self.logger.info(f"Mock backtest completed for {strategy_name} {symbol}, "
                        f"return: {total_return:.4f}, sharpe: {sharpe_ratio:.4f}")
        
        return results
    
    def _make_decision_from_results(self, 
                                  hyperopt_results: Dict[str, Any], 
                                  backtest_results: Dict[str, Any]) -> Dict[str, str]:
        """Make a decision based on hyperopt and backtest results."""
        decision = {
            "action": "none",
            "confidence": "low",
            "reasoning": [],
            "metrics": {
                "sharpe_ratio": backtest_results.get("sharpe_ratio", 0),
                "total_return": backtest_results.get("total_return", 0),
                "max_drawdown": backtest_results.get("max_drawdown", 0),
                "win_rate": backtest_results.get("win_rate", 0),
                "profit_factor": backtest_results.get("profit_factor", 0)
            }
        }
        
        # Decision logic
        sharpe = backtest_results.get("sharpe_ratio", 0)
        max_dd = backtest_results.get("max_drawdown", 0)
        win_rate = backtest_results.get("win_rate", 0)
        profit_factor = backtest_results.get("profit_factor", 0)
        
        if sharpe > 1.0 and max_dd > -0.10 and win_rate > 0.55 and profit_factor > 1.5:
            decision["action"] = "approve_for_live"
            decision["confidence"] = "high"
            decision["reasoning"].append("Strong performance metrics across all key indicators")
        elif sharpe > 0.5 and max_dd > -0.20 and win_rate > 0.50 and profit_factor > 1.3:
            decision["action"] = "approve_for_paper_trading"
            decision["confidence"] = "medium"
            decision["reasoning"].append("Acceptable performance, suitable for paper trading")
        elif sharpe > 0 and max_dd > -0.30:
            decision["action"] = "consider_with_caution"
            decision["confidence"] = "low"
            decision["reasoning"].append("Marginal performance, requires more validation")
        else:
            decision["action"] = "reject"
            decision["confidence"] = "high"
            decision["reasoning"].append("Poor performance metrics across key indicators")
        
        return decision
    
    def _compare_backtest_results(self, 
                                before_results: Dict[str, Any], 
                                after_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare before and after backtest results."""
        comparison = {
            "improvement_metrics": {},
            "percentage_changes": {},
            "absolute_changes": {}
        }
        
        metrics = ["total_return", "sharpe_ratio", "max_drawdown", "win_rate", "profit_factor"]
        
        for metric in metrics:
            before_val = before_results.get(metric, 0)
            after_val = after_results.get(metric, 0)
            
            comparison["absolute_changes"][metric] = after_val - before_val
            
            if before_val != 0:
                change_pct = ((after_val - before_val) / abs(before_val)) * 100
                comparison["percentage_changes"][metric] = change_pct
            else:
                comparison["percentage_changes"][metric] = float('inf') if after_val != 0 else 0
        
        # Calculate overall improvement
        overall_improvement = 0
        for metric in ["sharpe_ratio", "win_rate", "profit_factor"]:
            if metric in comparison["percentage_changes"]:
                # Don't include max_drawdown in positive improvement calculation (negative values)
                if metric != "max_drawdown":
                    overall_improvement += comparison["percentage_changes"][metric]
        
        comparison["improvement_percentage"] = overall_improvement / 3 if "sharpe_ratio" in before_results else 0
        comparison["improved"] = comparison["improvement_percentage"] > 0
        
        return comparison
    
    def _get_default_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Get default parameters for a strategy."""
        defaults = {
            "crypto_breakout": {
                "rsi_length": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "ema_fast": 9,
                "ema_slow": 21,
                "atr_multiplier": 2.0,
                "risk_per_trade": 0.02,
                "tp_ratio": 2.0,
                "sl_ratio": 1.0
            },
            "crypto_breakout": {
                "atr_length": 14,
                "atr_multiplier": 2.0,
                "risk_per_trade": 0.02,
                "tp_ratio": 2.5,
                "sl_ratio": 1.0
            },
            "mean_reversion": {
                "rsi_length": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "atr_multiplier": 1.5,
                "risk_per_trade": 0.015,
                "tp_ratio": 1.8,
                "sl_ratio": 1.0
            }
        }
        
        return defaults.get(strategy_name, {})


class WorkflowManager:
    """Main manager for running different workflow types."""
    
    def __init__(self, workflow: HyperoptBacktestWorkflow):
        self.workflow = workflow
        self.logger = EnhancedLogger("WorkflowManager")
    
    def run_workflow(self, 
                    workflow_type: str,
                    strategy_name: str,
                    symbol_or_symbols: str or List[str],
                    **kwargs) -> Dict[str, Any]:
        """Run a specified workflow type."""
        if workflow_type == "hyperopt_backtest_decision":
            if isinstance(symbol_or_symbols, list):
                symbol = symbol_or_symbols[0]  # Use first symbol if list provided
            else:
                symbol = symbol_or_symbols
            
            return self.workflow.hyperopt_backtest_decision_workflow(
                strategy_name=strategy_name,
                symbol=symbol,
                **kwargs
            )
        
        elif workflow_type == "backtest_hyperopt_backtest":
            if isinstance(symbol_or_symbols, list):
                symbol = symbol_or_symbols[0]  # Use first symbol if list provided
            else:
                symbol = symbol_or_symbols
            
            return self.workflow.backtest_hyperopt_backtest_workflow(
                strategy_name=strategy_name,
                symbol=symbol,
                **kwargs
            )
        
        elif workflow_type == "automated_pipeline":
            if isinstance(symbol_or_symbols, str):
                symbols = [symbol_or_symbols]  # Convert single symbol to list
            else:
                symbols = symbol_or_symbols
            
            return self.workflow.automated_pipeline_workflow(
                strategy_name=strategy_name,
                symbols=symbols,
                **kwargs
            )
        
        else:
            error_msg = f"Unknown workflow type: {workflow_type}"
            self.logger.error(error_msg)
            return {"error": error_msg}