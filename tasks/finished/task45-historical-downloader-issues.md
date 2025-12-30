Try to resolve the below issue for download the historical data from bingx or binance:

python runner_history_download.py --start 90d --end today --symbols MATICUSDT --exchange binance
🚀 History Download Runner Started
   Date Range: 2025-09-29 to 2025-12-28
   Symbols: ['MATICUSDT']
   Timeframes: ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
   Exchange: binance
📥 Starting history download process
   Symbols: ['MATICUSDT']
   Date Range: 2025-09-29 to 2025-12-28
   Timeframes: ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
   Exchange: binance
   Timestamp: 2025-12-28 12:57:17

🔍 Downloading data for MATICUSDT (MATICUSDT)...
   🕐 Downloading 1m timeframe (base data)...
      ✅ 1m: 0 candles
   🕐 Processing 5m timeframe from 1m base data...
      ✅ 5m: 0 candles
   🕐 Processing 15m timeframe from 1m base data...
      ✅ 15m: 0 candles
   🕐 Processing 30m timeframe from 1m base data...
      ✅ 30m: 0 candles
   🕐 Processing 1h timeframe from 1m base data...
      ✅ 1h: 0 candles
   🕐 Processing 4h timeframe from 1m base data...
      ✅ 4h: 0 candles
   🕐 Processing 1d timeframe from 1m base data...
      ✅ 1d: 0 candles

📊 HISTORY DOWNLOAD SUMMARY
   Symbols processed: 1
   Successful: 1
   Failed: 0
   Total candles downloaded: 0
   Duration: 30.62s

🎉 All downloads completed successfully!





python runner_history_download.py --start 90d --end today --symbols TRMPUSDT --exchange bingx
🚀 History Download Runner Started
   Date Range: 2025-09-29 to 2025-12-28
   Symbols: ['TRMPUSDT']
   Timeframes: ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
   Exchange: bingx
📥 Starting history download process
   Symbols: ['TRMPUSDT']
   Date Range: 2025-09-29 to 2025-12-28
   Timeframes: ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
   Exchange: binance
   Timestamp: 2025-12-28 19:04:06

🔍 Downloading data for TRMPUSDT (TRMPUSDT)...
   🕐 Downloading 1m timeframe (base data)...
      ✅ 1m: 0 candles
   🕐 Processing 5m timeframe from 1m base data...
      ✅ 5m: 0 candles
   🕐 Processing 15m timeframe from 1m base data...
      ✅ 15m: 0 candles
   🕐 Processing 30m timeframe from 1m base data...
      ✅ 30m: 0 candles
   🕐 Processing 1h timeframe from 1m base data...
      ✅ 1h: 0 candles
   🕐 Processing 4h timeframe from 1m base data...
      ✅ 4h: 0 candles
   🕐 Processing 1d timeframe from 1m base data...
      ✅ 1d: 0 candles

📊 HISTORY DOWNLOAD SUMMARY
   Symbols processed: 1
   Successful: 1
   Failed: 0
   Total candles downloaded: 0
   Duration: 10.09s

🎉 All downloads completed successfully!


for some symbols like ADAUSDT it's working correctly!!