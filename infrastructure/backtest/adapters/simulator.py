from typing import Dict, List, Optional, Callable
from shared.types import Signal, Order, Fill, Position, Balance, SignalType, OrderSide
from shared.logger import logger
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class BacktestSimulator:
    """Backtesting simulator that replays historical market data and tests strategies"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Backtest parameters
        self.start_date = config.get('start_date')
        self.end_date = config.get('end_date')
        self.initial_capital = config.get('initial_capital', 100000)
        self.commission = config.get('commission', 0.001)  # 0.1% commission
        self.slippage = config.get('slippage', 0.0005)   # 0.05% slippage
        self.timeframe = config.get('timeframe', '1h')
        
        # Market data
        self.market_data = {}
        self.data_index = 0
        
        # Portfolio tracking
        self.current_balance = self.initial_capital
        self.cash_balance = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades = []
        self.equity_curve = []
        self.drawdowns = []
        
        # Execution tracking
        self.pending_orders = []
        self.filled_orders = []
        
        # Performance metrics
        self.total_return = 0
        self.annual_return = 0
        self.volatility = 0
        self.sharpe_ratio = 0
        self.max_drawdown = 0
        self.win_rate = 0
        self.profit_factor = 0
        
    def load_market_data(self, data: Dict[str, pd.DataFrame]):
        """Load market data for backtesting"""
        self.market_data = data
        
        # Verify all dataframes have the same length and index
        lengths = [len(df) for df in data.values()]
        if len(set(lengths)) > 1:
            logger.warning("Market data has different lengths")
        
        self.data_index = 0
    
    def run_backtest(self, signal_generator: Callable, 
                     strategy_func: Callable,
                     risk_manager: Optional[Callable] = None) -> Dict:
        """Run the backtest simulation"""
        
        # Initialize tracking
        self.current_balance = self.initial_capital
        self.cash_balance = self.initial_capital
        self.trades = []
        self.equity_curve = []
        self.positions = {}
        
        # Get the minimum length of data across all symbols
        if not self.market_data:
            return self.get_performance_metrics()
            
        min_length = min(len(df) for df in self.market_data.values())
        
        # Main backtesting loop
        for i in range(min_length):
            # Update current market data
            current_data = {}
            for symbol, df in self.market_data.items():
                if i < len(df):
                    current_data[symbol] = df.iloc[i]
            
            if not current_data:
                continue
            
            # Generate signals
            signals = signal_generator(current_data)
            
            # Apply risk management if provided
            if risk_manager:
                signals = risk_manager(signals, self)
            
            # Process signals with strategy
            if signals:
                for signal in signals:
                    order = strategy_func(signal, self)
                    if order:
                        self.submit_order(order)
            
            # Execute any pending orders at current price
            self._execute_pending_orders(current_data)
            
            # Update equity curve
            current_equity = self.calculate_equity(current_data)
            self.equity_curve.append({
                'timestamp': current_data[list(current_data.keys())[0]].name if current_data else datetime.now(),
                'equity': current_equity
            })
            
            # Increment data index
            self.data_index += 1
        
        # Calculate performance metrics
        self._calculate_performance_metrics()
        
        return self.get_performance_metrics()
    
    def submit_order(self, order: Order):
        """Submit an order for execution"""
        # Apply risk management before accepting order
        if self._validate_order(order):
            # Calculate execution price with slippage
            current_price = self._get_current_price(order.symbol)
            if current_price is None:
                return False
            
            if order.side == OrderSide.BUY:
                execution_price = current_price * (1 + self.slippage)
            else:
                execution_price = current_price * (1 - self.slippage)
            
            # Create fill
            fill = Fill(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                timestamp=datetime.now(),  # In backtest, we'll use the current data's timestamp
                order_id=f"backtest_order_{len(self.filled_orders)}"
            )
            
            # Process the fill
            self._process_fill(fill)
            self.filled_orders.append(fill)
            
            return True
        else:
            logger.debug(f"Order rejected by risk management: {order.symbol} {order.side} {order.quantity}")
            return False
    
    def _validate_order(self, order: Order) -> bool:
        """Validate an order against risk constraints"""
        # Check if we have enough cash for buy orders
        if order.side == OrderSide.BUY:
            current_price = self._get_current_price(order.symbol)
            if current_price is None:
                return False
                
            order_value = order.quantity * current_price * (1 + self.commission)
            if order_value > self.cash_balance:
                return False
        
        # Add other risk validations here
        return True
    
    def _execute_pending_orders(self, current_data: Dict):
        """Execute any pending orders at current market prices"""
        # In this backtest implementation, we'll assume all orders get filled at current prices
        # In a more realistic backtest, you might check if limit orders should be filled
        
        for order in self.pending_orders[:]:
            execution_price = self._get_current_price(order.symbol)
            if execution_price is not None:
                self.submit_order(order)
                self.pending_orders.remove(order)
    
    def _process_fill(self, fill: Fill):
        """Process a fill and update portfolio"""
        # Calculate costs
        cost = fill.quantity * fill.price
        commission = cost * self.commission
        
        # Update cash balance
        if fill.side == OrderSide.BUY:
            total_cost = cost + commission
            if self.cash_balance >= total_cost:
                self.cash_balance -= total_cost
            else:
                logger.error(f"Insufficient cash for fill: {fill.quantity} {fill.symbol} @ {fill.price}")
                return
        else:  # SELL
            proceeds = cost - commission
            self.cash_balance += proceeds
        
        # Update position
        if fill.symbol in self.positions:
            current_pos = self.positions[fill.symbol]
            if current_pos.side == fill.side:
                # Increasing position
                new_quantity = current_pos.quantity + fill.quantity
                # Weighted average price
                new_price = (current_pos.entry_price * current_pos.quantity + fill.price * fill.quantity) / new_quantity
                self.positions[fill.symbol] = Position(
                    symbol=fill.symbol,
                    side=current_pos.side,
                    quantity=new_quantity,
                    entry_price=new_price,
                    unrealized_pnl=0,
                    timestamp=fill.timestamp
                )
            else:
                # Closing or reducing position
                if current_pos.quantity > fill.quantity:
                    # Partial close
                    remaining_qty = current_pos.quantity - fill.quantity
                    new_price = current_pos.entry_price  # Keep same entry price
                    self.positions[fill.symbol] = Position(
                        symbol=fill.symbol,
                        side=current_pos.side,
                        quantity=remaining_qty,
                        entry_price=new_price,
                        unrealized_pnl=0,
                        timestamp=fill.timestamp
                    )
                elif current_pos.quantity == fill.quantity:
                    # Complete close
                    del self.positions[fill.symbol]
                else:
                    # Close existing and create new position in opposite direction
                    new_qty = fill.quantity - current_pos.quantity
                    self.positions[fill.symbol] = Position(
                        symbol=fill.symbol,
                        side=fill.side,
                        quantity=new_qty,
                        entry_price=fill.price,
                        unrealized_pnl=0,
                        timestamp=fill.timestamp
                    )
        else:
            # New position
            self.positions[fill.symbol] = Position(
                symbol=fill.symbol,
                side=fill.side,
                quantity=fill.quantity,
                entry_price=fill.price,
                unrealized_pnl=0,
                timestamp=fill.timestamp
            )
        
        # Record the trade
        self.trades.append(fill)
    
    def calculate_equity(self, current_data: Dict) -> float:
        """Calculate total portfolio equity"""
        equity = self.cash_balance
        
        for symbol, position in self.positions.items():
            current_price = current_data.get(symbol)
            if current_price is not None:
                if position.side == 'LONG':
                    equity += position.quantity * current_price
                else:  # SHORT
                    # For short positions, equity increases when price decreases
                    equity += position.quantity * position.entry_price  # Initial credit
                    equity -= position.quantity * current_price      # Current liability
        
        return equity
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol from market data"""
        if not self.market_data or symbol not in self.market_data:
            return None
        
        symbol_data = self.market_data[symbol]
        if self.data_index >= len(symbol_data):
            return None
        
        return float(symbol_data.iloc[self.data_index]['close'])
    
    def _calculate_performance_metrics(self):
        """Calculate performance metrics"""
        if not self.equity_curve:
            return
        
        equity_values = [e['equity'] for e in self.equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        
        if len(returns) < 2:
            return
        
        # Total and annualized return
        self.total_return = (equity_values[-1] - equity_values[0]) / equity_values[0]
        
        # Assuming daily data, calculate annualized return
        years = len(returns) / 252  # 252 trading days per year
        if years > 0:
            self.annual_return = (equity_values[-1] / equity_values[0]) ** (1 / years) - 1
        
        # Volatility (annualized standard deviation of returns)
        self.volatility = np.std(returns) * np.sqrt(252)
        
        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        self.sharpe_ratio = (self.annual_return - risk_free_rate) / self.volatility if self.volatility > 0 else 0
        
        # Max drawdown
        running_max = np.maximum.accumulate(equity_values)
        drawdowns = (equity_values - running_max) / running_max
        self.max_drawdown = abs(np.min(drawdowns))
        
        # Win rate
        profitable_trades = [t for t in self.trades if self._is_profitable_trade(t)]
        self.win_rate = len(profitable_trades) / len(self.trades) if self.trades else 0
        
        # Profit factor
        gains = sum(max(0, self._calculate_trade_pnl(t)) for t in self.trades)
        losses = abs(sum(min(0, self._calculate_trade_pnl(t)) for t in self.trades))
        self.profit_factor = gains / losses if losses > 0 else float('inf')
    
    def _is_profitable_trade(self, trade: Fill) -> bool:
        """Determine if a trade was profitable (simplified)"""
        # This is a simplified check - in reality, you'd need to match buy/sell pairs
        # For this backtest, we'll use a placeholder approach
        return True  # Placeholder
    
    def _calculate_trade_pnl(self, trade: Fill) -> float:
        """Calculate P&L for a trade (simplified)"""
        # Simplified - would need proper trade matching in a real implementation
        return 0.0  # Placeholder
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'total_trades': len(self.trades),
            'final_equity': self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_capital,
            'initial_capital': self.initial_capital
        }
    
    def get_equity_curve(self) -> List[Dict]:
        """Get the equity curve data"""
        return self.equity_curve.copy()
    
    def get_trade_log(self) -> List[Fill]:
        """Get the trade log"""
        return self.trades.copy()


class BacktestDataProvider:
    """Provides historical data for backtesting"""
    
    def __init__(self):
        self.data = {}
    
    def add_data(self, symbol: str, data: pd.DataFrame):
        """Add historical data for a symbol"""
        self.data[symbol] = data
    
    def get_data_for_range(self, symbol: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """Get data for a specific date range"""
        if symbol not in self.data:
            return None
        
        df = self.data[symbol]
        
        # Filter by date range
        mask = (df.index >= start) & (df.index <= end)
        return df[mask]
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        return list(self.data.keys())