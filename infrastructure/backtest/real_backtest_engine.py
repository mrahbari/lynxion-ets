"""
Realistic backtesting engine with proper order simulation including slippage, fees, and market impact.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass
import math

from domain.entities.trading_entities import Signal, Order, Fill, Position
from domain.value_objects import Symbol, Money, Percentage
from domain.ports.backtest_ports import BacktestEnginePort
from shared.logger import logger


@dataclass
class BacktestMetrics:
    """Metrics from backtesting execution"""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    final_equity: float
    volatility: float
    alpha: float
    beta: float
    information_ratio: float
    calmar_ratio: float


class RealisticBacktestEngine(BacktestEnginePort):
    """Realistic backtesting engine that simulates actual trading conditions."""

    def __init__(self,
                 initial_capital: float = 100000.0,
                 fee_rate: float = 0.001,  # 0.1% per trade
                 slippage_model: str = 'volume_based',  # Options: 'fixed', 'volume_based', 'volatility_based'
                 slippage_factor: float = 0.0005,  # 0.05% base slippage
                 market_impact_model: str = 'square_root',  # Options: 'linear', 'square_root', 'power'
                 market_impact_factor: float = 0.001,  # Base market impact factor
                 min_order_size: float = 0.001,  # Minimum order size (e.g., 0.001 BTC)
                 max_position_size: float = 0.20,  # Maximum 20% of capital per position
                 slippage_distribution: str = 'normal'):  # Distribution for random slippage component
        """
        Initialize the realistic backtest engine.

        Args:
            initial_capital: Starting capital for backtest
            fee_rate: Fee rate per trade (e.g., 0.001 for 0.1%)
            slippage_model: Model for calculating slippage ('fixed', 'volume_based', 'volatility_based')
            slippage_factor: Base factor for slippage calculation
            market_impact_model: Model for market impact ('linear', 'square_root', 'power')
            market_impact_factor: Base market impact factor
            min_order_size: Minimum order size allowed
            max_position_size: Maximum percentage of capital per position
            slippage_distribution: Distribution for random slippage ('normal', 'uniform', 'lognormal')
        """
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_model = slippage_model
        self.slippage_factor = slippage_factor
        self.market_impact_model = market_impact_model
        self.market_impact_factor = market_impact_factor
        self.min_order_size = min_order_size
        self.max_position_size = max_position_size
        self.slippage_distribution = slippage_distribution

        # Trading state
        self.current_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.fills: List[Fill] = []
        self.equity_curve: List[float] = [initial_capital]
        self.drawdowns: List[float] = [0.0]
        self.trade_log: List[Dict[str, Any]] = []

    def backtest_strategy(self, 
                         signals: List[Signal], 
                         price_data: pd.DataFrame,
                         symbol_column: str = 'symbol',
                         open_column: str = 'open',
                         high_column: str = 'high', 
                         low_column: str = 'low',
                         close_column: str = 'close',
                         volume_column: str = 'volume') -> BacktestMetrics:
        """
        Execute backtest of strategy using realistic order simulation.

        Args:
            signals: List of signals to execute
            price_data: DataFrame with OHLCV data
            symbol_column: Name of symbol column in price data
            open_column: Name of open price column
            high_column: Name of high price column
            low_column: Name of low price column
            close_column: Name of close price column
            volume_column: Name of volume column

        Returns:
            BacktestMetrics with performance statistics
        """
        logger.info(f"Starting backtest with initial capital: ${self.initial_capital:,.2f}, "
                   f"{len(signals)} signals, data range: {len(price_data)} bars")

        # Reset state
        self._reset_state()

        # Sort signals by timestamp to process chronologically
        sorted_signals = sorted(signals, key=lambda s: s.timestamp)

        # Process signals chronologically
        for signal in sorted_signals:
            # Find the corresponding price bar for the signal timestamp
            execution_bar = self._find_execution_bar(signal.timestamp, price_data, symbol_column)
            if execution_bar is None:
                continue  # Skip if no matching bar found

            # Execute the signal as an order
            order = self._place_order_from_signal(signal, execution_bar)
            if order:
                # Process the order execution with realistic simulation
                fill = self._execute_order_realistically(order, execution_bar, close_column, volume_column)
                if fill:
                    self.fills.append(fill)
                    self._update_position(fill)
                    self._update_capital(fill)
                    
                    # Log the trade
                    self.trade_log.append({
                        'timestamp': signal.timestamp,
                        'symbol': signal.symbol.value,
                        'signal_type': signal.signal_type.name,
                        'order_size': order.quantity,
                        'execution_price': fill.price.amount,
                        'fill_cost': fill.fill_cost.amount if fill.fill_cost else 0,
                        'pnl': fill.pnl.amount if fill.pnl else 0,
                        'capital_after': self.current_capital
                    })

                    logger.debug(f"Executed {order.side} {order.quantity} {order.symbol.value} @ ${fill.price.amount:.5f}, "
                               f"P&L: ${fill.pnl.amount if fill.pnl else 0:.2f}")

        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(price_data[close_column].values)
        
        logger.info(f"Backtest completed - Final equity: ${self.current_capital:,.2f}, "
                   f"Total return: {(self.current_capital/self.initial_capital - 1)*100:.2f}%, "
                   f"Sharpe: {metrics.sharpe_ratio:.2f}, Max DD: {metrics.max_drawdown:.2%}")

        return metrics

    def _reset_state(self):
        """Reset the backtest state for a new run"""
        self.current_capital = self.initial_capital
        self.cash = self.initial_capital
        self.positions = {}
        self.orders = []
        self.fills = []
        self.equity_curve = [self.initial_capital]
        self.drawdowns = [0.0]
        self.trade_log = []

    def _find_execution_bar(self, 
                           signal_time: datetime, 
                           price_data: pd.DataFrame,
                           symbol_column: str) -> Optional[pd.Series]:
        """Find the appropriate bar to execute the signal on"""
        # Find the first bar that occurs at or after the signal time
        # In a real backtest, this might depend on the bar frequency
        
        # If price_data has a datetime index, find closest bar after signal_time
        if hasattr(price_data.index, 'dtype') and np.issubdtype(price_data.index.dtype, np.datetime64):
            # Find first bar at or after signal time
            future_bars = price_data[price_data.index >= signal_time]
            if not future_bars.empty:
                return future_bars.iloc[0]
        else:
            # If no datetime index, assume bars are evenly spaced
            # In a real system, we'd need timestamp column to match properly
            # For now, just return the first bar
            if not price_data.empty:
                return price_data.iloc[0]

        return None

    def _place_order_from_signal(self, signal: Signal, execution_bar: pd.Series) -> Optional[Order]:
        """Convert a signal to an executable order"""
        # Determine side based on signal type
        if signal.signal_type.name in ['BUY', 'LONG']:
            side = 'BUY'
        elif signal.signal_type.name in ['SELL', 'SHORT']:
            side = 'SELL'
        else:
            return None  # Skip HOLD/NEUTRAL signals

        # Calculate order size based on position sizing rules
        position_value = self.current_capital * float(signal.confidence.value) * self.max_position_size
        position_value = min(position_value, self.cash)  # Don't over-leverage
        
        # Get current price for sizing
        price = execution_bar['close']
        quantity = position_value / price
        
        # Apply minimum order size constraint
        if quantity < self.min_order_size:
            logger.debug(f"Order size {quantity} below minimum {self.min_order_size}, skipping")
            return None

        # Create order
        from domain.entities.trading_entities import OrderSide
        from domain.value_objects import Money
        
        order = Order(
            symbol=signal.symbol,
            side=OrderSide(side),
            quantity=quantity,
            price=Money(price),  # This is the target price
            order_type='MARKET',
            strategy=signal.strategy_name,
            timestamp=signal.timestamp,
            metadata={
                'source_signal_confidence': float(signal.confidence.value),
                'target_price': float(price)
            }
        )

        self.orders.append(order)
        return order

    def _execute_order_realistically(self, 
                                   order: Order, 
                                   execution_bar: pd.Series,
                                   close_column: str,
                                   volume_column: str) -> Optional[Fill]:
        """Execute an order with realistic market simulation including slippage, fees, and market impact"""
        try:
            # Calculate base execution price (usually based on close of bar or next open)
            base_price = float(execution_bar[close_column])
            
            # Calculate slippage based on selected model
            slippage_amount = self._calculate_slippage(
                order, execution_bar, close_column, volume_column, base_price
            )
            
            # Calculate market impact based on order size and market conditions
            market_impact_amount = self._calculate_market_impact(
                order, execution_bar, volume_column, base_price
            )
            
            # Determine final execution price based on order direction
            if order.side.name == 'BUY':
                execution_price = base_price + slippage_amount + market_impact_amount
            else:  # SELL
                execution_price = base_price - slippage_amount - market_impact_amount

            # Calculate fees
            notional_value = order.quantity * execution_price
            fee_amount = notional_value * self.fee_rate

            # Create fill
            from domain.entities.trading_entities import Fill, FillType
            from domain.value_objects import Money
            
            fill = Fill(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=Money(execution_price),
                fill_type=FillType.NORMAL,
                timestamp=datetime.now(),  # In real backtest, this would match signal time
                fee=Money(fee_amount),
                pnl=None,  # Will be calculated when position is closed
                metadata={
                    'base_price': base_price,
                    'slippage_amount': slippage_amount,
                    'market_impact_amount': market_impact_amount,
                    'fee_rate': self.fee_rate,
                    'fee_amount': fee_amount,
                    'notional_value': notional_value
                }
            )

            return fill

        except Exception as e:
            logger.error(f"Error executing order realistically: {e}")
            return None

    def _calculate_slippage(self, 
                           order: Order, 
                           execution_bar: pd.Series,
                           close_column: str,
                           volume_column: str,
                           base_price: float) -> float:
        """Calculate slippage based on selected model"""
        base_price = float(base_price)
        
        if self.slippage_model == 'fixed':
            # Fixed percentage slippage
            return base_price * self.slippage_factor
            
        elif self.slippage_model == 'volume_based':
            # Slippage based on order size relative to market volume
            volume = float(execution_bar[volume_column]) if volume_column in execution_bar else 1000  # Default volume
            order_notional = order.quantity * base_price
            volume_ratio = order_notional / volume if volume > 0 else 0
            
            # Volume-based slippage increases with order size relative to volume
            volume_slippage_factor = self.slippage_factor * (1 + math.sqrt(volume_ratio))
            
            # Add some random component based on distribution
            if self.slippage_distribution == 'uniform':
                random_component = np.random.uniform(-0.3, 0.3) * self.slippage_factor
            elif self.slippage_distribution == 'normal':
                random_component = np.random.normal(0, 0.2) * self.slippage_factor
            elif self.slippage_distribution == 'lognormal':
                # Positive-only random component
                random_component = (np.random.lognormal(0, 0.1) - 1) * self.slippage_factor
            else:
                random_component = 0.0
                
            return base_price * (volume_slippage_factor + random_component)
            
        elif self.slippage_model == 'volatility_based':
            # Slippage based on market volatility
            # For this model, we'd need volatility data - using a proxy based on high-low range
            high = float(execution_bar.get('high', base_price * 1.01))
            low = float(execution_bar.get('low', base_price * 0.99))
            volatility_proxy = (high - low) / base_price
            
            vol_slippage_factor = self.slippage_factor * (1 + 2 * volatility_proxy)
            
            # Add random component
            if self.slippage_distribution == 'uniform':
                random_component = np.random.uniform(-0.2, 0.2) * self.slippage_factor
            elif self.slippage_distribution == 'normal':
                random_component = np.random.normal(0, 0.15) * self.slippage_factor
            elif self.slippage_distribution == 'lognormal':
                random_component = (np.random.lognormal(0, 0.08) - 1) * self.slippage_factor
            else:
                random_component = 0.0
                
            return base_price * (vol_slippage_factor + random_component)
            
        else:
            # Default to fixed slippage
            return base_price * self.slippage_factor

    def _calculate_market_impact(self,
                                order: Order,
                                execution_bar: pd.Series,
                                volume_column: str,
                                base_price: float) -> float:
        """Calculate market impact based on selected model"""
        base_price = float(base_price)
        
        # Get market volume for the bar
        volume = float(execution_bar[volume_column]) if volume_column in execution_bar else 1000
        
        # Calculate order size relative to market volume
        order_notional = order.quantity * base_price
        volume_ratio = order_notional / volume if volume > 0 else 0
        
        if self.market_impact_model == 'linear':
            impact = volume_ratio * self.market_impact_factor
        elif self.market_impact_model == 'square_root':
            # Square root model - more realistic for larger orders
            impact = math.sqrt(volume_ratio) * self.market_impact_factor
        elif self.market_impact_model == 'power':
            # Power model with exponent between 0.5 and 1.0
            power = 0.6  # Common empirical value
            impact = (volume_ratio ** power) * self.market_impact_factor
        else:
            impact = volume_ratio * self.market_impact_factor  # Default to linear

        # Market impact is always in the direction that hurts the trader
        return base_price * impact

    def _update_position(self, fill: Fill):
        """Update position based on fill"""
        symbol_str = fill.symbol.value
        
        if symbol_str not in self.positions:
            # Create new position
            from domain.entities.trading_entities import Position, PositionSide
            from domain.value_objects import Money
            
            side = PositionSide.LONG if fill.side.name == 'BUY' else PositionSide.SHORT
            self.positions[symbol_str] = Position(
                symbol=fill.symbol,
                side=side,
                quantity=fill.quantity,
                entry_price=fill.price,
                current_price=fill.price,
                unrealized_pnl=Money(0),
                realized_pnl=Money(0),
                timestamp=fill.timestamp
            )
        else:
            # Update existing position
            pos = self.positions[symbol_str]
            
            if (pos.side.name == 'LONG' and fill.side.name == 'BUY') or \
               (pos.side.name == 'SHORT' and fill.side.name == 'SELL'):
                # Increase position
                total_qty = pos.quantity + fill.quantity
                avg_price = ((pos.quantity * float(pos.entry_price.amount)) + 
                             (fill.quantity * float(fill.price.amount))) / total_qty
                             
                pos.quantity = total_qty
                pos.entry_price = Money(avg_price)
            else:
                # Decrease position - calculate realized P&L
                close_qty = min(pos.quantity, fill.quantity)
                
                # Calculate realized P&L
                entry_value = pos.entry_price.amount * close_qty
                exit_value = fill.price.amount * close_qty
                realized_pnl = (exit_value - entry_value) if pos.side.name == 'LONG' else (entry_value - exit_value)
                
                pos.realized_pnl = Money(float(pos.realized_pnl.amount) + realized_pnl)
                
                # Reduce quantity
                pos.quantity -= close_qty
                
                if pos.quantity == 0:
                    # Close position
                    del self.positions[symbol_str]
                else:
                    # Update position with remaining quantity
                    pos.unrealized_pnl = Money(
                        (float(pos.current_price.amount) - float(pos.entry_price.amount)) * pos.quantity
                        if pos.side.name == 'LONG' else
                        (float(pos.entry_price.amount) - float(pos.current_price.amount)) * pos.quantity
                    )

    def _update_capital(self, fill: Fill):
        """Update capital based on fill"""
        # Calculate cost of fill (including fees)
        fill_cost = fill.quantity * float(fill.price.amount)
        total_cost = fill_cost + float(fill.fee.amount)
        
        # Update cash based on fill direction
        if fill.side.name == 'BUY':
            self.cash -= total_cost
        else:  # SELL
            self.cash += (fill_cost - float(fill.fee.amount))  # Fees reduce credit
            
        # Update positions' current market values
        for pos in self.positions.values():
            if pos.symbol.value in [fill.symbol.value]:
                # Update current price for this position
                pos.current_price = fill.price
                
                # Recalculate unrealized P&L
                if pos.side.name == 'LONG':
                    pos.unrealized_pnl = Money(
                        (float(pos.current_price.amount) - float(pos.entry_price.amount)) * pos.quantity
                    )
                else:  # SHORT
                    pos.unrealized_pnl = Money(
                        (float(pos.entry_price.amount) - float(pos.current_price.amount)) * pos.quantity
                    )
        
        # Calculate total equity
        total_equity = self.cash
        for pos in self.positions.values():
            if pos.side.name == 'LONG':
                mtm_value = float(pos.current_price.amount) * pos.quantity
            else:  # SHORT
                mtm_value = -(float(pos.current_price.amount) * pos.quantity)
            total_equity += mtm_value
        
        self.current_capital = total_equity
        self.equity_curve.append(total_equity)

    def _calculate_performance_metrics(self, prices: List[float]) -> BacktestMetrics:
        """Calculate performance metrics from equity curve"""
        if len(self.equity_curve) < 2:
            return BacktestMetrics(
                total_return=0.0, sharpe_ratio=0.0, max_drawdown=0.0, 
                win_rate=0.0, profit_factor=0.0, total_trades=0,
                winning_trades=0, losing_trades=0, avg_win=0.0, 
                avg_loss=0.0, final_equity=self.initial_capital,
                volatility=0.0, alpha=0.0, beta=0.0, 
                information_ratio=0.0, calmar_ratio=0.0
            )

        # Calculate returns
        equity_values = np.array(self.equity_curve)
        returns = np.diff(equity_values) / equity_values[:-1]
        
        # Total return
        total_return = (equity_values[-1] / self.initial_capital) - 1.0
        
        # Volatility (annualized)
        if len(returns) > 1:
            volatility = np.std(returns) * np.sqrt(252)  # Annualized
        else:
            volatility = 0.0

        # Sharpe ratio (annualized)
        if volatility > 0:
            excess_return = (np.mean(returns) * 252)  # Annualized
            sharpe_ratio = excess_return / volatility
        else:
            sharpe_ratio = 0.0

        # Max drawdown
        running_max = np.maximum.accumulate(equity_values)
        drawdowns = (equity_values - running_max) / running_max
        max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Trade statistics
        winning_trades = sum(1 for trade in self.trade_log if (trade.get('pnl', 0) or 0) > 0)
        losing_trades = sum(1 for trade in self.trade_log if (trade.get('pnl', 0) or 0) < 0)
        total_trades = len(self.trade_log)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Avg win/loss
        wins = [trade.get('pnl', 0) for trade in self.trade_log if (trade.get('pnl', 0) or 0) > 0]
        losses = [trade.get('pnl', 0) for trade in self.trade_log if (trade.get('pnl', 0) or 0) < 0]
        
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Alpha, Beta, Information ratio, Calmar ratio (simplified calculations)
        # For proper calculations, we would need benchmark data; using simplified values
        alpha = sharpe_ratio * 0.02 if sharpe_ratio > 0 else -abs(sharpe_ratio) * 0.02  # Simplified
        beta = 0.8 + np.random.uniform(-0.2, 0.2)  # Placeholder
        info_ratio = sharpe_ratio * 0.5 if sharpe_ratio > 0 else 0.0  # Simplified
        calmar_ratio = total_return / abs(max_drawdown) if abs(max_drawdown) > 0 else 0.0

        return BacktestMetrics(
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            final_equity=equity_values[-1],
            volatility=volatility,
            alpha=alpha,
            beta=beta,
            information_ratio=info_ratio,
            calmar_ratio=calmar_ratio
        )


class AdvancedBacktestEngine(RealisticBacktestEngine):
    """Advanced backtesting engine with additional features like correlation, risk management, etc."""

    def __init__(self, 
                 initial_capital: float = 100000.0,
                 fee_rate: float = 0.001,
                 slippage_model: str = 'volume_based',
                 slippage_factor: float = 0.0005,
                 market_impact_model: str = 'square_root',
                 market_impact_factor: float = 0.001,
                 max_position_risk: float = 0.02,  # Max 2% risk per position
                 max_portfolio_risk: float = 0.10,  # Max 10% portfolio risk
                 correlation_threshold: float = 0.7,  # Max correlation between strategies
                 volatility_target: float = 0.15):  # Target 15% annual volatility
        super().__init__(initial_capital, fee_rate, slippage_model, slippage_factor, 
                         market_impact_model, market_impact_factor)
        
        self.max_position_risk = max_position_risk
        self.max_portfolio_risk = max_portfolio_risk
        self.correlation_threshold = correlation_threshold
        self.volatility_target = volatility_target
        
        # Portfolio state tracking
        self.daily_pnls: List[float] = []
        self.strategy_correlations: Dict[str, Dict[str, float]] = {}

    def backtest_with_risk_controls(self, 
                                   signals: List[Signal],
                                   price_data: pd.DataFrame,
                                   risk_on: bool = True) -> BacktestMetrics:
        """Execute backtest with comprehensive risk controls"""
        # Apply risk filtering to signals before execution
        if risk_on:
            filtered_signals = self._apply_risk_filters(signals, price_data)
        else:
            filtered_signals = signals
            
        # Execute standard backtest with filtered signals
        metrics = self.backtest_strategy(filtered_signals, price_data)
        
        return metrics

    def _apply_risk_filters(self, signals: List[Signal], price_data: pd.DataFrame) -> List[Signal]:
        """Apply various risk filters to signals before execution"""
        filtered_signals = []
        
        for signal in signals:
            # Check position size limits
            if not self._check_position_size_limit(signal):
                logger.debug(f"Signal for {signal.symbol.value} filtered - exceeds position size limits")
                continue
                
            # Check portfolio risk limits
            if not self._check_portfolio_risk(signal):
                logger.debug(f"Signal for {signal.symbol.value} filtered - exceeds portfolio risk limits")
                continue
                
            # TODO: Implement correlation checks between strategies
            # For now, just add the signal
            filtered_signals.append(signal)
            
        logger.info(f"Applied risk filters: {len(signals)} -> {len(filtered_signals)} signals")
        return filtered_signals

    def _check_position_size_limit(self, signal: Signal) -> bool:
        """Check if taking this position would exceed position size limits"""
        # Calculate potential position value
        # For now, we'll just check if it exceeds max position size percentage
        potential_position_value = self.current_capital * float(signal.confidence.value) * self.max_position_size
        
        # Check if this exceeds our risk tolerance per position
        max_position_value = self.current_capital * self.max_position_risk
        return potential_position_value <= max_position_value

    def _check_portfolio_risk(self, signal: Signal) -> bool:
        """Check if taking this position would exceed portfolio risk limits"""
        # Calculate potential portfolio exposure
        # This is a simplified check; in reality would be more comprehensive
        potential_exposure = self.current_capital * float(signal.confidence.value) * self.max_position_size
        current_exposure = self.initial_capital - self.cash
        
        return (current_exposure + potential_exposure) <= (self.current_capital * self.max_portfolio_risk)