#!/usr/bin/env python3
"""Walk-forward CLI shell (E2.T4).

Owns argument parsing and process I/O for walk-forward optimization, builds the
composition root, resolves the ``wfo_orchestrator_factory`` port, and delegates
orchestration to :class:`RunWalkforwardUseCase`. CLI arguments, console output,
and exit codes are preserved verbatim from the legacy ``runner_walkforward``.
"""

import argparse
import json
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.run_walkforward import RunWalkforwardUseCase, WalkforwardRequest
from bootstrap.lifecycle import lifespan
from bootstrap.settings.loaders import load_settings


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = load_settings().wfo.wfo_coins if load_settings().wfo and load_settings().wfo.wfo_coins else "BTCUSDT,ETHUSDT"
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Run walk-forward optimization and analysis for trading strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --strategy crypto_breakout --symbols BTCUSDT ETHUSDT
  %(prog)s --strategy rsi_strategy --train 60 --test 20 --step 20 --evals 25
  %(prog)s --strategy ma_crossover_strategy --all --train 120 --test 30 --cv-splits 3
        """
    )

    parser.add_argument('--strategy', type=str,
                       default='crypto_breakout',
                       help='Strategy name to use for WFO (default: crypto_breakout)')

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to analyze (default: from WFO_COINS env var)')

    parser.add_argument('--train', type=int, default=90,
                       help='Training window size in days (default: 90)')

    parser.add_argument('--test', type=int, default=30,
                       help='Testing window size in days (default: 30)')

    parser.add_argument('--step', type=int, default=30,
                       help='Sliding step size in days (default: 30)')

    parser.add_argument('--evals', type=int, default=50,
                       help='Maximum hyperopt evaluations per asset (default: 50)')

    parser.add_argument('--cv-splits', type=int, default=5,
                       help='Number of cross-validation splits (default: 5)')

    parser.add_argument('--output', type=str,
                       help='Output file to save results (JSON format)')

    parser.add_argument('--validate', action='store_true',
                       help='Validate results after WFO')

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

    print(f"🚀 Walk-Forward Runner Started")
    print(f"   Strategy: {args.strategy}")
    print(f"   Symbols: {symbols}")
    print(f"   WFO Config: {args.train}/{args.test}/{args.step} (train/test/step)")
    print(f"   Max evals: {args.evals}")
    print(f"   CV splits: {args.cv_splits}")

    try:
        request = WalkforwardRequest(
            symbols=symbols,
            strategy_name=args.strategy,
            train_size=args.train,
            test_size=args.test,
            step_size=args.step,
            max_evals=args.evals,
            cv_splits=args.cv_splits,
        )

        with lifespan() as container:
            use_case = RunWalkforwardUseCase(
                settings=container.settings,
                wfo_orchestrator_factory=container.resolve("wfo_orchestrator_factory"),
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

        # Exit with appropriate code based on status
        if results['status'] == 'failed':
            print(f"\n❌ WFO process failed")
            return 1
        else:
            print(f"\n🎉 WFO process completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Walk-forward process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
