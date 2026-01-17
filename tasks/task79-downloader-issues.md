First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md



runner_historical_data_sync.py

I ran the project runner and face with the below issues :
I already had another solution for it can you check(Multi-Exchange Historical Data Fetcher), just check and use the parts that you are interested! 
no need to copy thw file!!!!




```
python runner_historical_data_sync.py
2026-01-16 19:11:40,110 ℹ️INFO CentralizedSymbolManager - Loaded 440 approved symbols from /Users/mojtaba.rahbari/Sites/python/lynxion-ets/application/configs/approved_symbols.json
2026-01-16 19:11:40,111 ℹ️INFO CentralizedSymbolManager - Loaded 26 sync symbols from /Users/mojtaba.rahbari/Sites/python/lynxion-ets/application/configs/sync_symbols.json
2026-01-16 19:11:40,111 ℹ️INFO CentralizedSymbolManager - Created unified symbol list with 26 symbols
2026-01-16 19:11:40,111 ℹ️INFO CentralizedSymbolManager - Initialized CentralizedSymbolManager with 26 symbols
Starting Historical Data Sync Job...
2026-01-16 19:11:40,112 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Binance broker not configured for historical data (missing API keys)
2026-01-16 19:11:40,112 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ BingX broker not configured for historical data (missing API keys)
2026-01-16 19:11:40,112 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ MEXC broker not configured for historical data (missing API keys)
2026-01-16 19:11:40,112 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Phemex broker not configured for historical data (missing API keys)
2026-01-16 19:11:40,112 ⚠️WARNING MultiBrokerExecutionService - ⚠️ Binance broker not configured (missing API keys)
2026-01-16 19:11:40,112 ⚠️WARNING MultiBrokerExecutionService - ⚠️ BingX broker not configured (missing API keys)
2026-01-16 19:11:40,113 ⚠️WARNING MultiBrokerExecutionService - ⚠️ MEXC broker not configured (missing API keys)
2026-01-16 19:11:40,113 ⚠️WARNING MultiBrokerExecutionService - ⚠️ Phemex broker not configured (missing API keys)
2026-01-16 19:11:40,113 ℹ️INFO ConfigurableHistoricalDataProvider - ✅ MultiBroker service initialized for historical data
2026-01-16 19:11:40,113 ℹ️INFO ConfigurableHistoricalDataProvider - Configurable Historical Data Provider initialized with preferred source: binance
2026-01-16 19:11:40,113 ℹ️INFO ConfigurableHistoricalDataProvider - Fallback sources: ['binance', 'mexc', 'phemex']
2026-01-16 19:11:40,114 - HistoricalDataSync - INFO - Data directory structure created at: ./data/history/raw/1m
2026-01-16 19:11:40,114 - HistoricalDataSync - INFO - Starting historical data sync scheduler
2026-01-16 19:11:40,114 - HistoricalDataSync - INFO - Running initial sync...
2026-01-16 19:11:40,114 - HistoricalDataSync - INFO - Starting historical data sync for approved symbols
2026-01-16 19:11:40,115 - HistoricalDataSync - INFO - Found 26 unified symbols to sync
2026-01-16 19:11:40,115 - HistoricalDataSync - INFO - Syncing data for ALGOUSDT
2026-01-16 19:11:40,115 ℹ️INFO ConfigurableHistoricalDataProvider - Fetching historical data for ALGOUSDT from sources: ['binance', 'mexc', 'phemex']
2026-01-16 19:11:40,115 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for ALGOUSDT from binance
2026-01-16 19:11:40,115 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for ALGOUSDT from binance: Data source binance not available
2026-01-16 19:11:40,115 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for ALGOUSDT from mexc
2026-01-16 19:11:40,115 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for ALGOUSDT from mexc: Data source mexc not available
2026-01-16 19:11:40,115 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for ALGOUSDT from phemex
2026-01-16 19:11:40,116 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for ALGOUSDT from phemex: Data source phemex not available
2026-01-16 19:11:55,879 ℹ️INFO ConfigurableHistoricalDataProvider - Loaded 280214 data points from CSV cache for ALGOUSDT
2026-01-16 19:11:55,881 ℹ️INFO ConfigurableHistoricalDataProvider - ✅ Retrieved cached data for ALGOUSDT from local storage as fallback
2026-01-16 19:11:57,803 - HistoricalDataSync - ERROR - Error syncing ALGOUSDT: 'CSVHistoryLoaderAdapter' object has no attribute 'logger'
2026-01-16 19:11:57,830 - HistoricalDataSync - INFO - Syncing data for BCHUSDT
2026-01-16 19:11:57,830 ℹ️INFO ConfigurableHistoricalDataProvider - Fetching historical data for BCHUSDT from sources: ['binance', 'mexc', 'phemex']
2026-01-16 19:11:57,831 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for BCHUSDT from binance
2026-01-16 19:11:57,831 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for BCHUSDT from binance: Data source binance not available
2026-01-16 19:11:57,831 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for BCHUSDT from mexc
2026-01-16 19:11:57,831 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for BCHUSDT from mexc: Data source mexc not available
2026-01-16 19:11:57,831 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for BCHUSDT from phemex
2026-01-16 19:11:57,831 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for BCHUSDT from phemex: Data source phemex not available
2026-01-16 19:12:14,328 ℹ️INFO ConfigurableHistoricalDataProvider - Loaded 280278 data points from CSV cache for BCHUSDT
2026-01-16 19:12:14,330 ℹ️INFO ConfigurableHistoricalDataProvider - ✅ Retrieved cached data for BCHUSDT from local storage as fallback
2026-01-16 19:12:16,220 - HistoricalDataSync - ERROR - Error syncing BCHUSDT: 'CSVHistoryLoaderAdapter' object has no attribute 'logger'
2026-01-16 19:12:16,245 - HistoricalDataSync - INFO - Syncing data for XRPUSDT
2026-01-16 19:12:16,246 ℹ️INFO ConfigurableHistoricalDataProvider - Fetching historical data for XRPUSDT from sources: ['binance', 'mexc', 'phemex']
2026-01-16 19:12:16,246 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for XRPUSDT from binance
2026-01-16 19:12:16,246 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for XRPUSDT from binance: Data source binance not available
2026-01-16 19:12:16,246 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for XRPUSDT from mexc
2026-01-16 19:12:16,246 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for XRPUSDT from mexc: Data source mexc not available
2026-01-16 19:12:16,246 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for XRPUSDT from phemex
2026-01-16 19:12:16,246 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for XRPUSDT from phemex: Data source phemex not available
2026-01-16 19:12:32,599 ℹ️INFO ConfigurableHistoricalDataProvider - Loaded 280298 data points from CSV cache for XRPUSDT
2026-01-16 19:12:32,601 ℹ️INFO ConfigurableHistoricalDataProvider - ✅ Retrieved cached data for XRPUSDT from local storage as fallback
2026-01-16 19:12:34,669 - HistoricalDataSync - ERROR - Error syncing XRPUSDT: 'CSVHistoryLoaderAdapter' object has no attribute 'logger'
2026-01-16 19:12:34,695 - HistoricalDataSync - INFO - Syncing data for LTCUSDT
2026-01-16 19:12:34,695 ℹ️INFO ConfigurableHistoricalDataProvider - Fetching historical data for LTCUSDT from sources: ['binance', 'mexc', 'phemex']
2026-01-16 19:12:34,695 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for LTCUSDT from binance
2026-01-16 19:12:34,696 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for LTCUSDT from binance: Data source binance not available
2026-01-16 19:12:34,696 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for LTCUSDT from mexc
2026-01-16 19:12:34,696 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for LTCUSDT from mexc: Data source mexc not available
2026-01-16 19:12:34,696 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for LTCUSDT from phemex
2026-01-16 19:12:34,696 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for LTCUSDT from phemex: Data source phemex not available
2026-01-16 19:15:53,366 - HistoricalDataSync - ERROR - Error syncing MANAUSDT: 'CSVHistoryLoaderAdapter' object has no attribute 'logger'
2026-01-16 19:15:53,389 - HistoricalDataSync - INFO - Syncing data for SOLUSDT
2026-01-16 19:15:53,389 ℹ️INFO ConfigurableHistoricalDataProvider - Fetching historical data for SOLUSDT from sources: ['binance', 'mexc', 'phemex']
2026-01-16 19:15:53,390 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for SOLUSDT from binance
2026-01-16 19:15:53,390 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for SOLUSDT from binance: Data source binance not available
2026-01-16 19:15:53,390 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for SOLUSDT from mexc
2026-01-16 19:15:53,390 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for SOLUSDT from mexc: Data source mexc not available
2026-01-16 19:15:53,390 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for SOLUSDT from phemex
2026-01-16 19:15:53,390 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for SOLUSDT from phemex: Data source phemex not available
2026-01-16 19:16:13,701 ℹ️INFO ConfigurableHistoricalDataProvider - Loaded 280329 data points from CSV cache for SOLUSDT
2026-01-16 19:16:13,703 ℹ️INFO ConfigurableHistoricalDataProvider - ✅ Retrieved cached data for SOLUSDT from local storage as fallback
2026-01-16 19:16:15,964 - HistoricalDataSync - ERROR - Error syncing SOLUSDT: 'CSVHistoryLoaderAdapter' object has no attribute 'logger'
2026-01-16 19:16:15,989 - HistoricalDataSync - INFO - Syncing data for SANDUSDT
2026-01-16 19:16:15,989 ℹ️INFO ConfigurableHistoricalDataProvider - Fetching historical data for SANDUSDT from sources: ['binance', 'mexc', 'phemex']
2026-01-16 19:16:15,989 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for SANDUSDT from binance
2026-01-16 19:16:15,990 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for SANDUSDT from binance: Data source binance not available
2026-01-16 19:16:15,990 🐞DEBUG ConfigurableHistoricalDat
```




````
"""
Multi-Exchange Historical Data Fetcher

This script fetches historical OHLCV data from multiple exchanges to get longer date ranges.
It tries different exchanges in order of preference to work around API limitations.
Updated to include MEXC and Phemex instead of Kraken.

Features:
- Fetches 1-minute interval data from multiple exchanges
- Handles API rate limits and various error conditions
- Detects and fills gaps in historical data
- Saves data incrementally to CSV files
- Resumes from last saved point when re-run
"""

import ccxt
import os
import time
import json
import pandas as pd
from datetime import datetime, timedelta

# ===================== CONFIG =====================
TIMEFRAME = '1m'                # Data interval (1 minute)
DAYS_BACK = 30                  # Number of days of historical data to fetch
CHUNK_HOURS = 12                # Hours to fetch in each chunk (reduced to avoid API limits)
LIMIT = 2000                    # Maximum number of candles per request
SLEEP = 0.2                     # Rate limiting delay between requests

BASE_DIR = './data/historical_multi_updated/1m'  # Base directory for saving data
SYMBOL_FILE = 'symbols_usdt_multi_updated.json'  # File to store fetched symbol list

# List of exchanges to try in order of preference
EXCHANGES = [
    {'name': 'binance', 'config': {'enableRateLimit': True, 'options': {'defaultType': 'spot'}}},
    {'name': 'bingx', 'config': {'enableRateLimit': True, 'options': {'defaultType': 'spot'}}},
    {'name': 'mexc', 'config': {'enableRateLimit': True, 'options': {'defaultType': 'spot'}}},
    {'name': 'phemex', 'config': {'enableRateLimit': True, 'options': {'defaultType': 'spot'}}},
]
# =================================================

os.makedirs(BASE_DIR, exist_ok=True)


def get_exchange(exchange_name, config):
    """Get exchange instance with specified configuration."""
    exchange_class = getattr(ccxt, exchange_name)
    return exchange_class(config)


# -------------------------------------------------
# Load symbols dynamically from the best available exchange
# -------------------------------------------------
def load_symbols():
    """
    Load active USDT trading pairs from the first available exchange.

    Returns:
        list: List of active USDT trading pair symbols
    """
    for exchange_info in EXCHANGES:
        try:
            exchange = get_exchange(exchange_info['name'], exchange_info['config'])
            markets = exchange.load_markets()
            symbols = [
                s for s in markets
                if s.endswith('/USDT') and markets[s].get('active', False)
            ]
            
            print(f'[INFO] Loaded {len(symbols)} USDT symbols from {exchange_info["name"]}')
            
            with open(SYMBOL_FILE, 'w') as f:
                json.dump(symbols, f, indent=2)
            
            return symbols
        except Exception as e:
            print(f'[ERROR] Could not load symbols from {exchange_info["name"]}: {str(e)}')
            continue
    
    raise Exception("Could not load symbols from any exchange")


# -------------------------------------------------
# Time helpers
# -------------------------------------------------
def get_time_range():
    """
    Calculate the time range for fetching historical data.

    Returns:
        tuple: (start_timestamp, end_timestamp) in milliseconds
    """
    end_ts = int(datetime.utcnow().timestamp() * 1000)
    start_ts = end_ts - int(DAYS_BACK * 24 * 60 * 60 * 1000)
    return start_ts, end_ts


# -------------------------------------------------
# Chunked OHLCV fetch with fallback exchanges
# -------------------------------------------------
def fetch_ohlcv_chunked_with_fallback(symbol, start_ts, end_ts):
    """
    Fetch OHLCV data using multiple exchanges as fallbacks.

    Args:
        symbol (str): Trading pair symbol (e.g., 'BTC/USDT')
        start_ts (int): Start timestamp in milliseconds
        end_ts (int): End timestamp in milliseconds

    Returns:
        list: List of OHLCV candles
    """
    all_rows = []
    since = start_ts

    # Convert chunk size from hours to milliseconds
    chunk_size_ms = CHUNK_HOURS * 60 * 60 * 1000

    while since < end_ts:
        chunk_end = min(since + chunk_size_ms, end_ts)
        data_fetched = False
        
        # Try each exchange in order until one works
        for exchange_info in EXCHANGES:
            try:
                exchange = get_exchange(exchange_info['name'], exchange_info['config'])
                
                print(f'[TRYING] {exchange_info["name"]} for {symbol} from {pd.to_datetime(since, unit="ms")} to {pd.to_datetime(chunk_end, unit="ms")}')
                
                candles = exchange.fetch_ohlcv(
                    symbol,
                    timeframe=TIMEFRAME,
                    since=since,
                    limit=LIMIT
                )
                
                if candles:
                    for c in candles:
                        if c[0] <= chunk_end and c[0] >= since:
                            all_rows.append(c)
                    
                    # Move the since pointer to the timestamp of the last candle + 1 minute
                    if candles:
                        since = candles[-1][0] + 60_000
                    
                    data_fetched = True
                    print(f'[SUCCESS] Got {len(candles)} candles from {exchange_info["name"]}')
                    break  # Successfully got data, move to next chunk
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'date of query is too wide' in error_msg or 'too wide' in error_msg:
                    print(f'[DATE RANGE ERROR] {exchange_info["name"]}: {str(e)}')
                    # Try with a smaller chunk
                    chunk_size_ms = 1 * 60 * 60 * 1000  # 1 hour
                    chunk_end = min(since + chunk_size_ms, end_ts)
                    continue
                elif 'invalid symbol' in error_msg or 'symbol not found' in error_msg:
                    print(f'[INVALID SYMBOL] {exchange_info["name"]}: {symbol}')
                    continue
                elif 'rate limit' in error_msg or 'rateLimit' in str(e):
                    print(f'[RATE LIMIT] {exchange_info["name"]}: Waiting {SLEEP*5} seconds')
                    time.sleep(SLEEP * 5)
                    continue
                else:
                    print(f'[ERROR] {exchange_info["name"]}: {str(e)}')
                    continue
        
        if not data_fetched:
            # If no exchange worked for this chunk, advance by chunk size
            since = min(since + chunk_size_ms, end_ts)
            print(f'[SKIPPED] Could not fetch data for chunk from {pd.to_datetime(since-chunk_size_ms, unit="ms")} to {pd.to_datetime(since, unit="ms")}')
        
        # Sleep to respect rate limits
        time.sleep(SLEEP)

    return all_rows


# -------------------------------------------------
# Gap detection
# -------------------------------------------------
def detect_gaps(df):
    """
    Detect gaps in the timestamp sequence of OHLCV data.

    Args:
        df (pandas.DataFrame): DataFrame with 'timestamp' column

    Returns:
        list: List of tuples containing (gap_start, gap_end) timestamps
    """
    gaps = []
    ts = df['timestamp'].values
    for i in range(1, len(ts)):
        if ts[i] - ts[i - 1] > 60000:  # More than 1 minute gap
            gaps.append((ts[i - 1], ts[i]))
    return gaps


# -------------------------------------------------
# Process single symbol
# -------------------------------------------------
def process_symbol(symbol):
    file_path = f"{BASE_DIR}/{symbol.replace('/', '-')}.csv"
    start_ts, end_ts = get_time_range()

    # Load existing data if file exists
    df = None
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            last_ts = int(df['timestamp'].iloc[-1])
            start_ts = last_ts + 60000
            print(f'[RESUME] {symbol}')
        except Exception as e:
            print(f'[ERROR] Could not read existing file for {symbol}: {str(e)}')
            df = None
    else:
        print(f'[NEW] {symbol}')

    # Fetch new data
    rows = fetch_ohlcv_chunked_with_fallback(symbol, start_ts, end_ts)
    if not rows:
        print(f'[EMPTY] {symbol}')
        return

    # Create new dataframe with fetched data
    try:
        new_df = pd.DataFrame(
            rows,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        new_df['datetime'] = pd.to_datetime(new_df['timestamp'], unit='ms')
    except Exception as e:
        print(f'[ERROR] Failed to create dataframe for {symbol}: {str(e)}')
        return

    # Combine with existing data if available
    if df is not None and not df.empty:
        df = pd.concat([df, new_df]).drop_duplicates('timestamp').reset_index(drop=True)
    else:
        df = new_df

    # GAP CHECK & REPAIR
    try:
        gaps = detect_gaps(df)
        if gaps:
            print(f'[GAPS FOUND] {symbol}: {len(gaps)} gaps detected')
            for g_start, g_end in gaps:
                print(f'  Gap: {pd.to_datetime(g_start, unit="ms")} to {pd.to_datetime(g_end, unit="ms")}')
                gap_rows = fetch_ohlcv_chunked_with_fallback(
                    symbol,
                    g_start + 60000,
                    g_end - 60000
                )
                if gap_rows:
                    gap_df = pd.DataFrame(
                        gap_rows,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    gap_df['datetime'] = pd.to_datetime(gap_df['timestamp'], unit='ms')
                    df = pd.concat([df, gap_df]).drop_duplicates('timestamp').reset_index(drop=True)
            df = df.sort_values('timestamp').reset_index(drop=True)
    except Exception as e:
        print(f'[ERROR] Gap detection failed for {symbol}: {str(e)}')

    # Save to CSV
    try:
        df.to_csv(file_path, index=False)
        print(f'[SAVED] {symbol} -> {file_path} ({len(df)} rows)')
    except Exception as e:
        print(f'[ERROR] Failed to save {symbol} to {file_path}: {str(e)}')
        return

    return df


# -------------------------------------------------
# Main execution
# -------------------------------------------------
def main():
    """
    Main function to orchestrate the historical data fetching process.
    Loads symbols and processes each one to fetch and save historical data.
    """
    print('[MULTI_EXCHANGE_FETCHER_UPDATED] Starting data fetch process...')

    # Load symbols
    try:
        with open(SYMBOL_FILE, 'r') as f:
            symbols = json.load(f)
        print(f'[INFO] Loaded {len(symbols)} symbols from {SYMBOL_FILE}')
    except FileNotFoundError:
        print(f'[INFO] {SYMBOL_FILE} not found, loading symbols from exchange...')
        symbols = load_symbols()

    # Process each symbol
    for i, symbol in enumerate(symbols):
        print(f'[{i+1}/{len(symbols)}] Processing {symbol}...')
        try:
            process_symbol(symbol)
        except Exception as e:
            print(f'[ERROR] Failed to process {symbol}: {str(e)}')
            continue

        # Rate limiting
        time.sleep(SLEEP)

    print('[MULTI_EXCHANGE_FETCHER_UPDATED] Process completed!')


if __name__ == '__main__':
    main()
````