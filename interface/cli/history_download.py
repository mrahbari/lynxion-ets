#!/usr/bin/env python3
"""History-download CLI shell (E2.T3).

Owns argument parsing and process I/O for the historical-data download feature
(F1/F2), builds the composition root, resolves the data-sync ports, and
delegates orchestration to :class:`SyncMarketDataUseCase`. CLI arguments,
console output, and exit codes are preserved verbatim from the legacy
``runner_history_download`` so the data-sync golden path stays byte-identical.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.sync_market_data import HistoryDownloadRequest, SyncMarketDataUseCase
from bootstrap.lifecycle import lifespan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Download historical market data for multiple symbols and timeframes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start 2023-01-01 --end 2023-12-31                    # Full year download
  %(prog)s --start 2023-01-01 --end 2023-03-31 --symbols BTCUSDT   # Single symbol quarterly
  %(prog)s --start 30d --end today --timeframes 1m 5m 15m          # Last 30 days for short timeframes
        """
    )

    parser.add_argument('--start', type=str, required=True,
                       help='Start date in YYYY-MM-DD format or relative (e.g., "30d", "90d")')

    parser.add_argument('--end', type=str, default='today',
                       help='End date in YYYY-MM-DD format or "today" (default: today)')

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to download (default: from WFO_COINS env var)')

    parser.add_argument('--timeframes', nargs='+', type=str,
                       default=['1m', '5m', '15m', '30m', '1h', '4h', '1d'],
                       help='Timeframes to download (default: 1m 5m 15m 30m 1h 4h 1d)')

    parser.add_argument('--exchange', type=str, default='binance',
                       help='Exchange to download from (default: binance)')

    parser.add_argument('--output', type=str,
                       help='Output file to save results (JSON format)')

    parser.add_argument('--validate', action='store_true',
                       help='Validate data integrity after download')

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

    if args.symbols:
        symbols = args.symbols
    else:
        from runner_history_download import load_symbols_from_env
        symbols = load_symbols_from_env()

    print(f"🚀 History Download Runner Started")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Symbols: {symbols}")
    print(f"   Timeframes: {args.timeframes}")
    print(f"   Exchange: {args.exchange}")

    try:
        request = HistoryDownloadRequest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframes=args.timeframes,
            exchange=args.exchange,
        )

        with lifespan() as container:
            use_case = SyncMarketDataUseCase(
                settings=container.settings,
                file_repository=container.resolve("file_repository"),
                data_downloader=container.resolve("data_downloader"),
                sync_manager=container.resolve("sync_manager"),
            )
            results = asyncio.run(use_case.download_history(request))

            # Validate results if requested
            if args.validate:
                validation_results = use_case.validate_download(results)
                results['validation'] = validation_results

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Check for download failures
        failed_count = results['summary']['failed_downloads']
        if failed_count > 0:
            print(f"\n⚠️  Process completed with {failed_count} failed downloads")
            return min(failed_count, 1)  # Return 1 if any failed, but cap at 1
        else:
            print(f"\n🎉 All downloads completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Download process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
