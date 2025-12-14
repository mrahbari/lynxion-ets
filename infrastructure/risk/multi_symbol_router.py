"""
Multi-Symbol Router for handling signals from multiple symbols and routing them to execution engine.
Following Hedge Fund standards for multi-asset strategy execution.
"""
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from domain.entities.trading_entities import Signal, Order
from domain.value_objects import Symbol
from shared.logger import logger
from infrastructure.backtest.realistic_backtester import RealisticBacktester


class SymbolWatcher:
    """
    Manage one symbol's data and strategy execution
    """
    def __init__(self, symbol: str, strategy_func, risk_manager):
        self.symbol = symbol
        self.strategy_func = strategy_func
        self.risk_manager = risk_manager
        self.signals = []
        self.data = None
        logger.info(f"SymbolWatcher initialized for {symbol}")

    def set_data(self, data: pd.DataFrame):
        """Set the market data for this symbol"""
        self.data = data
        logger.info(f"Set data for {self.symbol} with {len(data)} records")

    def step(self, i: int, backtester: RealisticBacktester):
        """Process one time step and generate signal"""
        if self.data is None or i >= len(self.data):
            return None

        row = self.data.iloc[i]
        
        # Prepare the row data with the current timestamp
        signal_data = row.to_dict()
        if 'timestamp' not in signal_data:
            signal_data['timestamp'] = self.data.index[i] if hasattr(self.data.index, 'to_pydatetime') else datetime.now()

        # Generate signal using strategy function
        signal_value = self.strategy_func(signal_data, self.risk_manager.get_strategy_params(self.symbol))
        
        # Convert signal value to actual Signal object
        if signal_value != 0:  # Only create signal if there's actually a signal
            from domain.entities.trading_entities import SignalType
            from domain.value_objects import Percentage
            from decimal import Decimal

            signal_type = SignalType.BUY if signal_value > 0 else SignalType.SELL
            signal_obj = Signal(
                symbol=Symbol(self.symbol),
                signal_type=signal_type,
                confidence=Percentage(Decimal('0.7')),  # Default confidence
                score=signal_value,
                strategy_name="default_strategy",
                timestamp=signal_data['timestamp']
            )
            
            self.signals.append(signal_obj)
            
            # Execute the signal through the backtester
            if signal_value > 0:  # Buy signal
                position_size = self.risk_manager.calculate_position_size(self.symbol, signal_obj, backtester.equity)
                if position_size > 0:
                    backtester.execute_order(
                        side='buy',
                        size=position_size,
                        price=float(row['close']),
                        timestamp=signal_data['timestamp'],
                        market_data={
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'volume': float(row['volume'])
                        }
                    )
            elif signal_value < 0:  # Sell signal
                # Only sell if there's a position
                if backtester.position > 0:
                    position_size = min(self.risk_manager.calculate_position_size(self.symbol, signal_obj, backtester.equity), backtester.position)
                    if position_size > 0:
                        backtester.execute_order(
                            side='sell',
                            size=position_size,
                            price=float(row['close']),
                            timestamp=signal_data['timestamp'],
                            market_data={
                                'high': float(row['high']),
                                'low': float(row['low']),
                                'volume': float(row['volume'])
                            }
                        )
            
            return signal_obj
        
        return None


class StrategyAggregator:
    """
    Combine signals from multiple engines for the same symbol
    """
    def __init__(self, watchers: List[SymbolWatcher]):
        self.watchers = watchers

    def aggregate(self, i: int, backtester: RealisticBacktester):
        """Aggregate signals from all watchers at time step i"""
        final_signals = []
        for watcher in self.watchers:
            signal = watcher.step(i, backtester)
            if signal:
                final_signals.append(signal)
        
        return final_signals


class RiskManager:
    """
    Capital Allocation / Max Exposure / Position Sizing
    """
    def __init__(self, capital_per_symbol: float = 0.05, max_total_exposure: float = 0.80):
        self.capital_per_symbol = capital_per_symbol  # fraction of total balance per symbol
        self.max_total_exposure = max_total_exposure  # max fraction of balance in positions
        self.strategy_params = {}
        logger.info(f"RiskManager initialized with capital_per_symbol: {capital_per_symbol}, max_total_exposure: {max_total_exposure}")

    def get_strategy_params(self, symbol: str) -> Dict:
        """Get strategy parameters for a specific symbol"""
        # Default parameters for backtesting
        return {
            "risk_per_trade": 0.02,
            "atr_multiplier": 2.0,
            "risk_reward_ratio": 2.0,
            "symbol": symbol
        }

    def calculate_position_size(self, symbol: str, signal: Signal, current_equity: float) -> float:
        """Calculate position size based on risk parameters"""
        # Use a percentage of available equity per symbol
        available_for_symbol = current_equity * self.capital_per_symbol
        
        # Calculate position size based on risk per trade (2% of equity per trade as default)
        risk_amount = available_for_symbol * 0.02  # 2% risk per trade
        
        # In a real implementation, this would also factor in stop loss distance
        # For now, return a simple position size
        return risk_amount / 1000 if risk_amount > 1000 else risk_amount / 100  # Default size based on available funds


class MultiSymbolRouter:
    """
    Send signals from all symbols to execution engine
    """
    def __init__(self, symbols: List[str], strategy_func, risk_manager: RiskManager):
        self.symbols = symbols
        self.strategy_func = strategy_func
        self.risk_manager = risk_manager
        self.watchers = []
        
        # Create a watcher for each symbol
        for symbol in symbols:
            watcher = SymbolWatcher(symbol, strategy_func, risk_manager)
            self.watchers.append(watcher)
        
        logger.info(f"MultiSymbolRouter initialized for {len(symbols)} symbols: {symbols}")

    def set_data_for_symbol(self, symbol: str, data: pd.DataFrame):
        """Set market data for a specific symbol"""
        for watcher in self.watchers:
            if watcher.symbol == symbol:
                watcher.set_data(data)
                break

    def run_backtest(self, market_data_loader, backtester: RealisticBacktester):
        """Run backtest across all symbols"""
        logger.info(f"Starting backtest for {len(self.watchers)} symbols")
        
        # Load data for each symbol
        for watcher in self.watchers:
            try:
                # Try to load data for the symbol
                # This assumes market_data_loader is compatible with our data format
                data = market_data_loader.load(watcher.symbol)
                if data is not None and not data.empty:
                    # Ensure timestamp is properly set as index if it exists as a column
                    if 'timestamp' in data.columns:
                        data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
                        data.set_index('timestamp', inplace=True)
                    watcher.set_data(data)
                    logger.info(f"Loaded {len(data)} records for {watcher.symbol}")
                else:
                    logger.warning(f"No data found for {watcher.symbol}")
                    # Create minimal data to avoid errors
                    import numpy as np
                    watcher.set_data(pd.DataFrame({
                        'open': [100],
                        'high': [101],
                        'low': [99],
                        'close': [100],
                        'volume': [1000]
                    }, index=[pd.Timestamp.now()]))
            except Exception as e:
                logger.error(f"Error loading data for {watcher.symbol}: {e}")
                # Create minimal data to avoid errors
                import numpy as np
                watcher.set_data(pd.DataFrame({
                    'open': [100],
                    'high': [101],
                    'low': [99],
                    'close': [100],
                    'volume': [1000]
                }, index=[pd.Timestamp.now()]))
        
        # Create aggregator
        aggregator = StrategyAggregator(self.watchers)
        
        # Run backtest across the time series of the first symbol
        if self.watchers and len(self.watchers[0].data) > 0:
            max_steps = min([len(watcher.data) for watcher in self.watchers if watcher.data is not None])
            
            for i in range(max_steps):
                # Process all watchers at time step i
                signals = aggregator.aggregate(i, backtester)
                
                if i % 100 == 0:  # Log progress every 100 steps
                    logger.info(f"Processed {i}/{max_steps} steps, generated {len(signals)} signals")
        
        logger.info("MultiSymbolRouter backtest completed")
        
        # Return backtester results
        return backtester._calculate_performance_metrics()