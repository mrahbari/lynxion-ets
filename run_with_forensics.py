#!/usr/bin/env python3
"""
Test script to run the trading system with forensic governance enabled
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from run_trading_system import main as run_trading_system_main
import argparse


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Run trading system with forensic governance')
    parser.add_argument('--mode', choices=['optimize', 'backtest', 'retune', 'monitor', 'production', 'config-test'], 
                       default='production', help='Operation mode to run')
    parser.add_argument('--strategy', default='crypto_breakout', help='Trading strategy to use')
    parser.add_argument('--symbol', default='BTC/USDT', help='Trading pair symbol')
    parser.add_argument('--symbols', help='Comma-separated list of symbols')
    parser.add_argument('--timeframe', default='1h', help='Timeframe for data')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--max-evals', type=int, default=100, help='Maximum number of hyperopt evaluations')
    parser.add_argument('--use-optimized-params', action='store_true', help='Use previously optimized parameters')
    parser.add_argument('--days-back', type=int, default=30, help='Number of days of historical data to use')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--log-dir', default='logs', help='Directory for log files')
    parser.add_argument('--auto-detect', action='store_true', help='Run in auto-detection mode')
    parser.add_argument('--comprehensive-logs', action='store_true', help='Enable comprehensive logging')
    
    args = parser.parse_args()
    
    # Set environment variable to enable forensic logging
    os.environ['FORENSIC_LOGGING_ENABLED'] = 'true'
    
    # Run the trading system with the provided arguments
    try:
        # Convert args to the format expected by run_trading_system
        sys.argv = ['run_trading_system.py']
        if args.mode:
            sys.argv.extend(['--mode', args.mode])
        if args.strategy:
            sys.argv.extend(['--strategy', args.strategy])
        if args.symbol:
            sys.argv.extend(['--symbol', args.symbol])
        if args.symbols:
            sys.argv.extend(['--symbols', args.symbols])
        if args.timeframe:
            sys.argv.extend(['--timeframe', args.timeframe])
        if args.config:
            sys.argv.extend(['--config', args.config])
        if args.max_evals != 100:  # default
            sys.argv.extend(['--max-evals', str(args.max_evals)])
        if args.use_optimized_params:
            sys.argv.append('--use-optimized-params')
        if args.days_back != 30:  # default
            sys.argv.extend(['--days-back', str(args.days_back)])
        if args.verbose:
            sys.argv.append('--verbose')
        if args.log_dir != 'logs':  # default
            sys.argv.extend(['--log-dir', args.log_dir])
        if args.auto_detect:
            sys.argv.append('--auto-detect')
        if args.comprehensive_logs:
            sys.argv.append('--comprehensive-logs')
        
        run_trading_system_main()
        
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error running trading system: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()