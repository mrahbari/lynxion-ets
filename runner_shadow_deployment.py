#!/usr/bin/env python3
"""
Shadow Deployment System - Run trading strategies with real market data
without executing real orders. Compare performance to backtest results.
"""
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import numpy as np
import time

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.portfolio.comprehensive_portfolio_backtester import load_sample_strategies
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
from infrastructure.monitoring.shadow_kpi_monitor import generate_shadow_kpi_report
from shared.logger import EnhancedLogger


class ShadowDeploymentSystem:
    def __init__(self, 
                 symbols: List[str],
                 strategies: List[str],
                 initial_capital: float = 100000.0,
                 risk_per_trade: float = 0.02):
        
        self.symbols = symbols
        self.strategies = strategies
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.logger = EnhancedLogger("ShadowDeployment")
        
        # Performance tracking
        self.trade_log = []
        self.equity_curve = [{'timestamp': datetime.now(), 'equity': initial_capital}]
        self.daily_pnl = {}
        
        # Initialize with validated strategy configurations
        self.strategy_functions = load_sample_strategies()
        
        # Shadow-specific metrics
        self.shadow_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'current_runup': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0
        }

        # Initialize baseline metrics for KPI comparison
        self.baseline_metrics = {
            'total_signals': 0,
            'win_rate': 0.5,  # Default 50% win rate
            'avg_trade_pnl': 0.0,
            'total_trades': 0,
            'regime_classification_accuracy': 0.8  # Default 80% accuracy
        }
        
    def run_shadow_cycle(self):
        """Run one cycle of shadow trading"""
        self.logger.info("Starting shadow trading cycle")
        
        # Get latest market data
        data_loader = CSVHistoryLoaderAdapter()
        current_data = {}
        
        for symbol in self.symbols:
            try:
                df = data_loader.load(symbol=symbol)
                if not df.empty:
                    # Get the most recent data point
                    latest_data = df.iloc[-1].to_dict()
                    latest_data['timestamp'] = df.index[-1]
                    current_data[symbol] = latest_data
                    self.logger.debug(f"Loaded data for {symbol}: {latest_data['close']}")
            except Exception as e:
                self.logger.error(f"Error loading data for {symbol}: {e}")
        
        if not current_data:
            self.logger.warning("No current data available, skipping cycle")
            return
        
        # Generate signals for each strategy
        signals = self.generate_signals(current_data)
        
        # Apply virtual execution
        executed_trades = self.virtual_execution(signals)
        
        # Update performance metrics
        self.update_performance(executed_trades)
        
        # Check for alerts
        self.check_alerts()
        
        # Log current status
        self.log_status()
        
    def generate_signals(self, current_data: Dict[str, Dict]) -> Dict[str, Any]:
        """Generate trading signals using validated strategies"""
        signals = {}
        
        for strategy_name in self.strategies:
            if strategy_name in self.strategy_functions:
                strategy_func = self.strategy_functions[strategy_name]
                
                for symbol, data_point in current_data.items():
                    try:
                        # Apply strategy to current data
                        signal = strategy_func(data_point, {})
                        
                        if signal != 0:  # Only log non-neutral signals
                            signal_key = f"{strategy_name}_{symbol}"
                            signals[signal_key] = {
                                'strategy': strategy_name,
                                'symbol': symbol,
                                'signal': signal,
                                'price': data_point.get('close'),
                                'timestamp': data_point.get('timestamp'),
                                'indicators': {k: v for k, v in data_point.items() 
                                             if k in ['rsi', 'adx', 'atr', 'sma_20', 'sma_50']}
                            }
                    except Exception as e:
                        self.logger.error(f"Error generating signal for {strategy_name} on {symbol}: {e}")
        
        return signals
    
    def virtual_execution(self, signals: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simulate trade execution without placing real orders"""
        executed_trades = []
        
        for signal_key, signal_data in signals.items():
            try:
                # Calculate position size based on risk management
                position_size = self.calculate_position_size(signal_data)
                
                if position_size > 0:
                    trade = {
                        'strategy': signal_data['strategy'],
                        'symbol': signal_data['symbol'],
                        'action': 'BUY' if signal_data['signal'] > 0 else 'SELL',
                        'price': signal_data['price'],
                        'size': position_size,
                        'timestamp': signal_data['timestamp'],
                        'signal_strength': abs(signal_data['signal']),
                        'virtual': True  # Indicates this is a shadow trade
                    }
                    
                    executed_trades.append(trade)
                    self.trade_log.append(trade)
                    self.shadow_metrics['total_trades'] += 1
                    self.logger.info(f"Shadow trade executed: {trade}")
                    
            except Exception as e:
                self.logger.error(f"Error in virtual execution for {signal_key}: {e}")
        
        return executed_trades
    
    def calculate_position_size(self, signal_data: Dict[str, Any]) -> float:
        """Request position size - this should be handled by the risk manager"""
        # According to the risk governance rules, the Strategy module should only
        # request risk parameters but not calculate them. The actual calculation
        # must be done by the Risk module.

        # Return a default value that will be overridden by the risk manager
        # This is just a placeholder to maintain interface compatibility
        return 0.0
    
    def update_performance(self, executed_trades: List[Dict[str, Any]]):
        """Update performance metrics based on executed trades"""
        # In a real implementation, this would track PnL based on subsequent price movements
        # For now, we'll just update the equity curve with a simple approach
        
        # This is a simplified version - in reality, you'd track actual PnL from trades
        current_time = datetime.now()
        current_equity = self.current_capital  # Would be updated based on actual PnL
        
        self.equity_curve.append({
            'timestamp': current_time,
            'equity': current_equity
        })
        
        # Update shadow metrics
        if len(self.equity_curve) > 1:
            # Calculate returns
            returns = []
            for i in range(1, len(self.equity_curve)):
                ret = (self.equity_curve[i]['equity'] - self.equity_curve[i-1]['equity']) / self.equity_curve[i-1]['equity']
                returns.append(ret)
            
            if returns:
                # Calculate Sharpe ratio (assuming risk-free rate of 0.02 annually)
                excess_returns = np.array(returns) - (0.02 / 252)  # Daily risk-free rate
                if np.std(returns) > 0:
                    self.shadow_metrics['sharpe_ratio'] = np.mean(excess_returns) / np.std(returns) * np.sqrt(252)
                
                # Calculate Sortino ratio (using downside deviation)
                negative_returns = [r for r in returns if r < 0]
                if negative_returns:
                    downside_dev = np.std(negative_returns)
                    if downside_dev > 0:
                        self.shadow_metrics['sortino_ratio'] = np.mean(returns) / downside_dev * np.sqrt(252)
                
                # Calculate max drawdown
                equity_values = [point['equity'] for point in self.equity_curve]
                running_max = np.maximum.accumulate(equity_values)
                drawdowns = (equity_values - running_max) / running_max
                self.shadow_metrics['max_drawdown'] = float(np.min(drawdowns)) if drawdowns.size > 0 else 0.0
    
    def log_status(self):
        """Log current system status"""
        total_trades = len(self.trade_log)
        current_equity = self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_capital
        return_pct = (current_equity - self.initial_capital) / self.initial_capital
        
        self.logger.info(f"Shadow Deployment Status:")
        self.logger.info(f"  Current Equity: ${current_equity:,.2f}")
        self.logger.info(f"  Return: {return_pct:.2%}")
        self.logger.info(f"  Total Shadow Trades: {total_trades}")
        self.logger.info(f"  Active Symbols: {len(self.symbols)}")
        self.logger.info(f"  Active Strategies: {len(self.strategies)}")
        self.logger.info(f"  Sharpe Ratio: {self.shadow_metrics['sharpe_ratio']:.3f}")
        self.logger.info(f"  Max Drawdown: {self.shadow_metrics['max_drawdown']:.2%}")
    
    def check_deviation_from_backtest(self, backtest_return: float) -> bool:
        """Check if shadow performance deviates significantly from backtest"""
        current_return = (self.current_capital - self.initial_capital) / self.initial_capital
        deviation = abs(current_return - backtest_return)
        
        threshold = float(os.getenv('PERFORMANCE_DEVIATION_THRESHOLD', '0.05'))
        
        if deviation > threshold:
            self.logger.warning(f"Performance deviation detected: backtest={backtest_return:.2%}, shadow={current_return:.2%}, deviation={deviation:.2%}")
            return True
        
        return False
    
    def check_alerts(self):
        """Check for various alert conditions"""
        # Check performance deviation
        # This would typically compare against known backtest results
        # For now, we'll just log the current state
        
        # Check drawdown threshold
        max_dd_threshold = float(os.getenv('MAX_TOTAL_DRAWDOWN', '0.15'))
        if abs(self.shadow_metrics['max_drawdown']) > max_dd_threshold:
            self.logger.critical(f"Maximum drawdown threshold exceeded: {self.shadow_metrics['max_drawdown']:.2%}")
        
        # Check daily loss threshold
        daily_loss_threshold = float(os.getenv('MAX_DAILY_LOSS', '0.02'))
        # This would require daily PnL tracking which we don't have in this simplified version
        
        # Check number of consecutive losing trades
        # This would require more sophisticated tracking
        
    def get_shadow_report(self) -> Dict[str, Any]:
        """Generate a comprehensive shadow deployment report"""
        current_equity = self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_capital
        return_pct = (current_equity - self.initial_capital) / self.initial_capital

        # Calculate current metrics for KPI comparison
        current_metrics = {
            'total_signals': len(self.trade_log),
            'win_rate': self.shadow_metrics['winning_trades'] / len(self.trade_log) if len(self.trade_log) > 0 else 0,
            'avg_trade_pnl': self.shadow_metrics['total_pnl'] / len(self.trade_log) if len(self.trade_log) > 0 else 0,
            'total_trades': len(self.trade_log),
            'regime_classification_accuracy': 0.8  # Placeholder - would be calculated based on actual regime detection
        }

        # Generate KPI report
        kpi_report = generate_shadow_kpi_report(
            current_metrics=current_metrics,
            baseline_metrics=self.baseline_metrics
        )

        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'initial_capital': self.initial_capital,
                'current_equity': current_equity,
                'return_pct': return_pct,
                'total_trades': len(self.trade_log),
                'total_equity_points': len(self.equity_curve)
            },
            'metrics': self.shadow_metrics,
            'kpi_report': kpi_report,
            'symbols': self.symbols,
            'strategies': self.strategies,
            'config': {
                'risk_per_trade': self.risk_per_trade,
                'max_position_size': 0.05
            }
        }

        return report


def main():
    """Main entry point for shadow deployment"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run shadow deployment of trading strategies')
    parser.add_argument('--symbols', nargs='+', required=True, help='Symbols to trade')
    parser.add_argument('--strategies', nargs='+', required=True, help='Strategies to use')
    parser.add_argument('--capital', type=float, default=100000.0, help='Initial capital')
    parser.add_argument('--risk-per-trade', type=float, default=0.02, help='Risk per trade')
    parser.add_argument('--interval', type=int, default=60, help='Interval between cycles in seconds')
    parser.add_argument('--report', action='store_true', help='Generate and save report')
    
    args = parser.parse_args()
    
    # Initialize shadow deployment system
    shadow_system = ShadowDeploymentSystem(
        symbols=args.symbols,
        strategies=args.strategies,
        initial_capital=args.capital,
        risk_per_trade=args.risk_per_trade
    )
    
    print(f"🚀 Starting shadow deployment for {args.symbols} with strategies {args.strategies}")
    print(f"   Initial Capital: ${args.capital:,.2f}")
    print(f"   Risk Per Trade: {args.risk_per_trade:.2%}")
    print(f"   Cycle Interval: {args.interval}s")
    
    try:
        cycle_count = 0
        while True:
            shadow_system.run_shadow_cycle()
            cycle_count += 1
            
            # Generate report periodically
            if args.report and cycle_count % 10 == 0:  # Every 10 cycles
                report = shadow_system.get_shadow_report()
                report_filename = f"shadow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_filename, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"   Saved shadow report to {report_filename}")
            
            time.sleep(args.interval)  # Run every interval seconds
    except KeyboardInterrupt:
        print("\n🛑 Shadow deployment stopped by user")
        
        # Generate final report
        if args.report:
            report = shadow_system.get_shadow_report()
            final_report_filename = f"final_shadow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(final_report_filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"   Saved final shadow report to {final_report_filename}")
    except Exception as e:
        print(f"\n❌ Shadow deployment error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()