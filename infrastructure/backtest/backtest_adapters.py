"""
Infrastructure implementations of backtesting services.
"""
from typing import List, Optional, Dict, Any
from domain.entities.trading_entities import Signal, Order, Fill, Position
from domain.value_objects import Symbol, Money
from domain.ports.backtest_ports import (
    BacktestEnginePort, HistoricalDataProviderPort, BacktestMetricsPort
)
from shared.logger import logger
from datetime import datetime, timedelta
import random


class MockHistoricalDataProviderAdapter(HistoricalDataProviderPort):
    """Infrastructure implementation of historical data provider"""
    
    def __init__(self):
        self.mock_data_cache = {}
    
    def get_historical_data(self, 
                           symbol: Symbol, 
                           start_date: str, 
                           end_date: str, 
                           timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical market data for backtesting"""
        logger.info(f"Retrieving historical data for {symbol.value} from {start_date} to {end_date}")
        
        # In a real implementation, this would fetch actual historical data
        # For demonstration, we'll generate mock data
        
        # Parse dates
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if 'Z' in start_date else datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if 'Z' in end_date else datetime.fromisoformat(end_date)
        
        # Generate mock price data
        current_time = start
        data = []
        current_price = 40000.0  # Starting price for BTC
        
        while current_time <= end:
            # Generate OHLCV data
            open_price = current_price
            high = open_price * (1 + abs(random.gauss(0, 0.005)))  # Random walk with volatility
            low = open_price * (1 - abs(random.gauss(0, 0.005)))
            close = min(max(random.gauss(open_price, 100), low), high)  # Random close within high/low
            volume = random.uniform(100, 1000)
            
            data.append({
                'timestamp': current_time.isoformat(),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'symbol': symbol.value
            })
            
            current_price = close  # Next open is current close
            current_time += timedelta(minutes=1)  # 1-minute intervals for '1m' timeframe
        
        logger.info(f"Generated {len(data)} historical data points for {symbol.value}")
        return data


class BasicBacktestEngineAdapter(BacktestEnginePort):
    """Infrastructure implementation of basic backtesting engine"""
    
    def __init__(self, strategy, risk_manager, historical_data_provider: HistoricalDataProviderPort):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.data_provider = historical_data_provider
        self.results = {}
    
    def run_backtest(self, 
                     symbol: Symbol, 
                     start_date: str, 
                     end_date: str, 
                     initial_capital: float) -> Dict[str, Any]:
        """Run a backtest for the given parameters"""
        logger.info(f"Running backtest for {symbol.value} from {start_date} to {end_date}")
        
        # Get historical data
        historical_data = self.data_provider.get_historical_data(
            symbol, start_date, end_date, '1m'
        )
        
        if not historical_data:
            logger.warning("No historical data available for backtest")
            return {}
        
        # Initialize backtest state
        current_capital = initial_capital
        position = 0  # Position size
        entry_price = 0  # Entry price if in position
        trades = []
        returns = [0.0]  # Track returns over time
        
        # Run backtest through historical data
        for i, candle in enumerate(historical_data):
            current_price = candle['close']
            
            # Generate signal based on current market data
            # In a real implementation, this would be more sophisticated
            signal = None
            if i > 10:  # Skip initial data points
                # Simple example: if price is going up, buy; if going down, sell
                if candle['close'] > historical_data[i-5]['close']:  # Price rising over last 5 minutes
                    signal = self._create_signal(symbol, 'BUY')
                elif candle['close'] < historical_data[i-5]['close']:  # Price falling
                    signal = self._create_signal(symbol, 'SELL')
            
            # Execute trades based on signals
            if signal and signal.signal_type.name == 'BUY' and position <= 0:
                # Enter long position
                if current_capital > 0:
                    position_size = current_capital * 0.1  # Use 10% of capital
                    entry_price = current_price
                    position = position_size / current_price
                    current_capital -= position_size
                    logger.info(f"Entering long position: {position:.6f} {symbol.base_asset()} at {current_price:.2f}")
            
            elif signal and signal.signal_type.name == 'SELL' and position >= 0:
                # Exit long position
                if position > 0:
                    exit_value = position * current_price
                    pnl = exit_value - (position * entry_price)
                    current_capital += exit_value
                    trade_return = pnl / (position * entry_price) if position * entry_price > 0 else 0
                    
                    trades.append({
                        'entry_time': historical_data[i-5]['timestamp'],
                        'exit_time': candle['timestamp'],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position_size': position,
                        'pnl': pnl,
                        'return_pct': trade_return
                    })
                    
                    position = 0
                    entry_price = 0
                    returns.append(returns[-1] + trade_return)
                    logger.info(f"Exiting position: P&L = {pnl:.2f} ({trade_return:.2%})")
        
        # Calculate final results
        final_capital = current_capital + (position * historical_data[-1]['close'] if position > 0 else 0)
        total_return = (final_capital - initial_capital) / initial_capital
        total_trades = len(trades)
        win_rate = sum(1 for t in trades if t['pnl'] > 0) / total_trades if total_trades > 0 else 0
        
        results = {
            'initial_capital': initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'sharpe_ratio': self._calculate_sharpe(returns) if len(returns) > 1 else 0,
            'max_drawdown': self._calculate_max_drawdown(returns),
            'trades': trades
        }
        
        self.results = results
        logger.info(f"Backtest completed. Total return: {total_return:.2%}, Total trades: {total_trades}")
        
        return results
    
    def get_backtest_results(self) -> Dict[str, Any]:
        """Get results from the last backtest"""
        return self.results
    
    def _create_signal(self, symbol: Symbol, signal_type: str) -> Signal:
        """Create a mock signal for backtesting"""
        from domain.entities.trading_entities import SignalType
        from domain.value_objects import Percentage
        from decimal import Decimal
        
        # Convert string signal type to enum
        signal_type_enum = getattr(SignalType, signal_type.upper(), SignalType.NEUTRAL)
        
        return Signal(
            symbol=symbol,
            signal_type=signal_type_enum,
            confidence=Percentage(Decimal('0.6')),  # 60% confidence
            score=0.5 if signal_type == 'BUY' else -0.5,
            strategy_name="MockStrategy",
            timestamp=datetime.now()
        )
    
    def _calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        # Calculate daily returns (in this case, per data point)
        daily_returns = [returns[i] - returns[i-1] for i in range(1, len(returns))]
        
        if not daily_returns:
            return 0.0
            
        avg_return = sum(daily_returns) / len(daily_returns)
        volatility = (sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5
        
        return (avg_return / volatility) * (365 ** 0.5) if volatility > 0 else 0.0  # Annualized
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown"""
        if not returns:
            return 0.0
        
        peak = returns[0]
        max_dd = 0.0
        
        for value in returns:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak != 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd


class BacktestMetricsCalculatorAdapter(BacktestMetricsPort):
    """Infrastructure implementation of backtest metrics calculator"""
    
    def __init__(self):
        pass
    
    def calculate_metrics(self, trades: List[Fill], initial_capital: float) -> Dict[str, Any]:
        """Calculate performance metrics from backtest results"""
        if not trades:
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0
            }
        
        # In a real implementation, this would calculate metrics from actual Fill objects
        # For this example, we'll work with the structure from our backtest engine
        # The trades in our backtest engine are dictionaries, not Fill objects
        
        returns = [trade['return_pct'] for trade in trades if 'return_pct' in trade]
        
        total_return = sum(returns) if returns else 0.0
        total_trades = len(returns)
        winning_trades = [r for r in returns if r > 0]
        losing_trades = [r for r in returns if r < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        # Calculate profit factor
        gross_profit = sum(winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate Sharpe ratio (simplified)
        avg_return = sum(returns) / len(returns) if returns else 0.0
        volatility = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0.0
        sharpe_ratio = (avg_return / volatility) * (365 ** 0.5) if volatility > 0 else 0.0
        
        metrics = {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': self._calculate_max_drawdown_from_trades(trades),
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': sum(winning_trades) / len(winning_trades) if winning_trades else 0.0,
            'avg_loss': sum(losing_trades) / len(losing_trades) if losing_trades else 0.0
        }
        
        return metrics
    
    def _calculate_max_drawdown_from_trades(self, trades) -> float:
        """Calculate max drawdown from trade results"""
        # This is a simplified version - in a real system, you'd track account value over time
        running_capital = 100000  # Starting from $100,000
        peak = running_capital
        max_dd = 0.0
        
        for trade in trades:
            if isinstance(trade, dict) and 'pnl' in trade:
                running_capital += trade['pnl']
            else:
                # If it's a Fill object, calculate P&L differently
                continue
            
            if running_capital > peak:
                peak = running_capital
            drawdown = (peak - running_capital) / peak if peak != 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd