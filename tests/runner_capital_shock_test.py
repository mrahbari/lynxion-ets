#!/usr/bin/env python3
"""
Capital Shock Testing Runner - Execute portfolio resilience testing under capital reductions
"""
import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import numpy as np

from application.configs.configs import Configs

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.risk.capital_shock_tester import run_capital_shock_test
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = Configs.wfo.wfo_coins if Configs.wfo and Configs.wfo.wfo_coins else "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,ADAUSDT"
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def main():
    """Main entry point for the capital shock testing runner."""
    parser = argparse.ArgumentParser(
        description='Run capital shock testing to evaluate portfolio resilience',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --shocks -0.2 -0.3 --symbols BTCUSDT ETHUSDT SOLUSDT
  %(prog)s --shocks -0.1 -0.2 -0.3 -0.5 --capital 50000
        """
    )

    parser.add_argument('--shocks', nargs='+', type=float, 
                       default=[-0.2, -0.3, -0.5],
                       help='Capital shock percentages to test (e.g., -0.2 for -20%%)')

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to test (default: from WFO_COINS env var)')

    parser.add_argument('--capital', type=float, default=100000.0,
                       help='Initial capital for testing (default: 100000.0)')

    parser.add_argument('--output', type=str,
                       help='Output file to save results (JSON format)')

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()

    print(f"💥 Starting capital shock testing...")
    print(f"   Shock Scenarios: {[f'{s:.1%}' for s in args.shocks]}")
    print(f"   Symbols: {symbols}")
    print(f"   Initial Capital: ${args.capital:,.2f}")

    try:
        # Run capital shock testing
        results = run_capital_shock_test(
            symbols=symbols,
            initial_capital=args.capital,
            shock_scenarios=args.shocks
        )

        # Print results summary
        if 'error' in results:
            print(f"\n❌ Capital shock testing failed: {results['error']}")
            return 1
        else:
            print(f"\n📊 CAPITAL SHOCK TESTING RESULTS")
            print(f"   Initial Capital: ${results['initial_capital']:,.2f}")
            print(f"   Test Symbols: {results['symbols']}")
            print(f"   Test Timestamp: {results['timestamp']}")
            
            # Print summary
            summary = results['summary']
            avg_resilience = summary['average_resilience_scores']
            if avg_resilience:
                print(f"   Average Resilience Score: {avg_resilience.get('mean', 0):.2f}")
                print(f"   Resilience Std Dev: {avg_resilience.get('std', 0):.2f}")
            
            # Print critical thresholds
            if summary['critical_thresholds']:
                print(f"   ⚠️  Critical Thresholds Detected:")
                for threshold in summary['critical_thresholds']:
                    print(f"      - {threshold['scenario']}: {threshold['resilience_score']:.2f} resilience")
            
            # Print recommendations
            print(f"   💡 Recommendations:")
            for rec in summary['recommendations']:
                print(f"      - {rec}")

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        print(f"\n✅ Capital shock testing completed successfully!")
        return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Capital shock testing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())