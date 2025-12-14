"""
Enterprise Hedge Fund Trading System - Comprehensive Integration
This module demonstrates the integration of all enterprise features
into a cohesive, production-ready trading system.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

from application.containers.container import container
from domain.value_objects import Symbol
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager, PositionDirection
from application.position_sizing.enterprise_position_sizing import PositionSizingService
from application.execution.advanced_execution_engine import AdvancedExecutionEngine
from application.data_processing.multi_timeframe_sync import DataPipeline
from application.validation.backtest_validator import ValidationService


def setup_container():
    """Set up the container with all enterprise services"""
    try:
        from main_hexagonal_container import setup_application
        setup_application()
        print("Container successfully initialized with enterprise features")
        return True
    except Exception as e:
        print(f"Error setting up container: {e}")
        return False


class EnterpriseTradingSystem:
    """
    Complete enterprise trading system integrating all enterprise features
    """
    def __init__(self):
        # Setup container first if not already done
        setup_container()

        # Initialize enterprise components
        self.risk_manager = container.resolve('enterprise_risk_manager')
        self.position_sizing = container.resolve('enterprise_position_sizing_service')
        self.execution_engine = container.resolve('enterprise_execution_engine')
        self.data_pipeline = container.resolve('data_pipeline')
        self.validation_service = container.resolve('validation_service')

        # Trading parameters
        self.symbols = []
        self.active_timeframes = ['1h', '4h', '1d']
        self.default_position_model = 'fixed_risk'

        # For demo purposes, set up some basic tracking
        self.backtest_data = {}

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def setup_demo_data(self):
        """
        Set up demonstration data for testing the enterprise features
        """
        symbols = ["BTC-USDT", "ETH-USDT", "XRP-USDT"]
        np.random.seed(42)  # Fixed seed for reproducibility

        for i, symbol in enumerate(symbols):
            # Create different price levels for different assets
            base_prices = {
                "BTC-USDT": 50000,
                "ETH-USDT": 3000,
                "XRP-USDT": 0.5
            }
            
            start_price = base_prices.get(symbol, 100)
            
            # Generate realistic price data
            timestamps = pd.date_range("2023-01-01 00:00", periods=200, freq='1h')
            returns = np.random.normal(0.0005, 0.02, len(timestamps))  # Daily returns with some drift
            
            # Create price series with realistic volatility
            prices = [start_price]
            for ret in returns[1:]:
                new_price = prices[-1] * (1 + ret)
                prices.append(new_price)
            
            # Add high, low, open for realistic OHLC data
            df = pd.DataFrame({
                'close': prices,
                'open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
                'volume': np.random.randint(100, 1000, len(prices))
            }, index=timestamps)

            # Ensure open, high, low, close have proper relationships
            df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])  # Use previous close as open
            # Create temp columns with proper volatility-based high/low values
            temp_high = df['close'] + np.abs(np.random.normal(0, df['close'] * 0.005, len(df)))
            temp_low = df['close'] - np.abs(np.random.normal(0, df['close'] * 0.005, len(df)))

            # Calculate high as max of open, close, and generated high
            df['high'] = pd.concat([df[['open', 'close']], pd.DataFrame({'temp': temp_high})], axis=1).max(axis=1)
            # Calculate low as min of open, close, and generated low
            df['low'] = pd.concat([df[['open', 'close']], pd.DataFrame({'temp': temp_low})], axis=1).min(axis=1)
            
            self.backtest_data[symbol] = df
        
        self.symbols = symbols
        self.logger.info(f"Demo data created for {len(symbols)} symbols")

    def run_enterprise_backtest(self):
        """
        Run a comprehensive backtest using all enterprise features
        """
        self.logger.info("Starting enterprise backtest...")
        
        # Use the demo data to run backtest
        for symbol in self.symbols:
            df = self.backtest_data[symbol].copy()
            
            # Load data into pipeline for multi-timeframe processing
            self.data_pipeline.load_data(symbol, '1h', df)
            
            # Process each candle
            for idx, row in df.iterrows():
                current_price = row['close']
                
                # Simulate signal generation (in real system, this would come from watchers/strategies)
                # For demo: generate random signals but with some bias
                signal_strength = np.random.uniform(-1, 1)
                
                if abs(signal_strength) > 0.6:  # Strong signal threshold
                    direction = PositionDirection.LONG if signal_strength > 0 else PositionDirection.SHORT
                    
                    # Prepare market data for execution
                    market_data = {
                        'price': current_price,
                        'volatility': (row['high'] - row['low']) / current_price,  # Simple volatility measure
                        'portfolio_equity': self.risk_manager.starting_equity + self.risk_manager.total_pnl,
                        'risk_per_trade': self.risk_manager.max_risk_per_trade
                    }
                    
                    # Process signal through execution engine
                    success = self.execution_engine.process_signal(
                        symbol=symbol.replace('-', '/'),  # Adjust format for our system
                        signal_direction=direction,
                        signal_confidence=abs(signal_strength),
                        market_data=market_data,
                        position_size_model=self.default_position_model
                    )
                    
                    if success:
                        self.logger.debug(f"Position entered for {symbol} at {current_price}")
                
                # Process candle for potential exits
                pnl = self.execution_engine.process_candle(
                    symbol=symbol.replace('-', '/'),
                    candle_high=row['high'],
                    candle_low=row['low'],
                    candle_close=row['close']
                )
                
                if pnl != 0:
                    self.logger.info(f"Position exited for {symbol}, PnL: {pnl:.2f}")
        
        # Get execution metrics
        metrics = self.execution_engine.get_execution_metrics()
        self.logger.info(f"Backtest completed. Metrics: {metrics}")
        
        return metrics

    def validate_enterprise_system(self):
        """
        Validate the entire enterprise system against hedge fund rules
        """
        self.logger.info("Running enterprise system validation...")
        
        # Generate validation report
        report = self.validation_service.run_comprehensive_validation(
            execution_engine=self.execution_engine,
            data_pipeline=self.data_pipeline,
            market_data=None  # In a real scenario, you'd provide actual market data
        )
        
        # Print validation summary
        self.validation_service.validator.print_validation_summary(
            execution_engine=self.execution_engine,
            market_data=None
        )
        
        return report

    def run_comprehensive_demo(self):
        """
        Run a comprehensive demo of all enterprise features
        """
        self.logger.info("Starting comprehensive enterprise features demo...")
        
        # Step 1: Set up demo data
        self.setup_demo_data()
        
        # Step 2: Run backtest with enterprise features
        metrics = self.run_enterprise_backtest()
        
        # Step 3: Validate the system
        validation_report = self.validate_enterprise_system()
        
        # Step 4: Export results
        trade_log_file = self.execution_engine.export_trade_log()
        validation_file = self.validation_service.export_validation_report(
            execution_engine=self.execution_engine,
            market_data=None
        )
        
        self.logger.info(f"Trade log exported to: {trade_log_file}")
        self.logger.info(f"Validation report exported to: {validation_file}")
        
        # Step 5: Print summary
        print("\n=== ENTERPRISE TRADING SYSTEM SUMMARY ===")
        print(f"Assets Traded: {len(self.symbols)}")
        print(f"Total Trades: {metrics.get('total_trades', 0)}")
        print(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
        print(f"Total PnL: ${metrics.get('total_pnl', 0):.2f}")
        print(f"Average Win: ${metrics.get('avg_win', 0):.2f}")
        print(f"Average Loss: ${metrics.get('avg_loss', 0):.2f}")
        print(f"Final Equity: ${metrics.get('risk_metrics', {}).get('equity', 0):.2f}")
        print(f"Current Drawdown: {metrics.get('risk_metrics', {}).get('current_drawdown', 0):.2%}")
        print(f"Total Risk Violations: {len(validation_report.get('violations', []))}")
        
        return {
            'metrics': metrics,
            'validation_report': validation_report,
            'trade_log_file': trade_log_file,
            'validation_file': validation_file
        }

    def get_enterprise_metrics(self) -> Dict:
        """
        Get comprehensive enterprise metrics
        """
        return self.execution_engine.get_execution_metrics()

    def get_risk_exposure(self) -> Dict:
        """
        Get risk exposure across all symbols
        """
        risk_metrics = self.risk_manager.get_risk_metrics()
        return risk_metrics


def run_enterprise_trading_demo():
    """
    Main entry point to run the enterprise trading system demo
    """
    print("Starting Enterprise Hedge Fund Trading System Demo...")
    print("="*60)
    
    enterprise_system = EnterpriseTradingSystem()
    
    try:
        # Run comprehensive demo
        results = enterprise_system.run_comprehensive_demo()
        
        print("\nDemo completed successfully!")
        print("="*60)
        
        return results
        
    except Exception as e:
        print(f"Error running enterprise demo: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    run_enterprise_trading_demo()