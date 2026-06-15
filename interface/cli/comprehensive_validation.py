#!/usr/bin/env python3
"""Comprehensive hedge-fund validation CLI shell (E2.T4).

Owns argument parsing and process I/O for the full portfolio validation pipeline,
builds the composition root, resolves the portfolio backtester factory, CSV
history loader and data-integrity checker ports, and delegates orchestration to
:class:`ValidatePortfolioUseCase`. CLI arguments, console output, and exit codes
are preserved verbatim from the legacy ``runner_comprehensive_validation``.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.validate_portfolio import ComprehensiveValidationRequest, ValidatePortfolioUseCase
from bootstrap.lifecycle import lifespan
from bootstrap.settings.loaders import load_settings


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = load_settings().wfo.wfo_coins if load_settings().wfo and load_settings().wfo.wfo_coins else "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,ADAUSDT"
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Run comprehensive hedge fund validation pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start 360d --end today --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT
  %(prog)s --start 2023-01-01 --end 2023-12-31 --capital 50000 --min-success-rate 0.6
        """
    )

    parser.add_argument('--start', type=str, required=True,
                       help='Start date in YYYY-MM-DD format or relative (e.g., "30d", "90d")')

    parser.add_argument('--end', type=str, default='today',
                       help='End date in YYYY-MM-DD format or "today" (default: today)')

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to validate (default: from WFO_COINS env var)')

    parser.add_argument('--capital', type=float, default=100000.0,
                       help='Initial capital for validation (default: 100000.0)')

    parser.add_argument('--fee', type=float, default=0.001,
                       help='Fee rate per trade (default: 0.001 = 0.1%%)')

    parser.add_argument('--slippage', type=float, default=0.0005,
                       help='Slippage factor (default: 0.0005 = 0.05%%)')

    parser.add_argument('--min-success-rate', type=float, default=0.7,
                       help='Minimum success rate for strategy acceptance (default: 0.7 = 70%%)')

    parser.add_argument('--output', type=str,
                       help='Output file to save results (JSON format)')

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    return parser


def _parse_date(date_str: str) -> datetime:
    if date_str == 'today':
        return datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    elif date_str.endswith('d'):
        days = int(date_str[:-1])
        return datetime.now() - timedelta(days=days)
    else:
        return datetime.strptime(date_str, '%Y-%m-%d')


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    start_date = _parse_date(args.start)
    end_date = _parse_date(args.end)

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()

    print(f"🚀 Comprehensive Hedge Fund Validation Pipeline Started")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Symbols: {symbols}")
    print(f"   Initial Capital: ${args.capital:,.2f}")
    print(f"   Min Success Rate: {args.min_success_rate:.1%}")

    # Load strategy functions
    from infrastructure.portfolio.comprehensive_portfolio_backtester import load_sample_strategies
    strategy_functions = load_sample_strategies()
    print(f"   Loaded {len(strategy_functions)} strategies")

    try:
        request = ComprehensiveValidationRequest(
            symbols=symbols,
            strategy_functions=strategy_functions,
            start_date=start_date,
            end_date=end_date,
            initial_capital=args.capital,
            fee_rate=args.fee,
            slippage_factor=args.slippage,
            min_success_rate=args.min_success_rate,
        )

        with lifespan() as container:
            use_case = ValidatePortfolioUseCase(
                settings=container.settings,
                portfolio_backtester_factory=container.resolve("portfolio_backtester_factory"),
                csv_history_loader=container.resolve("csv_history_loader"),
                data_integrity_checker=container.resolve("data_integrity_checker"),
                capital_allocator_factory=container.resolve("capital_allocator_factory"),
                monte_carlo_analyzer=container.resolve("monte_carlo_analyzer"),
                kill_switch_factory=container.resolve("kill_switch_factory"),
                portfolio_walk_forward_validator=container.resolve("portfolio_walk_forward_validator"),
            )
            results = use_case.run_comprehensive_validation(request)

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Check for pipeline failures
        if 'error' in results:
            print(f"\n❌ Validation pipeline failed")
            return 1
        else:
            print(f"\n🎉 Validation pipeline completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Validation pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
