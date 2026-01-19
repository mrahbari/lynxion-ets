"""
Data Integrity Report Generator - Creates comprehensive reports on market data quality
"""
import pandas as pd
import sys
import os
from datetime import datetime
from typing import List, Dict

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter


def generate_data_integrity_report(symbols: List[str], start_date: str, end_date: str, timeframe: str = "1d"):
    """
    Generate a comprehensive data integrity report for specified symbols and date range.
    
    Args:
        symbols: List of trading symbols to check
        start_date: Start date in YYYY-MM-DD format or relative format (e.g., '180d')
        end_date: End date in YYYY-MM-DD format or 'today'
        timeframe: Timeframe to check (default '1d')
    """
    print("📊 GENERATING DATA INTEGRITY REPORT")
    print(f"   Symbols: {symbols}")
    print(f"   Date Range: {start_date} to {end_date}")
    print(f"   Timeframe: {timeframe}")
    
    # Initialize data loader
    data_loader = CSVHistoryLoaderAdapter()
    
    # Prepare report data
    report_data = []
    
    for symbol in symbols:
        try:
            # Load data for the symbol
            df = data_loader.load(symbol=symbol, timeframe=timeframe)
            
            if df.empty:
                status = "NO DATA"
                missing_ratio = 1.0
                total_rows = 0
                date_range = "N/A"
            else:
                # Calculate expected number of candles based on date range
                if 'timestamp' in df.columns:
                    timestamps = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                else:
                    timestamps = pd.to_datetime(df.index, utc=True)
                
                if len(timestamps) == 0:
                    status = "NO DATA"
                    missing_ratio = 1.0
                    total_rows = 0
                    date_range = "N/A"
                else:
                    min_time = timestamps.min()
                    max_time = timestamps.max()
                    
                    # Calculate expected count based on timeframe
                    if timeframe.endswith('d'):  # Daily data
                        expected_count = (max_time - min_time).days + 1
                    elif timeframe.endswith('h'):  # Hourly data
                        expected_count = int((max_time - min_time).total_seconds() / 3600) + 1
                    elif timeframe.endswith('m'):  # Minute data
                        expected_count = int((max_time - min_time).total_seconds() / 60) + 1
                    else:
                        # Default to daily if timeframe not recognized
                        expected_count = (max_time - min_time).days + 1
                    
                    actual_count = len(df)
                    missing_ratio = 1 - (actual_count / expected_count) if expected_count > 0 else 0
                    
                    # Ensure ratio is between 0 and 1
                    missing_ratio = max(0.0, min(1.0, missing_ratio))
                    
                    status = "PASS" if missing_ratio <= 0.05 else "FAIL"
                    total_rows = actual_count
                    date_range = f"{min_time.date()} to {max_time.date()}"
            
            report_data.append({
                'Symbol': symbol,
                'Status': status,
                'Missing %': f"{missing_ratio:.2%}",
                'Total Rows': total_rows,
                'Date Range': date_range,
                'Expected Rows': (max_time - min_time).days + 1 if 'max_time' in locals() and 'min_time' in locals() else 0
            })
            
        except Exception as e:
            report_data.append({
                'Symbol': symbol,
                'Status': "ERROR",
                'Missing %': "N/A",
                'Total Rows': 0,
                'Date Range': "N/A",
                'Expected Rows': 0,
                'Error': str(e)
            })
    
    # Create DataFrame and display report
    df_report = pd.DataFrame(report_data)
    
    print("\n📈 DATA INTEGRITY REPORT")
    print("=" * 80)
    print(df_report.to_string(index=False))
    print("=" * 80)
    
    # Summary statistics
    total_symbols = len(symbols)
    failed_symbols = len(df_report[df_report['Status'] == 'FAIL'])
    error_symbols = len(df_report[df_report['Status'] == 'ERROR'])
    pass_symbols = len(df_report[df_report['Status'] == 'PASS'])
    
    print(f"\n📋 SUMMARY:")
    print(f"   Total Symbols Checked: {total_symbols}")
    print(f"   Passed Validation: {pass_symbols}")
    print(f"   Failed Validation: {failed_symbols}")
    print(f"   Errors Encountered: {error_symbols}")
    print(f"   Success Rate: {pass_symbols/total_symbols*100:.2f}%")
    
    # Recommendation
    if failed_symbols > 0 or error_symbols > 0:
        print(f"\n⚠️  RECOMMENDATION:")
        print(f"   Data quality is insufficient for reliable backtesting.")
        print(f"   {failed_symbols} symbols have excessive missing data (>5% missing).")
        print(f"   Consider using higher quality data sources or data repair techniques.")
    else:
        print(f"\n✅ RECOMMENDATION:")
        print(f"   Data quality is sufficient for backtesting.")
    
    return df_report


if __name__ == "__main__":
    # Generate report for the symbols mentioned in the task
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT']
    
    # Generate report
    report = generate_data_integrity_report(
        symbols=symbols,
        start_date='2025-07-22',
        end_date='2026-01-18',
        timeframe='1d'
    )
    
    # Save report
    report_file = f"./reports/data_integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    report.to_csv(report_file, index=False)
    print(f"\n💾 Report saved to: {report_file}")