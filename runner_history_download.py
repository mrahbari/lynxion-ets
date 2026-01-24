#!/usr/bin/env python3
"""
History Download Runner - Comprehensive historical data downloader.

This script manages the download of historical market data for multiple symbols
and timeframes, with support for various exchanges and data validation.
"""
import os
import sys
import argparse
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.symbol_management.centralized_symbol_manager import get_unified_symbols, get_approved_symbols, get_formatted_symbol_for_exchange
from application.configs.sync_settings import settings
from application.data_sync.sync_manager import SyncManager
from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
from infrastructure.data_sync.data_downloader_adapter import DataDownloaderAdapter
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from the centralized symbol manager."""
    # Use ALL approved symbols for historical data download, not just unified subset
    return list(get_approved_symbols())


def format_symbol_for_exchange(symbol: str) -> str:
    """Format symbol for exchange API (e.g., BTC-USDT to BTCUSDT)."""
    return get_formatted_symbol_for_exchange(symbol)


async def run_history_download(
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    timeframes: List[str] = None,
    exchange: str = 'binance'
) -> Dict[str, Any]:
    """Run the history download process for specified symbols and date range."""
    logger = EnhancedLogger("HistoryDownloadRunner")

    if timeframes is None:
        timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

    print(f"📥 Starting history download process")
    print(f"   Symbols: {symbols}")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Timeframes: {timeframes}")
    print(f"   Exchange: {exchange}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    # Create components
    file_repo = FileRepositoryAdapter()
    data_downloader = DataDownloaderAdapter()
    sync_manager = SyncManager(file_repo, data_downloader)

    # Use context manager for proper resource cleanup
    async with data_downloader:
        results = {
            'start_time': start_time.isoformat(),
            'symbols_processed': symbols,
            'timeframes_requested': timeframes,
            'exchange': exchange,
            'downloads': {},
            'summary': {
                'total_symbols': len(symbols),
                'successful_downloads': 0,
                'failed_downloads': 0,
                'total_candles': 0
            }
        }

        for symbol in symbols:
            formatted_symbol = format_symbol_for_exchange(symbol)
            print(f"\n🔍 Downloading data for {symbol} ({formatted_symbol})...")

            try:
                # Download 1-minute data once, then generate all timeframes from it
                print(f"   🕐 Downloading 1m timeframe (base data)...")

                # Calculate the date range for 1-minute data
                actual_start = start_date
                # For 1-minute data, we can use the full range
                download_result = await sync_manager.sync_symbol_data(
                    symbol=formatted_symbol,
                    timeframes=['1m'],  # Download 1-minute as base
                    start_time=int(actual_start.timestamp()),
                    end_time=int(end_date.timestamp()),
                    exchange=exchange
                )

                # Now check the actual count for each timeframe from the generated files
                symbol_results = {}

                # Count 1m candles within the requested date range
                raw_file_path = file_repo.get_raw_file_path(formatted_symbol)
                one_minute_count = 0
                if os.path.exists(raw_file_path):
                    import csv
                    with open(raw_file_path, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            try:
                                timestamp = int(float(row['timestamp']))  # Ensure timestamp is converted to int
                                # Only count candles within the requested date range
                                if int(actual_start.timestamp()) <= timestamp <= int(end_date.timestamp()):
                                    one_minute_count += 1
                            except (ValueError, KeyError, TypeError):
                                continue  # Skip invalid rows

                symbol_results['1m'] = {
                    'status': 'success',
                    'candles_count': one_minute_count,
                    'start_time': actual_start.isoformat(),
                    'end_time': end_date.isoformat(),
                    'timestamp': datetime.now().isoformat()
                }

                results['summary']['total_candles'] += one_minute_count
                print(f"      ✅ 1m: {one_minute_count} candles")

                # For other timeframes, check the generated files within the requested date range
                other_timeframes = [tf for tf in timeframes if tf != '1m']
                for timeframe in other_timeframes:
                    print(f"   🕐 Processing {timeframe} timeframe from 1m base data...")

                    try:
                        # Get the processed file path for this timeframe
                        processed_file_path = file_repo.get_processed_file_path(formatted_symbol, timeframe)

                        candles_count = 0
                        if os.path.exists(processed_file_path):
                            # Count only the rows within the requested date range
                            import csv
                            with open(processed_file_path, 'r') as f:
                                reader = csv.DictReader(f)
                                for row in reader:
                                    try:
                                        timestamp = int(float(row['timestamp']))  # Ensure timestamp is converted to int
                                        # Only count candles within the requested date range
                                        if int(actual_start.timestamp()) <= timestamp <= int(end_date.timestamp()):
                                            candles_count += 1
                                    except (ValueError, KeyError, TypeError):
                                        continue  # Skip invalid rows

                        symbol_results[timeframe] = {
                            'status': 'success',
                            'candles_count': candles_count,
                            'start_time': actual_start.isoformat(),
                            'end_time': end_date.isoformat(),
                            'timestamp': datetime.now().isoformat()
                        }

                        results['summary']['total_candles'] += candles_count
                        print(f"      ✅ {timeframe}: {candles_count} candles")

                    except Exception as tf_error:
                        symbol_results[timeframe] = {
                            'status': 'failed',
                            'error': str(tf_error),
                            'timestamp': datetime.now().isoformat()
                        }
                        print(f"      ❌ {timeframe}: {tf_error}")

                results['downloads'][symbol] = {
                    'status': 'partial' if any(r['status'] == 'failed' for r in symbol_results.values()) else 'success',
                    'timeframes': symbol_results,
                    'timestamp': datetime.now().isoformat()
                }

                # Count successful vs failed downloads
                successful_tfs = sum(1 for r in symbol_results.values() if r['status'] == 'success')
                if successful_tfs == len(timeframes):
                    results['summary']['successful_downloads'] += 1
                elif successful_tfs == 0:
                    results['summary']['failed_downloads'] += 1
                else:
                    # Partial success - count as partially successful
                    results['summary']['successful_downloads'] += 1  # Or could count differently

            except Exception as e:
                print(f"   ❌ Error downloading {symbol}: {e}")
                results['downloads'][symbol] = {
                    'status': 'failed',
                    'error': str(e),
                    'timeframes': {tf: {'status': 'failed', 'error': str(e)} for tf in timeframes},
                    'timestamp': datetime.now().isoformat()
                }
                results['summary']['failed_downloads'] += 1

        # Add end time and duration
        end_time = datetime.now()
        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = (end_time - start_time).total_seconds()

        # Print summary
        print(f"\n📊 HISTORY DOWNLOAD SUMMARY")
        print(f"   Symbols processed: {results['summary']['total_symbols']}")
        print(f"   Successful: {results['summary']['successful_downloads']}")
        print(f"   Failed: {results['summary']['failed_downloads']}")
        print(f"   Total candles downloaded: {results['summary']['total_candles']:,}")
        print(f"   Duration: {results['duration_seconds']:.2f}s")

        return results


def validate_downloaded_data(results: Dict[str, Any], file_repo: FileRepositoryAdapter) -> Dict[str, Any]:
    """Validate the integrity of downloaded data."""
    print(f"\n✅ Validating downloaded data...")
    
    validation_results = {
        'total_symbols_validated': 0,
        'valid_symbols': 0,
        'invalid_symbols': 0,
        'validation_details': {}
    }
    
    for symbol, result in results['downloads'].items():
        if result['status'] == 'success' or 'timeframes' in result:
            print(f"   📋 Validating {symbol}...")
            
            try:
                # Get file index to check data integrity
                index_info = file_repo.get_file_index(symbol)
                
                if index_info:
                    timeframes_validated = []
                    issues = []
                    
                    for tf, tf_result in result['timeframes'].items():
                        if tf_result['status'] == 'success':
                            tf_file_path = file_repo.get_processed_file_path(symbol, tf)
                            if os.path.exists(tf_file_path):
                                # Check file size, dates, etc.
                                file_size = os.path.getsize(tf_file_path)
                                expected_candles = tf_result.get('candles_count', 0)
                                
                                # Simple validation - file has content and expected candle count
                                if file_size > 0 and expected_candles > 0:
                                    timeframes_validated.append(tf)
                                else:
                                    issues.append(f"{tf}: Unexpected file state (size: {file_size}, expected candles: {expected_candles})")
                            else:
                                issues.append(f"{tf}: File not found")
                    
                    is_valid = len(timeframes_validated) > 0 and len(issues) == 0
                    validation_results['validation_details'][symbol] = {
                        'valid': is_valid,
                        'timeframes_validated': timeframes_validated,
                        'issues': issues
                    }
                    
                    if is_valid:
                        validation_results['valid_symbols'] += 1
                    else:
                        validation_results['invalid_symbols'] += 1
                        
                    validation_results['total_symbols_validated'] += 1
                else:
                    validation_results['validation_details'][symbol] = {
                        'valid': False,
                        'issues': ['No index information found']
                    }
                    validation_results['invalid_symbols'] += 1
                    validation_results['total_symbols_validated'] += 1
            except Exception as e:
                print(f"     ⚠️  Error validating {symbol}: {e}")
                validation_results['validation_details'][symbol] = {
                    'valid': False,
                    'issues': [f"Validation error: {str(e)}"]
                }
                validation_results['invalid_symbols'] += 1
                validation_results['total_symbols_validated'] += 1
        else:
            validation_results['validation_details'][symbol] = {
                'valid': False,
                'issues': ['No download results']
            }
            validation_results['invalid_symbols'] += 1
            validation_results['total_symbols_validated'] += 1
    
    print(f"   Valid: {validation_results['valid_symbols']}")
    print(f"   Invalid: {validation_results['invalid_symbols']}")
    print(f"   Total validated: {validation_results['total_symbols_validated']}")
    
    return validation_results


def main():
    """Main entry point for the history download runner."""
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

    args = parser.parse_args()

    # Parse dates
    def parse_date(date_str: str) -> datetime:
        if date_str == 'today':
            return datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        elif date_str.endswith('d'):
            days = int(date_str[:-1])
            return datetime.now() - timedelta(days=days)
        else:
            return datetime.strptime(date_str, '%Y-%m-%d')

    start_date = parse_date(args.start)
    end_date = parse_date(args.end)
    
    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()
    
    print(f"🚀 History Download Runner Started")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Symbols: {symbols}")
    print(f"   Timeframes: {args.timeframes}")
    print(f"   Exchange: {args.exchange}")

    try:
        # Run download process
        results = asyncio.run(run_history_download(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframes=args.timeframes,
            exchange=args.exchange
        ))

        # Validate results if requested
        if args.validate:
            file_repo = FileRepositoryAdapter()
            validation_results = validate_downloaded_data(results, file_repo)
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
    exit(main())