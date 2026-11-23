"""E17 data: Binance USD-M 5m klines WITH taker buy volume (E9 cache drops it), for the E9 symbols and period."""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402

CACHE = e9.ROOT / "data" / "research_cache" / "e17"
STEP = 300_000


def klines5(sym: str) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{sym}_5m_taker.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows, t, end = [], int(e9.START.timestamp() * 1000), int(e9.END.timestamp() * 1000)
    while t < end:
        for attempt in range(4):
            try:
                with urllib.request.urlopen(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=5m"
                                            f"&startTime={t}&limit=1500", timeout=30) as r:
                    batch = json.loads(r.read())
                break
            except Exception:
                time.sleep(3 + 3 * attempt)
        else:
            raise RuntimeError(sym)
        if not batch:
            break
        rows += batch
        t = batch[-1][0] + STEP
        time.sleep(0.12)
    d = pd.DataFrame(rows)
    out = pd.DataFrame({"t": d[0].astype("int64"), "c": d[4].astype(float), "qv": d[7].astype(float),
                        "tbq": d[10].astype(float)})
    out = out[out.t < end].drop_duplicates("t").sort_values("t").reset_index(drop=True)
    out.to_parquet(f)
    return out


if __name__ == "__main__":
    for s in e9.SYMBOLS:
        print(s, len(klines5(s)), flush=True)
