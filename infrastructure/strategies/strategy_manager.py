"""
Strategy Manager for handling strategy lifecycle, health monitoring, and execution coordination.
This is the ONLY layer that selects strategies and deploys capital.
"""
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from domain.value_objects import Symbol
from domain.entities.signal_entities import FusedSignal, ExecutionIntent
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter, TrendFollowingStrategy, MeanReversionStrategy, VolatilityBreakoutStrategy
from shared.logger import EnhancedLogger
from infrastructure.strategies.strategy_config import StrategyConfig


class StrategyManager:
    """
    Manages multiple strategies with health monitoring and execution coordination.
    This is the ONLY layer that selects strategies and decides on capital deployment.
    """

    def __init__(self):
        self.strategies: Dict[str, BaseStrategyAdapter] = {}
        self.strategy_factories: Dict[str, Callable[[], BaseStrategyAdapter]] = {}
        self.strategy_threads: Dict[str, threading.Thread] = {}
        self.strategy_status: Dict[str, str] = {}  # 'RUNNING', 'STOPPED', 'ERROR'
        self.health_check_interval = 30  # seconds
        self.auto_restart_enabled = True
        self.logger = EnhancedLogger("StrategyManager")
        self.monitoring_active = False
        self.monitoring_thread = None

        # Register default strategies based on configuration
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register default strategies with the manager based on configuration."""
        # Define available strategies with their classes
        available_strategies = {
            'trend_following': TrendFollowingStrategy,
            'mean_reversion': MeanReversionStrategy,
            'volatility_breakout': VolatilityBreakoutStrategy
        }

        # Register strategies based on their configuration-enabled status
        for strategy_name, strategy_class in available_strategies.items():
            # Check if strategy is enabled via configuration
            if StrategyConfig.get_strategy_enabled(strategy_name):
                try:
                    strategy_instance = strategy_class()
                    self.register_strategy(strategy_name, strategy_instance)
                    self.logger.info(f"✅ Registered and enabled strategy: {strategy_name}")
                except Exception as e:
                    self.logger.error(f"❌ Failed to register strategy {strategy_name}: {e}")
            else:
                self.logger.info(f"⏭️ Skipped disabled strategy: {strategy_name}")

    def register_strategy(self, name: str, strategy: BaseStrategyAdapter,
                         factory: Optional[Callable[[], BaseStrategyAdapter]] = None):
        """Register a strategy with the manager."""
        self.strategies[name] = strategy
        if factory:
            self.strategy_factories[name] = factory
        self.strategy_status[name] = 'RUNNING'
        self.logger.info(f"Registered strategy: {name}")

    def unregister_strategy(self, name: str):
        """Unregister a strategy from the manager."""
        if name in self.strategies:
            # Stop the strategy if it's running
            strategy = self.strategies[name]
            if hasattr(strategy, 'stop'):
                try:
                    strategy.stop()
                except Exception as e:
                    self.logger.error(f"Error stopping strategy {name}: {e}")
                    
            del self.strategies[name]
        if name in self.strategy_factories:
            del self.strategy_factories[name]
        if name in self.strategy_status:
            del self.strategy_status[name]
        self.logger.info(f"Unregistered strategy: {name}")

    def start_monitoring(self):
        """Start the health monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            self.logger.info("Strategy monitoring started")

    def stop_monitoring(self):
        """Stop the health monitoring thread."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
        self.logger.info("Strategy monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop to check strategy health."""
        self.logger.info("Strategy monitoring loop started")

        while self.monitoring_active:
            try:
                self._check_all_strategies_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in strategy monitoring loop: {e}")
                time.sleep(self.health_check_interval)

    def _check_all_strategies_health(self):
        """Check health of all registered strategies."""
        for name, strategy in self.strategies.items():
            try:
                health_status = self._get_strategy_health_status(name)

                # Check if strategy is in error state
                if health_status.get('health_status') == 'ERROR':
                    self.logger.warning(f"Strategy {name} is in ERROR state")
                    self._handle_strategy_error(name, strategy)
                elif health_status.get('health_status') == 'WARNING':
                    # Check if error count is too high
                    error_count = health_status.get('error_count', 0)
                    if error_count > 5:  # Threshold for restart
                        self.logger.warning(f"Strategy {name} has {error_count} errors, restarting...")
                        self._restart_strategy(name)

                # Log strategy metrics periodically
                if health_status.get('execution_intents_count', 0) % 10 == 0:  # Every 10 execution intents
                    self.logger.info(f"Strategy {name} - Execution Intents: {health_status.get('execution_intents_count')}, "
                                   f"Errors: {health_status.get('error_count')}, "
                                   f"Status: {health_status.get('health_status')}")

            except Exception as e:
                self.logger.error(f"Error checking health for strategy {name}: {e}")
                self._handle_strategy_error(name, strategy)

    def _get_strategy_health_status(self, name: str) -> Dict[str, Any]:
        """Get health status for a specific strategy"""
        # For now, return a basic status - in a real implementation, strategies would track their own health
        return {
            'strategy_name': name,
            'health_status': 'HEALTHY',
            'execution_intents_count': 0,  # Would be tracked by the strategy
            'error_count': 0,
            'last_update': time.time()
        }

    def _handle_strategy_error(self, name: str, strategy: BaseStrategyAdapter):
        """Handle strategy errors based on configuration."""
        if self.auto_restart_enabled and name in self.strategy_factories:
            self.logger.info(f"Attempting to restart strategy: {name}")
            self._restart_strategy(name)
        else:
            self.logger.error(f"Strategy {name} failed and auto-restart is disabled")
            self.strategy_status[name] = 'ERROR'

    def _restart_strategy(self, name: str):
        """Restart a failed strategy."""
        if name not in self.strategy_factories:
            self.logger.error(f"Cannot restart strategy {name}: no factory available")
            return False

        try:
            self.logger.info(f"Restarting strategy: {name}")

            # Get the old strategy's data if needed
            old_strategy = self.strategies[name]

            # Create new instance using factory
            new_strategy = self.strategy_factories[name]()

            # Transfer any important state if needed
            # For now, we'll just replace the strategy
            self.strategies[name] = new_strategy
            self.strategy_status[name] = 'RUNNING'

            self.logger.info(f"Successfully restarted strategy: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to restart strategy {name}: {e}")
            self.strategy_status[name] = 'ERROR'
            return False

    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate a fused signal across all available strategies using evidence-competitive approach."""
        # Collect all strategy evaluations with performance attribution
        strategy_evaluations = []

        for name, strategy in self.strategies.items():
            # Check if strategy is enabled before evaluating
            if not StrategyConfig.get_strategy_enabled(name):
                continue

            try:
                intent = strategy.evaluate_fused_signal(fused_signal)
                if intent:
                    # Calculate performance attribution score for this strategy
                    performance_score = self._calculate_performance_attribution(
                        strategy, fused_signal, intent
                    )

                    strategy_evaluations.append({
                        'strategy_name': name,
                        'intent': intent,
                        'performance_score': performance_score,
                        'confidence': float(intent.intent_confidence.value),
                        'regime_compatibility': self._calculate_regime_compatibility_score(
                            name, fused_signal.regime_context
                        ),
                        'risk_adjusted_score': self._calculate_risk_adjusted_score(
                            intent, performance_score
                        )
                    })
            except Exception as e:
                self.logger.error(f"Error evaluating fused signal with strategy {name}: {e}")
                continue

        # Rank strategies based on risk-adjusted performance
        ranked_evaluations = self._rank_strategies_by_performance(strategy_evaluations)

        # Apply promotion/demotion logic based on performance
        self._apply_promotion_demotion_logic(ranked_evaluations)

        # Return the top-ranked execution intent
        if ranked_evaluations:
            top_evaluation = ranked_evaluations[0]
            self.logger.info(f"Selected strategy {top_evaluation['strategy_name']} with risk-adjusted score: {top_evaluation['risk_adjusted_score']:.3f}")
            return top_evaluation['intent']

        return None

    def _calculate_performance_attribution(self, strategy, fused_signal: FusedSignal, intent: ExecutionIntent) -> float:
        """Calculate performance attribution score for a strategy based on market conditions."""
        # Base score from intent confidence
        base_score = float(intent.intent_confidence.value)

        # Adjust for regime compatibility
        regime_factor = self._calculate_regime_compatibility_score(
            strategy.get_strategy_name(), fused_signal.regime_context
        )

        # Adjust for signal alignment with strategy type
        alignment_factor = self._calculate_signal_alignment_score(strategy, fused_signal)

        # Combine factors for final performance attribution
        performance_score = base_score * regime_factor * alignment_factor

        return performance_score

    def _calculate_regime_compatibility_score(self, strategy_name: str, regime_context: str) -> float:
        """Calculate how compatible a strategy is with the current regime."""
        # Different strategies perform differently in different regimes
        if regime_context == "trending":
            if "trend" in strategy_name.lower() or "momentum" in strategy_name.lower():
                return 1.2  # Boost trend-following strategies in trending regime
            elif "mean" in strategy_name.lower() or "reversion" in strategy_name.lower():
                return 0.7  # Reduce mean reversion in trending regime
            else:
                return 1.0  # Neutral
        elif regime_context == "mean_reverting":
            if "mean" in strategy_name.lower() or "reversion" in strategy_name.lower():
                return 1.2  # Boost mean reversion strategies
            elif "trend" in strategy_name.lower() or "momentum" in strategy_name.lower():
                return 0.7  # Reduce trend-following in mean reverting regime
            else:
                return 1.0  # Neutral
        elif regime_context == "volatile":
            # In volatile markets, conservative strategies might perform better
            if "breakout" in strategy_name.lower():
                return 1.1  # Breakout strategies might work in volatile markets
            else:
                return 0.9  # Reduce aggressive strategies
        elif regime_context == "choppy":
            # In choppy markets, range-bound strategies might work better
            if "range" in strategy_name.lower() or "scalp" in strategy_name.lower():
                return 1.1
            else:
                return 0.8  # Reduce trend-following in choppy markets
        else:
            # Default for other regimes
            return 1.0

    def _calculate_signal_alignment_score(self, strategy, fused_signal: FusedSignal) -> float:
        """Calculate how well a strategy aligns with the fused signal."""
        # Get strategy's directional preference
        strategy_type = strategy.get_strategy_type().lower()

        # Check if signal direction aligns with strategy preference
        signal_direction = fused_signal.direction
        if signal_direction > 0.1 and ('long' in strategy_type or 'buy' in strategy_type or 'trend' in strategy_type):
            return 1.1  # Good alignment
        elif signal_direction < -0.1 and ('short' in strategy_type or 'sell' in strategy_type or 'bear' in strategy_type):
            return 1.1  # Good alignment
        elif abs(signal_direction) < 0.1:  # Neutral signal
            # Conservative strategies might be better for neutral signals
            if 'conservative' in strategy_type or 'balanced' in strategy_type:
                return 1.1
            else:
                return 0.9  # Slightly reduce for directional strategies on neutral signals
        else:
            return 0.9  # Slight penalty for misalignment

    def _calculate_risk_adjusted_score(self, intent: ExecutionIntent, performance_score: float) -> float:
        """Calculate risk-adjusted score for an execution intent."""
        # Get risk parameters from the intent
        risk_params = intent.risk_parameters

        # Calculate risk-adjusted score based on risk parameters
        risk_factor = 1.0

        # Adjust for stop loss distance (tighter stops = higher risk)
        if 'stop_loss_pct' in risk_params:
            stop_loss_pct = risk_params['stop_loss_pct']
            if stop_loss_pct < 0.01:  # Very tight stops
                risk_factor *= 0.8
            elif stop_loss_pct > 0.05:  # Very wide stops
                risk_factor *= 0.9  # Wide stops might indicate poor risk management

        # Adjust for position size relative to account
        if 'max_position_size' in risk_params:
            pos_size = risk_params['max_position_size']
            if pos_size > 0.1:  # Large position size
                risk_factor *= 0.9
            elif pos_size < 0.01:  # Very small position
                risk_factor *= 0.95  # Might be overly conservative

        # Combine performance score with risk adjustment
        risk_adjusted_score = performance_score * risk_factor

        return risk_adjusted_score

    def _rank_strategies_by_performance(self, evaluations: List[Dict]) -> List[Dict]:
        """Rank strategies based on their performance scores."""
        # Sort by risk-adjusted score in descending order
        sorted_evaluations = sorted(
            evaluations,
            key=lambda x: x['risk_adjusted_score'],
            reverse=True
        )

        # Log the ranking for transparency
        self.logger.info("Strategy rankings:")
        for i, eval_item in enumerate(sorted_evaluations):
            self.logger.info(f"  {i+1}. {eval_item['strategy_name']}: "
                           f"Performance={eval_item['performance_score']:.3f}, "
                           f"Risk-Adjusted={eval_item['risk_adjusted_score']:.3f}")

        return sorted_evaluations

    def _apply_promotion_demotion_logic(self, ranked_evaluations: List[Dict]):
        """Apply promotion/demotion/suspension rules based on strategy performance."""
        if not ranked_evaluations:
            return

        # Get the top performing strategy
        top_strategy = ranked_evaluations[0]['strategy_name']
        top_score = ranked_evaluations[0]['risk_adjusted_score']

        # Get the bottom performing strategy
        bottom_strategy = ranked_evaluations[-1]['strategy_name']
        bottom_score = ranked_evaluations[-1]['risk_adjusted_score']

        # Promotion logic: if top strategy significantly outperforms others, consider promoting
        if len(ranked_evaluations) > 1:
            second_best_score = ranked_evaluations[1]['risk_adjusted_score']
            performance_gap = top_score - second_best_score

            if performance_gap > 0.2:  # Significant performance gap
                self.logger.info(f"Promoting strategy {top_strategy} due to superior performance gap: {performance_gap:.3f}")
                # In a real system, this might increase the strategy's allocation or priority

        # Demotion/suspension logic: if bottom strategy significantly underperforms, consider demoting
        if len(ranked_evaluations) > 1 and bottom_score < 0.3:  # Poor performance threshold
            self.logger.info(f"Considering suspension for strategy {bottom_strategy} due to poor performance: {bottom_score:.3f}")
            # In a real system, this might reduce allocation or temporarily suspend the strategy

    def get_active_strategies(self) -> List[str]:
        """Get list of active strategy names."""
        active_strategies = []
        for name, strategy in self.strategies.items():
            if StrategyConfig.get_strategy_enabled(name):
                active_strategies.append(name)
        return active_strategies

    def add_strategy(self, strategy: BaseStrategyAdapter):
        """Add a strategy to the manager."""
        name = strategy.get_strategy_name()
        # Check if strategy is enabled before adding
        if StrategyConfig.get_strategy_enabled(name):
            self.register_strategy(name, strategy)
        else:
            self.logger.info(f"Skipped adding disabled strategy: {name}")

    def get_all_health_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all strategies."""
        statuses = {}
        for name in self.strategies.keys():
            try:
                statuses[name] = self._get_strategy_health_status(name)
            except Exception as e:
                self.logger.error(f"Error getting health status for strategy {name}: {e}")
                statuses[name] = {
                    'strategy_name': name,
                    'health_status': 'ERROR',
                    'error': str(e)
                }
        return statuses

    def get_strategy_performance(self, name: str) -> Dict[str, Any]:
        """Get performance metrics for a specific strategy."""
        if name not in self.strategies:
            return {}

        try:
            return self._get_strategy_health_status(name)
        except Exception as e:
            self.logger.error(f"Error getting performance for strategy {name}: {e}")
            return {}

    def is_strategy_healthy(self, name: str) -> bool:
        """Check if a specific strategy is healthy."""
        if name not in self.strategies:
            return False

        try:
            health_status = self._get_strategy_health_status(name)
            return health_status.get('health_status') == 'HEALTHY'
        except Exception:
            return False

    def enable_strategy(self, strategy_name: str) -> bool:
        """Enable a strategy dynamically."""
        try:
            # Update environment variable to persist the change
            import os
            os.environ[f"{strategy_name.upper()}_STRATEGY_ENABLED"] = "true"
            
            # If the strategy isn't already registered and is now enabled, register it
            if strategy_name not in self.strategies:
                strategy_class_map = {
                    'trend_following': TrendFollowingStrategy,
                    'mean_reversion': MeanReversionStrategy,
                    'volatility_breakout': VolatilityBreakoutStrategy
                }
                
                if strategy_name in strategy_class_map:
                    strategy_class = strategy_class_map[strategy_name]
                    strategy_instance = strategy_class()
                    self.register_strategy(strategy_name, strategy_instance)
                    self.logger.info(f"✅ Dynamically enabled and registered strategy: {strategy_name}")
            
            self.logger.info(f"✅ Strategy enabled: {strategy_name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to enable strategy {strategy_name}: {e}")
            return False

    def disable_strategy(self, strategy_name: str) -> bool:
        """Disable a strategy dynamically."""
        try:
            # Update environment variable to persist the change
            import os
            os.environ[f"{strategy_name.upper()}_STRATEGY_ENABLED"] = "false"
            
            # If the strategy is currently registered, unregister it
            if strategy_name in self.strategies:
                self.unregister_strategy(strategy_name)
                self.logger.info(f"✅ Strategy unregistered and disabled: {strategy_name}")
            else:
                self.logger.info(f"✅ Strategy disabled (was not registered): {strategy_name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to disable strategy {strategy_name}: {e}")
            return False

    def get_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific strategy."""
        # Return configuration based on the StrategyConfig system
        return {
            'name': strategy_name,
            'enabled': StrategyConfig.get_strategy_enabled(strategy_name),
            'max_position_size': StrategyConfig.get_strategy_max_position_size(strategy_name, 0.05),
            'min_confidence': StrategyConfig.get_strategy_min_confidence(strategy_name, 0.3),
            'max_confidence': StrategyConfig.get_strategy_max_confidence(strategy_name, 0.95),
            'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade(strategy_name, 0.02),
            'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier(strategy_name, 1.5),
            'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier(strategy_name, 2.0),
            'lookback_period': StrategyConfig.get_strategy_lookback_period(strategy_name, 50),
            'timeframe': StrategyConfig.get_strategy_timeframe(strategy_name, '1h')
        }

    def update_strategy_config(self, strategy_name: str, **kwargs) -> bool:
        """Update configuration for a specific strategy."""
        try:
            # For now, we can only update environment variables
            for key, value in kwargs.items():
                if key == 'enabled':
                    import os
                    env_key = f"{strategy_name.upper()}_STRATEGY_ENABLED"
                    os.environ[env_key] = str(value).lower()
                    if value and strategy_name not in self.strategies:
                        # If enabling and not registered, register it
                        self.enable_strategy(strategy_name)
                    elif not value and strategy_name in self.strategies:
                        # If disabling and registered, unregister it
                        self.disable_strategy(strategy_name)
            self.logger.info(f"✅ Updated configuration for strategy: {strategy_name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to update strategy {strategy_name} config: {e}")
            return False

    def get_all_strategies_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all strategies (enabled/disabled)."""
        all_strategy_names = ['trend_following', 'mean_reversion', 'volatility_breakout']
        status_report = {}
        
        for name in all_strategy_names:
            is_registered = name in self.strategies
            status_report[name] = {
                'enabled': StrategyConfig.get_strategy_enabled(name),
                'is_registered': is_registered,
                'status': self.strategy_status.get(name, 'NOT_REGISTERED'),
                'last_updated': datetime.now().isoformat()
            }
        
        return status_report


# Global strategy manager instance
strategy_manager = StrategyManager()