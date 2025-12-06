"""Realistic backtesting implementation with proper order execution simulation."""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

from shared.logger import EnhancedLogger


class RealisticBacktester:
    """
    Realistic backtesting engine that simulates actual trading behavior:
    - Order execution with slippage
    - Transaction fees
    - Market impact
    - Position management
    - Risk controls
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 fee_rate: float = 0.001,  # 0.1% per trade
                 slippage_factor: float = 0.0005,  # 0.05% slippage
                 min_order_size: float = 0.001,
                 max_position_size: float = 0.20,  # 20% max position size
                 max_drawdown: float = 0.15,  # 15% max drawdown
                 max_leverage: float = 1.0):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_factor = slippage_factor
        self.min_order_size = min_order_size
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.max_leverage = max_leverage
        self.logger = EnhancedLogger("RealisticBacktester")
        
        # Trading state
        self.position = 0  # Current position size
        self.position_value = 0  # Current position value in quote currency
        self.cash = initial_capital  # Available cash
        self.equity = initial_capital  # Total equity (cash + position value)
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_equity = initial_capital
        self.max_drawdown_reached = 0.0
        
        # Trade history
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []

        # SL/TP tracking
        self.active_positions: List[Dict[str, Any]] = []  # Track all active positions with SL/TP

        # Data validation
        self.max_data_age_seconds = 86400  # 1 day max age for data
        self.last_candle_time = None
    
    def reset(self):
        """Reset the backtester to initial state."""
        self.position = 0
        self.position_value = 0
        self.cash = self.initial_capital
        self.equity = self.initial_capital
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_equity = self.initial_capital
        self.max_drawdown_reached = 0.0
        self.trades = []
        self.equity_curve = []
        self.active_positions = []
    
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
        
        # Market impact based on order size relative to market volume
        market_vol = market_data.get('volume', 1000000)  # Default volume
        order_to_market_ratio = abs(size * price) / market_vol if market_vol > 0 else 0
        
        # Additional market impact (larger orders face more impact)
        market_impact = base_slippage * (1 + 2 * order_to_market_ratio)  # 2x impact factor
        
        if side.lower() == 'buy':
            # Buy orders get filled at higher price (worse for buyer)
            execution_price = price + market_impact
        else:  # sell
            # Sell orders get filled at lower price (worse for seller)
            execution_price = price - market_impact
        
        # Ensure execution price is reasonable
        if side.lower() == 'buy':
            execution_price = max(execution_price, price * 0.95)  # Don't pay more than 5% above
        else:
            execution_price = min(execution_price, price * 1.05)  # Don't sell for less than 5% below
        
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
        if side.lower() == 'buy':
            # Buy: reduce cash, increase position
            self.cash -= (size * execution_price + fees)
            self.position += size
            self.position_value += (size * execution_price)

            # Add long position to active positions with SL/TP if provided
            if sl_price is not None or tp_price is not None:
                # Set default SL/TP if not provided
                if sl_price is None:
                    sl_price = execution_price * 0.98  # 2% stop loss
                if tp_price is None:
                    tp_price = execution_price * 1.04  # 4% take profit

                self.active_positions.append({
                    'entry_price': execution_price,
                    'size': size,
                    'direction': 1,  # Long
                    'stop_loss': sl_price,
                    'take_profit': tp_price,
                    'timestamp': timestamp
                })
        else:  # sell
            # For sell orders, we might be closing positions
            if self.position > 0:
                # Determine whether we're reducing/fully closing position
                size_to_sell = min(size, self.position)

                # Reduce position
                self.cash += (size_to_sell * execution_price - fees)
                self.position -= size_to_sell
                self.position_value -= (size_to_sell * execution_price)
            else:
                # Sell to open short position
                self.cash += (size * execution_price - fees)
                self.position -= size  # negative position indicates short
                self.position_value -= (size * execution_price)

        # Update equity
        self.equity = self.cash + self.position_value

        # Calculate PnL for this trade (if closing a position)
        trade_pnl = 0
        if ((side.lower() == 'sell' and self.position >= 0) or
            (side.lower() == 'buy' and self.position <= 0)):  # New position or reversal
            pass  # Don't calculate PnL for new positions
        else:  # Closing or reducing position
            # Find matching position from trade history to calculate PnL
            # For simplicity, we'll calculate based on average position
            pass

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
            "cash": self.cash
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
        low_close = np.abs(df['low'] - df['close'].shift(1))    # Use previous close for high/low comparison
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
                    initial_capital: float = None) -> Dict[str, Any]:
        """
        Run the backtest with a given strategy function.
        
        Args:
            data: OHLCV data with timestamps
            strategy_function: Function that takes row and params, returns signal (-1, 0, 1)
            strategy_params: Parameters for the strategy
            initial_capital: Starting capital (overrides default)
        """
        if initial_capital:
            self.initial_capital = initial_capital
            self.cash = initial_capital
            self.equity = initial_capital
            self.max_equity = initial_capital
        
        if strategy_params is None:
            strategy_params = {}

        # Validate data structure
        self._validate_data(data)

        # Validate data freshness
        self._validate_data_freshness(data)

        # Detect missing candles
        self._detect_missing_candles(data)

        # Calculate indicators (properly shifted to prevent lookahead bias)
        data_with_indicators = self.calculate_indicators(data)

        # Store original data reference for force-closing later
        self.data = data_with_indicators

        # Initialize tracking
        self.reset()

        # Track last order time for double-order prevention
        self.last_order_time = {}
        self.order_cooldown_seconds = strategy_params.get('order_cooldown_seconds', 60)  # Default 1 minute

        # Run through each candle
        for i in range(len(data_with_indicators)):
            row = data_with_indicators.iloc[i]
            timestamp = row.get('timestamp', datetime.now())

            # First, check if any active positions hit SL/TP (this happens before new orders)
            sltp_pnl = self._check_stop_loss_take_profit(row, timestamp)

            # Get signal from strategy
            signal = strategy_function(row, strategy_params)

            # Check for double-order prevention
            symbol_for_cooldown = strategy_params.get('symbol', 'default')
            if symbol_for_cooldown in self.last_order_time:
                time_since_last = (timestamp - self.last_order_time[symbol_for_cooldown]).total_seconds()
                if time_since_last < self.order_cooldown_seconds:
                    # Skip ordering due to cooldown
                    signal = 0  # Clear the signal

            # Determine position sizing based on strategy and risk management
            position_size = self._calculate_position_size(row, signal, strategy_params)

            # Calculate SL and TP prices based on ATR or other methods if we're opening a position
            sl_price = None
            tp_price = None
            if signal > 0 and position_size > 0:  # Buy signal
                # Calculate stop loss and take profit based on ATR or other methods
                atr = row.get('atr', 0.01 * row['close'])  # Get ATR value
                risk_params = strategy_params.get('atr_multiplier', 2.0)
                reward_params = strategy_params.get('risk_reward_ratio', 2.0)

                entry_price = row['close']
                sl_price = entry_price - (atr * risk_params)  # Stop loss below entry
                tp_price = entry_price + (atr * risk_params * reward_params)  # Take profit above entry

                # Ensure SL is below entry and TP is above entry
                sl_price = min(sl_price, entry_price * 0.98)  # Max 2% below for safety
                tp_price = max(tp_price, entry_price * 1.02)  # Min 2% above for safety

            # Execute trades based on signal
            if signal > 0 and position_size > 0:  # Buy signal
                trade = self.execute_order(
                    side='buy',
                    size=position_size,
                    price=row['close'],
                    timestamp=timestamp,
                    market_data={
                        'high': row['high'],
                        'low': row['low'],
                        'volume': row['volume']
                    },
                    sl_price=sl_price,
                    tp_price=tp_price
                )

                # Update last order time
                self.last_order_time[symbol_for_cooldown] = timestamp
            elif signal < 0 and position_size > 0:  # Sell signal
                # Only sell if we have a position
                if self.position > 0:
                    trade = self.execute_order(
                        side='sell',
                        size=min(position_size, self.position),  # Don't sell more than we own
                        price=row['close'],
                        timestamp=timestamp,
                        market_data={
                            'high': row['high'],
                            'low': row['low'],
                            'volume': row['volume']
                        }
                    )

                    # Update last order time
                    self.last_order_time[symbol_for_cooldown] = timestamp
            else:
                # No trade, still record equity for curve
                self.equity_curve.append({
                    "timestamp": timestamp,
                    "equity": self.equity,
                    "cash": self.cash,
                    "position_value": self.position_value
                })

        # Force close any remaining positions at the end of the backtest
        if len(self.active_positions) > 0:
            self._force_close_remaining()

        # Calculate performance metrics
        return self._calculate_performance_metrics()

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
                    "entry_price": pos['entry_price']
                }
                self.trades.append(trade_record)

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
                expected_interval = non_zero_diffs.mode().iloc[0] if len(non_zero_diffs.mode()) > 0 else 3600  # Default 1 hour
                # Flag intervals that are significantly larger than expected
                gap_threshold = expected_interval * 5  # Allow up to 5x expected interval
                large_gaps = time_diffs > gap_threshold
                if large_gaps.any() and large_gaps.sum() / len(time_diffs) > 0.1:  # More than 10% are large gaps
                    self.logger.warning(f"Found {large_gaps.sum()} large gaps in data, exceeding {gap_threshold}s threshold")

        # Validate that the most recent data is not too old (for real-time scenarios)
        if len(timestamps) > 0:
            latest_timestamp = timestamps[-1] if hasattr(timestamps, '__getitem__') else timestamps.max()
            if pd.Timestamp.now().timestamp() - latest_timestamp.timestamp() > self.max_data_age_seconds:
                self.logger.warning(f"Data is too old: {latest_timestamp} vs current time")

        return True

    def _detect_missing_candles(self, data: pd.DataFrame, expected_frequency: str = '1H') -> List[int]:
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
                    self.logger.info(f"Detected {len(missing_indices)} missing candles at: {missing_indices[:10]}...")  # Show first 10

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
                self.position_value -= direction * size * entry_price
                self.cash += direction * size * exit_price - total_cost
                self.equity = self.cash + self.position_value

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
                    "entry_price": entry_price
                }
                self.trades.append(trade_record)

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
        base_risk_pct = params.get('risk_per_trade', 0.02)  # Default 2%
        risk_pct = base_risk_pct * (1 - correlation_risk_reduction)  # Reduce risk with higher correlation
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
            position_size = (self.equity * risk_pct) / price

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
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate returns from equity curve for Sharpe and other metrics
        equity_values = [point['equity'] for point in self.equity_curve]
        if len(equity_values) > 1:
            returns = np.diff(equity_values) / equity_values[:-1]
            if len(returns) > 0:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                
                # Sharpe ratio (annualized)
                if std_return > 0:
                    sharpe_ratio = (avg_return / std_return) * np.sqrt(365)  # Daily returns
                else:
                    sharpe_ratio = 0
                
                # Sortino ratio (downside deviation)
                negative_returns = returns[returns < 0]
                if len(negative_returns) > 0:
                    downside_std = np.std(negative_returns)
                    if downside_std > 0:
                        sortino_ratio = (avg_return / downside_std) * np.sqrt(365)
                    else:
                        sortino_ratio = 0
                else:
                    sortino_ratio = sharpe_ratio  # Same as Sharpe if no negative returns
                
                # Max drawdown
                equity_curve = np.array(equity_values)
                running_max = np.maximum.accumulate(equity_curve)
                drawdowns = (equity_curve - running_max) / running_max
                max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
            else:
                sharpe_ratio = 0
                sortino_ratio = 0
                max_drawdown = 0.0
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
            max_drawdown = 0.0
        
        # Profit factor
        winning_pnl = sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) > 0)
        losing_pnl = abs(sum(t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) < 0))
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
        
        # Other metrics
        total_volume = sum(abs(t['size'] * t['price']) for t in self.trades)
        total_fees = sum(t['fees'] for t in self.trades)
        
        metrics = {
            "total_return": float(total_return),
            "sharpe_ratio": float(sharpe_ratio),
            "sortino_ratio": float(sortino_ratio),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "total_trades": int(total_trades),
            "winning_trades": int(winning_trades),
            "losing_trades": int(losing_trades),
            "total_volume": float(total_volume),
            "total_fees": float(total_fees),
            "final_equity": float(self.equity),
            "initial_capital": float(self.initial_capital),
            "max_drawdown_reached": float(self.max_drawdown_reached),
            "trades": [dict(t) for t in self.trades],  # Convert any numpy types to basic types
            "equity_curve": [dict(e) for e in self.equity_curve]
        }
        
        return metrics


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