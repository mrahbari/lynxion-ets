"""
Resample Engine for converting 1m data to higher timeframes (5m, 15m, 30m, 1h).
Following Hedge Fund standards for production-level resampling with zero-drift.
"""
import os
import pandas as pd
from datetime import datetime
from shared.logger import logger


class ResampleEngine:
    def __init__(self, raw_root="./data/history/raw/1m/", out_root="./data/history/processed/"):
        self.raw_root = raw_root
        self.out_root = out_root

        # Create output folders
        for tf in ["5m", "15m", "30m", "1h"]:
            os.makedirs(f"{self.out_root}/{tf}/", exist_ok=True)
        logger.info(f"ResampleEngine initialized. Raw root: {self.raw_root}, Out root: {self.out_root}")

    def _load_1m(self, symbol):
        path = f"{self.raw_root}/{symbol}.csv"
        if not os.path.exists(path):
            raise Exception(f"Raw 1m data for {symbol} not found at {path}")
        return pd.read_csv(path)

    def _save(self, symbol, df, tf):
        """Save resampled data to the appropriate directory."""
        os.makedirs(f"{self.out_root}/{tf}/", exist_ok=True)
        df.to_csv(f"{self.out_root}/{tf}/{symbol}.csv", index=False)
        logger.info(f"Saved {len(df)} resampled records for {symbol} {tf} to {self.out_root}/{tf}/{symbol}.csv")

    def _prepare_df(self, df):
        """Prepare data for resampling by setting timestamp as index."""
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    def resample_tf(self, symbol):
        """Resample a symbol from 1m to all higher timeframes."""
        logger.info(f"Resampling {symbol} ...")

        df = self._load_1m(symbol)
        df = self._prepare_df(df)

        # OHLC rules (industry standard)
        ohlc_rule = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }

        # Timeframe map
        tf_map = {
            "5m": "5T",  # 5 minutes
            "15m": "15T",  # 15 minutes
            "30m": "30T",  # 30 minutes
            "1h": "1H"  # 1 hour
        }

        for name, rule in tf_map.items():
            try:
                df_res = df.resample(rule).apply(ohlc_rule).dropna()
                df_res.reset_index(inplace=True)

                # Convert timestamp back to milliseconds integer
                df_res["timestamp"] = (df_res["timestamp"].astype("int64") // 10**6).astype(int)

                self._save(symbol, df_res, name)
                logger.info(f"Successfully resampled {symbol} to {name} timeframe. {len(df_res)} rows")
            except Exception as e:
                logger.error(f"Error resampling {symbol} to {name}: {str(e)}")
                raise e

    def resample_all(self, symbols):
        """Resample all symbols to all higher timeframes."""
        logger.info(f"Starting resample for {len(symbols)} symbols")
        for symbol in symbols:
            try:
                self.resample_tf(symbol)
            except Exception as e:
                logger.error(f"[ERROR] Could not resample {symbol}: {e}")


if __name__ == "__main__":
    # Example usage
    engine = ResampleEngine()
    # Example symbols to resample
    symbols = ["BTCUSDT", "ETHUSDT"]  # Add more symbols as needed
    engine.resample_all(symbols)