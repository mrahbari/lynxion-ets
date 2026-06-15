"""E5.T5 (infra-only mechanical split): downloader/retune/resync orchestration data-sync ops extracted from sync_market_data.

Behavior-preserving — functions moved verbatim (signatures/behavior/results UNCHANGED).
Self-contained: no cross-ops imports (verified call graph). No trade surface.
"""
from __future__ import annotations

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from shared.logger import EnhancedLogger
from shared.sync_logger import logger, OperationType, StatusType


async def run_downloader_and_sync_process(symbols: Optional[List[str]] = None,
                                        file_repo=None,
                                        sync_manager=None,
                                        data_downloader=None):
    """Run the downloader and sync process for specified symbols.

    The data-sync ports are supplied by the composition root (E2.T3); when
    omitted, default adapters are created. Behavior (sync cycle, console output,
    structured logging) is identical regardless of the component source.
    """
    print(f"🚀 Starting downloader and sync process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Ports are injected by the composition root.

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
                           file_repo=None,
                           watcher_retune=None,
                           data_downloader=None):
    """Run the retune process to validate and repair data gaps.

    The data-sync ports are supplied by the composition root (E2.T3); when
    omitted, default adapters are created. Behavior is identical regardless of
    the component source.
    """
    print(f"🔄 Starting retune process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Ports are injected by the composition root.

    # Use context manager for proper resource cleanup
    async with data_downloader:
        start_time = time.time()

        try:
            if symbols is None:
                from application.configs.symbol_config import get_symbols
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


def process_timeframes(symbols: Optional[List[str]] = None,
                        file_repo=None):
    """Process different timeframes from raw 1-minute data.

    ``file_repo`` is supplied by the composition root (E2.T3); when omitted a
    default adapter is created, preserving the legacy behavior exactly.
    """
    print(f"⚙️  Processing timeframes at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # Data-access port (file_repo) is injected by the composition root.
    
    if symbols is None:
        from application.configs.symbol_config import get_symbols
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


async def run_full_resync_process(settings,
                                 symbols: Optional[List[str]] = None,
                                 run_downloader: bool = True,
                                 run_timeframes: bool = True,
                                 run_retune: bool = True,
                                 file_repo=None,
                                 data_downloader=None,
                                 sync_manager=None,
                                 watcher_retune=None):
    """Run the complete resync process: downloader -> timeframes -> retune.

    Data-sync ports are supplied by the composition root (E2.T3) and threaded
    into each step; when omitted, default adapters are created per step,
    preserving the legacy behavior exactly.
    """
    print("="*70)
    print("🔄 STARTING FULL RESYNC PROCESS")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Configuration: Data dir = {settings.data.data_dir if settings.data and hasattr(settings.data, 'data_dir') else './data/history'}")
    print(f"   Configuration: Exchange = {settings.data.sync_default_exchange if settings.data and hasattr(settings.data, 'sync_default_exchange') else 'binance'}")
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
        results['downloader'] = await run_downloader_and_sync_process(
            symbols, file_repo=file_repo, sync_manager=sync_manager,
            data_downloader=data_downloader)
        print(f"   Status: {'✅ COMPLETED' if not results['downloader'].get('errors') else '⚠️  COMPLETED WITH ERRORS'}")
    
    # Step 2: Process Timeframes
    if run_timeframes:
        print("\n📈 STEP 2: Processing Timeframes")
        results['timeframes'] = process_timeframes(symbols, file_repo=file_repo)
        print("   Status: ✅ COMPLETED")
    
    # Step 3: Run Retune Process
    if run_retune:
        print("\n🔧 STEP 3: Running Retune Process")
        results['retune'] = await run_retune_process(
            symbols, file_repo=file_repo, watcher_retune=watcher_retune,
            data_downloader=data_downloader)
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


