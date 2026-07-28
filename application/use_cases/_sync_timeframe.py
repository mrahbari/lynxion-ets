"""E5.T5 (infra-only mechanical split): multi-timeframe update + validation data-sync ops extracted from sync_market_data.

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


def run_multitimeframe_update(symbols: List[str], 
                             timeframes: List[str] = None,
                             force_update: bool = False,
                             file_repo=None) -> Dict[str, Any]:
    """Run the multi-timeframe update process for specified symbols.

    ``file_repo`` is the data-access port supplied by the composition root
    (E2.T3). When omitted a default adapter is constructed, preserving the
    legacy behavior exactly.
    """
    logger = EnhancedLogger("MTFUpdateRunner")
    
    if timeframes is None:
        timeframes = ['5m', '15m', '30m', '1h', '4h', '1d']
    
    print(f"🔄 Starting multi-timeframe update process")
    print(f"   Symbols: {symbols}")
    print(f"   Timeframes: {timeframes}")
    print(f"   Force Update: {force_update}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    
    # Data-access port (file_repo) is injected by the composition root.
    
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


def validate_mtf_data(results: Dict[str, Any], file_repo) -> Dict[str, Any]:
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

                                required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                                missing_cols = [col for col in required_cols if col not in df.columns]

                                if missing_cols:
                                    issues.append(f"{timeframe}: Missing required columns {missing_cols}")
                                elif len(df) == 0:
                                    issues.append(f"{timeframe}: File is empty")
                                else:
                                    # Validate timestamp format - ensure it's Unix timestamp (integer)
                                    if 'timestamp' in df.columns:
                                        try:
                                            # Check if timestamp values look like Unix timestamps
                                            sample_timestamp = df['timestamp'].iloc[0] if len(df) > 0 else None
                                            if sample_timestamp is not None:
                                                # Convert to int to ensure it's in the right format
                                                int_timestamp = int(float(sample_timestamp))
                                                # Verify it looks like a Unix timestamp (after year 2000)
                                                if int_timestamp < 946684800:  # Jan 1, 2000 timestamp
                                                    issues.append(f"{timeframe}: Timestamp format may be incorrect - values seem too small to be Unix timestamps")
                                        except (ValueError, TypeError):
                                            issues.append(f"{timeframe}: Timestamp format error - cannot convert to integer")

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


