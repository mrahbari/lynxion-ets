#!/usr/bin/env python3
"""
Resync Runner - Orchestrates downloader, sync, and retune processes.

This script coordinates all data synchronization and optimization processes
for the trading system, ensuring data consistency and system stability.
"""
import asyncio
import os
import sys
import argparse
import time
from datetime import datetime
from typing import List, Optional

from application.configs.configs import Configs

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.configs.symbol_config import get_symbols
from application.configs.sync_settings import settings
from application.data_sync.sync_manager import SyncManager
from application.data_sync.watcher_retune import WatcherRetuneUseCase
from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
from infrastructure.data_sync.data_downloader_adapter import DataDownloaderAdapter
from utils.logger import logger, OperationType, StatusType
from utils.logger import SyncLogger


async def create_sync_components():
    """Create all necessary components for sync operations with async support"""
    file_repo = FileRepositoryAdapter()
    data_downloader = DataDownloaderAdapter()
    sync_manager = SyncManager(file_repo, data_downloader)
    watcher_retune = WatcherRetuneUseCase(file_repo, data_downloader, sync_manager)

    return file_repo, data_downloader, sync_manager, watcher_retune


async def run_downloader_and_sync_process(symbols: Optional[List[str]] = None,
                                        file_repo: FileRepositoryAdapter = None,
                                        sync_manager: SyncManager = None):
    """Run the downloader and sync process for specified symbols"""
    print(f"🚀 Starting downloader and sync process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create components if not provided
    if file_repo is None or sync_manager is None:
        file_repo, data_downloader, sync_manager, _ = await create_sync_components()

        # Use context manager for proper resource cleanup when we create the downloader
        async with data_downloader:
            start_time = time.time()

            try:
                # Run the sync cycle using the sync manager
                result = await sync_manager.run_sync_cycle(symbols)

                duration = time.time() - start_time

                # Log the results
                print(f"✅ Download and sync completed in {duration:.2f} seconds")
                print(f"  Symbols processed: {result['symbols_scanned']}")
                print(f"  Symbols updated: {result['symbols_fixed']}")
                print(f"  Rows written: {result['rows_written']:,}")
                print(f"  Errors: {len(result['errors'])}")

                if result['errors']:
                    print("⚠️  Errors encountered:")
                    for error in result['errors']:
                        print(f"   - {error}")

                # Log operation with structured format
                logger.log_operation(
                    operation=OperationType.CYCLE,
                    symbol="ALL" if symbols is None else f"{len(symbols)}_SYMBOLS",
                    status=StatusType.ERROR if result['errors'] else StatusType.OK,
                    duration_ms=int(duration * 1000),
                    rows_written=result['rows_written'],
                    bytes_written=result['bytes_written'],
                    errors=result['errors'] if result['errors'] else None
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ Download and sync failed after {duration:.2f} seconds: {e}")

                logger.log_operation(
                    operation=OperationType.CYCLE,
                    symbol="ALL" if symbols is None else f"{len(symbols)}_SYMBOLS",
                    status=StatusType.ERROR,
                    duration_ms=int(duration * 1000),
                    error=str(e)
                )

                raise
    else:
        # When components are provided, we assume they were created with proper resource management
        # However, we still need to create a downloader for this specific operation
        data_downloader = DataDownloaderAdapter()
        sync_manager = SyncManager(file_repo, data_downloader)

        # Use context manager for proper resource cleanup
        async with data_downloader:
            start_time = time.time()

            try:
                # Run the sync cycle using the sync manager
                result = await sync_manager.run_sync_cycle(symbols)

                duration = time.time() - start_time

                # Log the results
                print(f"✅ Download and sync completed in {duration:.2f} seconds")
                print(f"  Symbols processed: {result['symbols_scanned']}")
                print(f"  Symbols updated: {result['symbols_fixed']}")
                print(f"  Rows written: {result['rows_written']:,}")
                print(f"  Errors: {len(result['errors'])}")

                if result['errors']:
                    print("⚠️  Errors encountered:")
                    for error in result['errors']:
                        print(f"   - {error}")

                # Log operation with structured format
                logger.log_operation(
                    operation=OperationType.CYCLE,
                    symbol="ALL" if symbols is None else f"{len(symbols)}_SYMBOLS",
                    status=StatusType.ERROR if result['errors'] else StatusType.OK,
                    duration_ms=int(duration * 1000),
                    rows_written=result['rows_written'],
                    bytes_written=result['bytes_written'],
                    errors=result['errors'] if result['errors'] else None
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ Download and sync failed after {duration:.2f} seconds: {e}")

                logger.log_operation(
                    operation=OperationType.CYCLE,
                    symbol="ALL" if symbols is None else f"{len(symbols)}_SYMBOLS",
                    status=StatusType.ERROR,
                    duration_ms=int(duration * 1000),
                    error=str(e)
                )

                raise


async def run_retune_process(symbols: Optional[List[str]] = None,
                           file_repo: FileRepositoryAdapter = None,
                           watcher_retune: WatcherRetuneUseCase = None):
    """Run the retune process to validate and repair data gaps"""
    print(f"🔄 Starting retune process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create components if not provided
    if file_repo is None or watcher_retune is None:
        # If we create the components, we need to handle the data downloader resource properly
        _, data_downloader, _, watcher_retune = await create_sync_components()
        file_repo = FileRepositoryAdapter()

        # Use context manager for proper resource cleanup when we create the downloader
        async with data_downloader:
            start_time = time.time()

            try:
                if symbols is None:
                    symbols = [sym.symbol for sym in get_symbols() if sym.enabled]

                retune_results = []
                total_fixed = 0

                for symbol in symbols:
                    try:
                        # Check if symbol has gaps in the most recent data
                        index_info = file_repo.get_file_index(symbol)
                        if index_info and 'latest_timestamp' in index_info:
                            # Check a recent window for gaps (last 24 hours)
                            latest_ts = index_info['latest_timestamp']
                            recent_start = latest_ts - (24 * 60 * 60)  # 24 hours ago
                            recent_start = max(recent_start, index_info.get('earliest_timestamp', recent_start))

                            is_valid = watcher_retune.validate_interval(symbol, recent_start, latest_ts)

                            if not is_valid:
                                print(f"  🔍 Found gaps in {symbol}, initiating repair...")
                                success = watcher_retune.request_repair_sync(symbol, recent_start, latest_ts, timeout=300)
                                if success:
                                    total_fixed += 1
                                    print(f"  ✅ {symbol} repaired successfully")
                                else:
                                    print(f"  ❌ {symbol} repair timeout")
                                retune_results.append((symbol, success))
                            else:
                                print(f"  🟢 {symbol} is gap-free")
                        else:
                            print(f"  ⚠️  {symbol} has no data to validate")

                    except Exception as e:
                        print(f"  ❌ Error validating {symbol}: {e}")
                        retune_results.append((symbol, False))

                duration = time.time() - start_time

                print(f"✅ Retune process completed in {duration:.2f} seconds")
                print(f"  Symbols validated: {len(symbols)}")
                print(f"  Symbols fixed: {total_fixed}")

                return {
                    'total_symbols': len(symbols),
                    'fixed_symbols': total_fixed,
                    'results': retune_results,
                    'duration_ms': int(duration * 1000)
                }

            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ Retune process failed after {duration:.2f} seconds: {e}")
                raise
    else:
        # When components are provided, we need to get the data_downloader from the watcher_retune
        # The WatcherRetuneUseCase should have access to the data_downloader
        # For now, we'll assume the watcher_retune was properly set up with resources
        start_time = time.time()

        try:
            if symbols is None:
                symbols = [sym.symbol for sym in get_symbols() if sym.enabled]

            retune_results = []
            total_fixed = 0

            for symbol in symbols:
                try:
                    # Check if symbol has gaps in the most recent data
                    index_info = file_repo.get_file_index(symbol)
                    if index_info and 'latest_timestamp' in index_info:
                        # Check a recent window for gaps (last 24 hours)
                        latest_ts = index_info['latest_timestamp']
                        recent_start = latest_ts - (24 * 60 * 60)  # 24 hours ago
                        recent_start = max(recent_start, index_info.get('earliest_timestamp', recent_start))

                        is_valid = watcher_retune.validate_interval(symbol, recent_start, latest_ts)

                        if not is_valid:
                            print(f"  🔍 Found gaps in {symbol}, initiating repair...")
                            success = watcher_retune.request_repair_sync(symbol, recent_start, latest_ts, timeout=300)
                            if success:
                                total_fixed += 1
                                print(f"  ✅ {symbol} repaired successfully")
                            else:
                                print(f"  ❌ {symbol} repair timeout")
                            retune_results.append((symbol, success))
                        else:
                            print(f"  🟢 {symbol} is gap-free")
                    else:
                        print(f"  ⚠️  {symbol} has no data to validate")

                except Exception as e:
                    print(f"  ❌ Error validating {symbol}: {e}")
                    retune_results.append((symbol, False))

            duration = time.time() - start_time

            print(f"✅ Retune process completed in {duration:.2f} seconds")
            print(f"  Symbols validated: {len(symbols)}")
            print(f"  Symbols fixed: {total_fixed}")

            return {
                'total_symbols': len(symbols),
                'fixed_symbols': total_fixed,
                'results': retune_results,
                'duration_ms': int(duration * 1000)
            }

        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ Retune process failed after {duration:.2f} seconds: {e}")
            raise


def process_timeframes(symbols: Optional[List[str]] = None):
    """Process different timeframes from raw 1-minute data"""
    print(f"⚙️  Processing timeframes at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # Create file repository
    file_repo = FileRepositoryAdapter()
    
    if symbols is None:
        symbols = [sym.symbol for sym in get_symbols() if sym.enabled]
    
    processed_count = 0
    
    for symbol in symbols:
        try:
            # Generate all timeframes from raw data
            file_repo.compact_and_aggregate(symbol, cleanup_old=True)
            processed_count += 1
            
            # Log progress for large symbol sets
            if processed_count % 10 == 0:
                print(f"  🔄 Processed {processed_count}/{len(symbols)} symbols...")
                
        except Exception as e:
            print(f"  ❌ Error processing timeframes for {symbol}: {e}")
    
    duration = time.time() - start_time
    
    print(f"✅ Timeframe processing completed in {duration:.2f} seconds")
    print(f"  Symbols processed: {processed_count}")
    
    return {
        'processed_symbols': processed_count,
        'duration_ms': int(duration * 1000)
    }


async def run_full_resync_process(symbols: Optional[List[str]] = None, 
                                 run_downloader: bool = True,
                                 run_timeframes: bool = True,
                                 run_retune: bool = True):
    """Run the complete resync process: downloader -> timeframes -> retune"""
    print("="*70)
    print("🔄 STARTING FULL RESYNC PROCESS")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Configuration: Data dir = {settings.data_dir}")
    print(f"   Configuration: Exchange = {Configs.data.sync_default_exchange if Configs.data and hasattr(Configs.data, 'sync_default_exchange') else 'binance'}")
    print("="*70)
    
    start_time = time.time()
    
    results = {
        'downloader': None,
        'timeframes': None,
        'retune': None,
        'start_time': start_time
    }
    
    # Step 1: Run Downloader and Sync
    if run_downloader:
        print("\n📊 STEP 1: Running Downloader and Sync")
        results['downloader'] = await run_downloader_and_sync_process(symbols)
        print(f"   Status: {'✅ COMPLETED' if not results['downloader'].get('errors') else '⚠️  COMPLETED WITH ERRORS'}")
    
    # Step 2: Process Timeframes
    if run_timeframes:
        print("\n📈 STEP 2: Processing Timeframes")
        results['timeframes'] = process_timeframes(symbols)
        print("   Status: ✅ COMPLETED")
    
    # Step 3: Run Retune Process
    if run_retune:
        print("\n🔧 STEP 3: Running Retune Process")
        results['retune'] = await run_retune_process(symbols)
        print("   Status: ✅ COMPLETED")
    
    total_duration = time.time() - start_time
    
    print("\n" + "="*70)
    print("🏁 RESYNC PROCESS COMPLETED")
    print(f"   Total Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    
    if results['downloader']:
        print(f"   Downloaded/Synced: {results['downloader']['symbols_fixed']}/{results['downloader']['symbols_scanned']} symbols")
        print(f"   Rows Processed: {results['downloader']['rows_written']:,}")
        
    if results['timeframes']:
        print(f"   Timeframes Generated: {results['timeframes']['processed_symbols']} symbols")
        
    if results['retune']:
        print(f"   Retune: {results['retune']['fixed_symbols']}/{results['retune']['total_symbols']} symbols fixed")
    
    print("="*70)
    
    return results


def main():
    """Main entry point for the resync runner"""
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
    
    args = parser.parse_args()

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
    print(f"   Environment: SYNC_DEFAULT_EXCHANGE={Configs.data.sync_default_exchange if Configs.data and hasattr(Configs.data, 'sync_default_exchange') else 'binance'}")
    
    try:
        # Run the appropriate process(es)
        asyncio.run(run_full_resync_process(
            symbols=args.symbols,
            run_downloader=args.download,
            run_timeframes=args.timeframes,
            run_retune=args.retune
        ))
        
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
    exit(main())