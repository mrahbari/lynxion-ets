"""
Realistic backtesting engine with proper order simulation including slippage, fees, and market impact.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import math
from decimal import Decimal

from domain.entities.trading_entities import Signal, Order, Fill, Position
from domain.value_objects import Symbol, Money, Percentage
from domain.ports.backtest_ports import BacktestEnginePort
from shared.logger import logger


class RealisticBacktestEngine(BacktestEnginePort):
    """Realistic backtesting engine that simulates actual trading conditions."""

    def __init__(self,
                 initial_capital: float = 100000.0,
                 fee_rate: float = 0.001,  # 0.1% per trade
                 slippage_model: str = 'volume_based',  # 'fixed', 'volume_based', 'volatility_based'
                 slippage_factor: float = 0.0005,  # 0.05% base slippage
                 market_impact_model: str = 'square_root',  # 'linear', 'square_root', 'power'
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
                         **kwargs) -> Dict[str, Any]:
        """
        Execute backtest of strategy using realistic order simulation.

        Args:
            signals: List of signals to execute
            price_data: DataFrame with OHLCV data
            **kwargs: Additional parameters

        Returns:
            Dictionary with backtest results and metrics
        """
        logger.info(f"Starting backtest with initial capital: ${self.initial_capital:,.2f}, "
                   f"{len(signals)} signals, data range: {len(price_data)} bars")

        # Reset state
        self._reset_state()

        # Sort signals by timestamp to process chronologically
        sorted_signals = sorted(signals, key=lambda s: s.timestamp)

        # Process signals chronologically
        for signal in sorted_signals:
            # Execute the signal as an order
            order = self._create_order_from_signal(signal)
            if order:
                # Execute the order through realistic simulation
                fills = self._execute_order_realistically(order, price_data, signal)
                if fills:
                    for fill in fills:
                        self.fills.append(fill)
                        self._update_position(fill)
                        self._update_capital(fill)
                        
                        # Log the trade
                        self.trade_log.append({
                            'timestamp': signal.timestamp,
                            'symbol': signal.symbol.value,
                            'signal_type': signal.signal_type.name,
                            'order_size': order.quantity,
                            'execution_price': float(fill.price.amount),
                            'fill_cost': float(fill.fill_cost.amount) if fill.fill_cost else 0,
                            'pnl': float(fill.pnl.amount) if fill.pnl else 0,
                            'capital_after': self.current_capital
                        })

                        logger.debug(f"Executed {order.side.name} {order.quantity} {order.symbol.value} @ ${float(fill.price.amount):.5f}, "
                                   f"P&L: ${float(fill.pnl.amount) if fill.pnl else 0:.2f}")

        # Calculate performance metrics
        metrics = self._calculate_performance_metrics()

        logger.info(f"Backtest completed - Final equity: ${self.current_capital:,.2f}, "
                   f"Total return: {(self.current_capital/self.initial_capital - 1)*100:.2f}%")

        return {
            'final_equity': self.current_capital,
            'total_return': (self.current_capital / self.initial_capital) - 1,
            'total_trades': len(self.fills),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'max_drawdown': metrics.get('max_drawdown', 0),
            'win_rate': metrics.get('win_rate', 0),
            'profit_factor': metrics.get('profit_factor', 0),
            'volatility': metrics.get('volatility', 0),
            'trades': self.trade_log,
            'equity_curve': self.equity_curve
        }

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

    def _create_order_from_signal(self, signal: Signal) -> Optional[Order]:
        """Convert a signal to an executable order with proper sizing"""
        # Determine order side based on signal type
        if signal.signal_type.name in ['BUY', 'LONG']:
            side = 'BUY'
        elif signal.signal_type.name in ['SELL', 'SHORT']:
            side = 'SELL'
        else:
            return None  # Skip HOLD/NEUTRAL signals

        # Calculate position size based on signal confidence and risk management
        position_size = self._calculate_position_size(signal)
        if position_size < self.min_order_size:
            logger.debug(f"Position size {position_size} below minimum {self.min_order_size}, skipping signal")
            return None

        # Get current market price (we'll use close price from most recent data in backtest)
        # In a real backtest, we would get the price at the signal timestamp
        current_price = 1.0  # This will be set by realistic execution

        # Create order
        from domain.entities.trading_entities import Order as DomainOrder, OrderSide
        from domain.value_objects import Money as DomainMoney
        
        order = DomainOrder(
            symbol=signal.symbol,
            side=OrderSide(side),
            quantity=position_size,
            price=DomainMoney(Decimal(str(current_price))),  # Will be updated during execution
            order_type='MARKET',
            strategy=signal.strategy_name,
            timestamp=signal.timestamp,
            metadata={
                'source_signal_confidence': float(signal.confidence.value),
                'target_price': current_price
            }
        )

        self.orders.append(order)
        return order

    def _calculate_position_size(self, signal: Signal) -> float:
        """Calculate proper position size based on risk management"""
        # Calculate position size based on confidence and max position limits
        base_size = self.current_capital * float(signal.confidence.value)
        max_position_size = self.current_capital * self.max_position_size
        
        # Limit position size to maximum allowed
        position_size = min(base_size, max_position_size, self.cash)
        
        # Ensure we have enough cash for the position
        if position_size > self.cash:
            position_size = self.cash
            
        return position_size

    def _execute_order_realistically(self, 
                                   order: Order, 
                                   price_data: pd.DataFrame,
                                   original_signal: Signal) -> List[Fill]:
        """Execute an order with realistic market simulation including slippage, fees, and market impact"""
        fills = []
        
        # Find the price data at or around the signal time
        execution_price = self._get_execution_price(order, price_data, original_signal)
        if not execution_price:
            return fills

        # Calculate slippage based on selected model
        slippage_amount = self._calculate_slippage(order, execution_price)

        # Calculate market impact based on order size and market conditions
        market_impact_amount = self._calculate_market_impact(order, execution_price)

        # Determine final execution price based on order direction
        if order.side.name == 'BUY':
            execution_price = execution_price + slippage_amount + market_impact_amount
        else:  # SELL
            execution_price = execution_price - slippage_amount - market_impact_amount

        # Calculate fees
        notional_value = order.quantity * execution_price
        fee_amount = notional_value * self.fee_rate

        # Create fill
        from domain.entities.trading_entities import Fill as DomainFill, FillType
        from domain.value_objects import Money as DomainMoney
        
        fill = DomainFill(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=DomainMoney(Decimal(str(execution_price))),
            fill_type=FillType.NORMAL,
            timestamp=order.timestamp,
            fee=DomainMoney(Decimal(str(fee_amount))),
            pnl=None,  # Will be calculated when position is closed
            metadata={
                'base_price': order.price.amount,
                'slippage_amount': slippage_amount,
                'market_impact_amount': market_impact_amount,
                'fee_rate': self.fee_rate,
                'fee_amount': fee_amount,
                'notional_value': notional_value
            }
        )

        fills.append(fill)
        return fills

    def _get_execution_price(self, order: Order, price_data: pd.DataFrame, original_signal: Signal) -> Optional[float]:
        """Get the appropriate execution price for the order"""
        # In a real backtest, this would match the signal timestamp to the appropriate price bar
        # For this simulation, we'll just return a reasonable price based on the data
        if not price_data.empty:
            # Return the last close price as a proxy (in real system, match by timestamp)
            return float(price_data['close'].iloc[-1])
        return None

    def _calculate_slippage(self, order: Order, base_price: float) -> float:
        """Calculate slippage based on selected model"""
        base_price = float(base_price)
        
        if self.slippage_model == 'fixed':
            # Fixed percentage slippage
            return base_price * self.slippage_factor
            
        elif self.slippage_model == 'volume_based':
            # In a real implementation, we'd use actual volume data
            # This is a simplified simulation
            volume_ratio = min(1.0, order.quantity / 1000.0)  # Normalize against assumed volume of 1000
            return base_price * self.slippage_factor * (1 + volume_ratio)
            
        elif self.slippage_model == 'volatility_based':
            # For this model, assume higher slippage in more volatile markets
            # In a real system, this would be based on actual volatility data
            volatility_factor = 1.0 + (np.random.random() * 0.5)  # Random volatility effect
            return base_price * self.slippage_factor * volatility_factor
            
        else:
            # Default to fixed slippage
            return base_price * self.slippage_factor

    def _calculate_market_impact(self, order: Order, base_price: float) -> float:
        """Calculate market impact based on selected model"""
        base_price = float(base_price)
        
        # Calculate order size relative to market liquidity
        # For simulation, assume a base liquidity level
        order_notional = order.quantity * base_price
        assumed_daily_volume = 1000000  # Assumed daily volume of $1M
        volume_ratio = order_notional / assumed_daily_volume if assumed_daily_volume > 0 else 0
        
        if self.market_impact_model == 'linear':
            impact = volume_ratio * self.market_impact_factor
        elif self.market_impact_model == 'square_root':
            # Square root model - more realistic for larger orders
            impact = math.sqrt(volume_ratio) * self.market_impact_factor
        elif self.market_impact_model == 'power':
            # Power model with exponent around 0.5-1.0
            power = 0.6  # Common empirical value
            impact = (volume_ratio ** power) * self.market_impact_factor
        else:
            impact = volume_ratio * self.market_impact_factor  # Default to linear

        # Market impact is always in the direction that hurts the trader
        return base_price * impact

    def _update_position(self, fill: Fill):
        """Update position based on fill"""
        symbol_str = fill.symbol.value
        
        from domain.entities.trading_entities import Position as DomainPosition, PositionSide
        from domain.value_objects import Money as DomainMoney
        
        if symbol_str not in self.positions:
            # Create new position
            side = PositionSide.LONG if fill.side.name == 'BUY' else PositionSide.SHORT
            self.positions[symbol_str] = DomainPosition(
                symbol=fill.symbol,
                side=side,
                quantity=fill.quantity,
                entry_price=fill.price,
                current_price=fill.price,
                unrealized_pnl=DomainMoney(Decimal('0')),
                realized_pnl=DomainMoney(Decimal('0')),
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
                pos.entry_price = DomainMoney(Decimal(str(avg_price)))
            else:
                # Decrease position - calculate realized P&L
                close_qty = min(pos.quantity, fill.quantity)
                
                # Calculate realized P&L
                entry_value = float(pos.entry_price.amount) * close_qty
                exit_value = float(fill.price.amount) * close_qty
                realized_pnl = (exit_value - entry_value) if pos.side.name == 'LONG' else (entry_value - exit_value)
                
                pos.realized_pnl = DomainMoney(Decimal(str(float(pos.realized_pnl.amount) + realized_pnl)))
                
                # Reduce quantity
                pos.quantity -= close_qty
                
                if pos.quantity == 0:
                    # Close position completely
                    del self.positions[symbol_str]
                else:
                    # Update position with remaining quantity
                    if pos.side.name == 'LONG':
                        pos.unrealized_pnl = DomainMoney(Decimal(str(
                            (float(pos.current_price.amount) - float(pos.entry_price.amount)) * pos.quantity
                        )))
                    else:  # SHORT
                        pos.unrealized_pnl = DomainMoney(Decimal(str(
                            (float(pos.entry_price.amount) - float(pos.current_price.amount)) * pos.quantity
                        )))

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
            # For the filled symbol, update its current price
            if pos.symbol.value == fill.symbol.value:
                pos.current_price = fill.price
                
                # Recalculate unrealized P&L
                if pos.side.name == 'LONG':
                    pos.unrealized_pnl = DomainMoney(Decimal(str(
                        (float(pos.current_price.amount) - float(pos.entry_price.amount)) * pos.quantity
                    )))
                else:  # SHORT
                    pos.unrealized_pnl = DomainMoney(Decimal(str(
                        (float(pos.entry_price.amount) - float(pos.current_price.amount)) * pos.quantity
                    )))
        
        # Calculate total equity
        total_equity = self.cash
        for pos in self.positions.values():
            if pos.side.name == 'LONG':
                mtm_value = float(pos.current_price.amount) * pos.quantity
            else:  # SHORT (this is simplified; short positions would be calculated differently)
                # For this simplified model, we'll just calculate MTM for long positions
                mtm_value = 0
            total_equity += mtm_value
        
        self.current_capital = total_equity
        self.equity_curve.append(total_equity)

    def _calculate_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics from trade log and equity curve"""
        if len(self.equity_curve) < 2:
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'volatility': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }

        # Calculate returns
        equity_values = np.array(self.equity_curve)
        returns = np.diff(equity_values) / equity_values[:-1]
        
        # Total return
        total_return = (equity_values[-1] / self.initial_capital) - 1.0
        
        # Volatility (annualized)
        if len(returns) > 1:
            volatility = float(np.std(returns) * np.sqrt(252))  # Annualized
        else:
            volatility = 0.0

        # Sharpe ratio (annualized)
        if volatility > 0:
            excess_return = float(np.mean(returns) * 252)  # Annualized
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
        
        avg_win = float(np.mean(wins)) if wins else 0.0
        avg_loss = float(np.mean(losses)) if losses else 0.0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'volatility': volatility,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }