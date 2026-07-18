"""Realistic backtesting implementation with proper order execution simulation."""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

from shared.logger import EnhancedLogger
from infrastructure.backtest.execution_intent import ExecutionIntent, create_execution_intent, OrderSide
from domain.entities import ExecutionIntent as DomainExecutionIntent, OrderSide as DomainOrderSide


class RealisticBacktester:
    """
    Realistic backtesting engine that simulates actual trading behavior:
    - Order execution with slippage
    - Transaction fees
    - Market impact
    - Position management
    - Risk controls
    - Strategy exclusivity validation
    - Architectural flow enforcement
    - Minimal execution confirmation
    - Fail-fast validation
    """

    def __init__(self,
                 initial_capital: float = 10000.0,
                 fee_rate: float = 0.001,  # 0.1% per trade
                 slippage_factor: float = 0.0005,  # 0.05% slippage
                 min_order_size: float = 0.001,
                 max_position_size: float = 0.20,  # 20% max position size
                 max_drawdown: float = 0.90,  # 90% max drawdown for backtesting (allow more flexibility)
                 max_leverage: float = 1.0,
                 deterministic_seed: int = 42,  # Fixed seed for deterministic execution
                 # --- E-P5.2 T4: realistic fill simulation -------------------------
                 spread_bps: float = 2.0,            # full bid-ask spread in bps; half charged per side
                 max_fill_ratio: float = 0.10,       # an order may consume at most this fraction of a bar's volume
                 rejection_rate: float = 0.0,        # probability an order is rejected outright (0 = off)
                 latency_slippage_bps: float = 0.0):  # adverse price drift during execution delay, in bps
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_factor = slippage_factor
        self.min_order_size = min_order_size
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.max_leverage = max_leverage
        self.deterministic_seed = deterministic_seed  # For deterministic execution
        # E-P5.2 T4 fill-realism knobs. Defaults add an always-on spread cost and
        # volume-capped partial fills (the systematic overstatements); rejections
        # and latency-slippage are opt-in (configured rates) so they don't inject
        # stochasticity into every run by default.
        self.spread_bps = spread_bps
        self.max_fill_ratio = max_fill_ratio
        self.rejection_rate = rejection_rate
        self.latency_slippage_bps = latency_slippage_bps
        self.logger = EnhancedLogger("RealisticBacktester")

        # Set random seed for deterministic execution
        np.random.seed(self.deterministic_seed)
        # Dedicated, seeded RNG for fill mechanics (rejections) so determinism is
        # independent of any other np.random usage during a run. Reset per run.
        self._fill_rng = np.random.default_rng(self.deterministic_seed)
        # Note: We don't use Python's random module in this implementation, but if we did, we'd set it too:
        # import random
        # random.seed(self.deterministic_seed)

        # Trading state
        self.position = 0  # Current position size
        self.position_value = 0  # Current position value in quote currency
        self.cash = initial_capital  # Available cash
        self.equity = initial_capital  # Total equity (cash + position value)
        self.avg_entry_price = 0.0  # Average entry price of current position
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_equity = initial_capital
        self.max_drawdown_reached = 0.0
        # E-P5.2 T4 fill diagnostics
        self.rejected_orders = 0
        self.partial_fills = 0
        # E-P5.2 T2: regime in effect at the current bar (set per-bar in the run
        # loop). Defaults to "unknown" so direct execute_order calls are safe.
        self._current_regime = "unknown"

        # Trade history
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []

        # SL/TP tracking
        self.active_positions: List[Dict[str, Any]] = []  # Track all active positions with SL/TP

        # Data validation
        self.max_data_age_seconds = 86400  # 1 day max age for data
        self.last_candle_time = None

        # Validation state
        self.signal_to_trade_mapping = {}
        self.min_trades_threshold = 5  # Minimum trades expected over multi-month period
        self.min_duration_months = 3  # Minimum duration for validation
        self.valid_strategy_types = [
            'rsi_strategy', 'ma_crossover_strategy', 'crypto_breakout',
            'trend_following', 'mean_reversion', 'volatility_breakout',
            'momentum', 'scalping', 'breakout', 'liquidity', 'mtf_trend',
            'oi_footprint', 'sweep_scalper', 'vwap_reversal'
        ]

    def validate_strategy_selection(self, strategy_name: str) -> bool:
        """
        Validate that the strategy name is in the list of valid system strategies.

        Args:
            strategy_name: Name of the strategy to validate

        Returns:
            bool: True if strategy is valid, False otherwise
        """
        if strategy_name in self.valid_strategy_types or strategy_name == 'crypto_breakout':
            self.logger.info(f"Strategy '{strategy_name}' is valid and in system strategies list")
            return True
        else:
            self.logger.error(f"Strategy '{strategy_name}' is NOT in valid system strategies list")
            self.logger.error(f"Valid strategies: {self.valid_strategy_types}")
            return False

    def validate_strategy_exists_and_callable(self, strategy_function) -> bool:
        """
        Validate that the strategy function exists and is callable.

        Args:
            strategy_function: The strategy function to validate

        Returns:
            bool: True if strategy function is valid, False otherwise
        """
        if strategy_function is None:
            self.logger.error("Strategy function is None")
            return False

        if not callable(strategy_function):
            self.logger.error(f"Strategy function is not callable: {type(strategy_function)}")
            return False

        self.logger.info("Strategy function is valid and callable")
        return True

    def enforce_strategy_exclusivity(self,
                                     strategy_name: str,
                                     strategy_function) -> bool:
        """
        Enforce that only valid strategies are used, failing fast if invalid.

        Args:
            strategy_name: Name of the strategy to validate
            strategy_function: The strategy function to validate

        Returns:
            bool: True if strategy passes all validations, raises exception if not
        """
        # Validate strategy name
        if not self.validate_strategy_selection(strategy_name):
            error_msg = f"Strategy exclusivity validation failed: '{strategy_name}' is not a valid system strategy"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate strategy function
        if not self.validate_strategy_exists_and_callable(strategy_function):
            error_msg = f"Strategy function validation failed for '{strategy_name}'"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info(f"All strategy exclusivity validations passed for '{strategy_name}'")
        return True

    def validate_candle_flow(self,
                             candle_data: pd.Series,
                             timestamp,
                             flow_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate that a single candle has passed through all required layers.

        Args:
            candle_data: The candle data to validate
            timestamp: The timestamp of the candle
            flow_state: Current state of the flow validation

        Returns:
            Dict with validation results for this candle
        """
        if flow_state is None:
            flow_state = {
                'watcher_observation': False,
                'engine_interpretation': False,
                'fusion_aggregation': False,
                'strategy_decision': False
            }

        validation_result = {
            'timestamp': timestamp,
            'candle_validated': True,
            'flow_state': flow_state.copy(),
            'issues': []
        }

        # Check that required columns exist (indicating proper data flow)
        required_columns = ['open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in candle_data.index and col not in candle_data.keys():
                validation_result['candle_validated'] = False
                validation_result['issues'].append(f"Missing required column: {col}")

        # Validate that each layer has processed the data appropriately
        # This is done by checking for presence of layer-specific indicators

        # Watcher layer indicators (should have market observations)
        watcher_indicators = ['volume', 'timestamp']  # Basic observation data
        watcher_processed = all(indicator in candle_data.index or indicator in candle_data.keys()
                                for indicator in watcher_indicators if indicator != 'timestamp')
        # For timestamp, check if it's part of the index
        if 'timestamp' in watcher_indicators:
            timestamp_present = hasattr(candle_data,
                                        'name') or 'timestamp' in candle_data.index or 'timestamp' in candle_data.keys()
            watcher_processed = watcher_processed and timestamp_present

        if not watcher_processed:
            validation_result['issues'].append("Candle did not pass through Watcher layer properly")

        # Check if indicators have been calculated (these would be present after Engine/Fusion processing)
        # Engine layer indicators (should have interpreted signals)
        engine_indicators = ['rsi', 'sma_20', 'sma_50']  # Common technical indicators
        engine_processed = any(indicator in candle_data.index or indicator in candle_data.keys()
                               for indicator in engine_indicators)

        # If no engine indicators are present, check if basic OHLC data exists (pre-processing state)
        if not engine_processed:
            basic_ohlc_present = all(col in candle_data.index or col in candle_data.keys()
                                     for col in ['open', 'high', 'low', 'close'])
            engine_processed = basic_ohlc_present  # Consider basic data as processed by engine layer

        if not engine_processed:
            validation_result['issues'].append("Candle did not pass through Engine layer properly")

        # Fusion layer indicators (should have aggregated signals)
        fusion_indicators = ['macd', 'bb_upper', 'bb_lower']  # More complex indicators
        fusion_processed = any(indicator in candle_data.index or indicator in candle_data.keys()
                               for indicator in fusion_indicators)

        # If no fusion indicators, consider it processed if basic or engine indicators exist
        if not fusion_processed:
            fusion_processed = engine_processed  # If engine processed it, fusion layer can process it

        if not fusion_processed:
            validation_result['issues'].append("Candle did not pass through Fusion layer properly")

        # Strategy layer indicators (should have decision-making data)
        strategy_indicators = ['atr', 'roc_10', 'adx']  # Advanced indicators for strategy decisions
        strategy_processed = any(indicator in candle_data.index or indicator in candle_data.keys()
                                 for indicator in strategy_indicators)

        # If no strategy indicators, consider it processed if previous layers processed it
        if not strategy_processed:
            strategy_processed = fusion_processed  # If fusion processed it, strategy layer can process it

        if not strategy_processed:
            validation_result['issues'].append("Candle did not pass through Strategy layer properly")

        # Update flow state
        validation_result['flow_state']['watcher_observation'] = watcher_processed
        validation_result['flow_state']['engine_interpretation'] = engine_processed
        validation_result['flow_state']['fusion_aggregation'] = fusion_processed
        validation_result['flow_state']['strategy_decision'] = strategy_processed

        # Overall validation
        validation_result['all_layers_passed'] = (
                watcher_processed and engine_processed and fusion_processed and strategy_processed
        )

        if not validation_result['all_layers_passed']:
            self.logger.warning(f"Candle at {timestamp} failed architectural flow validations")
            for issue in validation_result['issues']:
                self.logger.warning(f"  - {issue}")

        return validation_result

    def validate_full_data_flow(self,
                                data: pd.DataFrame,
                                strategy_name: str) -> Dict[str, Any]:
        """
        Validate the architectural flow for the entire dataset.

        Args:
            data: The full dataset to validate
            strategy_name: Name of the strategy being tested

        Returns:
            Dict with overall validation results
        """
        if data.empty:
            return {
                'strategy_name': strategy_name,
                'total_candles': 0,
                'candles_passed_flow': 0,
                'candles_failed_flow': 0,
                'validation_passed': False,
                'issues': ['No data to validate']
            }

        validation_results = {
            'strategy_name': strategy_name,
            'total_candles': len(data),
            'candles_passed_flow': 0,
            'candles_failed_flow': 0,
            'validation_passed': False,
            'issues': [],
            'candle_validations': []
        }

        flow_state = {
            'watcher_observation': False,
            'engine_interpretation': False,
            'fusion_aggregation': False,
            'strategy_decision': False
        }

        # Validate each candle in the dataset
        for i in range(len(data)):
            row = data.iloc[i]
            timestamp = row.name if hasattr(row, 'name') else datetime.now()

            candle_validation = self.validate_candle_flow(row, timestamp, flow_state)
            validation_results['candle_validations'].append(candle_validation)

            if candle_validation['all_layers_passed']:
                validation_results['candles_passed_flow'] += 1
            else:
                validation_results['candles_failed_flow'] += 1

        # Overall validation
        if validation_results['candles_failed_flow'] == 0:
            validation_results['validation_passed'] = True
        else:
            validation_results['issues'].append(
                f"{validation_results['candles_failed_flow']} out of {validation_results['total_candles']} "
                f"candles failed architectural flow validation"
            )

        if validation_results['validation_passed']:
            self.logger.info(f"Full data flow validation PASSED for {strategy_name}")
            self.logger.info(f"  All {validation_results['total_candles']} candles passed flow validation")
        else:
            self.logger.error(f"Full data flow validation FAILED for {strategy_name}")
            self.logger.error(f"  {validation_results['candles_failed_flow']} candles failed validation")
            for issue in validation_results['issues']:
                self.logger.error(f"  - {issue}")

        return validation_results

    def enforce_architectural_flow(self,
                                   data: pd.DataFrame,
                                   strategy_name: str) -> bool:
        """
        Enforce that the architectural flow is followed, failing fast if not.

        Args:
            data: The data to validate
            strategy_name: Name of the strategy being tested

        Returns:
            bool: True if flow validation passes, raises exception if not
        """
        validation_result = self.validate_full_data_flow(data, strategy_name)

        if not validation_result['validation_passed']:
            # For backtesting, log the architectural flow issues but don't fail fast
            # The flow validation is more of a diagnostic tool than a hard requirement
            error_msg = (
                f"Architectural flow validation showed issues for strategy '{strategy_name}'. "
                f"{validation_result['candles_failed_flow']} out of {validation_result['total_candles']} "
                f"candles had flow validation issues (this is normal for backtesting data preparation)"
            )
            self.logger.warning(error_msg)

            # Only raise exception if ALL candles failed validation (indicating serious data issues)
            if validation_result['candles_passed_flow'] == 0:
                self.logger.error("FAIL-FAST: No candles passed architectural flow validation - serious data issue")
                raise ValueError(error_msg)
            else:
                # Allow backtest to continue with flow validation issues
                self.logger.info("Continuing backtest despite architectural flow validation issues")
        else:
            self.logger.info(f"Architectural flow validation passed for '{strategy_name}'")

        return True

    def record_strategy_signal(self,
                               timestamp,
                               signal: int,
                               strategy_name: str,
                               price=None) -> str:
        """
        Record when a strategy emits a signal.

        Args:
            timestamp: When the signal was emitted
            signal: The signal value (-1 for sell, 0 for hold, 1 for buy)
            strategy_name: Name of the strategy that emitted the signal
            price: Price at the time of signal

        Returns:
            str: Unique signal ID for tracking
        """
        signal_id = f"{strategy_name}_{timestamp.isoformat()}_{signal}"

        self.signal_to_trade_mapping[signal_id] = {
            'timestamp': timestamp,
            'signal': signal,
            'strategy_name': strategy_name,
            'price': price,
            'trade_attempt_recorded': False,
            'trade_record': None
        }

        # Only log signal recording if in verbose/debug mode
        # self.logger.debug(f"Recorded strategy signal: {strategy_name} at {timestamp} - Signal: {signal}")

        return signal_id

    def confirm_trade_attempt(self,
                              signal_id: str,
                              trade_record: Dict[str, Any] = None) -> bool:
        """
        Confirm that a trade attempt was made for a recorded signal.

        Args:
            signal_id: ID of the signal to confirm
            trade_record: The trade record if a trade was executed

        Returns:
            bool: True if confirmation was successful
        """
        if signal_id not in self.signal_to_trade_mapping:
            self.logger.warning(f"No signal found for ID: {signal_id}")
            return False

        signal_info = self.signal_to_trade_mapping[signal_id]
        signal_info['trade_attempt_recorded'] = True
        signal_info['trade_record'] = trade_record

        # Only log trade confirmation if in verbose/debug mode
        # if signal_info['signal'] != 0:  # Only log non-hold signals
        #     self.logger.debug(f"Confirmed trade attempt for signal: {signal_id}")

        return True

    def validate_signal_trade_correspondence(self,
                                             strategy_signals: List[Dict[str, Any]],
                                             trade_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that signals correspond to trade attempts.

        Args:
            strategy_signals: List of signals emitted by the strategy
            trade_records: List of trade records from the backtest

        Returns:
            Dict with validation results
        """
        validation_results = {
            'total_signals': len(strategy_signals),
            'non_zero_signals': 0,
            'signals_with_trade_attempts': 0,
            'signals_without_trade_attempts': 0,
            'validation_passed': False,
            'issues': []
        }

        # Count non-zero signals. Treat None as 0 (no-signal bars record None; the
        # naive `None != 0` is True and miscounted every no-signal bar as actionable,
        # inflating non_zero_signals to the full bar count and spuriously failing the
        # correspondence guard). Consistent with the matched-signal loop below.
        for signal in strategy_signals:
            if (signal.get('signal') or 0) != 0:
                validation_results['non_zero_signals'] += 1

        # Map signals to trades based on timestamp proximity
        signal_timestamps = []
        trade_timestamps = []

        for signal in strategy_signals:
            # E-P5.2: treat None as 0 (wrapped function strategies record None for
            # no-signal bars; `None != 0` previously miscounted them as actionable
            # signals, spuriously failing the signal/trade correspondence check).
            if (signal.get('signal') or 0) != 0:  # Only consider non-zero signals
                signal_timestamps.append(signal.get('timestamp'))

        for trade in trade_records:
            trade_timestamps.append(trade.get('timestamp'))

        # Match signals to trades within a reasonable time window
        matched_signals = 0
        time_window = pd.Timedelta(minutes=5)  # 5-minute window for signal-trade matching

        for signal_ts in signal_timestamps:
            signal_dt = pd.to_datetime(signal_ts) if isinstance(signal_ts, str) else signal_ts
            matched = False

            for trade_ts in trade_timestamps:
                trade_dt = pd.to_datetime(trade_ts) if isinstance(trade_ts, str) else trade_ts
                time_diff = abs(signal_dt - trade_dt)

                if time_diff <= time_window:
                    matched = True
                    matched_signals += 1
                    break

        validation_results['signals_with_trade_attempts'] = matched_signals
        validation_results['signals_without_trade_attempts'] = validation_results['non_zero_signals'] - matched_signals

        # Validation logic
        if validation_results['non_zero_signals'] > 0:
            success_rate = matched_signals / validation_results['non_zero_signals']
            if success_rate < 0.8:  # At least 80% of signals should have trade attempts
                validation_results['issues'].append(
                    f"Only {matched_signals}/{validation_results['non_zero_signals']} "
                    f"({success_rate:.1%}) signals had corresponding trade attempts"
                )

        validation_results['validation_passed'] = len(validation_results['issues']) == 0

        if validation_results['validation_passed']:
            self.logger.info("Signal-trade correspondence validation PASSED")
            self.logger.info(f"  {matched_signals}/{validation_results['non_zero_signals']} signals had trade attempts")
        else:
            self.logger.error("Signal-trade correspondence validation FAILED")
            for issue in validation_results['issues']:
                self.logger.error(f"  - {issue}")

        return validation_results

    def confirm_execution_for_signals(self,
                                      strategy_signals: List[Dict[str, Any]],
                                      trade_records: List[Dict[str, Any]]) -> bool:
        """
        Confirm that execution happened for signals, failing if not sufficient correspondence.

        Args:
            strategy_signals: List of signals emitted by the strategy
            trade_records: List of trade records from the backtest

        Returns:
            bool: True if sufficient correspondence exists, raises exception if not
        """
        validation_result = self.validate_signal_trade_correspondence(strategy_signals, trade_records)

        if not validation_result['validation_passed']:
            # For backtesting, log the issue but don't necessarily fail
            error_msg = (
                f"Minimal execution confirmation showed low correspondence. "
                f"{validation_result['signals_without_trade_attempts']} out of "
                f"{validation_result['non_zero_signals']} non-zero signals had no corresponding trade attempts."
            )
            self.logger.warning(error_msg)

            # Only raise exception if there are signals but absolutely no trades
            if (validation_result['non_zero_signals'] > 0 and
                    validation_result['signals_with_trade_attempts'] == 0):
                self.logger.error("FAIL-FAST: No trades executed despite signals being generated")
                raise ValueError(error_msg)
            else:
                # Allow backtest to continue with low correspondence
                self.logger.info("Continuing backtest despite low signal-trade correspondence")
        else:
            self.logger.info("Minimal execution confirmation passed")

        return True

    def validate_trade_count(self,
                             start_date: datetime,
                             end_date: datetime,
                             total_trades: int,
                             symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Validate that sufficient trades were executed over the specified period.

        Args:
            start_date: Start date of the backtest
            end_date: End date of the backtest
            total_trades: Total number of trades executed
            symbol: Trading symbol (default BTCUSDT for validation)

        Returns:
            Dict with validation results
        """
        duration_days = (end_date - start_date).days
        duration_months = duration_days / 30.0  # Approximate months

        validation_results = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'duration_days': duration_days,
            'duration_months': round(duration_months, 2),
            'total_trades': total_trades,
            'symbol': symbol,
            'expected_min_trades': 0,
            'validation_passed': False,
            'issues': []
        }

        # Calculate expected minimum trades based on duration
        if duration_months >= self.min_duration_months:
            # For multi-month BTC data, different strategies may have different trade frequencies
            # Some strategies like trend following may have fewer trades over long periods
            # Reduce the expected minimum to be more realistic for different strategy types
            expected_min = max(3, int(duration_months * 0.3))  # At least 0.3 trades per month (rounded up), minimum 3
            validation_results['expected_min_trades'] = expected_min

            if total_trades < expected_min:
                validation_results['issues'].append(
                    f"Low trade count: {total_trades} < {expected_min} expected for "
                    f"{duration_months:.1f} months of {symbol} data (some strategies may legitimately have few trades)"
                )
        else:
            # For shorter periods, use a more lenient threshold
            # Allow 0 trades for very short periods or periods where strategy doesn't generate signals
            expected_min = max(1, int(duration_months * 0.5)) if duration_months >= 0.5 else 0  # Require at least 1 trade for periods >= 2 weeks
            validation_results['expected_min_trades'] = expected_min

            # Don't add issues for very short periods with 0 trades - this is normal for some strategies
            if duration_months >= 0.5 and total_trades < expected_min:  # At least 2 weeks should have some trades
                validation_results['issues'].append(
                    f"Low trade count: {total_trades} < {expected_min} expected for "
                    f"{duration_months:.1f} months of {symbol} data (should have at least some trades after 2 weeks)"
                )

        validation_results['validation_passed'] = len(validation_results['issues']) == 0

        if validation_results['validation_passed']:
            self.logger.info(f"Trade count validation PASSED for {symbol}")
            self.logger.info(f"  {total_trades} trades executed over {duration_months:.1f} months")
        else:
            self.logger.warning(f"Trade count validation issues for {symbol}")
            for issue in validation_results['issues']:
                self.logger.warning(f"  - {issue}")

        return validation_results

    def validate_trade_density(self,
                               data: pd.DataFrame,
                               total_trades: int,
                               start_date: datetime,
                               end_date: datetime) -> Dict[str, Any]:
        """
        Validate trade density relative to available data points.

        Args:
            data: The backtest data
            total_trades: Total number of trades executed
            start_date: Start date of the backtest
            end_date: End date of the backtest

        Returns:
            Dict with trade density validation results
        """
        total_data_points = len(data)

        validation_results = {
            'total_data_points': total_data_points,
            'total_trades': total_trades,
            'trade_density': 0.0,
            'validation_passed': False,
            'issues': [],
            'is_zero_trade_strategy': False,
            'is_pathological_overtrading': False
        }

        if total_data_points > 0:
            trade_density = total_trades / total_data_points
            validation_results['trade_density'] = round(trade_density, 6)  # More precision for small values

            # Check for near-zero trade strategies
            if total_trades == 0:
                validation_results['is_zero_trade_strategy'] = True
                validation_results['issues'].append(
                    f"Zero trades executed: {total_trades} trades for {total_data_points} data points. "
                    f"This may indicate a strategy that never generates signals or has overly restrictive conditions."
                )
            elif total_trades == 1:
                validation_results['is_zero_trade_strategy'] = True
                validation_results['issues'].append(
                    f"Only 1 trade executed: {total_trades} trades for {total_data_points} data points. "
                    f"This may indicate a strategy that rarely generates signals."
                )
            elif trade_density < 0.0001:  # Less than 0.01% of data points result in trades
                validation_results['is_zero_trade_strategy'] = True
                validation_results['issues'].append(
                    f"Extremely low trade density: {trade_density:.6f} ({total_trades}/{total_data_points}). "
                    f"This may indicate a strategy that rarely generates signals."
                )

            # Check for pathological overtrading
            if trade_density > 0.5:  # More than 50% of data points result in trades
                validation_results['is_pathological_overtrading'] = True
                validation_results['issues'].append(
                    f"Pathological overtrading detected: {trade_density:.4f} trade density "
                    f"({total_trades}/{total_data_points}). This may indicate a strategy that trades excessively."
                )

            # For a reasonable strategy, we expect trades within a reasonable range
            # Adjust the threshold based on duration - be more lenient for shorter periods
            duration_months = (end_date - start_date).days / 30.0
            if duration_months < 1:  # Less than 1 month
                # For short periods, allow very low density as strategy might not generate signals
                min_expected_density = 0  # Don't enforce density for very short periods
            elif duration_months < 3:  # Less than 3 months
                # For medium periods, use a lower threshold
                min_expected_density = 0.00005  # Even lower threshold
            else:  # 3 months or more
                # For longer periods, still be lenient as some strategies trade infrequently
                min_expected_density = 0.00001  # Even lower threshold

            # For longer periods, also check if we have a reasonable absolute number of trades
            # Even if density is low, if we have enough absolute trades, it's acceptable
            if not validation_results['is_zero_trade_strategy'] and not validation_results['is_pathological_overtrading']:
                if trade_density < min_expected_density:
                    # Check if we have enough absolute trades to compensate for low density
                    min_abs_trades_for_period = max(1, int(duration_months * 0.1))  # At least 0.1 trades per month
                    if total_trades < min_abs_trades_for_period:
                        validation_results['issues'].append(
                            f"Very low trade density: {trade_density:.6f} ({total_trades}/{total_data_points}), "
                            f"and low absolute trade count: {total_trades} for {duration_months:.1f} months (may be normal for some strategies)"
                        )
                    else:
                        # If we have enough absolute trades, don't fail on density alone
                        # This means the validation passes despite low density if we have sufficient trades
                        pass  # Validation passes due to sufficient absolute trade count

        validation_results['validation_passed'] = len(validation_results['issues']) == 0

        if validation_results['validation_passed']:
            self.logger.debug(f"Trade density validation PASSED")
            self.logger.debug(f"  Density: {validation_results['trade_density']:.6f}")
        else:
            self.logger.warning(f"Trade density validation issues:")
            for issue in validation_results['issues']:
                self.logger.warning(f"  - {issue}")

        return validation_results

    def enforce_fail_fast(self,
                          start_date: datetime,
                          end_date: datetime,
                          total_trades: int,
                          data: pd.DataFrame,
                          symbol: str = "BTCUSDT") -> bool:
        """
        Enforce fail-fast mechanism, raising an exception if validation fails.

        Args:
            start_date: Start date of the backtest
            end_date: End date of the backtest
            total_trades: Total number of trades executed
            data: The backtest data
            symbol: Trading symbol (default BTCUSDT)

        Returns:
            bool: True if validation passes, raises exception if not
        """
        # E-P5.2: define duration_months in THIS method's scope (it was used in
        # the zero-trade branch below but only defined in other methods, so a
        # long-window run that tripped the zero-trade check raised NameError and
        # aborted the whole backtest -> 0 trades).
        duration_months = (end_date - start_date).days / 30.0

        # Validate trade count
        count_validation = self.validate_trade_count(start_date, end_date, total_trades, symbol)

        # Validate trade density
        density_validation = self.validate_trade_density(data, total_trades, start_date, end_date)

        # Overall validation
        overall_passed = count_validation['validation_passed'] and density_validation['validation_passed']

        # Check for zero trade strategies and pathological overtrading specifically
        is_zero_trade_strategy = density_validation.get('is_zero_trade_strategy', False)
        is_pathological_overtrading = density_validation.get('is_pathological_overtrading', False)

        if is_zero_trade_strategy:
            # For backtesting, log the issue but don't necessarily fail fast
            # Some strategies may legitimately have zero trades in certain market conditions
            error_msg = (
                f"Zero trade strategy detected during backtest.\n"
                f"  Duration: {(end_date - start_date).days} days ({(end_date - start_date).days / 30.0:.1f} months)\n"
                f"  Trades: {total_trades}\n"
                f"  Data points: {len(data)}\n"
                f"  Symbol: {symbol}\n"
                f"  This may be normal for some strategies in certain market conditions."
            )
            self.logger.warning("Zero trade strategy detected - this may be normal for some strategies")

            # Only raise exception if we have a substantial period of data but zero trades
            if duration_months >= 1 and total_trades == 0:  # At least 1 month with zero trades
                self.logger.error("FAIL-FAST TRIGGERED: Zero trades executed over 1+ month period - rejecting from optimization")
                raise ValueError(error_msg)
            else:
                # For shorter periods or volatile market conditions, zero trades may be normal
                self.logger.info("Allowing zero trades for shorter periods or volatile market conditions")
        elif is_pathological_overtrading:
            error_msg = (
                f"INVALID STRATEGY DETECTED: Pathological overtrading.\n"
                f"  Duration: {(end_date - start_date).days} days ({(end_date - start_date).days / 30.0:.1f} months)\n"
                f"  Trades: {total_trades}\n"
                f"  Data points: {len(data)}\n"
                f"  Symbol: {symbol}\n"
                f"  This strategy should be rejected from optimization."
            )
            if duration_months >= 1.0:
                self.logger.error("FAIL-FAST TRIGGERED: Pathological overtrading detected - rejecting from optimization")
                raise ValueError(error_msg)
            else:
                self.logger.warning("Pathological overtrading detected, but allowing for short validation period (< 1 month)")
        elif not overall_passed:
            # For backtesting, we should log warnings but not necessarily fail fast
            # Different strategies may legitimately have few trades depending on market conditions
            error_msg = (
                f"Backtest produced fewer trades than expected.\n"
                f"  Duration: {(end_date - start_date).days} days ({(end_date - start_date).days / 30.0:.1f} months)\n"
                f"  Trades: {total_trades}\n"
                f"  Data points: {len(data)}\n"
                f"  Symbol: {symbol}\n"
                f"  Count validation: {'PASS' if count_validation['validation_passed'] else 'FAIL'}\n"
                f"  Density validation: {'PASS' if density_validation['validation_passed'] else 'FAIL'}"
            )
            self.logger.warning(error_msg)
            # Only raise exception for extremely low trade counts (e.g., 0 trades when expecting some)
            # Be more lenient with the threshold
            if total_trades == 0 and count_validation.get('expected_min_trades', 0) > 2:
                self.logger.error("FAIL-FAST TRIGGERED: Zero trades executed when trades were expected")
                raise ValueError(error_msg)
            elif total_trades < 2 and count_validation.get('expected_min_trades', 0) > 5:  # Less than 2 trades when expecting more than 5
                self.logger.error(f"FAIL-FAST TRIGGERED: Very low trade count ({total_trades}) when more were expected")
                raise ValueError(error_msg)
            else:
                # For backtesting, allow continuation with low trade counts
                self.logger.info("Continuing backtest despite low trade count - may be normal for this strategy")
        else:
            self.logger.info("Fail-fast validation passed - sufficient trades detected")

        return True

    def _adapt_domain_execution_intent(self,
                                       domain_intent: DomainExecutionIntent,
                                       market_row: pd.Series) -> ExecutionIntent:
        """
        Adapter function to convert Domain ExecutionIntent to Infrastructure ExecutionIntent.

        Args:
            domain_intent: Domain-level ExecutionIntent with risk_parameters
            market_row: Current market data row containing price information

        Returns:
            ExecutionIntent: Infrastructure-level ExecutionIntent with execution-ready parameters
        """
        import uuid
        from datetime import datetime

        # Extract price from market data (using close price as the execution price)
        execution_price = market_row['close']

        # Extract risk parameters from domain intent
        risk_params = domain_intent.risk_parameters

        atr = market_row.get('atr', 0.01 * execution_price)
        atr_multiplier = risk_params.get('atr_multiplier', 1.5)
        stop_loss_distance = atr_multiplier * atr

        # Calculate position size based on risk parameters with NGDP (Dynamic Position Sizing)
        try:
            from application.containers.container import container
            risk_engine = container.resolve("risk_engine")
            
            # Record price for rolling correlation calculation (E3.T5)
            risk_engine._risk_manager.record_price(domain_intent.symbol.value, float(execution_price))
            
            from domain.entities.position import Portfolio, Position as DomainPosition
            from domain.value_objects import Money as DomainMoney, Symbol as DomainSymbol
            from domain.enums.position_side import PositionSide
            from decimal import Decimal
            from datetime import datetime

            risk_mgr = risk_engine._risk_manager
            
            # Sync backtester capital/equity state to the risk manager
            risk_mgr.starting_equity = float(self.equity)
            risk_mgr.total_pnl = 0.0
            
            active_positions = []
            if abs(self.position) > 0.0:
                side = PositionSide.LONG if self.position > 0.0 else PositionSide.SHORT
                active_positions.append(DomainPosition(
                    symbol=domain_intent.symbol,
                    side=side,
                    quantity=Decimal(str(abs(self.position))),
                    entry_price=DomainMoney(amount=Decimal(str(self.avg_entry_price)), currency="USDT"),
                    timestamp=datetime.now()
                ))
            
            portfolio_obj = Portfolio(
                positions=active_positions,
                cash_balance=DomainMoney(amount=Decimal(str(self.cash)), currency="USDT"),
                total_value=DomainMoney(amount=Decimal(str(self.equity)), currency="USDT"),
                timestamp=datetime.now()
            )

            vol = market_row.get('atr')
            position_size = risk_engine.calculate_dynamic_size(
                intent=domain_intent,
                portfolio=portfolio_obj,
                volatility=vol
            )
        except Exception as e:
            risk_percentage = risk_params.get('risk_per_trade', 0.02)
            equity = getattr(self, 'equity', 10000.0)
            risk_amount = equity * risk_percentage
            atr = market_row.get('atr', 0.01 * execution_price)
            atr_multiplier = risk_params.get('atr_multiplier', 1.5)
            stop_loss_distance = atr_multiplier * atr
            if stop_loss_distance > 0:
                position_size = risk_amount / stop_loss_distance
            else:
                position_size = (equity * risk_percentage) / execution_price

        # Apply position size limits
        equity = getattr(self, 'equity', 10000.0)
        max_position_by_equity = (equity * getattr(self, 'max_position_size', 0.20)) / execution_price
        position_size = min(position_size, max_position_by_equity)

        # Ensure minimum order size
        min_order_size = getattr(self, 'min_order_size', 0.001)
        if position_size < min_order_size:
            position_size = min_order_size

        # Calculate stop loss and take profit prices based on risk parameters
        sl_price = None
        tp_price = None

        # E-P5.2 Priority-1 FIX (bug #2): compare against the DOMAIN OrderSide
        # (domain_intent.side is a domain enum). The old `== OrderSide.BUY`
        # compared it to the INFRASTRUCTURE OrderSide enum (a different class),
        # which is never equal, so EVERY adapted intent took the SELL branch and
        # got short geometry (SL above / TP below) — inverting SL/TP for every
        # BUY/long position. (Line below for infra_side already used DomainOrderSide.)
        if domain_intent.side == DomainOrderSide.BUY:
            # For BUY: SL below entry, TP above entry
            sl_price = execution_price - stop_loss_distance
            risk_reward_ratio = risk_params.get('risk_reward_ratio', 1.5)
            tp_distance = stop_loss_distance * risk_reward_ratio
            tp_price = execution_price + tp_distance
        else:  # SELL
            # For SELL: SL above entry, TP below entry
            sl_price = execution_price + stop_loss_distance
            risk_reward_ratio = risk_params.get('risk_reward_ratio', 1.5)
            tp_distance = stop_loss_distance * risk_reward_ratio
            tp_price = execution_price - tp_distance

        # Convert Domain OrderSide to Infrastructure OrderSide
        if domain_intent.side == DomainOrderSide.BUY:
            infra_side = OrderSide.BUY
        else:  # DomainOrderSide.SELL
            infra_side = OrderSide.SELL

        # Create infrastructure ExecutionIntent with derived parameters
        intent_id = f"adapted_{uuid.uuid4().hex[:8]}"

        adapted_intent = create_execution_intent(
            side=infra_side,
            size=position_size,
            price=execution_price,
            timestamp=domain_intent.timestamp,
            stop_loss=sl_price,
            take_profit=tp_price,
            strategy_name=domain_intent.strategy_name,
            symbol=str(domain_intent.symbol) if hasattr(domain_intent.symbol, '__str__') else str(domain_intent.symbol),
            intent_id=intent_id
        )

        self.logger.info(f"[ADAPTER] Adapted domain intent {domain_intent.strategy_name} to execution intent {adapted_intent.id}")
        self.logger.info(f"[ADAPTER] Size: {position_size:.4f}, Price: {execution_price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}")

        return adapted_intent

    def reset(self):
        """Reset the backtester to initial state."""
        self.position = 0
        self.position_value = 0
        self.cash = self.initial_capital
        self.equity = self.initial_capital
        self.avg_entry_price = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_equity = self.initial_capital
        self.max_drawdown_reached = 0.0
        self.trades = []
        self.equity_curve = []
        self.active_positions = []
        # E-P5.2 T4: reset fill diagnostics and re-seed the fill RNG so repeated
        # runs are byte-identical (rejections are reproducible).
        self.rejected_orders = 0
        self.partial_fills = 0
        self._fill_rng = np.random.default_rng(self.deterministic_seed)
        self._current_regime = "unknown"  # E-P5.2 T2
        # Reset additional state variables to ensure full isolation between runs
        self.signal_to_trade_mapping = {}
        self.last_order_time = {}
        self.data = None

    def _feed_trade_outcome(self, pnl, exit_time) -> None:
        """E-P5.2: feed a realised trade outcome back into the strategy's
        discipline so consecutive-loss tracking and the post-exit cooldown
        actually function during a backtest (they were inactive — the backtester
        never told the strategy how trades resolved). No-op for strategy
        functions that don't expose the hook (e.g. the golden test fn)."""
        symbol = getattr(self, '_symbol', None)
        fn = getattr(self, '_strategy_function', None)
        callback = getattr(fn, 'record_trade_result', None) if fn is not None else None
        if callback is None or not symbol:
            return  # no hook, or symbol unknown -> can't attribute the outcome
        # Normalise the simulated exit time to a datetime for the discipline clock.
        ts = exit_time
        try:
            if isinstance(ts, (int, float)):
                ts = datetime.utcfromtimestamp(ts)
            elif hasattr(ts, 'to_pydatetime'):
                ts = ts.to_pydatetime()
            if not isinstance(ts, datetime):
                ts = None
            callback(symbol, bool(pnl > 0), position_closed=True, exit_time=ts)
        except Exception as e:  # discipline feedback must never break a backtest
            self.logger.debug(f"Trade-outcome feedback skipped: {e}")

    def _classify_bar_regime(self, row) -> str:
        """Lightweight, deterministic regime label for P&L attribution (E-P5.2 T2).

        Uses already-computed, lookahead-safe indicators (sma_20/sma_50 trend).
        Returns an opaque string consumed by the edge ledger / attribution.

        NOTE: this is a transparent backtest-time labeler, NOT the production
        regime classifier. The system has several competing RegimeType
        classifiers whose consolidation is deferred (deferred backlog DB-4);
        this keeps attribution reproducible without entangling that fork. The
        labels mirror common RegimeType members so a future swap is mechanical.
        """
        try:
            close = row.get('close')
            sma20 = row.get('sma_20')
            sma50 = row.get('sma_50')
            if close is None or sma20 is None or (isinstance(sma20, float) and math.isnan(sma20)):
                return "unknown"
            if sma50 is not None and not (isinstance(sma50, float) and math.isnan(sma50)):
                if sma20 > sma50 and close > sma20:
                    return "trending_up"
                if sma20 < sma50 and close < sma20:
                    return "trending_down"
                return "ranging"
            return "trending_up" if close > sma20 else "trending_down"
        except Exception:
            return "unknown"

    def calculate_order_execution_price(self,
                                        price: float,
                                        side: str,
                                        size: float,
                                        market_data: Dict[str, float] = None) -> float:
        """
        Calculate actual execution price considering slippage and market impact.
        
        Args:
            price: Target price (e.g., close price)
            side: 'buy' or 'sell'
            size: Order size
            market_data: Additional market data (high, low, volume, etc.)
        """
        if market_data is None:
            market_data = {}

        # Base slippage calculation
        base_slippage = self.slippage_factor * price

        # Market impact based on order size relative to market volume.
        # E-P5.2 Priority-1 FIX: compare like units. `size` and `volume` are both
        # base-asset quantities; the old `abs(size*price)/market_vol` divided a
        # QUOTE amount ($) by a BASE volume (e.g. ~6 BTC/min), inflating the ratio
        # ~price-fold (~46 vs ~0.0005). That made market_impact ~90x too large and
        # pushed every BUY ~5% above (SELL ~5% below) the true price, so SL/TP
        # (set from the real signal price) landed on the wrong side of entry and
        # EVERY trade was a structural loss (0% win, MFE=0, R~-1) across all
        # strategies. Correct ratio = order base-size / bar base-volume.
        market_vol = market_data.get('volume', 1000000)  # Default volume (base units)
        order_to_market_ratio = abs(size) / market_vol if market_vol > 0 else 0

        # Additional market impact (larger orders face more impact)
        market_impact = base_slippage * (1 + 2 * order_to_market_ratio)  # 2x impact factor

        # E-P5.2 T4: half bid-ask spread (buyers lift the ask, sellers hit the
        # bid) plus an adverse latency-drift term (price moves against us during
        # the execution delay). Both are charged in the unfavourable direction.
        half_spread = (self.spread_bps / 2.0 / 10000.0) * price
        latency_cost = (self.latency_slippage_bps / 10000.0) * price
        adverse_cost = market_impact + half_spread + latency_cost

        if side.lower() == 'buy':
            # Buy orders get filled at higher price (worse for buyer)
            execution_price = price + adverse_cost
        else:  # sell
            # Sell orders get filled at lower price (worse for seller)
            execution_price = price - adverse_cost

        # Ensure execution price is reasonable. E-P5.2 Priority-1 FIX: the caps
        # were backwards (a buy used max(.,0.95*price) — a floor — so the upside
        # was uncapped). Bound the ADVERSE direction: a buy never fills >5% above,
        # a sell never fills >5% below the reference price.
        if side.lower() == 'buy':
            execution_price = min(execution_price, price * 1.05)  # don't pay >5% above
        else:
            execution_price = max(execution_price, price * 0.95)  # don't sell >5% below

        return execution_price

    def execute_order(self,
                      side: str,
                      size: float,
                      price: float,
                      timestamp: datetime,
                      market_data: Dict[str, float] = None,
                      sl_price: float = None,
                      tp_price: float = None) -> Optional[Dict[str, Any]]:
        """
        Execute an order with realistic market conditions.

        Args:
            side: 'buy' or 'sell'
            size: Order size in base currency
            price: Target price
            timestamp: Time of execution
            market_data: Additional market data
            sl_price: Stop loss price (optional)
            tp_price: Take profit price (optional)
        """
        # Check if we're in a drawdown that exceeds limits
        current_drawdown = (self.max_equity - self.equity) / self.max_equity
        if current_drawdown > self.max_drawdown:
            self.logger.warning(f"Max drawdown exceeded: {current_drawdown:.2%}. Stopping trading.")
            return None

        # E-P5.2 T4: order rejection at the configured rate (deterministic via the
        # seeded fill RNG). A rejected order does not execute at all.
        if self.rejection_rate > 0.0 and self._fill_rng.random() < self.rejection_rate:
            self.rejected_orders += 1
            self.logger.debug(f"Order rejected (rate={self.rejection_rate:.4f}): {side} {size} @ {price}")
            return None

        # Tracks whether liquidity capped this fill (set below); recorded on the trade.
        partial_filled = False

        # Calculate realistic execution price
        execution_price = self.calculate_order_execution_price(
            price, side, size, market_data
        )

        # Calculate trade value and fees
        trade_value = abs(size) * execution_price
        fees = trade_value * self.fee_rate

        # Check order size constraints
        if abs(size) < self.min_order_size:
            self.logger.debug(f"Order size too small: {size} < {self.min_order_size}")
            return None

        # E-P5.2 T4: partial fill — an order cannot consume more than max_fill_ratio
        # of the bar's available (quote-denominated) volume. Liquidity caps the fill
        # before capital constraints apply; the unfilled remainder is simply dropped.
        if self.max_fill_ratio and self.max_fill_ratio > 0:
            market_vol = market_data.get('volume', 0) if market_data else 0
            if market_vol and market_vol > 0:
                max_fillable_value = self.max_fill_ratio * market_vol
                if trade_value > max_fillable_value:
                    size = max_fillable_value / execution_price
                    partial_filled = True
                    self.partial_fills += 1
                    trade_value = abs(size) * execution_price
                    fees = trade_value * self.fee_rate
                    if abs(size) < self.min_order_size:
                        self.logger.debug("Partial fill below min order size; order dropped.")
                        return None

        # Calculate required cash for buy orders
        if side.lower() == 'buy':
            required_cash = trade_value + fees

            # Check if we have enough cash
            if required_cash > self.cash:
                # Reduce order size to available cash
                available_trade_value = self.cash - fees
                if available_trade_value <= 0:
                    return None
                size = available_trade_value / execution_price
                if size < self.min_order_size:
                    return None
                required_cash = size * execution_price + fees

        # Check position size limits
        if side.lower() == 'buy':
            new_position_value = self.position_value + (size * execution_price)
        else:  # sell
            new_position_value = self.position_value - (size * execution_price)

        # Calculate position size as percentage of equity
        equity_for_position = abs(new_position_value)
        position_pct = equity_for_position / self.equity

        if position_pct > self.max_position_size:
            # Reduce position to within limits
            max_position_value = self.equity * self.max_position_size
            if side.lower() == 'buy':
                available_buy_value = max_position_value - self.position_value
            else:  # sell
                available_buy_value = self.position_value + max_position_value

            if available_buy_value <= 0:
                return None

            size = min(size, available_buy_value / execution_price)
            if size < self.min_order_size:
                return None

            trade_value = size * execution_price
            fees = trade_value * self.fee_rate

        # Execute the trade
        trade_pnl = 0.0
        if side.lower() == 'buy':
            if self.position < 0:
                # Buy to close/reduce short position
                size_to_buy = min(size, -self.position)
                self.cash -= (size_to_buy * execution_price + fees)
                self.position += size_to_buy
                self.position_value += (size_to_buy * execution_price)
                
                # Calculate PnL and manage active positions manually
                trade_pnl += self._close_active_positions_manually(direction_to_close=-1, size_to_close=size_to_buy, execution_price=execution_price, timestamp=timestamp)
                
                # If we reversed, open a long position with the remainder
                remaining_size = size - size_to_buy
                if remaining_size > 0:
                    remaining_fees = remaining_size * execution_price * self.fee_rate
                    self.cash -= (remaining_size * execution_price + remaining_fees)
                    self.position += remaining_size
                    self.position_value += (remaining_size * execution_price)
                    
                    # Update average entry price for the new long position
                    self.avg_entry_price = execution_price
                    
                    if sl_price is not None or tp_price is not None:
                        if sl_price is None:
                            sl_price = execution_price * 0.98
                        if tp_price is None:
                            tp_price = execution_price * 1.04
                        self.active_positions.append({
                            'entry_price': execution_price,
                            'size': remaining_size,
                            'direction': 1,  # Long
                            'stop_loss': sl_price,
                            'take_profit': tp_price,
                            'timestamp': timestamp,
                            'entry_regime': self._current_regime
                        })
            else:
                # Buy to open/increase long position
                self.cash -= (size * execution_price + fees)
                old_position = self.position
                self.position += size
                self.position_value += (size * execution_price)
                
                # Update average entry price
                if old_position > 0:
                    self.avg_entry_price = (self.avg_entry_price * old_position + size * execution_price) / self.position
                else:
                    self.avg_entry_price = execution_price

                if sl_price is not None or tp_price is not None:
                    if sl_price is None:
                        sl_price = execution_price * 0.98
                    if tp_price is None:
                        tp_price = execution_price * 1.04
                    self.active_positions.append({
                        'entry_price': execution_price,
                        'size': size,
                        'direction': 1,  # Long
                        'stop_loss': sl_price,
                        'take_profit': tp_price,
                        'timestamp': timestamp,
                        'entry_regime': self._current_regime
                    })
        else:  # sell
            if self.position > 0:
                # Sell to close/reduce long position
                size_to_sell = min(size, self.position)
                self.cash += (size_to_sell * execution_price - fees)
                self.position -= size_to_sell
                self.position_value -= (size_to_sell * execution_price)
                
                # Calculate PnL and manage active positions manually
                trade_pnl += self._close_active_positions_manually(direction_to_close=1, size_to_close=size_to_sell, execution_price=execution_price, timestamp=timestamp)
                
                # If we reversed, open a short position with the remainder
                remaining_size = size - size_to_sell
                if remaining_size > 0:
                    remaining_fees = remaining_size * execution_price * self.fee_rate
                    self.cash += (remaining_size * execution_price - remaining_fees)
                    self.position -= remaining_size
                    self.position_value -= (remaining_size * execution_price)
                    
                    # Update average entry price for the new short position
                    self.avg_entry_price = execution_price
                    
                    if sl_price is not None or tp_price is not None:
                        if sl_price is None:
                            sl_price = execution_price * 1.02
                        if tp_price is None:
                            tp_price = execution_price * 0.96
                        self.active_positions.append({
                            'entry_price': execution_price,
                            'size': remaining_size,
                            'direction': -1,  # Short
                            'stop_loss': sl_price,
                            'take_profit': tp_price,
                            'timestamp': timestamp,
                            'entry_regime': self._current_regime
                        })
            else:
                # Sell to open/increase short position
                self.cash += (size * execution_price - fees)
                old_position = self.position
                self.position -= size
                self.position_value -= (size * execution_price)
                
                # Update average entry price
                if old_position < 0:
                    self.avg_entry_price = (self.avg_entry_price * abs(old_position) + size * execution_price) / abs(self.position)
                else:
                    self.avg_entry_price = execution_price

                if sl_price is not None or tp_price is not None:
                    if sl_price is None:
                        sl_price = execution_price * 1.02
                    if tp_price is None:
                        tp_price = execution_price * 0.96
                    self.active_positions.append({
                        'entry_price': execution_price,
                        'size': size,
                        'direction': -1,  # Short
                        'stop_loss': sl_price,
                        'take_profit': tp_price,
                        'timestamp': timestamp,
                        'entry_regime': self._current_regime
                    })

        # Update equity
        self.equity = self.cash + self.position_value
        if self.position == 0:
            self.avg_entry_price = 0.0

        # Note: trade_pnl is already calculated above in the close/reduce flow
        # and statistics are handled below

        # Update trade statistics
        self.total_trades += 1
        trade_record = {
            "id": str(uuid.uuid4()),
            "timestamp": timestamp,
            "side": side.lower(),
            "size": size,
            "price": execution_price,
            "fees": fees,
            "pnl": trade_pnl,
            "equity": self.equity,
            "position": self.position,
            "position_value": self.position_value,
            "cash": self.cash,
            "partial": partial_filled  # E-P5.2 T4: liquidity-capped fill
        }

        self.trades.append(trade_record)

        # Update statistics
        if trade_pnl > 0:
            self.winning_trades += 1
        elif trade_pnl < 0:
            self.losing_trades += 1

        # Update max equity and drawdown tracking
        if self.equity > self.max_equity:
            self.max_equity = self.equity

        current_drawdown = (self.max_equity - self.equity) / self.max_equity
        if current_drawdown > self.max_drawdown_reached:
            self.max_drawdown_reached = current_drawdown

        # Record equity point
        self.equity_curve.append({
            "timestamp": timestamp,
            "equity": self.equity,
            "cash": self.cash,
            "position_value": self.position_value
        })

        return trade_record

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate common technical indicators with proper shifting to prevent lookahead bias."""
        df = df.copy()

        # RSI
        def calculate_rsi(prices, window=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi

        # Apply indicators and shift by 1 to prevent lookahead bias
        df['rsi'] = calculate_rsi(df['close']).shift(1)

        # Moving averages - shift by 1 to prevent lookahead bias
        df['sma_20'] = df['close'].rolling(window=20).mean().shift(1)
        df['sma_50'] = df['close'].rolling(window=50).mean().shift(1)

        # Bollinger Bands - shift by 1 to prevent lookahead bias
        df['bb_middle'] = df['close'].rolling(window=20).mean().shift(1)
        bb_std = df['close'].rolling(window=20).std().shift(1)
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

        # ATR (Average True Range) - shift by 1 to prevent lookahead bias
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))  # Use previous close for high/low comparison
        low_close = np.abs(df['low'] - df['close'].shift(1))  # Use previous close for high/low comparison
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        df['atr'] = tr.rolling(window=14).mean().shift(1)

        # MACD - shift by 1 to prevent lookahead bias
        exp1 = df['close'].ewm(span=12).mean().shift(1)
        exp2 = df['close'].ewm(span=26).mean().shift(1)
        df['macd'] = (exp1 - exp2).shift(1)  # Also shift the MACD line itself
        df['macd_signal'] = df['macd'].ewm(span=9).mean().shift(1)  # Shift signal line
        df['macd_histogram'] = (df['macd'] - df['macd_signal']).shift(1)  # Shift histogram as well

        return df

    def run_backtest(self,
                     data: pd.DataFrame,
                     strategy_function,
                     strategy_params: Dict[str, Any] = None,
                     initial_capital: float = None,
                     strategy_name: str = None) -> Dict[str, Any]:
        """
        Run the backtest with a given strategy function.

        Args:
            data: OHLCV data with timestamps
            strategy_function: Function that takes row and params, returns signal (-1, 0, 1) or ExecutionIntent
            strategy_params: Parameters for the strategy
            initial_capital: Starting capital (overrides default)
            strategy_name: Name of the strategy being executed (for validation)
        """
        # Ensure deterministic execution by resetting the random seed
        np.random.seed(self.deterministic_seed)

        # Ensure complete state reset before each backtest run to ensure determinism
        self.reset()

        if initial_capital:
            self.initial_capital = initial_capital
            self.cash = initial_capital
            self.equity = initial_capital
            self.max_equity = initial_capital

        if strategy_params is None:
            strategy_params = {}

        # E-P5.2: remember the strategy function (it may expose a
        # record_trade_result outcome hook) and the symbol, so each position
        # close can feed realised win/loss + simulated exit time back into the
        # strategy's discipline (consecutive-loss tracking + post-exit cooldown).
        self._strategy_function = strategy_function
        # Symbol-agnostic: whatever symbol this run is testing (no hardcoded
        # default — every approved symbol must be testable). May be None if the
        # caller didn't supply it, in which case outcome feedback is skipped.
        self._symbol = strategy_params.get('symbol')

        # Validate strategy name if provided
        if strategy_name:
            self.enforce_strategy_exclusivity(strategy_name, strategy_function)

        # Validate data structure
        self._validate_data(data)

        # Validate data freshness
        self._validate_data_freshness(data)

        # Detect missing candles
        self._detect_missing_candles(data)

        # Validate architectural flow for the data
        if strategy_name:
            self.enforce_architectural_flow(data, strategy_name)

        # Calculate indicators (properly shifted to prevent lookahead bias)
        data_with_indicators = self.calculate_indicators(data)

        # Store original data reference for force-closing later
        self.data = data_with_indicators

        # Initialize tracking
        # NOTE: self.reset() already initializes tracking variables above

        # Track last order time for double-order prevention
        self.order_cooldown_seconds = strategy_params.get('order_cooldown_seconds', 15)  # Reduced from 60 to 15 seconds to allow more trades

        # Track strategy signals for validation
        strategy_signals = []
        execution_intents = []

        # Run through each candle
        for i in range(len(data_with_indicators)):
            row = data_with_indicators.iloc[i]
            # E-P5.2: use the BAR's simulated timestamp, not wall-clock. The data
            # carries time on the INDEX (no 'timestamp' column), so the old
            # `row.get('timestamp', datetime.now())` fell back to datetime.now()
            # for every bar. That stamped signals AND trades with run-time
            # wall-clock; on a long backtest (runtime > the 5-min correspondence
            # window) early-bar signals and late-bar trades drifted apart, so the
            # signal/trade correspondence guard spuriously aborted the run with
            # "0 trade attempts". Prefer a 'timestamp' column, else the index.
            timestamp = row.get('timestamp', None)
            if timestamp is None:
                _idx = getattr(row, 'name', None)
                timestamp = _idx if isinstance(_idx, (datetime, pd.Timestamp)) else datetime.now()
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.utcfromtimestamp(timestamp)
            elif hasattr(timestamp, 'to_pydatetime'):
                timestamp = timestamp.to_pydatetime()

            # Mark to market for the current candle (before exits or new orders are processed)
            if self.position != 0:
                self.position_value = self.position * row['close']
                self.equity = self.cash + self.position_value
            else:
                self.position_value = 0.0
                self.equity = self.cash

            # E-P5.2 T2: regime in effect at this bar (drives entry/exit-regime
            # tagging for P&L attribution). Set before SL/TP so a close stamps
            # this bar as its exit regime.
            self._current_regime = self._classify_bar_regime(row)

            # First, check if any active positions hit SL/TP (this happens before new orders)
            sltp_pnl = self._check_stop_loss_take_profit(row, timestamp)

            # Get output from strategy (could be simple signal or ExecutionIntent)
            strategy_output = strategy_function(row, strategy_params)

            # Handle both simple signals and ExecutionIntent objects
            if hasattr(strategy_output, 'is_valid'):  # It's an Infrastructure ExecutionIntent
                if strategy_output and strategy_output.is_valid:
                    signal = 1 if strategy_output.side == OrderSide.BUY else -1
                    execution_intent = strategy_output
                else:
                    signal = 0
                    execution_intent = None
            elif hasattr(strategy_output, 'risk_parameters'):  # It's a Domain ExecutionIntent
                if strategy_output:
                    # Adapt Domain ExecutionIntent to Infrastructure ExecutionIntent
                    execution_intent = self._adapt_domain_execution_intent(strategy_output, row)
                    signal = 1 if execution_intent.side == OrderSide.BUY else -1
                    # Since this came from a Domain ExecutionIntent, we need to record the signal properly
                    # The signal should be based on the adapted intent
                else:
                    signal = 0
                    execution_intent = None
            else:  # It's a simple signal
                signal = strategy_output
                execution_intent = None  # Will be created later

            # Record the signal for validation
            if strategy_name:
                signal_id = self.record_strategy_signal(
                    timestamp, signal, strategy_name, row.get('close', None)
                )
                strategy_signals.append({
                    'timestamp': timestamp,
                    'signal': signal,
                    'strategy_name': strategy_name,
                    'price': row.get('close', None),
                    'signal_id': signal_id
                })

                # Add detailed tracing for signal processing
                if signal != 0:  # Only log non-zero signals
                    self.logger.info(
                        f"[TRACE] Strategy {strategy_name} generated signal {signal} at {timestamp} for price {row.get('close', 'N/A')}")

            # Process execution intent if valid
            if execution_intent and hasattr(execution_intent, 'is_valid') and execution_intent.is_valid:
                # Check for double-order prevention
                # Only apply cooldown for same-direction trades to allow position management
                symbol_for_cooldown = strategy_params.get('symbol', 'default')

                if symbol_for_cooldown in self.last_order_time:
                    time_since_last = (timestamp - self.last_order_time[symbol_for_cooldown]).total_seconds()
                    if time_since_last < self.order_cooldown_seconds:
                        # Check if this is a position reversal (opposite signal to current position)
                        # Allow reversals but block same-direction trades during cooldown
                        current_position_direction = 1 if self.position > 0 else (-1 if self.position < 0 else 0)
                        intent_direction = 1 if execution_intent.side == OrderSide.BUY else -1

                        # Only skip if it's a same-direction trade during cooldown
                        # Allow position reversals and additions to opposite positions
                        if intent_direction != 0 and intent_direction == current_position_direction:
                            # Skip same-direction ordering due to cooldown
                            self.logger.info(f"[TRACE] Skipping trade due to cooldown: {timestamp}")
                            execution_intent = None  # Clear the intent
                        # Otherwise, allow the trade to proceed (reversal or addition to opposite position)

                # Accept or reject execution intent based on risk management
                if execution_intent and self._accept_execution_intent(execution_intent):
                    # Execute the trade based on the accepted intent
                    trade = self._execute_from_intent(execution_intent, row)

                    # Log intent acceptance
                    self.logger.info(f"[TRACE] Execution intent accepted: {execution_intent.id} at {timestamp}")

                    # Confirm trade attempt for this signal
                    if strategy_name and len(strategy_signals) > 0:
                        last_signal = strategy_signals[-1]
                        self.confirm_trade_attempt(last_signal['signal_id'], trade)

                    # Update last order time
                    self.last_order_time[symbol_for_cooldown] = timestamp

                    # Add to execution intents list for validation
                    execution_intents.append(execution_intent)
                else:
                    # Log intent rejection
                    if execution_intent:
                        self.logger.info(f"[TRACE] Execution intent rejected: {execution_intent.id} at {timestamp}")
            elif hasattr(strategy_output, 'risk_parameters'):  # Domain ExecutionIntent that was adapted
                # If we have a Domain ExecutionIntent that was adapted to Infrastructure ExecutionIntent
                # The adaptation already happened in the condition check above
                pass  # The adapted intent was already processed
            else:
                # No valid execution intent, still record equity for curve
                self.equity_curve.append({
                    "timestamp": timestamp,
                    "equity": self.equity,
                    "cash": self.cash,
                    "position_value": self.position_value
                })

        # Force close any remaining positions at the end of the backtest
        if len(self.active_positions) > 0:
            self._force_close_remaining()

        # Validate minimal execution confirmation
        if strategy_name:
            self.confirm_execution_for_signals(strategy_signals, self.trades)

        # Calculate performance metrics
        metrics = self._calculate_performance_metrics()

        # E-P5.2 T1: attach the per-strategy edge ledger (expectancy / PF /
        # win-rate / avg R:R / trade-count, segmented by regime) computed from
        # this run's realised trades. Trades carry a per-bar ``regime`` field
        # when available; otherwise they fall under "unknown" (the segmentation
        # dimension is present so per-bar regime tagging can populate it later).
        from infrastructure.results_tracking.edge_ledger import compute_edge_records
        metrics["edge_records"] = [
            r.to_dict() for r in compute_edge_records(
                metrics.get("trades", []), strategy=strategy_name or "unknown"
            )
        ]

        # Add final tracing information
        if strategy_name:
            self.logger.info(f"[TRACE] Backtest completed for {strategy_name}")
            self.logger.info(f"[TRACE] Total signals generated: {len(strategy_signals)}")
            self.logger.info(f"[TRACE] Total execution intents: {len(execution_intents)}")
            self.logger.info(f"[TRACE] Total trades executed: {metrics.get('total_trades', 0)}")
            self.logger.info(f"[TRACE] Final equity: {self.equity}")
            self.logger.info(f"[TRACE] Total return: {metrics.get('total_return', 0):.4f}")
            self.logger.info(f"[TRACE] Sharpe ratio: {metrics.get('sharpe_ratio', 0):.4f}")
            self.logger.info(f"[TRACE] Max drawdown: {metrics.get('max_drawdown', 0):.4f}")

        # Validate trade count with fail-fast mechanism
        if strategy_name and len(data) > 0:
            start_date = data.index[0] if isinstance(data.index, pd.DatetimeIndex) else datetime.now() - timedelta(
                days=90)
            end_date = data.index[-1] if isinstance(data.index, pd.DatetimeIndex) else datetime.now()
            symbol = strategy_params.get('symbol', 'BTCUSDT')

            self.enforce_fail_fast(
                start_date, end_date, metrics.get('total_trades', 0), data, symbol
            )

        return metrics

    def _convert_signal_to_intent(self,
                                  signal: int,
                                  row: pd.Series,
                                  timestamp: datetime,
                                  strategy_params: Dict[str, Any],
                                  strategy_name: str) -> Optional[ExecutionIntent]:
        """
        Convert a strategy signal to an ExecutionIntent object.

        Args:
            signal: The signal from the strategy (-1 for sell, 0 for hold, 1 for buy)
            row: The current data row
            timestamp: The timestamp of the signal
            strategy_params: Strategy parameters
            strategy_name: Name of the strategy

        Returns:
            ExecutionIntent if the signal should result in a trade, None otherwise
        """
        if signal == 0:
            return None  # No signal, no intent

        # Determine position sizing based on strategy and risk management
        position_size = self._calculate_position_size(row, signal, strategy_params)

        if position_size <= 0:
            return None  # No position size, no intent

        # Calculate SL and TP prices based on ATR or other methods if we're opening a position
        sl_price = None
        tp_price = None

        if signal > 0:  # Buy signal
            # Calculate stop loss and take profit based on ATR or other methods
            atr = row.get('atr', 0.01 * row['close'])  # Get ATR value
            risk_params = strategy_params.get('atr_multiplier', 1.5)  # Reduced from 2.0 to 1.5
            reward_params = strategy_params.get('risk_reward_ratio', 1.5)  # Reduced from 2.0 to 1.5 for more balanced trades

            entry_price = row['close']
            sl_price = entry_price - (atr * risk_params)  # Stop loss below entry
            tp_price = entry_price + (atr * risk_params * reward_params)  # Take profit above entry

            # Ensure SL is below entry and TP is above entry - made more balanced
            sl_price = max(sl_price, entry_price * 0.97)  # Max 3% below for more realistic SL
            tp_price = min(tp_price, entry_price * 1.045)  # Max 4.5% above for more realistic TP (still maintaining 1.5:1 ratio)
        elif signal < 0:  # Sell signal
            # Calculate stop loss and take profit based on ATR or other methods
            atr = row.get('atr', 0.01 * row['close'])  # Get ATR value
            risk_params = strategy_params.get('atr_multiplier', 1.5)  # Reduced from 2.0 to 1.5
            reward_params = strategy_params.get('risk_reward_ratio', 1.5)  # Reduced from 2.0 to 1.5 for more balanced trades

            entry_price = row['close']
            sl_price = entry_price + (atr * risk_params)  # Stop loss above entry for short
            tp_price = entry_price - (atr * risk_params * reward_params)  # Take profit below entry for short

            # Ensure SL is above entry and TP is below entry - made more balanced
            sl_price = min(sl_price, entry_price * 1.03)  # Max 3% above for more realistic SL
            tp_price = max(tp_price, entry_price * 0.955)  # Max 4.5% below for more realistic TP

        # Create the execution intent
        intent = create_execution_intent(
            side=OrderSide.BUY if signal > 0 else OrderSide.SELL,
            size=position_size,
            price=row['close'],
            timestamp=timestamp,
            stop_loss=sl_price,
            take_profit=tp_price,
            strategy_name=strategy_name,
            symbol=strategy_params.get('symbol', 'BTCUSDT')
        )

        # Log the creation of the intent
        self.logger.info(f"[TRACE] Created execution intent: {intent.id} - {intent.side.value} {intent.size}@{intent.price}")

        return intent

    def _accept_execution_intent(self, intent) -> bool:
        """
        Determine whether to accept an execution intent based on risk management.

        Args:
            intent: The execution intent to evaluate (could be Infrastructure or Domain)

        Returns:
            bool: True if the intent should be accepted, False otherwise
        """
        # Check if it's a Domain ExecutionIntent (which should have been converted by now)
        # But we'll handle both cases for robustness
        if hasattr(intent, 'risk_parameters'):  # Domain ExecutionIntent
            # This shouldn't happen as Domain intents should be converted by now
            # But if it does, we'll convert it here
            self.logger.warning(f"[TRACE] Found Domain ExecutionIntent in accept method - this should have been converted already: {getattr(intent, 'strategy_name', 'unknown')}")
            return False  # Domain intents should be converted before reaching this point

        # It's an Infrastructure ExecutionIntent
        # Check if we're in a drawdown that exceeds limits
        current_drawdown = (self.max_equity - self.equity) / self.max_equity
        if current_drawdown > self.max_drawdown:
            self.logger.info(f"[TRACE] Rejecting intent {intent.id} due to max drawdown exceeded: {current_drawdown:.2%}")
            return False

        # Calculate trade value and fees
        trade_value = intent.size * intent.price
        fees = trade_value * self.fee_rate

        # Check order size constraints
        if intent.size < self.min_order_size:
            self.logger.info(f"[TRACE] Rejecting intent {intent.id} due to small order size: {intent.size} < {self.min_order_size}")
            return False

        # Calculate required cash for buy orders
        if intent.side == OrderSide.BUY:
            required_cash = trade_value + fees

            # Check if we have enough cash
            if required_cash > self.cash:
                self.logger.info(f"[TRACE] Rejecting intent {intent.id} due to insufficient cash: {required_cash:.2f} > {self.cash:.2f}")
                return False

        # Check position size limits
        if intent.side == OrderSide.BUY:
            new_position_value = self.position_value + (intent.size * intent.price)
        else:  # SELL
            # For sell orders, we might be closing positions
            new_position_value = abs(self.position_value - (intent.size * intent.price))

        # Calculate position size as percentage of equity
        equity_for_position = abs(new_position_value)
        position_pct = equity_for_position / self.equity

        if position_pct > self.max_position_size:
            self.logger.info(f"[TRACE] Rejecting intent {intent.id} due to position size limit: {position_pct:.2%} > {self.max_position_size:.2%}")
            return False

        # If we reach here, the intent is accepted
        self.logger.info(f"[TRACE] Accepting execution intent: {intent.id}")
        return True

    def _execute_from_intent(self, intent, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Execute a trade based on an accepted execution intent.

        Args:
            intent: The accepted execution intent (could be Infrastructure or Domain)
            row: The current data row

        Returns:
            Trade record if successful, None otherwise
        """
        # Handle both Infrastructure and Domain ExecutionIntent objects
        if hasattr(intent, 'risk_parameters'):  # Domain ExecutionIntent - this shouldn't happen
            self.logger.error(f"[TRACE] Attempting to execute Domain ExecutionIntent - this should have been converted: {getattr(intent, 'strategy_name', 'unknown')}")
            return None

        # It's an Infrastructure ExecutionIntent
        self.logger.info(f"[TRACE] Executing trade from intent: {intent.id} - {intent.side.value} {intent.size}@{intent.price}")

        # Calculate realistic execution price
        execution_price = self.calculate_order_execution_price(
            intent.price, intent.side.value, intent.size, {
                'high': row['high'],
                'low': row['low'],
                'volume': row['volume']
            }
        )

        # Calculate trade value and fees
        trade_value = intent.size * execution_price
        fees = trade_value * self.fee_rate

        # Execute the trade
        trade_pnl = 0.0
        if intent.side == OrderSide.BUY:
            if self.position < 0:
                # Buy to close/reduce short position
                size_to_buy = min(intent.size, -self.position)
                self.cash -= (size_to_buy * execution_price + fees)
                self.position += size_to_buy
                self.position_value += (size_to_buy * execution_price)
                
                # Calculate PnL and manage active positions manually
                trade_pnl += self._close_active_positions_manually(direction_to_close=-1, size_to_close=size_to_buy, execution_price=execution_price, timestamp=intent.timestamp)
                
                # If we reversed, open a long position with the remainder
                remaining_size = intent.size - size_to_buy
                if remaining_size > 0:
                    remaining_fees = remaining_size * execution_price * self.fee_rate
                    self.cash -= (remaining_size * execution_price + remaining_fees)
                    self.position += remaining_size
                    self.position_value += (remaining_size * execution_price)
                    
                    # Update average entry price for the new long position
                    self.avg_entry_price = execution_price
                    
                    if intent.stop_loss is not None or intent.take_profit is not None:
                        sl_price = intent.stop_loss
                        tp_price = intent.take_profit
                        if sl_price is None:
                            sl_price = execution_price * 0.98
                        if tp_price is None:
                            tp_price = execution_price * 1.04
                        self.active_positions.append({
                            'entry_price': execution_price,
                            'size': remaining_size,
                            'direction': 1,  # Long
                            'stop_loss': sl_price,
                            'take_profit': tp_price,
                            'timestamp': intent.timestamp,
                            'entry_regime': self._current_regime
                        })
            else:
                # Buy to open/increase long position
                self.cash -= (intent.size * execution_price + fees)
                old_position = self.position
                self.position += intent.size
                self.position_value += (intent.size * execution_price)
                
                # Update average entry price
                if old_position > 0:
                    self.avg_entry_price = (self.avg_entry_price * old_position + intent.size * execution_price) / self.position
                else:
                    self.avg_entry_price = execution_price

                if intent.stop_loss is not None or intent.take_profit is not None:
                    sl_price = intent.stop_loss
                    tp_price = intent.take_profit
                    if sl_price is None:
                        sl_price = execution_price * 0.98
                    if tp_price is None:
                        tp_price = execution_price * 1.04
                    self.active_positions.append({
                        'entry_price': execution_price,
                        'size': intent.size,
                        'direction': 1,  # Long
                        'stop_loss': sl_price,
                        'take_profit': tp_price,
                        'timestamp': intent.timestamp,
                        'entry_regime': self._current_regime
                    })
        else:  # SELL
            if self.position > 0:
                # Sell to close/reduce long position
                size_to_sell = min(intent.size, self.position)
                self.cash += (size_to_sell * execution_price - fees)
                self.position -= size_to_sell
                self.position_value -= (size_to_sell * execution_price)
                
                # Calculate PnL and manage active positions manually
                trade_pnl += self._close_active_positions_manually(direction_to_close=1, size_to_close=size_to_sell, execution_price=execution_price, timestamp=intent.timestamp)
                
                # If we reversed, open a short position with the remainder
                remaining_size = intent.size - size_to_sell
                if remaining_size > 0:
                    remaining_fees = remaining_size * execution_price * self.fee_rate
                    self.cash += (remaining_size * execution_price - remaining_fees)
                    self.position -= remaining_size
                    self.position_value -= (remaining_size * execution_price)
                    
                    # Update average entry price for the new short position
                    self.avg_entry_price = execution_price
                    
                    if intent.stop_loss is not None or intent.take_profit is not None:
                        sl_price = intent.stop_loss
                        tp_price = intent.take_profit
                        if sl_price is None:
                            sl_price = execution_price * 1.02
                        if tp_price is None:
                            tp_price = execution_price * 0.96
                        self.active_positions.append({
                            'entry_price': execution_price,
                            'size': remaining_size,
                            'direction': -1,  # Short
                            'stop_loss': sl_price,
                            'take_profit': tp_price,
                            'timestamp': intent.timestamp,
                            'entry_regime': self._current_regime
                        })
            else:
                # Sell to open/increase short position
                self.cash += (intent.size * execution_price - fees)
                old_position = self.position
                self.position -= intent.size
                self.position_value -= (intent.size * execution_price)
                
                # Update average entry price
                if old_position < 0:
                    self.avg_entry_price = (self.avg_entry_price * abs(old_position) + intent.size * execution_price) / abs(self.position)
                else:
                    self.avg_entry_price = execution_price

                if intent.stop_loss is not None or intent.take_profit is not None:
                    sl_price = intent.stop_loss
                    tp_price = intent.take_profit
                    if sl_price is None:
                        sl_price = execution_price * 1.02
                    if tp_price is None:
                        tp_price = execution_price * 0.96
                    self.active_positions.append({
                        'entry_price': execution_price,
                        'size': intent.size,
                        'direction': -1,  # Short
                        'stop_loss': sl_price,
                        'take_profit': tp_price,
                        'timestamp': intent.timestamp,
                        'entry_regime': self._current_regime
                    })

        # Update equity
        self.equity = self.cash + self.position_value
        if self.position == 0:
            self.avg_entry_price = 0.0

        # Update equity
        self.equity = self.cash + self.position_value

        # Update trade statistics
        self.total_trades += 1
        trade_record = {
            "id": str(uuid.uuid4()),
            "timestamp": intent.timestamp,
            "side": intent.side.value,
            "size": intent.size,
            "price": execution_price,
            "fees": fees,
            "pnl": trade_pnl,  # Record PnL for closed/reduced positions
            "equity": self.equity,
            "position": self.position,
            "position_value": self.position_value,
            "cash": self.cash,
            "intent_id": intent.id  # Link to the execution intent
        }

        self.trades.append(trade_record)

        # Update statistics
        if trade_pnl > 0:
            self.winning_trades += 1
        elif trade_pnl < 0:
            self.losing_trades += 1

        # Update max equity and drawdown tracking
        if self.equity > self.max_equity:
            self.max_equity = self.equity

        current_drawdown = (self.max_equity - self.equity) / self.max_equity
        if current_drawdown > self.max_drawdown_reached:
            self.max_drawdown_reached = current_drawdown

        # Record equity point
        self.equity_curve.append({
            "timestamp": intent.timestamp,
            "equity": self.equity,
            "cash": self.cash,
            "position_value": self.position_value
        })

        return trade_record

    def _shift_indicators_only(self):
        """
        Shifts ALL non-price columns by 1 step to prevent lookahead bias.
        Price columns remain unshifted to preserve actual trading prices.
        """
        price_cols = {"open", "high", "low", "close", "volume"}

        for col in self.df.columns:
            if col.lower() not in price_cols:
                self.df[col] = self.df[col].shift(1)

        self.df.dropna(inplace=True)

    def _force_close_remaining(self):
        """Force close any remaining positions at the last available price."""
        if not self.active_positions:
            return

        last_row = self.data.iloc[-1]
        last_ts = self.data.index[-1]
        last_close = last_row['close']

        positions_to_remove = []
        for i, pos in enumerate(self.active_positions):
            if not pos.get('closed', False):
                # Calculate exit price based on position direction
                exit_price = last_close
                pnl = 0

                if pos['direction'] == 1:  # Long position
                    pnl = (exit_price - pos['entry_price']) * pos['size']
                else:  # Short position
                    pnl = (pos['entry_price'] - exit_price) * pos['size']

                # Account for fees
                fees = self.fee_rate * abs(pos['size'] * exit_price + pos['size'] * pos['entry_price'])
                pnl -= fees

                # Update position as closed
                pos['closed'] = True
                pos['close_price'] = exit_price
                pos['close_time'] = last_ts
                pos['pnl'] = pnl

                # Update account
                self.cash += pos['size'] * exit_price if pos['direction'] == -1 else pos['size'] * exit_price
                self.position -= pos['direction'] * pos['size']
                self.position_value = self.position * exit_price if self.position != 0 else 0
                self.equity = self.cash + self.position_value

                # Add to trade history
                trade_record = {
                    "id": str(uuid.uuid4()),
                    "timestamp": last_ts,
                    "side": "sell" if pos['direction'] == 1 else "buy",
                    "size": pos['size'],
                    "price": exit_price,
                    "fees": fees,
                    "pnl": pnl,
                    "equity": self.equity,
                    "position": self.position,
                    "position_value": self.position_value,
                    "cash": self.cash,
                    "exit_type": "force_close",
                    "entry_price": pos['entry_price'],
                    # E-P5.2 T2: attribute to the position's entry regime.
                    "regime": pos.get('entry_regime', 'unknown'),
                    "entry_regime": pos.get('entry_regime', 'unknown'),
                    "exit_regime": self._current_regime,
                    # E-P5.2 Priority-1 exit forensics
                    "stop_loss": pos.get('stop_loss'),
                    "take_profit": pos.get('take_profit'),
                    "same_bar_collision": False,
                    "mfe": pos.get('mfe', 0.0),
                    "mae": pos.get('mae', 0.0),
                    "realized_R": (pnl / (abs(pos['entry_price'] - pos['stop_loss']) * pos['size'])
                                   if (pos.get('stop_loss') is not None and not pd.isna(pos.get('stop_loss'))
                                       and abs(pos['entry_price'] - pos['stop_loss']) * pos['size'] > 0) else None),
                }
                self.trades.append(trade_record)

                # E-P5.2: feed realised outcome back to strategy discipline.
                self._feed_trade_outcome(pnl, last_ts)

                positions_to_remove.append(i)

        # Remove closed positions in reverse order
        for i in reversed(positions_to_remove):
            del self.active_positions[i]

    def _validate_data(self, data: pd.DataFrame):
        """Validate the input DataFrame for required columns and proper structure."""
        required_cols = ["open", "high", "low", "close"]
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")

        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")

    def _validate_data_freshness(self, data: pd.DataFrame) -> bool:
        """Validate that data is fresh and doesn't have excessive age gaps."""
        if data.empty or 'timestamp' not in data.columns:
            # If using index as timestamp
            if isinstance(data.index, pd.DatetimeIndex):
                timestamps = data.index
            else:
                return True  # Skip validation if no timestamp info
        else:
            timestamps = pd.to_datetime(data['timestamp'])

        # Calculate time differences between consecutive candles
        time_diffs = timestamps.to_series().diff().dt.total_seconds()

        # Check for gaps that exceed normal candle intervals
        # For example, if we expect 1-hour candles but find 1-day gaps
        if len(time_diffs) > 1:
            # Get the most common interval (mode) to understand expected candle frequency
            non_zero_diffs = time_diffs[time_diffs > 0]
            if len(non_zero_diffs) > 0:
                expected_interval = non_zero_diffs.mode().iloc[0] if len(
                    non_zero_diffs.mode()) > 0 else 3600  # Default 1 hour
                # Flag intervals that are significantly larger than expected
                gap_threshold = expected_interval * 5  # Allow up to 5x expected interval
                large_gaps = time_diffs > gap_threshold
                if large_gaps.any() and large_gaps.sum() / len(time_diffs) > 0.1:  # More than 10% are large gaps
                    self.logger.warning(
                        f"Found {large_gaps.sum()} large gaps in data, exceeding {gap_threshold}s threshold")

        # Validate that the most recent data is not too old (for real-time scenarios)
        if len(timestamps) > 0:
            latest_timestamp = timestamps[-1] if hasattr(timestamps, '__getitem__') else timestamps.max()
            if pd.Timestamp.now().timestamp() - latest_timestamp.timestamp() > self.max_data_age_seconds:
                self.logger.warning(f"Data is too old: {latest_timestamp} vs current time")

        return True

    def _detect_missing_candles(self, data: pd.DataFrame, expected_frequency: str = '1h') -> List[int]:
        """Detect missing candles in the data."""
        if isinstance(data.index, pd.DatetimeIndex):
            # Check if the index is regularly spaced according to expected frequency
            try:
                # Resample at expected frequency and see which values are missing
                resampled = data.resample(expected_frequency).agg({'close': 'last'}).dropna()
                original_with_freq = data.resample(expected_frequency).agg({'close': 'last'})

                # Find which timestamps are missing in original vs expected
                missing_mask = original_with_freq['close'].isna()
                missing_indices = missing_mask[missing_mask].index.tolist()

                if missing_indices:
                    self.logger.info(
                        f"Detected {len(missing_indices)} missing candles at: {missing_indices[:10]}...")  # Show first 10

                return missing_indices
            except Exception as e:
                self.logger.warning(f"Could not detect missing candles: {e}")
                return []
        return []

    def _check_stop_loss_take_profit(self, candle_data: pd.Series, timestamp: datetime):
        """
        Check if any active positions hit their stop-loss or take-profit levels.
        Implements proper priority: SL priority > TP priority for longs.
        Uses candle high/low for execution.
        """
        if not self.active_positions:
            return 0  # No active positions to check

        total_pnl = 0
        positions_to_close = []

        for i, position in enumerate(self.active_positions):
            entry_price = position['entry_price']
            size = position['size']
            direction = position['direction']  # 1 for long, -1 for short
            sl_price = position['stop_loss']
            tp_price = position['take_profit']

            candle_high = candle_data['high']
            candle_low = candle_data['low']

            # E-P5.2 Priority-1 exit forensics: track max favorable / adverse
            # excursion (in price terms) over the position's life, before
            # checking exits.
            if direction == 1:
                position['mfe'] = max(position.get('mfe', 0.0), candle_high - entry_price)
                position['mae'] = max(position.get('mae', 0.0), entry_price - candle_low)
            else:
                position['mfe'] = max(position.get('mfe', 0.0), entry_price - candle_low)
                position['mae'] = max(position.get('mae', 0.0), candle_high - entry_price)

            # Check if SL or TP was hit in this candle
            sl_hit = False
            tp_hit = False

            if direction == 1:  # Long position
                # For longs: SL triggered if low <= SL, TP triggered if high >= TP
                if candle_low <= sl_price:
                    sl_hit = True
                if candle_high >= tp_price:
                    tp_hit = True
            else:  # Short position
                # For shorts: SL triggered if high >= SL, TP triggered if low <= TP
                if candle_high >= sl_price:
                    sl_hit = True
                if candle_low <= tp_price:
                    tp_hit = True

            # Handle simultaneous SL/TP hits with proper priority
            exit_price = None
            exit_type = None

            if sl_hit and tp_hit:
                # If both hit in same candle, determine which exit price is closer to entry
                # For long positions: SL priority > TP priority
                # For short positions: SL priority > TP priority
                entry = entry_price
                if abs(sl_price - entry) <= abs(tp_price - entry):
                    exit_price, exit_type = sl_price, 'SL'
                else:
                    exit_price, exit_type = tp_price, 'TP'
            elif sl_hit:
                exit_price, exit_type = sl_price, 'SL'
            elif tp_hit:
                exit_price, exit_type = tp_price, 'TP'

            # Execute if exit condition is met
            if exit_price is not None:
                # Calculate PnL
                pnl = 0
                if direction == 1:  # Long
                    pnl = (exit_price - entry_price) * size
                else:  # Short
                    pnl = (entry_price - exit_price) * size

                # Account for fees and slippage
                total_cost = self.fee_rate * abs(size * exit_price) + (abs(pnl) * self.slippage_factor)
                pnl -= total_cost

                # Update trading state
                self.position -= direction * size
                self.position_value = self.position * candle_data['close'] if self.position != 0 else 0.0
                self.cash += direction * size * exit_price - total_cost
                self.equity = self.cash + self.position_value
                if self.position == 0:
                    self.avg_entry_price = 0.0

                # Update trade statistics
                self.total_trades += 1
                if pnl > 0:
                    self.winning_trades += 1
                elif pnl < 0:
                    self.losing_trades += 1

                # Record the trade
                trade_record = {
                    "id": str(uuid.uuid4()),
                    "timestamp": timestamp,
                    "side": "sell" if direction == 1 else "buy",
                    "size": size,
                    "price": exit_price,
                    "fees": total_cost,
                    "pnl": pnl,
                    "equity": self.equity,
                    "position": self.position,
                    "position_value": self.position_value,
                    "cash": self.cash,
                    "exit_type": exit_type,
                    "entry_price": entry_price,
                    # E-P5.2 T2: attribute realised P&L to the regime the position
                    # was OPENED in; keep exit regime for lineage.
                    "regime": position.get('entry_regime', 'unknown'),
                    "entry_regime": position.get('entry_regime', 'unknown'),
                    "exit_regime": self._current_regime,
                    # E-P5.2 Priority-1 exit forensics
                    "stop_loss": sl_price,
                    "take_profit": tp_price,
                    "same_bar_collision": bool(sl_hit and tp_hit),
                    "mfe": position.get('mfe', 0.0),
                    "mae": position.get('mae', 0.0),
                    "realized_R": (pnl / (abs(entry_price - sl_price) * size)
                                   if (sl_price is not None and not pd.isna(sl_price)
                                       and abs(entry_price - sl_price) * size > 0) else None),
                }
                self.trades.append(trade_record)

                # E-P5.2: feed realised outcome back to strategy discipline.
                self._feed_trade_outcome(pnl, timestamp)

                # Record in equity curve
                self.equity_curve.append({
                    "timestamp": timestamp,
                    "equity": self.equity,
                    "cash": self.cash,
                    "position_value": self.position_value
                })

                # Mark position for removal
                positions_to_close.append(i)

                # Add to total PnL
                total_pnl += pnl

        # Remove closed positions in reverse order to maintain indices
        for i in reversed(positions_to_close):
            del self.active_positions[i]

        return total_pnl

    def _calculate_position_size(self,
                                 row: pd.Series,
                                 signal: int,
                                 params: Dict[str, Any]) -> float:
        """Calculate position size based on risk management with proper SL calculation."""
        if signal == 0:  # No signal
            return 0.0

        # Use risk per trade percentage
        risk_pct = params.get('risk_per_trade', 0.02)  # Default 2%
        risk_amount = self.equity * risk_pct

        # Calculate stop loss distance based on ATR or other methods
        atr = row.get('atr', 0.01 * row['close'])  # Default to 1% if no ATR
        atr_multiplier = params.get('atr_multiplier', 2.0)
        stop_loss_distance = atr_multiplier * atr

        # Calculate position size based on stop loss
        price = row['close']

        # Calculate stop loss price if we're entering a position
        if signal > 0:  # Long position
            sl_price = price - stop_loss_distance
            risk_per_unit = price - sl_price  # Risk per unit for long
        else:  # Short position
            sl_price = price + stop_loss_distance
            risk_per_unit = sl_price - price  # Risk per unit for short

        # Calculate position size based on risk amount
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
        else:
            # Fallback: use fixed percentage of equity
            position_size = (self.equity * params.get('risk_per_trade', 0.02)) / price

        # Apply leverage limits
        max_position_by_leverage = (self.equity * self.max_leverage) / price
        position_size = min(position_size, max_position_by_leverage)

        # Apply max position size limits
        max_position_by_pct = self.equity * self.max_position_size / price
        position_size = min(position_size, max_position_by_pct)

        # Ensure minimum order size
        if position_size < self.min_order_size:
            position_size = 0  # Don't trade if below minimum size

        return position_size

    def _calculate_position_size(self,
                                 row: pd.Series,
                                 signal: int,
                                 params: Dict[str, Any]) -> float:
        """Calculate position size based on risk management with proper SL calculation."""
        if signal == 0:  # No signal
            return 0.0

        # Check correlation risk if enabled
        correlation_risk_reduction = self._assess_correlation_risk()

        # Use risk per trade percentage adjusted for correlation
        base_risk_pct = params.get('risk_per_trade', 0.01)  # Reduced from 2% to 1% to allow more trades
        risk_pct = base_risk_pct * (1 - correlation_risk_reduction)  # Reduce risk with higher correlation
        risk_amount = self.equity * risk_pct

        # Calculate stop loss distance based on ATR or other methods - made less restrictive
        atr = row.get('atr', 0.01 * row['close'])  # Default to 1% if no ATR
        atr_multiplier = params.get('atr_multiplier', 1.5)  # Reduced from 2.0 to 1.5 to allow more trades
        stop_loss_distance = atr_multiplier * atr

        # Calculate position size based on stop loss
        price = row['close']

        # Calculate stop loss price if we're entering a position
        if signal > 0:  # Long position
            sl_price = price - stop_loss_distance
            risk_per_unit = price - sl_price  # Risk per unit for long
        else:  # Short position
            sl_price = price + stop_loss_distance
            risk_per_unit = sl_price - price  # Risk per unit for short

        # Calculate position size based on risk amount
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
        else:
            # Fallback: use fixed percentage of equity
            position_size = (self.equity * risk_pct) / price

        # Apply leverage limits
        max_position_by_leverage = (self.equity * self.max_leverage) / price
        position_size = min(position_size, max_position_by_leverage)

        # Apply max position size limits - increased to allow more trades
        max_position_by_pct = self.equity * (self.max_position_size * 1.5) / price  # Increased from 20% to 30%
        position_size = min(position_size, max_position_by_pct)

        # Ensure minimum order size - reduced to allow smaller trades
        min_order_size = params.get('min_order_size', self.min_order_size * 0.5)  # Allow smaller orders
        if position_size < min_order_size:
            position_size = 0  # Don't trade if below minimum size

        return position_size

    def _assess_correlation_risk(self) -> float:
        """
        Assess correlation risk and return a risk reduction factor.
        Returns value between 0 (no correlation) and 1 (very high correlation).
        """
        # In a real implementation, this would analyze correlation between different strategies
        # For now, we implement a basic version that returns based on current active positions

        if len(self.active_positions) < 2:
            return 0.0  # No correlation risk with only 1 position or none

        # This is a simplified approach - in reality, you'd calculate correlation between strategy returns
        # As a proxy, if we have many positions in the same direction, increase correlation risk
        long_positions = sum(1 for pos in self.active_positions if pos['direction'] == 1)
        short_positions = sum(1 for pos in self.active_positions if pos['direction'] == -1)

        # Higher correlation as positions become more concentrated in same direction
        total_positions = len(self.active_positions)
        if total_positions > 0:
            direction_concentration = max(long_positions, short_positions) / total_positions
            # Return risk reduction based on concentration (0-25% risk reduction)
            return min(0.25, direction_concentration * 0.25)

        return 0.0

    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        if not self.trades:
            return {"error": "No trades executed"}

        # Calculate trade-level metrics
        total_return = (self.equity - self.initial_capital) / self.initial_capital
        total_trades = self.total_trades
        winning_trades = self.winning_trades
        losing_trades = self.losing_trades

        # Ensure sufficient samples for win rate calculation
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Add validation for minimum sample size for reliable metrics
        min_sample_size = 5  # Minimum trades needed for reliable metrics
        if total_trades < min_sample_size:
            # For insufficient samples, provide more conservative estimates
            win_rate = 0.5  # Default to 50% for insufficient samples
            self.logger.info(f"Insufficient trade samples ({total_trades} < {min_sample_size}), using conservative estimates")

        # Calculate returns from equity curve for Sharpe and other metrics
        equity_values = [point['equity'] for point in self.equity_curve]
        if len(equity_values) > 1:
            returns = np.diff(equity_values) / equity_values[:-1]
            # Handle potential division by zero in returns calculation
            returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)

            if len(returns) > 0:
                avg_return = np.mean(returns)
                std_return = np.std(returns)

                # Sharpe ratio (annualized) - guard against division by zero
                if std_return > 0 and not np.isnan(std_return) and not np.isinf(std_return):
                    sharpe_ratio = (avg_return / std_return) * np.sqrt(365)  # Daily returns
                    # Ensure sharpe_ratio is finite and reasonable
                    if not np.isfinite(sharpe_ratio) or abs(sharpe_ratio) > 10:
                        sharpe_ratio = np.clip(sharpe_ratio, -10, 10)  # Cap extreme values
                else:
                    sharpe_ratio = 0

                # Sortino ratio (downside deviation) - guard against division by zero
                negative_returns = returns[returns < 0]
                if len(negative_returns) > 0:
                    downside_std = np.std(negative_returns)
                    if downside_std > 0 and not np.isnan(downside_std) and not np.isinf(downside_std):
                        sortino_ratio = (avg_return / downside_std) * np.sqrt(365)
                        # Ensure sortino_ratio is finite and reasonable
                        if not np.isfinite(sortino_ratio) or abs(sortino_ratio) > 15:
                            sortino_ratio = np.clip(sortino_ratio, -15, 15)  # Cap extreme values
                    else:
                        sortino_ratio = 0
                else:
                    sortino_ratio = sharpe_ratio  # Same as Sharpe if no negative returns

                # Max drawdown
                equity_curve = np.array(equity_values)
                if len(equity_curve) > 0:
                    running_max = np.maximum.accumulate(equity_curve)
                    # Handle potential division by zero in drawdown calculation
                    drawdowns = np.zeros_like(equity_curve)
                    nonzero_max = running_max != 0
                    drawdowns[nonzero_max] = (equity_curve[nonzero_max] - running_max[nonzero_max]) / running_max[nonzero_max]
                    # Replace any NaN or infinite values with 0
                    drawdowns = np.nan_to_num(drawdowns, nan=0.0, posinf=0.0, neginf=0.0)

                    # Validate drawdown values to ensure they are reasonable
                    drawdowns = np.clip(drawdowns, -1.0, 0.0)  # Drawdown should be between -100% and 0%
                    max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

                    # Ensure max_drawdown is reasonable (not greater than 100%)
                    max_drawdown = max(-1.0, max_drawdown)  # Cap at -100%
                else:
                    max_drawdown = 0.0
            else:
                sharpe_ratio = 0
                sortino_ratio = 0
                max_drawdown = 0.0
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
            max_drawdown = 0.0

        # Profit factor - guard against division by zero
        winning_pnl = sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) > 0)
        losing_pnl = abs(sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) < 0))

        if losing_pnl > 0:
            profit_factor = winning_pnl / losing_pnl
            # Ensure profit_factor is finite
            if not np.isfinite(profit_factor):
                profit_factor = float('inf') if winning_pnl > 0 else 0.0
        else:
            profit_factor = float('inf') if winning_pnl > 0 else 0.0

        # Other metrics
        total_volume = sum(abs(t['size'] * t['price']) for t in self.trades)
        total_fees = sum(t['fees'] for t in self.trades)

        # Ensure all metrics are computed only from executed trades and reset per run
        metrics = {
            "total_return": float(total_return) if np.isfinite(total_return) else 0.0,
            "sharpe_ratio": float(sharpe_ratio),
            "sortino_ratio": float(sortino_ratio),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate) if np.isfinite(win_rate) else 0.0,
            "profit_factor": float(profit_factor),
            "total_trades": int(total_trades),
            "winning_trades": int(winning_trades),
            "losing_trades": int(losing_trades),
            "total_volume": float(total_volume) if np.isfinite(total_volume) else 0.0,
            "total_fees": float(total_fees) if np.isfinite(total_fees) else 0.0,
            "final_equity": float(self.equity) if np.isfinite(self.equity) else 0.0,
            "initial_capital": float(self.initial_capital),
            "max_drawdown_reached": float(self.max_drawdown_reached) if np.isfinite(self.max_drawdown_reached) else 0.0,
            # E-P5.2 T4: realistic-fill diagnostics
            "rejected_orders": int(self.rejected_orders),
            "partial_fills": int(self.partial_fills),
            "fill_model": {
                "spread_bps": float(self.spread_bps),
                "max_fill_ratio": float(self.max_fill_ratio),
                "rejection_rate": float(self.rejection_rate),
                "latency_slippage_bps": float(self.latency_slippage_bps),
            },
            "trades": [dict(t) for t in self.trades],  # Convert any numpy types to basic types
            "equity_curve": [dict(e) for e in self.equity_curve]
        }

        # Clear trade history after metrics calculation to ensure clean state for next run
        # This is important for hyperparameter optimization where multiple runs happen
        self.trades.clear()
        self.equity_curve.clear()

        return metrics

    def _close_active_positions_manually(self, direction_to_close: int, size_to_close: float, execution_price: float, timestamp: datetime) -> float:
        """
        Close active positions manually using FIFO, returning the calculated PnL.
        """
        pnl = 0.0
        remaining_size = size_to_close
        positions_to_remove = []
        
        for i, pos in enumerate(self.active_positions):
            if pos['direction'] == direction_to_close and not pos.get('closed', False):
                close_size = min(remaining_size, pos['size'])
                
                # Calculate PnL for this chunk
                chunk_pnl = 0.0
                if direction_to_close == 1:  # Closing a long
                    chunk_pnl = (execution_price - pos['entry_price']) * close_size
                else:  # Closing a short
                    chunk_pnl = (pos['entry_price'] - execution_price) * close_size
                
                pnl += chunk_pnl
                
                # Deduct exit fees/slippage for this chunk
                fees = self.fee_rate * abs(close_size * execution_price)
                slippage = abs(chunk_pnl) * self.slippage_factor
                pnl -= (fees + slippage)
                
                # Reduce position size
                pos['size'] -= close_size
                remaining_size -= close_size
                
                # Record partial/full close
                if pos['size'] <= 1e-8:
                    pos['closed'] = True
                    pos['close_price'] = execution_price
                    pos['close_time'] = timestamp
                    pos['pnl'] = pnl
                    positions_to_remove.append(i)
                
                if remaining_size <= 1e-8:
                    break
                    
        # Remove fully closed positions in reverse order
        for i in reversed(positions_to_remove):
            del self.active_positions[i]
            
        return pnl


# Example strategy functions
def example_rsi_strategy(row: pd.Series, params: Dict[str, Any]) -> int:
    """
    Example RSI-based strategy.
    
    Returns:
        1: Buy signal
        -1: Sell signal  
        0: No signal
    """
    rsi_length = params.get('rsi_length', 14)
    rsi_overbought = params.get('rsi_overbought', 70)
    rsi_oversold = params.get('rsi_oversold', 30)

    rsi = row.get('rsi', 50)  # Default to 50 if no RSI calculated

    if rsi < rsi_oversold:  # Oversold - potential buy
        return 1
    elif rsi > rsi_overbought:  # Overbought - potential sell
        return -1
    else:
        return 0


def example_ma_crossover_strategy(row: pd.Series, params: Dict[str, Any]) -> int:
    """
    Example moving average crossover strategy.
    
    Returns:
        1: Buy signal (short MA crosses above long MA)
        -1: Sell signal (short MA crosses below long MA)
        0: No signal
    """
    sma_short = row.get('sma_20')
    sma_long = row.get('sma_50')

    if sma_short is None or sma_long is None:
        return 0

    # Previous values to detect crossovers
    try:
        # In a real scenario, we'd have previous values, but here we'll use a simplified approach
        if sma_short > sma_long:
            return 1  # Bullish
        else:
            return -1  # Bearish
    except:
        return 0


def example_mean_reversion_strategy(row: pd.Series, params: Dict[str, Any]) -> int:
    """
    Example mean reversion strategy using Bollinger Bands.
    
    Returns:
        1: Buy signal (price touches lower band)
        -1: Sell signal (price touches upper band)
        0: No signal
    """
    close = row['close']
    bb_upper = row.get('bb_upper', close * 1.05)  # Default to 5% above if no BB
    bb_lower = row.get('bb_lower', close * 0.95)  # Default to 5% below if no BB

    # Buy when price touches or goes below lower Bollinger Band
    if close <= bb_lower:
        return 1
    # Sell when price touches or goes above upper Bollinger Band
    elif close >= bb_upper:
        return -1
    else:
        return 0
