"""Hyperopt objective function implementation following hexagonal architecture."""

import numpy as np
from typing import Dict, Any, List, Callable
import pandas as pd
from datetime import datetime

from shared.logger import EnhancedLogger
from infrastructure.optimization.hyperopt_space import parameter_space
from infrastructure.backtest.realistic_backtester import RealisticBacktester
from hyperopt import fmin, tpe, rand, anneal, Trials, STATUS_OK
from domain.ports.engine_ports import StrategyPort
from domain.entities.trading_entities import SignalType


class HyperoptObjective:
    """Objective function for hyperopt optimization."""

    def __init__(self):
        self.logger = EnhancedLogger("HyperoptObjective")

    def create_objective_function(self,
                                 data_dict: Dict[str, pd.DataFrame],
                                 risk_config: Dict[str, Any],
                                 strategy_or_strategy_function=None,
                                 optimization_objectives: List[str] = None):
        """
        Create an objective function for hyperopt with the given data and risk config.

        Args:
            data_dict: Dictionary of asset data {'XAUUSD': df, 'BTCUSD': df, ...}
            risk_config: Risk configuration parameters
            strategy_or_strategy_function: Either a strategy instance or a strategy function
            optimization_objectives: List of objectives to optimize (e.g., ['sharpe_ratio', 'max_drawdown'])
        """
        if not optimization_objectives:
            optimization_objectives = ['sharpe_ratio']  # Default single objective

        def objective(params: Dict[str, Any]) -> Dict[str, Any]:
            """
            Objective function that hyperopt will minimize.
            """
            try:
                # Calculate total score across all assets using backtesting
                total_scores = {}

                # Initialize scores for all objectives
                for obj in optimization_objectives:
                    total_scores[obj] = 0

                for asset_name, df in data_dict.items():
                    # Run backtest for this asset with the given parameters
                    metrics = self._calculate_metrics_for_asset(params, df, risk_config, strategy_or_strategy_function)

                    # Add metrics to total scores
                    for obj in optimization_objectives:
                        if obj in metrics:
                            total_scores[obj] += metrics[obj]

                # For multi-objective optimization, we can combine objectives or return individual scores
                # For single objective, we just return that value
                if len(optimization_objectives) == 1:
                    primary_objective = optimization_objectives[0]
                    primary_score = total_scores.get(primary_objective, 0)
                    loss = -primary_score  # Hyperopt minimizes, so we negate for maximization
                else:
                    # For multiple objectives, we can create a weighted combination
                    # This is a simple approach - more sophisticated methods could be used
                    combined_score = 0
                    weights = {obj: 1.0/len(optimization_objectives) for obj in optimization_objectives}

                    for obj in optimization_objectives:
                        obj_score = total_scores.get(obj, 0)
                        combined_score += weights[obj] * obj_score

                    loss = -combined_score

                return {
                    "loss": loss,
                    "status": "ok",
                    "eval_time": datetime.now().timestamp()
                }

            except Exception as e:
                self.logger.error(f"Error in hyperopt objective: {e}")
                return {"loss": float("inf"), "status": "error"}

        return objective

    def _calculate_metrics_for_asset(self, params: Dict[str, Any], df: pd.DataFrame, risk_config: Dict[str, Any], strategy_or_strategy_function=None) -> Dict[str, Any]:
        """
        Calculate performance metrics for a single asset by running a backtest with the given parameters.
        Returns a dictionary of metrics to support multi-objective optimization.
        """
        try:
            if len(df) < 2:
                return {"sharpe_ratio": 0, "total_return": 0, "max_drawdown": 0, "win_rate": 0, "profit_factor": 0}

            # Initialize backtester with risk config
            initial_capital = risk_config.get('initial_capital', 10000.0)
            fee_rate = risk_config.get('fee_rate', 0.001)
            slippage_factor = risk_config.get('slippage_factor', 0.0005)

            backtester = RealisticBacktester(
                initial_capital=initial_capital,
                fee_rate=fee_rate,
                slippage_factor=slippage_factor
            )

            # Determine if we have a strategy class or a function (same as in _calculate_score_for_asset)
            if strategy_or_strategy_function is None:
                # Default to a simple strategy function
                def default_strategy(row, strategy_params):
                    # Example signal function using RSI
                    rsi = row.get('rsi', 50)
                    rsi_oversold = strategy_params.get('rsi_oversold', 30)
                    rsi_overbought = strategy_params.get('rsi_overbought', 70)

                    if rsi < rsi_oversold:
                        return 1  # Buy
                    elif rsi > rsi_overbought:
                        return -1  # Sell
                    else:
                        return 0  # Hold
                strategy_function = default_strategy
                strategy_params = params
            elif hasattr(strategy_or_strategy_function, '__class__') and hasattr(strategy_or_strategy_function.__class__, 'generate_signal'):
                # It's likely a strategy instance, create a wrapper function
                strategy = strategy_or_strategy_function
                def strategy_function(row, strategy_params):
                    # Create a simple data point from the row
                    # In the actual system, we might need to convert pandas row to Symbol
                    # For now, we'll create a minimal signal generation approach
                    # since the StrategyPort interface uses Symbol and Signal objects
                    from domain.value_objects import Symbol
                    symbol = Symbol('BTC-USDT')  # Use proper symbol format

                    # Update strategy with market data first
                    market_data = {
                        'close': row.get('close', 0),
                        'open': row.get('open', 0),
                        'high': row.get('high', 0),
                        'low': row.get('low', 0),
                        'volume': row.get('volume', 0),
                        'rsi': row.get('rsi', 50),  # Assuming indicators exist
                        'sma_20': row.get('sma_20', 0),
                        'sma_50': row.get('sma_50', 0),
                        'atr': row.get('atr', 0),
                        'timestamp': row.get('timestamp', None),
                        # Add other indicators as needed
                    }
                    if hasattr(strategy, 'update_with_market_data'):
                        strategy.update_with_market_data(market_data)

                    # Generate signal using the StrategyPort interface
                    signal = strategy.generate_signal(symbol)
                    if signal is None:
                        return 0  # No signal = hold
                    # Convert signal to numeric value (-1 for sell, 1 for buy, 0 for hold)
                    if hasattr(signal, 'signal_type') and signal.signal_type == SignalType.BUY:
                        return 1  # Buy signal
                    elif hasattr(signal, 'signal_type') and signal.signal_type == SignalType.SELL:
                        return -1  # Sell signal
                    elif hasattr(signal, 'signal_type') and signal.signal_type in [SignalType.HOLD, SignalType.NEUTRAL]:
                        return 0  # Hold/Neutral signal
                    else:
                        return 0  # Default to hold for any other signal type
                strategy_params = params
            elif callable(strategy_or_strategy_function):
                # It's a strategy function
                strategy_function = strategy_or_strategy_function
                strategy_params = params
            else:
                # Unknown strategy type - use default
                def default_strategy(row, strategy_params):
                    rsi = row.get('rsi', 50)
                    rsi_oversold = strategy_params.get('rsi_oversold', 30)
                    rsi_overbought = strategy_params.get('rsi_overbought', 70)

                    if rsi < rsi_oversold:
                        return 1  # Buy
                    elif rsi > rsi_overbought:
                        return -1  # Sell
                    else:
                        return 0  # Hold
                strategy_function = default_strategy
                strategy_params = params

            # Run backtest with the prepared strategy and parameters
            metrics = backtester.run_backtest(
                data=df,
                strategy_function=strategy_function,
                strategy_params=strategy_params
            )

            # Check if backtest ran successfully
            if 'error' in metrics:
                self.logger.warning(f"Backtest error for {params}: {metrics['error']}")
                return {"sharpe_ratio": -1, "total_return": -1, "max_drawdown": -1, "win_rate": -1, "profit_factor": -1}

            # Extract performance metrics
            return {
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'total_return': metrics.get('total_return', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'win_rate': metrics.get('win_rate', 0),
                'profit_factor': metrics.get('profit_factor', 1.0),
                'total_trades': metrics.get('total_trades', 0)
            }

        except Exception as e:
            self.logger.error(f"Error calculating metrics for asset: {e}")
            return {"sharpe_ratio": -1000.0, "total_return": -1000.0, "max_drawdown": -1000.0, "win_rate": -1000.0, "profit_factor": -1000.0}

    def _calculate_score_for_asset(self, params: Dict[str, Any], df: pd.DataFrame, risk_config: Dict[str, Any], strategy_or_strategy_function=None) -> float:
        """
        Calculate score for a single asset by running a backtest with the given parameters.
        Supports both strategy classes and strategy functions.
        """
        try:
            if len(df) < 2:
                return 0.0

            # Initialize backtester with risk config
            initial_capital = risk_config.get('initial_capital', 10000.0)
            fee_rate = risk_config.get('fee_rate', 0.001)
            slippage_factor = risk_config.get('slippage_factor', 0.0005)

            backtester = RealisticBacktester(
                initial_capital=initial_capital,
                fee_rate=fee_rate,
                slippage_factor=slippage_factor
            )

            # Determine if we have a strategy class or a function
            if strategy_or_strategy_function is None:
                # Default to a simple strategy function
                def default_strategy(row, strategy_params):
                    # Example signal function using RSI
                    rsi = row.get('rsi', 50)
                    rsi_oversold = strategy_params.get('rsi_oversold', 30)
                    rsi_overbought = strategy_params.get('rsi_overbought', 70)

                    if rsi < rsi_oversold:
                        return 1  # Buy
                    elif rsi > rsi_overbought:
                        return -1  # Sell
                    else:
                        return 0  # Hold
                strategy_function = default_strategy
                strategy_params = params
            elif hasattr(strategy_or_strategy_function, '__class__') and hasattr(strategy_or_strategy_function.__class__, 'generate_signal'):
                # It's likely a strategy instance, create a wrapper function
                strategy = strategy_or_strategy_function
                def strategy_function(row, strategy_params):
                    # Create a simple data point from the row
                    # In the actual system, we might need to convert pandas row to Symbol
                    # For now, we'll create a minimal signal generation approach
                    # since the StrategyPort interface uses Symbol and Signal objects
                    from domain.value_objects import Symbol
                    symbol = Symbol('BTC-USDT')  # Use proper symbol format

                    # Update strategy with market data first
                    market_data = {
                        'close': row.get('close', 0),
                        'open': row.get('open', 0),
                        'high': row.get('high', 0),
                        'low': row.get('low', 0),
                        'volume': row.get('volume', 0),
                        'rsi': row.get('rsi', 50),  # Assuming indicators exist
                        'sma_20': row.get('sma_20', 0),
                        'sma_50': row.get('sma_50', 0),
                        'atr': row.get('atr', 0),
                        'timestamp': row.get('timestamp', None),
                        # Add other indicators as needed
                    }
                    if hasattr(strategy, 'update_with_market_data'):
                        strategy.update_with_market_data(market_data)

                    # Generate signal using the StrategyPort interface
                    signal = strategy.generate_signal(symbol)
                    if signal is None:
                        return 0  # No signal = hold
                    # Convert signal to numeric value (-1 for sell, 1 for buy, 0 for hold)
                    if hasattr(signal, 'signal_type') and signal.signal_type == SignalType.BUY:
                        return 1  # Buy signal
                    elif hasattr(signal, 'signal_type') and signal.signal_type == SignalType.SELL:
                        return -1  # Sell signal
                    elif hasattr(signal, 'signal_type') and signal.signal_type in [SignalType.HOLD, SignalType.NEUTRAL]:
                        return 0  # Hold/Neutral signal
                    else:
                        return 0  # Default to hold for any other signal type
                strategy_params = params
            elif callable(strategy_or_strategy_function):
                # It's a strategy function
                strategy_function = strategy_or_strategy_function
                strategy_params = params
            else:
                # Unknown strategy type - use default
                def default_strategy(row, strategy_params):
                    rsi = row.get('rsi', 50)
                    rsi_oversold = strategy_params.get('rsi_oversold', 30)
                    rsi_overbought = strategy_params.get('rsi_overbought', 70)

                    if rsi < rsi_oversold:
                        return 1  # Buy
                    elif rsi > rsi_overbought:
                        return -1  # Sell
                    else:
                        return 0  # Hold
                strategy_function = default_strategy
                strategy_params = params

            # Run backtest with the prepared strategy and parameters
            metrics = backtester.run_backtest(
                data=df,
                strategy_function=strategy_function,
                strategy_params=strategy_params
            )

            # Check if backtest ran successfully
            if 'error' in metrics:
                self.logger.warning(f"Backtest error for {params}: {metrics['error']}")
                return -1000.0  # Large negative score for failed backtests

            # Extract performance metrics
            sharpe_ratio = metrics.get('sharpe_ratio', 0)
            win_rate = metrics.get('win_rate', 0)
            total_return = metrics.get('total_return', 0)
            max_drawdown = metrics.get('max_drawdown', 0)
            profit_factor = metrics.get('profit_factor', 1.0)
            total_trades = metrics.get('total_trades', 0)

            # Apply minimum trade filter to avoid overfitting to strategies with very few trades
            if total_trades < 5:
                return -100.0  # Penalize strategies with too few trades

            # Weighted scoring function that balances multiple performance metrics
            score = (
                sharpe_ratio * 2.0 +      # Sharpe ratio is most important
                win_rate * 1.0 +          # Win rate
                total_return * 5.0 +      # Total return (scaled appropriately)
                max_drawdown * (-3.0) +   # Drawdown penalty (negative value becomes positive penalty)
                profit_factor * 0.5       # Profit factor bonus
            )

            # Additional penalty for maximum drawdown exceeding threshold
            max_dd_threshold = risk_config.get('max_drawdown_threshold', -0.15)  # 15% default
            if max_drawdown < max_dd_threshold:
                score *= 0.5  # Apply penalty for excessive drawdown

            return score

        except Exception as e:
            self.logger.error(f"Error calculating score for asset: {e}")
            return -1000.0  # Large negative score on error

    def calculate_strategy_score(self, strategy: StrategyPort, params: Dict[str, Any], data: pd.DataFrame, risk_config: Dict[str, Any]) -> float:
        """
        Calculate score for a strategy class with given parameters on given data.
        """
        return self._calculate_score_for_asset(params, data, risk_config, strategy)

    def calculate_function_score(self, strategy_function: Callable, params: Dict[str, Any], data: pd.DataFrame, risk_config: Dict[str, Any]) -> float:
        """
        Calculate score for a strategy function with given parameters on given data.
        """
        return self._calculate_score_for_asset(params, data, risk_config, strategy_function)


# Standalone function for backward compatibility
def hyperopt_objective(params: Dict[str, Any], data_dict: Dict[str, pd.DataFrame], risk_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standalone hyperopt objective function for compatibility with existing code.
    Creates a simple strategy function for demonstration.
    """
    def simple_rsi_strategy(row, strategy_params):
        rsi = row.get('rsi', 50)
        rsi_oversold = strategy_params.get('rsi_oversold', 30)
        rsi_overbought = strategy_params.get('rsi_overbought', 70)

        if rsi < rsi_oversold:
            return 1  # Buy
        elif rsi > rsi_overbought:
            return -1  # Sell
        else:
            return 0  # Hold

    objective_handler = HyperoptObjective()
    objective_fn = objective_handler.create_objective_function(data_dict, risk_config, simple_rsi_strategy)
    return objective_fn(params)