"""Fetch design-TF history for the Phase-12 broader symbol universe (data prep only).

Uses the existing ConfigurableHistoricalDataProvider (Binance public klines, capped ~1000
bars/call) to fetch 1h/15m/5m for the new symbols and write them to the canonical
data/history/raw/<tf>/<SYM>-USDT.csv layout. No strategy code touched. ~1000 bars/cell
(shorter calendar window than BTC/ETH/SOL — documented in the reports).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import logging
logging.disable(logging.WARNING)
os.environ.pop("BROKER_PAPER_TRADING", None)
os.environ.pop("LIVE_TRADING", None)

from bootstrap.settings.loaders import load_settings
from domain.value_objects import Symbol
from infrastructure.data.configurable_historical_data_provider import ConfigurableHistoricalDataProvider

NEW = ["BNB", "XRP", "DOGE", "ADA", "LINK", "TON", "TRX", "SUI", "AVAX", "HYPE"]
TFS = ["1h", "15m", "5m"]


def main():
    p = ConfigurableHistoricalDataProvider(settings=load_settings(),
                                           preferred_data_source="binance",
                                           fallback_sources=["mexc", "phemex"])
    for sym in NEW:
        for tf in TFS:
            try:
                d = p.get_historical_data(Symbol(f"{sym}USDT"), "365d", tf)
            except Exception as e:
                print(f"{sym} {tf}: ERROR {e}", file=sys.stderr)
                continue
            if not d:
                print(f"{sym} {tf}: 0 rows", file=sys.stderr)
                continue
            rows = sorted({int(b["timestamp"]): b for b in d}.values(), key=lambda b: int(b["timestamp"]))
            outdir = os.path.join(REPO, "data", "history", "raw", tf)
            os.makedirs(outdir, exist_ok=True)
            out = os.path.join(outdir, f"{sym}-USDT.csv")
            with open(out, "w", encoding="utf-8") as f:
                f.write("timestamp,open,high,low,close,volume\n")
                for b in rows:
                    f.write(f"{int(b['timestamp'])},{b['open']},{b['high']},{b['low']},{b['close']},{b['volume']}\n")
            print(f"{sym} {tf}: {len(rows)} rows -> {out}", file=sys.stderr)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
