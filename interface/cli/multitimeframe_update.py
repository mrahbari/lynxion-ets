#!/usr/bin/env python3
"""Multi-timeframe update CLI shell (E2.T3).

Owns argument parsing and process I/O for the MTF aggregation feature (F3),
builds the composition root, resolves the ``file_repository`` port, and
delegates orchestration to :class:`SyncMarketDataUseCase`. CLI arguments,
console output, and exit codes are preserved verbatim from the legacy
``runner_multitimeframe_update``.
"""

import argparse
import json
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.sync_market_data import MultiTimeframeUpdateRequest, SyncMarketDataUseCase
from bootstrap.lifecycle import lifespan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Update multi-timeframe data from raw 1-minute data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                              # Update all symbols and timeframes
  %(prog)s --symbols BTCUSDT                  # Update specific symbol
  %(prog)s --timeframes 5m 15m 30m           # Update specific timeframes only
  %(prog)s --force                            # Force update even if files exist
        """
    )

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to update (default: from WFO_COINS env var)')

    parser.add_argument('--timeframes', nargs='+', type=str,
                       default=['5m', '15m', '30m', '1h', '4h', '1d'],
                       help='Timeframes to update (default: 5m 15m 30m 1h 4h 1d)')

    parser.add_argument('--force', action='store_true',
                       help='Force update even if processed files already exist')

    parser.add_argument('--output', type=str,
                       help='Output file to save results (JSON format)')

    parser.add_argument('--validate', action='store_true',
                       help='Validate data integrity after update')

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.symbols:
        symbols = args.symbols
    else:
        from runner_multitimeframe_update import load_symbols_from_env
        symbols = load_symbols_from_env()

    print(f"🚀 Multi-Timeframe Update Runner Started")
    print(f"   Symbols: {symbols}")
    print(f"   Timeframes: {args.timeframes}")
    print(f"   Force Update: {args.force}")

    try:
        request = MultiTimeframeUpdateRequest(
            symbols=symbols,
            timeframes=args.timeframes,
            force_update=args.force,
        )

        with lifespan() as container:
            use_case = SyncMarketDataUseCase(
                settings=container.settings,
                file_repository=container.resolve("file_repository"),
            )
            results = use_case.update_multitimeframe(request)

            # Validate results if requested
            if args.validate:
                validation_results = use_case.validate_mtf(results)
                results['validation'] = validation_results

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Check for update failures
        failed_count = results['summary']['failed_updates']
        if failed_count > 0:
            print(f"\n⚠️  Process completed with {failed_count} failed updates")
            return min(failed_count, 1)  # Return 1 if any failed, but cap at 1
        else:
            print(f"\n🎉 All updates completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Multi-timeframe update process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
