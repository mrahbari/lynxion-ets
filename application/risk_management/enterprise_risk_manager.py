"""
Enhanced Enterprise Risk Manager based on Enterprise Hedge Fund Architecture
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from infrastructure.tracking.trade_tracker import trade_tracker
from infrastructure.market_regime.regime_detector import regime_detector, RegimeType


class PositionDirection(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    symbol: str
    entry_price: float
    size: float
    direction: PositionDirection
    stop_loss: float
    take_profit: float
    entry_time: datetime
    risk_amount: float = 0.0
    trade_id: str = None
    regime_context: str = None  # Store the regime context when position was opened
    setup_type: str = None


class EnterpriseRiskManager:
    """
    Advanced risk management system with multi-level controls and validation
    """
    def __init__(self,
                 max_portfolio_exposure: float = 100000,
                 max_position_exposure: float = 50000,
                 max_risk_per_trade: float = 0.01,  # 1%
                 max_daily_loss_pct: float = 0.05,  # 5%
                 max_drawdown_pct: float = 0.15,    # 15%
                 fees_per_trade: float = 0.1,       # Fixed fee per trade
                 slippage_tolerance: float = 0.001, # 0.1%
                 max_correlation: float = 0.8,
                 fixed_position_size_enabled: bool = False,
                 fixed_position_amount: float = 10.0,
                 default_account_balance: float = 10000.0,
                 risk_config: Dict[str, Any] = None,
                 regime_risk_multipliers: Optional[Dict[str, float]] = None,
                 drawdown_decay_factor: float = 0.95,
                 enable_multi_position: bool = True,
                 max_concurrent_positions: int = 50):

        import os
        from shared.logger import logger

        # Load capacity values with priority: Env Var -> risk_config -> Constructor Parameter
        env_enable_multi = os.getenv("ENABLE_MULTI_POSITION")
        if env_enable_multi is not None:
            self.enable_multi_position = env_enable_multi.lower() in ("true", "1", "yes")
        elif risk_config and 'enable_multi_position' in risk_config:
            self.enable_multi_position = bool(risk_config['enable_multi_position'])
        else:
            self.enable_multi_position = enable_multi_position

        if max_concurrent_positions != 50:
            self.max_concurrent_positions = max_concurrent_positions
        else:
            env_max_positions = os.getenv("MAX_TOTAL_POSITIONS") or os.getenv("MAX_CONCURRENT_POSITIONS")
            if env_max_positions is not None:
                self.max_concurrent_positions = int(env_max_positions)
            elif risk_config and 'max_concurrent_positions' in risk_config:
                self.max_concurrent_positions = int(risk_config['max_concurrent_positions'])
            else:
                self.max_concurrent_positions = max_concurrent_positions

        # Use risk_config if provided, otherwise use individual parameters
        if risk_config:
            self.max_portfolio_exposure = risk_config.get('max_portfolio_exposure', max_portfolio_exposure)
            self.max_position_exposure = risk_config.get('max_position_exposure', max_position_exposure)
            self.max_risk_per_trade = risk_config.get('max_risk_per_trade', max_risk_per_trade)
            self.max_daily_loss_pct = risk_config.get('max_daily_loss_pct', max_daily_loss_pct)
            self.max_drawdown_pct = risk_config.get('max_drawdown_pct', max_drawdown_pct)
            self.fees_per_trade = risk_config.get('fees_per_trade', fees_per_trade)
            self.slippage_tolerance = risk_config.get('slippage_tolerance', slippage_tolerance)
            self.max_correlation = risk_config.get('max_correlation', max_correlation)
            # Configuration for fixed position sizing
            self.fixed_position_size_enabled = risk_config.get('fixed_position_size_enabled', fixed_position_size_enabled)
            self.fixed_position_amount = risk_config.get('fixed_position_amount', fixed_position_amount)
            self.default_account_balance = risk_config.get('default_account_balance', default_account_balance)
            self.drawdown_decay_factor = risk_config.get('drawdown_decay_factor', drawdown_decay_factor)
            self.regime_risk_multipliers = risk_config.get('regime_risk_multipliers', regime_risk_multipliers or {
                RegimeType.TRENDING_UP.value: 1.0,
                RegimeType.TRENDING_DOWN.value: 1.0,
                RegimeType.RANGING.value: 1.2,
                RegimeType.HIGH_VOLATILITY.value: 0.7,
                RegimeType.LOW_VOLATILITY.value: 1.1,
                RegimeType.CHOPPY.value: 0.6,
                RegimeType.BREAKOUT.value: 0.8
            })
        else:
            self.max_portfolio_exposure = max_portfolio_exposure
            self.max_position_exposure = max_position_exposure
            self.max_risk_per_trade = max_risk_per_trade
            self.max_daily_loss_pct = max_daily_loss_pct
            self.max_drawdown_pct = max_drawdown_pct
            self.fees_per_trade = fees_per_trade
            self.slippage_tolerance = slippage_tolerance
            self.max_correlation = max_correlation
            # Configuration for fixed position sizing
            self.fixed_position_size_enabled = fixed_position_size_enabled
            self.fixed_position_amount = fixed_position_amount
            self.default_account_balance = default_account_balance
            self.drawdown_decay_factor = drawdown_decay_factor
            self.regime_risk_multipliers = regime_risk_multipliers or {
                RegimeType.TRENDING_UP.value: 1.0,
                RegimeType.TRENDING_DOWN.value: 1.0,
                RegimeType.RANGING.value: 1.2,
                RegimeType.HIGH_VOLATILITY.value: 0.7,
                RegimeType.LOW_VOLATILITY.value: 1.1,
                RegimeType.CHOPPY.value: 0.6,
                RegimeType.BREAKOUT.value: 0.8
            }

        # Track positions and PnL
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.equity_curve: List[float] = []
        self.violations: List[str] = []

        # Track start of day for daily limits
        self.daily_start = datetime.now().date()
        self.starting_equity = self.max_portfolio_exposure

        # Track correlations between symbols dynamically with background worker
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        import threading
        self.correlation_lock = threading.Lock()
        self.price_history_for_correlation: Dict[str, List[float]] = {}
        self.max_price_history_len = 100
        self.correlation_update_interval_sec = 10.0  # Configurable update interval
        
        # Start background correlation thread
        self.worker_thread = threading.Thread(target=self._correlation_worker_loop, daemon=True)
        self.worker_thread.start()

        # Track regime-specific risk metrics
        self.regime_exposures: Dict[str, float] = {}

    def calculate_position_size(self, entry_price: float, stop_loss: float,
                               portfolio_equity: float, risk_percentage: Optional[float] = None,
                               regime_context: Optional[str] = None, volatility: Optional[float] = None,
                               correlation_penalty: float = 1.0, drawdown_factor: float = 1.0) -> float:
        """
        Calculate position size based on risk management principles with unified formula

        If FIXED_POSITION_SIZE_ENABLED is true: position size = FIXED_POSITION_AMOUNT / entry_price
        If FIXED_POSITION_SIZE_ENABLED is false: position size = (portfolio_equity * risk_percentage) / |entry_price - stop_loss|

        The final position size is constrained by portfolio and position exposure limits.
        """
        # Determine risk percentage to use
        risk_pct = risk_percentage or self.max_risk_per_trade

        # Apply regime-based risk multiplier if regime context is provided
        if regime_context and regime_context in self.regime_risk_multipliers:
            risk_pct *= self.regime_risk_multipliers[regime_context]

        # Apply drawdown factor to reduce risk during drawdown periods
        risk_pct *= drawdown_factor

        # Apply correlation penalty to reduce position size when correlation is high
        risk_pct /= correlation_penalty  # Higher penalty means lower risk allocation

        # Calculate position size based on FIXED_POSITION_SIZE_ENABLED flag
        if self.fixed_position_size_enabled:
            # Fixed position sizing: always use the fixed dollar amount
            fixed_dollar_amount = self.fixed_position_amount
            position_size = fixed_dollar_amount / entry_price if entry_price > 0 else 0.0
            # Calculate the actual risk amount for this fixed position
            risk_amount = position_size * abs(entry_price - stop_loss) if stop_loss != entry_price else portfolio_equity * risk_pct
        else:
            # Dynamic position sizing: calculate based on risk percentage and stop loss
            risk_amount = portfolio_equity * risk_pct

            # Normalize risk by volatility if provided
            risk_per_unit = abs(entry_price - stop_loss)
            if volatility and volatility > 0:
                # Use volatility as a normalizer - higher volatility means wider stop loss distance
                risk_per_unit = max(risk_per_unit, volatility * entry_price)

            if risk_per_unit <= 0:
                return 0.0  # Invalid stop loss

            # Calculate position size in units based on risk amount and risk per unit
            position_size = risk_amount / risk_per_unit

        # Apply portfolio-level constraints
        # Apply a safety buffer of 0.99 (0.1% - 1% standard range) to prevent minor price/rounding discrepancies
        # between sizing and validation phases from triggering limit violations.
        sizing_buffer = 0.99
        # 1. Ensure we don't exceed max position exposure limit
        max_position_by_exposure = (self.max_position_exposure * sizing_buffer) / entry_price if entry_price > 0 else float('inf')
        position_size = min(position_size, max_position_by_exposure)

        # 2. Ensure we don't exceed remaining portfolio exposure capacity
        current_total_exposure = self.get_total_exposure()
        remaining_portfolio_capacity = self.max_portfolio_exposure - current_total_exposure
        max_position_by_portfolio = (remaining_portfolio_capacity * sizing_buffer) / entry_price if entry_price > 0 else float('inf')
        position_size = min(position_size, max_position_by_portfolio)

        # 3. Ensure position size is positive
        position_size = max(position_size, 0.0)

        from shared.logger import logger
        logger.info(
            f"NGDP Sizing Decision: entry_price={entry_price:.4f}, stop_loss={stop_loss:.4f}, "
            f"portfolio_equity=${portfolio_equity:.2f}, calculated_size={position_size:.4f} units"
        )

        return position_size

    def validate_position_entry(self, symbol: str, size: float, entry_price: float) -> bool:
        """
        Validate if a position entry is allowed based on risk constraints
        """
        from shared.logger import logger

        active_count = len(self.positions)
        current_exposure = sum(p.size * p.entry_price for p in self.positions.values())
        position_value = size * entry_price
        exposure_after = current_exposure + position_value

        # Structured log of active positions count and exposure before/after
        logger.info(
            f"Risk Entry Validation for {symbol}: active_positions_count={active_count}, "
            f"exposure_before=${current_exposure:.2f}, exposure_after=${exposure_after:.2f}"
        )

        # Capacity guard check (number of open positions)
        if symbol not in self.positions:
            if not self.enable_multi_position and active_count >= 1:
                msg = f"{symbol}: Entry blocked due to portfolio capacity: ENABLE_MULTI_POSITION is disabled and an active position already exists."
                self.violations.append(msg)
                logger.warning(msg)
                return False
            if active_count >= self.max_concurrent_positions:
                msg = f"{symbol}: Entry blocked due to portfolio capacity: Active positions count ({active_count}) meets or exceeds max capacity of {self.max_concurrent_positions} concurrent positions."
                self.violations.append(msg)
                logger.warning(msg)
                return False

        # Check if we're within position size limits
        if position_value > self.max_position_exposure:
            self.violations.append(f"{symbol}: Position size ${position_value:.2f} exceeds max position limit ${self.max_position_exposure}")
            return False

        # Check portfolio exposure limits
        if current_exposure + position_value > self.max_portfolio_exposure:
            self.violations.append(f"{symbol}: Portfolio exposure would exceed limit ${self.max_portfolio_exposure}")
            return False

        return True

    def enter_position(self, symbol: str, entry_price: float, size: float,
                      direction: PositionDirection, stop_loss: float, take_profit: float,
                      trade_id: str = None, regime_context: str = None, setup_type: str = None) -> bool:
        """
        Enter a new position with risk validation
        """
        if not self.validate_position_entry(symbol, size, entry_price):
            return False

        # Calculate risk amount for this position based on actual position size
        risk_amount = size * abs(entry_price - stop_loss)

        # If no trade_id provided, generate one
        if not trade_id:
            from infrastructure.logging.forensic_logger import forensic_logger
            trade_id = forensic_logger._generate_trade_id(symbol, "BINANCE")

        # Create and store position
        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            size=size,
            direction=direction,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=datetime.now(),
            risk_amount=risk_amount,
            trade_id=trade_id,
            regime_context=regime_context,
            setup_type=setup_type
        )

        self.positions[symbol] = position

        # Update regime exposure tracking
        if regime_context:
            self.regime_exposures[regime_context] = self.regime_exposures.get(regime_context, 0.0) + (size * entry_price)

        # Register the trade with the trade tracker
        trade_tracker.register_trade(
            trade_id=trade_id,
            symbol=symbol,
            side=direction.value,
            price=entry_price,
            quantity=size,
            sl=stop_loss,
            tp=take_profit,
            timestamp=position.entry_time,
            setup_type=setup_type
        )

        return True

    def check_stop_loss_take_profit(self, symbol: str, candle_high: float, candle_low: float) -> tuple[Optional[float], Optional[str]]:
        """
        Check if stop loss or take profit has been hit for a position
        Handles simultaneous SL/TP scenarios with priority logic
        """
        position = self.positions.get(symbol)
        if not position:
            return None, None

        exit_price, exit_type = None, None

        if position.direction == PositionDirection.LONG:
            # For long positions: SL triggered if low <= SL, TP triggered if high >= TP
            sl_hit = candle_low <= position.stop_loss
            tp_hit = candle_high >= position.take_profit

            if sl_hit and tp_hit:
                # If both hit in same candle, determine which exit price is closer to entry
                # More conservative: prioritize the exit that results in less favorable outcome
                entry = position.entry_price
                if abs(position.stop_loss - entry) <= abs(position.take_profit - entry):
                    exit_price, exit_type = position.stop_loss, 'SL'
                else:
                    exit_price, exit_type = position.take_profit, 'TP'
            elif sl_hit:
                exit_price, exit_type = position.stop_loss, 'SL'
            elif tp_hit:
                exit_price, exit_type = position.take_profit, 'TP'

        elif position.direction == PositionDirection.SHORT:
            # For short positions: SL triggered if high >= SL, TP triggered if low <= TP
            sl_hit = candle_high >= position.stop_loss
            tp_hit = candle_low <= position.take_profit

            if sl_hit and tp_hit:
                # If both hit in same candle, determine which exit price is closer to entry
                entry = position.entry_price
                if abs(position.stop_loss - entry) <= abs(position.take_profit - entry):
                    exit_price, exit_type = position.stop_loss, 'SL'
                else:
                    exit_price, exit_type = position.take_profit, 'TP'
            elif sl_hit:
                exit_price, exit_type = position.stop_loss, 'SL'
            elif tp_hit:
                exit_price, exit_type = position.take_profit, 'TP'

        return exit_price, exit_type

    def exit_position(self, symbol: str, exit_price: float, exit_type: str) -> float:
        """
        Exit a position and return PnL
        """
        position = self.positions.get(symbol)
        if not position:
            return 0.0

        # Calculate PnL
        pnl = 0.0
        if position.direction == PositionDirection.LONG:
            pnl = (exit_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - exit_price) * position.size

        # Account for fees and slippage
        total_cost = self.fees_per_trade + (abs(pnl) * self.slippage_tolerance)
        pnl -= total_cost

        # Update daily and total PnL
        self.daily_pnl += pnl
        self.total_pnl += pnl

        # Close the trade with the trade tracker using the trade_id stored in the position
        if position.trade_id:
            trade_tracker.close_trade(
                trade_id=position.trade_id,
                exit_price=exit_price,
                exit_reason=exit_type,
                exit_timestamp=datetime.now()
            )

        # Remove position
        del self.positions[symbol]

        # Update equity curve
        current_equity = self.starting_equity + self.total_pnl
        self.equity_curve.append(current_equity)

        return pnl

    def calculate_drawdown(self) -> float:
        """
        Calculate current drawdown based on equity curve
        """
        if not self.equity_curve:
            return 0.0

        equity_array = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity_array)
        drawdown = peak - equity_array
        current_drawdown = drawdown[-1] if len(drawdown) > 0 else 0.0
        
        return current_drawdown / peak[-1] if peak[-1] > 0 else 0.0

    def is_trading_allowed(self) -> bool:
        """
        Check if trading is allowed based on risk limits
        """
        # Check daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.starting_equity if self.starting_equity > 0 else 0
        if daily_loss_pct > self.max_daily_loss_pct:
            self.violations.append(f"Daily loss limit exceeded: {daily_loss_pct:.2%} > {self.max_daily_loss_pct:.2%}")
            return False

        # Check drawdown limit
        current_drawdown = self.calculate_drawdown()
        if current_drawdown > self.max_drawdown_pct:
            self.violations.append(f"Drawdown limit exceeded: {current_drawdown:.2%} > {self.max_drawdown_pct:.2%}")
            return False

        return True

    def get_position_exposure(self, symbol: str) -> float:
        """
        Get current exposure for a specific symbol
        """
        position = self.positions.get(symbol)
        if position:
            return position.size * position.entry_price
        return 0.0

    def get_total_exposure(self) -> float:
        """
        Get total portfolio exposure
        """
        return sum(p.size * p.entry_price for p in self.positions.values())

    def get_violations(self) -> List[str]:
        """
        Get list of current risk violations
        """
        return self.violations.copy()

    def reset_daily_counters(self):
        """
        Reset daily counters (should be called at start of each trading day)
        """
        self.daily_pnl = 0.0
        self.daily_start = datetime.now().date()

    def get_risk_metrics(self) -> Dict[str, Any]:
        """
        Get current risk metrics
        """
        return {
            'total_exposure': self.get_total_exposure(),
            'number_of_positions': len(self.positions),
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'current_drawdown': self.calculate_drawdown(),
            'violations_count': len(self.violations),
            'equity': self.starting_equity + self.total_pnl if self.equity_curve else self.starting_equity + self.total_pnl
        }

    def has_active_position_in_direction(self, symbol: str, direction: PositionDirection) -> bool:
        """
        Check if there is already an active position in the same direction for the given symbol.

        Args:
            symbol: The trading symbol
            direction: The position direction (LONG or SHORT)

        Returns:
            True if there is already an active position in the same direction, False otherwise
        """
        position = self.positions.get(symbol)
        if position and position.direction == direction:
            return True
        return False

    def calculate_correlation_penalty(self, symbol: str, portfolio_symbols: List[str]) -> float:
        """
        Calculate correlation penalty based on correlation with other positions in portfolio.
        Higher correlation increases the penalty (reducing position size).
        """
        if not portfolio_symbols:
            return 1.0  # No penalty if no other positions

        total_penalty = 0.0
        penalty_count = 0

        for other_symbol in portfolio_symbols:
            if other_symbol != symbol:
                # Get correlation between symbols (placeholder - in real implementation,
                # this would come from actual correlation calculations)
                correlation = self.correlation_matrix.get(symbol, {}).get(other_symbol, 0.0)

                # If correlation is above threshold, apply penalty
                if abs(correlation) > self.max_correlation:
                    penalty = 1 + (abs(correlation) - self.max_correlation)
                    total_penalty += penalty
                    penalty_count += 1

        # Average penalty across all correlated positions
        if penalty_count > 0:
            avg_penalty = total_penalty / penalty_count
            # Cap the penalty to prevent extreme reductions
            return min(avg_penalty, 3.0)  # Maximum 3x penalty
        else:
            return 1.0

    def calculate_drawdown_factor(self) -> float:
        """
        Calculate drawdown factor to reduce risk during drawdown periods.
        Returns a value between 0 and 1, where lower values indicate higher drawdown.
        """
        current_drawdown = self.calculate_drawdown()

        if current_drawdown <= 0:
            return 1.0  # No drawdown, full risk allocation

        # Apply exponential decay based on drawdown magnitude
        # As drawdown increases, the factor decreases exponentially
        decay_factor = self.drawdown_decay_factor
        max_drawdown = self.max_drawdown_pct

        # Normalize drawdown to 0-1 scale relative to max drawdown
        normalized_drawdown = min(current_drawdown / max_drawdown, 1.0)

        # Apply exponential decay: factor = decay_factor ^ normalized_drawdown
        drawdown_factor = pow(decay_factor, normalized_drawdown * 10)  # Multiply by 10 to make decay steeper

        # Ensure factor is between 0.1 and 1.0
        return max(0.1, drawdown_factor)

    def get_optimizable_params(self) -> Dict[str, Any]:
        """Get the current risk parameters that can be optimized."""
        return {
            'max_portfolio_exposure': self.max_portfolio_exposure,
            'max_position_exposure': self.max_position_exposure,
            'max_risk_per_trade': self.max_risk_per_trade,
            'max_daily_loss_pct': self.max_daily_loss_pct,
            'max_drawdown_pct': self.max_drawdown_pct,
            'fees_per_trade': self.fees_per_trade,
            'slippage_tolerance': self.slippage_tolerance,
            'max_correlation': self.max_correlation,
            'fixed_position_size_enabled': self.fixed_position_size_enabled,
            'fixed_position_amount': self.fixed_position_amount,
            'default_account_balance': self.default_account_balance,
            'drawdown_decay_factor': self.drawdown_decay_factor,
            'regime_risk_multipliers': self.regime_risk_multipliers
        }

    def update_from_params(self, params: Dict[str, Any]):
        """Update risk parameters from optimization results."""
        self.max_portfolio_exposure = params.get('max_portfolio_exposure', self.max_portfolio_exposure)
        self.max_position_exposure = params.get('max_position_exposure', self.max_position_exposure)
        self.max_risk_per_trade = params.get('max_risk_per_trade', self.max_risk_per_trade)
        self.max_daily_loss_pct = params.get('max_daily_loss_pct', self.max_daily_loss_pct)
        self.max_drawdown_pct = params.get('max_drawdown_pct', self.max_drawdown_pct)
        self.fees_per_trade = params.get('fees_per_trade', self.fees_per_trade)
        self.slippage_tolerance = params.get('slippage_tolerance', self.slippage_tolerance)
        self.max_correlation = params.get('max_correlation', self.max_correlation)
        self.fixed_position_size_enabled = params.get('fixed_position_size_enabled', self.fixed_position_size_enabled)
        self.fixed_position_amount = params.get('fixed_position_amount', self.fixed_position_amount)
        self.default_account_balance = params.get('default_account_balance', self.default_account_balance)
        self.drawdown_decay_factor = params.get('drawdown_decay_factor', self.drawdown_decay_factor)
        self.regime_risk_multipliers = params.get('regime_risk_multipliers', self.regime_risk_multipliers)
        # Update starting equity if portfolio exposure changes
        self.starting_equity = self.max_portfolio_exposure

    def record_price(self, symbol: str, price: float):
        """Record close price of a symbol for dynamic correlation calculation."""
        with self.correlation_lock:
            if symbol not in self.price_history_for_correlation:
                self.price_history_for_correlation[symbol] = []
            self.price_history_for_correlation[symbol].append(price)
            if len(self.price_history_for_correlation[symbol]) > self.max_price_history_len:
                self.price_history_for_correlation[symbol].pop(0)

    def _correlation_worker_loop(self):
        """Background daemon thread to periodically recalculate symbol correlations."""
        import time
        while True:
            try:
                time.sleep(self.correlation_update_interval_sec)
                self.recalculate_correlations()
            except Exception:
                pass

    def recalculate_correlations(self):
        """Calculate rolling Pearson correlation coefficients between active symbols."""
        with self.correlation_lock:
            symbols = list(self.price_history_for_correlation.keys())
            if len(symbols) < 2:
                return
            
            # Find minimum history length across symbols to align data
            min_len = min(len(self.price_history_for_correlation[s]) for s in symbols)
            if min_len < 5:  # Need at least 5 observations to compute correlation
                return
                
            # Align price series
            series_data = {}
            for s in symbols:
                series_data[s] = self.price_history_for_correlation[s][-min_len:]
                
            new_matrix = {}
            for s1 in symbols:
                new_matrix[s1] = {}
                for s2 in symbols:
                    if s1 == s2:
                        new_matrix[s1][s2] = 1.0
                    else:
                        x = series_data[s1]
                        y = series_data[s2]
                        n = len(x)
                        mean_x = sum(x) / n
                        mean_y = sum(y) / n
                        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
                        den_x = sum((xi - mean_x) ** 2 for xi in x)
                        den_y = sum((yi - mean_y) ** 2 for yi in y)
                        if den_x > 0 and den_y > 0:
                            corr = num / ((den_x * den_y) ** 0.5)
                        else:
                            corr = 0.0
                        new_matrix[s1][s2] = float(corr)
            
            self.correlation_matrix = new_matrix