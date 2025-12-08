"""Advanced retuning system with schedule-based and performance-based triggers."""

import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Callable, Optional
from pathlib import Path
import pandas as pd
import time

from shared.logger import EnhancedLogger
from infrastructure.results_tracking.results_tracker import ResultsTracker


class RetuningScheduler:
    """Scheduler for managing when retuning should occur."""
    
    def __init__(self, 
                 results_tracker: ResultsTracker,
                 schedule_config: Dict[str, Any] = None):
        self.results_tracker = results_tracker
        self.schedule_config = schedule_config or self._default_schedule_config()
        self.logger = EnhancedLogger("RetuningScheduler")
        self.scheduled_tasks = {}
        self.running = False
        
    def _default_schedule_config(self) -> Dict[str, Any]:
        """Default schedule configuration."""
        return {
            "daily_retuning_enabled": True,
            "weekly_retuning_enabled": True,
            "monthly_retuning_enabled": True,
            "daily_time": "02:00",  # 2 AM UTC
            "weekly_day": "Sunday",  # Day of week for weekly retune
            "monthly_day": 1,        # Day of month for monthly retune
            "minimum_performance_check_interval": 3600,  # Every hour
        }
    
    def start_schedule_monitoring(self):
        """Start monitoring for scheduled retuning events."""
        self.running = True
        self.logger.info("Started schedule monitoring for retuning")
        
        # In a real implementation, this would run a background thread
        # For now, we'll just log that monitoring has started
        self._monitor_schedule()
    
    def stop_schedule_monitoring(self):
        """Stop monitoring for scheduled retuning events."""
        self.running = False
        self.logger.info("Stopped schedule monitoring for retuning")
    
    def _monitor_schedule(self):
        """Internal method to check for scheduled events."""
        # This would run in a background thread in a real implementation
        pass
    
    def check_scheduled_retuning(self, strategy_name: str, symbol: str) -> bool:
        """Check if scheduled retuning is needed for a strategy/symbol."""
        # Check daily schedule
        if self.schedule_config.get("daily_retuning_enabled", False):
            last_run = self._get_last_run_time(strategy_name, symbol, "daily")
            if last_run is None or (datetime.now() - last_run) >= timedelta(days=1):
                if self._should_run_daily_retuning(strategy_name, symbol):
                    return True
        
        # Check weekly schedule
        if self.schedule_config["weekly_retuning_enabled"]:
            last_run = self._get_last_run_time(strategy_name, symbol, "weekly")
            if last_run is None or (datetime.now() - last_run) >= timedelta(days=7):
                if self._should_run_weekly_retuning(strategy_name, symbol):
                    return True
        
        # Check monthly schedule
        if self.schedule_config["monthly_retuning_enabled"]:
            last_run = self._get_last_run_time(strategy_name, symbol, "monthly")
            if last_run is None or (datetime.now() - last_run) >= timedelta(days=30):
                if self._should_run_monthly_retuning(strategy_name, symbol):
                    return True
        
        return False
    
    def _get_last_run_time(self, strategy_name: str, symbol: str, run_type: str) -> Optional[datetime]:
        """Get the last time a specific type of retuning was performed."""
        # This would query the results tracker for last run times
        # For now, we'll return a basic implementation
        return None
    
    def _should_run_daily_retuning(self, strategy_name: str, symbol: str) -> bool:
        """Determine if daily retuning should run."""
        # Check if it's the right time of day
        current_time = datetime.now().strftime("%H:%M")
        if current_time != self.schedule_config["daily_time"]:
            return False
        
        # Additional logic for daily retuning could go here
        return True
    
    def _should_run_weekly_retuning(self, strategy_name: str, symbol: str) -> bool:
        """Determine if weekly retuning should run."""
        current_weekday = datetime.now().strftime("%A")
        if current_weekday != self.schedule_config["weekly_day"]:
            return False
        
        return True
    
    def _should_run_monthly_retuning(self, strategy_name: str, symbol: str) -> bool:
        """Determine if monthly retuning should run."""
        current_day = datetime.now().day
        if current_day != self.schedule_config["monthly_day"]:
            return False
        
        return True


class PerformanceBasedRetuner:
    """Class for triggering retuning based on performance degradation."""

    def __init__(self,
                 results_tracker: ResultsTracker,
                 performance_config: Dict[str, Any] = None):
        self.results_tracker = results_tracker
        self.performance_config = performance_config or self._default_performance_config()
        self.logger = EnhancedLogger("PerformanceBasedRetuner")
        self.performance_history = {}

    def get_optimizable_params(self) -> Dict[str, Any]:
        """Get the current performance parameters that can be optimized."""
        return {
            'sharpe_ratio_threshold': self.performance_config.get('sharpe_ratio_threshold'),
            'max_drawdown_threshold': self.performance_config.get('max_drawdown_threshold'),
            'win_rate_threshold': self.performance_config.get('win_rate_threshold'),
            'profit_factor_threshold': self.performance_config.get('profit_factor_threshold'),
            'consecutive_loss_threshold': self.performance_config.get('consecutive_loss_threshold'),
            'performance_window': self.performance_config.get('performance_window'),
            'min_trades_for_evaluation': self.performance_config.get('min_trades_for_evaluation'),
            'performance_threshold': self.performance_config.get('performance_threshold'),
            'retune_check_interval': self.performance_config.get('retune_check_interval'),
            'max_evals_per_retune': self.performance_config.get('max_evals_per_retune'),
        }

    def update_from_params(self, params: Dict[str, Any]):
        """Update performance parameters from optimization results."""
        self.performance_config['sharpe_ratio_threshold'] = params.get('sharpe_ratio_threshold',
            self.performance_config.get('sharpe_ratio_threshold'))
        self.performance_config['max_drawdown_threshold'] = params.get('max_drawdown_threshold',
            self.performance_config.get('max_drawdown_threshold'))
        self.performance_config['win_rate_threshold'] = params.get('win_rate_threshold',
            self.performance_config.get('win_rate_threshold'))
        self.performance_config['profit_factor_threshold'] = params.get('profit_factor_threshold',
            self.performance_config.get('profit_factor_threshold'))
        self.performance_config['consecutive_loss_threshold'] = params.get('consecutive_loss_threshold',
            self.performance_config.get('consecutive_loss_threshold'))
        self.performance_config['performance_window'] = params.get('performance_window',
            self.performance_config.get('performance_window'))
        self.performance_config['min_trades_for_evaluation'] = params.get('min_trades_for_evaluation',
            self.performance_config.get('min_trades_for_evaluation'))
        self.performance_config['performance_threshold'] = params.get('performance_threshold',
            self.performance_config.get('performance_threshold'))
        self.performance_config['retune_check_interval'] = params.get('retune_check_interval',
            self.performance_config.get('retune_check_interval'))
        self.performance_config['max_evals_per_retune'] = params.get('max_evals_per_retune',
            self.performance_config.get('max_evals_per_retune'))
    
    def _default_performance_config(self) -> Dict[str, Any]:
        """Default performance configuration."""
        return {
            "sharpe_ratio_threshold": 0.15,      # Retune if sharpe drops below this
            "max_drawdown_threshold": -0.15,     # Retune if drawdown exceeds this
            "win_rate_threshold": 0.40,          # Retune if win rate drops below this
            "profit_factor_threshold": 1.3,      # Retune if profit factor drops below this
            "consecutive_loss_threshold": 5,     # Retune after X consecutive losses
            "performance_window": 20,            # Look at last N trades
            "min_trades_for_evaluation": 10,     # Minimum trades before evaluation
            "performance_threshold": -0.1,       # Performance threshold that triggers retuning
            "retune_check_interval": 3600,       # Interval in seconds to check performance
            "max_evals_per_retune": 50,          # Maximum evaluations per retuning session
        }
    
    def should_trigger_retuning(self, 
                              strategy_name: str, 
                              symbol: str,
                              current_performance: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Check if retuning should be triggered based on performance metrics.
        
        Returns a dictionary of reasons why retuning should be triggered.
        """
        reasons = {}
        
        if current_performance:
            # Check specific performance metrics
            if 'sharpe_ratio' in current_performance:
                if current_performance.get('sharpe_ratio', 0) < self.performance_config.get('sharpe_ratio_threshold', 0.5):
                    reasons['sharpe_ratio'] = (
                        f"Sharpe ratio {current_performance['sharpe_ratio']} "
                        f"below threshold {self.performance_config['sharpe_ratio_threshold']}"
                    )
            
            if 'max_drawdown' in current_performance:
                if current_performance['max_drawdown'] < self.performance_config['max_drawdown_threshold']:
                    reasons['max_drawdown'] = (
                        f"Max drawdown {current_performance['max_drawdown']} "
                        f"exceeds threshold {self.performance_config['max_drawdown_threshold']}"
                    )
            
            if 'win_rate' in current_performance:
                if current_performance['win_rate'] < self.performance_config['win_rate_threshold']:
                    reasons['win_rate'] = (
                        f"Win rate {current_performance['win_rate']} "
                        f"below threshold {self.performance_config['win_rate_threshold']}"
                    )
            
            if 'profit_factor' in current_performance:
                if current_performance['profit_factor'] < self.performance_config['profit_factor_threshold']:
                    reasons['profit_factor'] = (
                        f"Profit factor {current_performance['profit_factor']} "
                        f"below threshold {self.performance_config['profit_factor_threshold']}"
                    )
        
        # If no current performance provided, get it from recent results
        if not current_performance:
            recent_result = self.results_tracker.get_backtest_results(
                strategy_name=strategy_name, 
                symbol=symbol, 
                limit=1
            )
            
            if recent_result:
                recent = recent_result[0]
                reasons.update(self.should_trigger_retuning(strategy_name, symbol, {
                    'sharpe_ratio': recent.get('sharpe_ratio'),
                    'max_drawdown': recent.get('max_drawdown'),
                    'win_rate': recent.get('win_rate'),
                    'profit_factor': recent.get('profit_factor')
                }))
        
        return reasons
    
    def update_performance_history(self, 
                                 strategy_name: str, 
                                 symbol: str, 
                                 performance_metrics: Dict[str, Any]):
        """Update performance history for tracking degradation."""
        key = f"{strategy_name}_{symbol}"
        
        if key not in self.performance_history:
            self.performance_history[key] = []
        
        # Add the full performance record
        self.performance_history[key].append({
            'timestamp': datetime.now(),
            'metrics': performance_metrics
        })
        
        # Keep only recent history
        max_history = self.performance_config['performance_window'] * 2  # Keep extra for analysis
        if len(self.performance_history[key]) > max_history:
            self.performance_history[key] = self.performance_history[key][-max_history:]
    
    def analyze_performance_trend(self, strategy_name: str, symbol: str) -> str:
        """Analyze performance trend to predict when retuning might be needed."""
        key = f"{strategy_name}_{symbol}"
        
        if key not in self.performance_history or len(self.performance_history[key]) < 3:
            return "insufficient_data"
        
        history = self.performance_history[key]
        latest_metrics = history[-1]['metrics']
        previous_metrics = history[-2]['metrics']
        
        # Check if key metrics are degrading
        degrading_metrics = []
        
        for metric in ['sharpe_ratio', 'win_rate', 'profit_factor']:
            if metric in latest_metrics and metric in previous_metrics:
                if latest_metrics[metric] < previous_metrics[metric] * 0.95:  # 5% degradation
                    degrading_metrics.append(metric)
        
        if len(degrading_metrics) >= 2:
            return "degrading"
        elif degrading_metrics:
            return "slightly_degrading"
        else:
            return "stable"


class ManualRetuningTrigger:
    """Class for handling manual retuning requests."""
    
    def __init__(self, results_tracker: ResultsTracker):
        self.results_tracker = results_tracker
        self.logger = EnhancedLogger("ManualRetuningTrigger")
        self.manual_requests = []
    
    def request_manual_retuning(self, 
                              strategy_name: str, 
                              symbol: str, 
                              reason: str = "manual_request",
                              priority: str = "normal") -> str:
        """Request manual retuning for a strategy/symbol."""
        request_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{strategy_name}_{symbol}"
        
        request = {
            "request_id": request_id,
            "strategy_name": strategy_name,
            "symbol": symbol,
            "reason": reason,
            "priority": priority,
            "timestamp": datetime.now(),
            "status": "pending"
        }
        
        self.manual_requests.append(request)
        self.logger.info(f"Manual retuning requested: {request_id} for {strategy_name} {symbol}")
        
        return request_id
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending manual retuning requests."""
        return [req for req in self.manual_requests if req['status'] == 'pending']
    
    def approve_request(self, request_id: str) -> bool:
        """Approve a manual retuning request."""
        for req in self.manual_requests:
            if req['request_id'] == request_id:
                req['status'] = 'approved'
                self.logger.info(f"Approved manual retuning request: {request_id}")
                return True
        return False
    
    def reject_request(self, request_id: str, reason: str = "not_approved") -> bool:
        """Reject a manual retuning request."""
        for req in self.manual_requests:
            if req['request_id'] == request_id:
                req['status'] = 'rejected'
                req['rejection_reason'] = reason
                self.logger.info(f"Rejected manual retuning request: {request_id}, reason: {reason}")
                return True
        return False


class AdaptiveRetuningManager:
    """
    Main manager that coordinates all retuning triggers:
    - Schedule-based retuning
    - Performance-based retuning
    - Manual retuning requests
    """

    def __init__(self,
                 results_tracker: ResultsTracker,
                 schedule_config: Dict[str, Any] = None,
                 performance_config: Dict[str, Any] = None):
        self.results_tracker = results_tracker
        self.schedule_manager = RetuningScheduler(results_tracker, schedule_config)
        self.performance_manager = PerformanceBasedRetuner(results_tracker, performance_config)
        self.manual_trigger = ManualRetuningTrigger(results_tracker)
        self.logger = EnhancedLogger("AdaptiveRetuningManager")

        # Threading locks for thread safety
        self._retuning_lock = threading.RLock()
        self._history_lock = threading.RLock()

        # Track when last retuning was performed
        self.last_retuning_times = {}
    
    def should_retune(self,
                     strategy_name: str,
                     symbol: str,
                     current_performance: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Determine if retuning should be performed based on all trigger mechanisms.

        Returns a dictionary with trigger information.
        """
        with self._retuning_lock:  # Use lock to protect this method from race conditions
            response = {
                "should_retune": False,
                "triggers": {
                    "scheduled": False,
                    "performance_based": False,
                    "manual": False
                },
                "reasons": [],
                "next_check_in": None  # How long to wait before checking again
            }

            # Check scheduled retuning
            if self.schedule_manager.check_scheduled_retuning(strategy_name, symbol):
                response["triggers"]["scheduled"] = True
                response["reasons"].append("Scheduled retuning due")
                response["should_retune"] = True

            # Check performance-based triggers
            performance_triggers = self.performance_manager.should_trigger_retuning(
                strategy_name, symbol, current_performance
            )

            if performance_triggers:
                response["triggers"]["performance_based"] = True
                response["reasons"].extend(list(performance_triggers.values()))
                response["should_retune"] = True

            # Check manual requests
            key = f"{strategy_name}_{symbol}"
            for req in self.manual_trigger.get_pending_requests():
                if req['strategy_name'] == strategy_name and req['symbol'] == symbol:
                    if req['status'] == 'approved':
                        response["triggers"]["manual"] = True
                        response["reasons"].append(f"Manual request: {req['reason']}")
                        response["should_retune"] = True

            # Check if enough time has passed since last retuning
            with self._history_lock:  # Use history lock to protect access to last_retuning_times
                last_retune = self.last_retuning_times.get(key)
                if last_retune:
                    min_interval = timedelta(hours=1)  # Minimum interval between retuning
                    if datetime.now() - last_retune < min_interval:
                        response["should_retune"] = False
                        response["reasons"].append("Minimum interval not reached since last retuning")

            return response
    
    def execute_retuning(self,
                        strategy_name: str,
                        symbol: str,
                        data: pd.DataFrame = None,
                        custom_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the retuning process for a strategy/symbol.

        Returns the results of the optimization.
        """
        with self._retuning_lock:  # Use lock for thread safety
            self.logger.info(f"Starting retuning for {strategy_name} on {symbol}")

            # In a real implementation, this would call the hyperopt system
            # For now, we'll return a mock result
            result = {
                "status": "completed",
                "strategy": strategy_name,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "new_parameters": self._get_mock_parameters(),
                "optimization_method": "adaptive_retuning"
            }

            # Update the last retuning time
            key = f"{strategy_name}_{symbol}"
            with self._history_lock:  # Use history lock to protect access to last_retuning_times
                self.last_retuning_times[key] = datetime.now()

            # Save the result to the tracker
            self.results_tracker.save_hyperopt_result(
                strategy_name=strategy_name,
                symbol=symbol,
                parameters=result["new_parameters"],
                best_value=-0.12,  # Mock value
                trials_completed=50,
                optimization_objective="sharpe_ratio",
                notes="Adaptive retuning execution"
            )

            self.logger.info(f"Completed retuning for {strategy_name} on {symbol}")
            return result
    
    def _get_mock_parameters(self) -> Dict[str, Any]:
        """Generate mock parameters for testing."""
        return {
            "rsi_length": 14,
            "ema_fast": 9,
            "ema_slow": 21,
            "atr_multiplier": 2.0,
            "risk_per_trade": 0.02,
            "tp_ratio": 2.0,
            "sl_ratio": 1.0
        }
    
    def get_retuning_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for which strategy/symbol pairs should be retuned."""
        recommendations = []
        
        # In a real implementation, this would analyze all tracked strategies
        # For now, we'll return a simple mock implementation
        return recommendations
    
    def start_automatic_monitoring(self, check_interval: int = 3600):
        """
        Start automatic monitoring for retuning opportunities.
        
        Args:
            check_interval: Interval in seconds between checks
        """
        def monitoring_loop():
            self.logger.info("Started automatic retuning monitoring")
            while True:
                # Get all unique strategy/symbol pairs from results
                # This would normally come from the results tracker
                strategy_symbol_pairs = self._get_tracked_pairs()
                
                for strategy, symbol in strategy_symbol_pairs:
                    try:
                        needs_retuning = self.should_retune(strategy, symbol)
                        if needs_retuning["should_retune"]:
                            self.logger.info(f"Retuning needed for {strategy} {symbol}: "
                                           f"{', '.join(needs_retuning['reasons'])}")
                    except Exception as e:
                        self.logger.error(f"Error checking retuning for {strategy} {symbol}: {e}")
                
                # Sleep for the check interval
                time.sleep(check_interval)
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitor_thread.start()
        
        return monitor_thread
    
    def _get_tracked_pairs(self) -> List[tuple]:
        """Get all strategy/symbol pairs that are being tracked."""
        # This would normally query the results tracker for all unique pairs
        # For mock purposes:
        return [("crypto_breakout", "BTC/USDT"), ("mean_reversion", "ETH/USDT")]