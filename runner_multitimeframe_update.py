#!/usr/bin/env python3
"""
Multi-timeframe Update Runner - Aggregates 1-minute data to higher timeframes.

This script processes raw 1-minute data and creates aggregated files for 
higher timeframes (5m, 15m, 30m, 1h, etc.) following the proper MTF sync pattern:
downsample → ffill → shift → align
"""
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import pandas as pd

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
from application.configs.symbol_config import get_symbols
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = os.getenv("WFO_COINS", "BTCUSDT,ETHUSDT")
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def run_multitimeframe_update(symbols: List[str], 
                             timeframes: List[str] = None,
                             force_update: bool = False) -> Dict[str, Any]:
    """Run the multi-timeframe update process for specified symbols."""
    logger = EnhancedLogger("MTFUpdateRunner")
    
    if timeframes is None:
        timeframes = ['5m', '15m', '30m', '1h', '4h', '1d']
    
    print(f"🔄 Starting multi-timeframe update process")
    print(f"   Symbols: {symbols}")
    print(f"   Timeframes: {timeframes}")
    print(f"   Force Update: {force_update}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    
    # Create file repository
    file_repo = FileRepositoryAdapter()
    
    results = {
        'start_time': start_time.isoformat(),
        'symbols_processed': symbols,
        'timeframes_processed': timeframes,
        'updates': {},
        'summary': {
            'total_symbols': len(symbols),
            'successful_updates': 0,
            'failed_updates': 0,
            'total_files_processed': 0
        }
    }
    
    for symbol in symbols:
        print(f"\n🔍 Processing {symbol}...")
        
        try:
            # Process all timeframes for this symbol
            symbol_results = {}
            
            for timeframe in timeframes:
                print(f"   🕐 Updating {timeframe} timeframe...")
                
                try:
                    # Use the file repository's built-in method for compacting and aggregating
                    # This follows the downsample → ffill → shift → align pattern
                    # NOTE: compact_and_aggregate generates all timeframes at once, regardless of the specific timeframe
                    # This is by design to ensure consistency across timeframes
                    result = file_repo.compact_and_aggregate(
                        symbol=symbol,
                        cleanup_old=not force_update  # If forcing update, keep old files temporarily for comparison
                    )
                    
                    symbol_results[timeframe] = {
                        'status': 'success',
                        'files_processed': 1 if result else 0,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    results['summary']['total_files_processed'] += (1 if result else 0)
                    
                    if result:
                        print(f"      ✅ {timeframe} timeframe updated")
                    else:
                        print(f"      ⚠️  {timeframe} timeframe update returned: {result}")
                        
                except Exception as tf_error:
                    symbol_results[timeframe] = {
                        'status': 'failed',
                        'error': str(tf_error),
                        'timestamp': datetime.now().isoformat()
                    }
                    print(f"      ❌ {timeframe} update failed: {tf_error}")
            
            results['updates'][symbol] = {
                'status': 'partial' if any(r['status'] == 'failed' for r in symbol_results.values()) else 'success',
                'timeframes': symbol_results,
                'timestamp': datetime.now().isoformat()
            }
            
            # Count successful symbols
            all_successful = all(r['status'] == 'success' for r in symbol_results.values())
            if all_successful:
                results['summary']['successful_updates'] += 1
            else:
                results['summary']['failed_updates'] += 1
                
        except Exception as e:
            print(f"   ❌ Error processing {symbol}: {e}")
            results['updates'][symbol] = {
                'status': 'failed',
                'error': str(e),
                'timeframes': {tf: {'status': 'failed', 'error': str(e)} for tf in timeframes},
                'timestamp': datetime.now().isoformat()
            }
            results['summary']['failed_updates'] += 1
    
    # Add end time and duration
    end_time = datetime.now()
    results['end_time'] = end_time.isoformat()
    results['duration_seconds'] = (end_time - start_time).total_seconds()
    
    # Print summary
    print(f"\n📊 MULTI-TIMEFRAME UPDATE SUMMARY")
    print(f"   Symbols processed: {results['summary']['total_symbols']}")
    print(f"   Successful: {results['summary']['successful_updates']}")
    print(f"   Failed: {results['summary']['failed_updates']}")
    print(f"   Total files processed: {results['summary']['total_files_processed']}")
    print(f"   Duration: {results['duration_seconds']:.2f}s")
    
    return results


def validate_mtf_data(results: Dict[str, Any], file_repo: FileRepositoryAdapter) -> Dict[str, Any]:
    """Validate the integrity of multi-timeframe data."""
    print(f"\n✅ Validating multi-timeframe data...")
    
    validation_results = {
        'total_symbols_validated': 0,
        'valid_symbols': 0,
        'invalid_symbols': 0,
        'validation_details': {}
    }
    
    for symbol, result in results['updates'].items():
        if result['status'] in ['success', 'partial']:
            print(f"   📋 Validating {symbol}...")
            
            try:
                issues = []
                
                # Check each timeframe
                for timeframe, tf_result in result['timeframes'].items():
                    if tf_result['status'] == 'success':
                        # Verify that the processed file exists and has content
                        tf_file_path = file_repo.get_processed_file_path(symbol, timeframe)
                        
                        if os.path.exists(tf_file_path):
                            # Check if file is not empty and has proper OHLCV columns
                            try:
                                df = pd.read_csv(tf_file_path)
                                
                                required_cols = ['open', 'high', 'low', 'close', 'volume']
                                missing_cols = [col for col in required_cols if col not in df.columns]
                                
                                if missing_cols:
                                    issues.append(f"{timeframe}: Missing required columns {missing_cols}")
                                elif len(df) == 0:
                                    issues.append(f"{timeframe}: File is empty")
                                else:
                                    # Basic OHLCV validation
                                    if not (df['high'] >= df['low']).all():
                                        issues.append(f"{timeframe}: Invalid OHLC relationship (high < low)")
                                    elif not (df['high'] >= df['open']).all() or not (df['high'] >= df['close']).all():
                                        issues.append(f"{timeframe}: Invalid OHLC relationship (high < open/close)")
                                    elif not (df['low'] <= df['open']).all() or not (df['low'] <= df['close']).all():
                                        issues.append(f"{timeframe}: Invalid OHLC relationship (low > open/close)")
                            except Exception as read_error:
                                issues.append(f"{timeframe}: Error reading file - {str(read_error)}")
                        else:
                            issues.append(f"{timeframe}: File does not exist")
                
                is_valid = len(issues) == 0
                validation_results['validation_details'][symbol] = {
                    'valid': is_valid,
                    'issues': issues
                }
                
                if is_valid:
                    validation_results['valid_symbols'] += 1
                else:
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
                'issues': ['No update results']
            }
            validation_results['invalid_symbols'] += 1
            validation_results['total_symbols_validated'] += 1
    
    print(f"   Valid: {validation_results['valid_symbols']}")
    print(f"   Invalid: {validation_results['invalid_symbols']}")
    print(f"   Total validated: {validation_results['total_symbols_validated']}")
    
    return validation_results


def main():
    """Main entry point for the multi-timeframe update runner."""
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

    args = parser.parse_args()

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()
    
    print(f"🚀 Multi-Timeframe Update Runner Started")
    print(f"   Symbols: {symbols}")
    print(f"   Timeframes: {args.timeframes}")
    print(f"   Force Update: {args.force}")

    try:
        # Run update process
        results = run_multitimeframe_update(
            symbols=symbols,
            timeframes=args.timeframes,
            force_update=args.force
        )

        # Validate results if requested
        if args.validate:
            file_repo = FileRepositoryAdapter()
            validation_results = validate_mtf_data(results, file_repo)
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
    exit(main())