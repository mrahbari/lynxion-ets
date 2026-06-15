#!/usr/bin/env python3
"""Retune / optimization CLI shell (E2.T4).

Owns argument parsing and process I/O for automated hyperparameter retuning,
builds the composition root, resolves the data-sync ports plus the parameter
space / hyperopt optimizer factories, and delegates orchestration to
:class:`OptimizeStrategyUseCase`. CLI arguments, console output, and exit codes
are preserved verbatim from the legacy ``runner_retune``.
"""

import argparse
import json
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.optimize_strategy import OptimizeStrategyRequest, OptimizeStrategyUseCase
from bootstrap.lifecycle import lifespan
from bootstrap.settings.loaders import load_settings


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = load_settings().wfo.wfo_coins if load_settings().wfo and load_settings().wfo.wfo_coins else "BTCUSDT,ETHUSDT"
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Automated hyperparameter retuning for trading strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                         # Retune all strategies for all symbols
  %(prog)s --strategy crypto_breakout    # Retune specific strategy for all symbols
  %(prog)s --symbols BTCUSDT ETHUSDT     # Retune all strategies for specific symbols
  %(prog)s --strategy crypto_breakout --symbols BTCUSDT --evals 100 --days 60
        """
    )

    parser.add_argument('--strategy', type=str,
                        default='crypto_breakout',
                        help='Strategy name to retune (default: crypto_breakout)')

    parser.add_argument('--symbols', nargs='+', type=str,
                        help='Specific symbols to retune (default: from WFO_COINS env var)')

    parser.add_argument('--evals', type=int, default=50,
                        help='Maximum number of hyperopt evaluations per symbol (default: 50)')

    parser.add_argument('--days', type=int, default=90,
                        help='Number of days of historical data to use (default: 90)')

    parser.add_argument('--output', type=str,
                        help='Output file to save results (JSON format)')

    parser.add_argument('--validate', action='store_true',
                        help='Validate results after retuning')

    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()

    print(f"🚀 Retune Runner Started")
    print(f"   Strategy: {args.strategy}")
    print(f"   Symbols: {symbols}")
    print(f"   Max evals: {args.evals}")
    print(f"   Days back: {args.days}")

    try:
        request = OptimizeStrategyRequest(
            symbols=symbols,
            strategy_name=args.strategy,
            max_evals=args.evals,
            days_back=args.days,
        )

        with lifespan() as container:
            use_case = OptimizeStrategyUseCase(
                settings=container.settings,
                file_repository=container.resolve("file_repository"),
                sync_manager=container.resolve("sync_manager"),
                data_downloader=container.resolve("data_downloader"),
                hyperopt_param_space_factory=container.resolve("hyperopt_param_space_factory"),
                hyperopt_optimizer_factory=container.resolve("hyperopt_optimizer_factory"),
            )
            results = use_case.execute(request)

            # Validate results if requested
            if args.validate:
                validation_results = use_case.validate_results(results)
                results['validation'] = validation_results

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Exit with appropriate code
        failed_count = results['failed_optimizations']
        if failed_count > 0:
            print(f"\n⚠️  Process completed with {failed_count} failed optimizations")
            return min(failed_count, 1)  # Return 1 if any failed, but cap at 1
        else:
            print(f"\n🎉 All optimizations completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Retune process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
