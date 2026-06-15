#!/usr/bin/env python3
"""Resync CLI shell (E2.T3).

Owns argument parsing and process I/O for the orchestrated resync feature
(downloader -> timeframes -> retune; F6), builds the composition root, resolves
the data-sync ports, and delegates orchestration to
:class:`SyncMarketDataUseCase`. CLI arguments, console output, and exit codes
are preserved verbatim from the legacy ``runner_resync``.
"""

import argparse
import asyncio
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bootstrap.settings.loaders import load_settings
from application.use_cases.sync_market_data import ResyncRequest, SyncMarketDataUseCase
from bootstrap.lifecycle import lifespan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Orchestrate downloader, sync, and retune processes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                            # Run all processes
  %(prog)s --download --timeframes          # Run downloader and timeframes only
  %(prog)s --retune --symbols BTC-USDT      # Run retune for specific symbol
  %(prog)s --all --symbols BTC-USDT ETH-USDT # Run all for specific symbols
        """
    )

    parser.add_argument('--all', action='store_true',
                       help='Run all processes: downloader, timeframes, and retune')

    parser.add_argument('--download', action='store_true',
                       help='Run downloader and sync process')

    parser.add_argument('--timeframes', action='store_true',
                       help='Process timeframes from raw data')

    parser.add_argument('--retune', action='store_true',
                       help='Run retune process to validate and repair data')

    parser.add_argument('--symbols', nargs='+', type=str, default=None,
                       help='Specific symbols to process (e.g., BTC-USDT ETH-USDT)')

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # If no specific process is selected, default to --all
    if not any([args.all, args.download, args.timeframes, args.retune]):
        args.all = True

    # If --all is specified, enable all individual processes
    if args.all:
        args.download = args.timeframes = args.retune = True

    # If no symbols specified, get them from environment (WFO_COINS)
    if args.symbols is None:
        from application.configs.symbol_config import get_symbols
        env_symbols = get_symbols()
        args.symbols = [sym.symbol for sym in env_symbols if sym.enabled]
        print(f"   Using symbols from environment (WFO_COINS equivalent): {len(args.symbols)} symbols")
    else:
        # Normalize symbol format if provided manually
        normalized_symbols = []
        for symbol in args.symbols:
            # Convert formats like BTCUSDT to BTC-USDT
            if not '-' in symbol and 'USDT' in symbol:
                normalized_symbol = symbol.replace('USDT', '-USDT')
            elif not '-' in symbol and ('USD' in symbol or 'BTC' in symbol or 'ETH' in symbol):
                # Handle other common formats
                for base in ['USDT', 'USD', 'BTC', 'ETH']:
                    if base in symbol and base != symbol[-len(base):]:  # Not already formatted
                        normalized_symbol = symbol[:-len(base)] + '-' + symbol[-len(base):]
                        break
                else:
                    normalized_symbol = symbol
            else:
                normalized_symbol = symbol
            normalized_symbols.append(normalized_symbol)
        args.symbols = normalized_symbols
        print(f"   Using manually specified symbols: {len(args.symbols)} symbols")

    print(f"🚀 Resync Runner Started")
    print(f"   Processes: {'Downloader' if args.download else ''}{' | ' if args.download and (args.timeframes or args.retune) else ''}{'Timeframes' if args.timeframes else ''}{' | ' if args.timeframes and args.retune else ''}{'Retune' if args.retune else ''}")
    print(f"   Symbols: {args.symbols if args.symbols else 'All configured symbols'}")
    print(f"   Environment: SYNC_DEFAULT_EXCHANGE={load_settings().data.sync_default_exchange if load_settings().data and hasattr(load_settings().data, 'sync_default_exchange') else 'binance'}")

    try:
        request = ResyncRequest(
            symbols=args.symbols,
            run_downloader=args.download,
            run_timeframes=args.timeframes,
            run_retune=args.retune,
        )

        with lifespan() as container:
            use_case = SyncMarketDataUseCase(
                settings=container.settings,
                file_repository=container.resolve("file_repository"),
                data_downloader=container.resolve("data_downloader"),
                sync_manager=container.resolve("sync_manager"),
                watcher_retune=container.resolve("watcher_retune"),
            )
            asyncio.run(use_case.resync(request))

        print("\n🎉 Resync process completed successfully!")
        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Resync process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
