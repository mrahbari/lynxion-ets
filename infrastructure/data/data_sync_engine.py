"""
Data Sync Engine for managing download, incremental updates, and full refresh.
Following Hedge Fund standards for production-level data sync with 25 coins.
"""
import time
import pandas as pd
from datetime import datetime, timedelta
from shared.logger import logger
from infrastructure.data.binance_client import BinanceClient
from infrastructure.data.candle_store import CandleStore


class DataSyncEngine:
    """
    Manages full refresh (6 months) and incremental updates (daily) of 1m data.
    """

    def __init__(self, symbols: list, client: BinanceClient, store: CandleStore):
        self.symbols = symbols
        self.client = client
        self.store = store
        logger.info(f"DataSyncEngine initialized for {len(symbols)} symbols: {symbols}")

    def _now_ms(self):
        return int(time.time() * 1000)

    def _days_to_ms(self, days):
        return days * 24 * 60 * 60 * 1000

    def full_refresh(self, days=180):
        """
        Download full 6 months (or more) of 1m candles.
        """
        logger.info(f"\n=== FULL REFRESH START for {len(self.symbols)} symbols: {self.symbols} ===\n")

        end = self._now_ms()
        start = end - self._days_to_ms(days)

        for symbol in self.symbols:
            logger.info(f"Starting full refresh for: {symbol}")
            all_rows = []

            batch_start = start
            while batch_start < end:
                # 2 days per request to stay within API limits (safe approach)
                batch_end = min(batch_start + self._days_to_ms(2), end)
                
                # Adjust start to be multiple of minute to avoid partial candles
                batch_start_adj = (batch_start // 60000) * 60000
                
                data = self.client.get_klines(symbol, "1m", batch_start_adj, batch_end)

                if not data:
                    logger.warning(f" - No data in chunk for {symbol} from {datetime.fromtimestamp(batch_start/1000)} to {datetime.fromtimestamp(batch_end/1000)}, skipping…")
                    batch_start = batch_end
                    continue

                rows = []
                for x in data:
                    rows.append([
                        int(x[0]), float(x[1]), float(x[2]),
                        float(x[3]), float(x[4]), float(x[5])
                    ])
                all_rows.extend(rows)

                batch_start = batch_end
                time.sleep(0.2)  # Rate-limit safe

            if all_rows:
                df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df_clean = self.store.merge_and_clean(symbol, df)
                self.store.save(symbol, df_clean)
                logger.info(f"Full refresh completed for {symbol}: {len(df_clean)} total records")
            else:
                logger.warning(f"No data retrieved for {symbol}")

        logger.info("\n=== FULL REFRESH FINISHED ===\n")

    def incremental_update(self):
        """
        Append last 24h (or more) candles to each symbol.
        """
        logger.info("\n=== INCREMENTAL UPDATE START ===\n")

        end = self._now_ms()
        start = end - self._days_to_ms(2)  # 2 days to be safe

        for symbol in self.symbols:
            logger.info(f"Updating: {symbol}")

            data = self.client.get_klines(symbol, "1m", start, end)

            rows = []
            for x in data:
                rows.append([
                    int(x[0]), float(x[1]), float(x[2]),
                    float(x[3]), float(x[4]), float(x[5])
                ])

            if rows:
                df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df_clean = self.store.merge_and_clean(symbol, df)
                self.store.save(symbol, df_clean)
                logger.info(f"Incremental update completed for {symbol}: {len(df)} new records added, {len(df_clean)} total")
            else:
                logger.info(f"No new data for {symbol}")

        logger.info("\n=== INCREMENTAL UPDATE FINISHED ===\n")


if __name__ == "__main__":
    # Example usage
    symbols_25 = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", 
        "SOLUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "SHIBUSDT",
        "MATICUSDT", "LTCUSDT", "UNIUSDT", "LINKUSDT", "LUNAUSDT",
        "TONUSDT", "ALGOUSDT", "XLMUSDT", "ETCUSDT", "BCHUSDT",
        "NEARUSDT", "FLOWUSDT", "MANAUSDT", "SANDUSDT", "AAVEUSDT"
    ]
    
    client = BinanceClient()
    store = CandleStore()
    engine = DataSyncEngine(symbols_25, client, store)
    
    # Example usage (uncomment to run):
    # engine.full_refresh(30)  # 30 days for testing
    # engine.incremental_update()