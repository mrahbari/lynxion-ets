"""Bybit linear (USDT perp) public history -> research lake (free API; H2 cross-venue funding study, 2026-11-26).

  funding   data/lake/bybit_linear/funding/<SYM>.parquet   (calc_time ms, funding_rate)
  klines 1h data/lake/bybit_linear/klines_1h/<SYM>.parquet (open_time ms, open, high, low, close, turnover)
Backward pagination from now to 2021-01-01. Resumable: existing files are skipped unless --refresh.
Usage: cd research/v2 && python data/bybit_lake.py --symbols BTCUSDT,ETHUSDT   |   --top 60
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3] / "data" / "lake" / "bybit_linear"
API = "https://api.bybit.com"
START = int(pd.Timestamp("2021-01-01", tz="UTC").timestamp() * 1000)


def _get(path: str):
    for i in range(5):
        try:
            d = json.loads(urllib.request.urlopen(API + path, timeout=30).read())
            if d.get("retCode") == 0:
                return d["result"]
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1 + 2 * i)
    raise RuntimeError(path)


def funding(sym: str) -> pd.DataFrame:
    rows, end = [], int(time.time() * 1000)
    while end > START:
        r = _get(f"/v5/market/funding/history?category=linear&symbol={sym}&limit=200&endTime={end}")["list"]
        if not r:
            break
        rows += r
        oldest = min(int(x["fundingRateTimestamp"]) for x in r)
        if oldest >= end:
            break
        end = oldest - 1
        time.sleep(0.05)
    d = pd.DataFrame({"calc_time": [int(x["fundingRateTimestamp"]) for x in rows],
                      "funding_rate": [float(x["fundingRate"]) for x in rows]})
    return d.drop_duplicates("calc_time").sort_values("calc_time").reset_index(drop=True)


def klines(sym: str) -> pd.DataFrame:
    rows, end = [], int(time.time() * 1000)
    while end > START:
        r = _get(f"/v5/market/kline?category=linear&symbol={sym}&interval=60&limit=1000&end={end}")["list"]
        if not r:
            break
        rows += r
        oldest = min(int(x[0]) for x in r)
        if oldest >= end:
            break
        end = oldest - 1
        time.sleep(0.05)
    d = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume", "turnover"])
    d = d.astype({"open_time": "int64", "open": float, "high": float, "low": float, "close": float, "turnover": float})
    return d.drop(columns="volume").drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)


def fetch(sym: str, refresh: bool = False) -> tuple[str, int, int]:
    out = []
    for kind, fn in (("funding", funding), ("klines_1h", klines)):
        p = ROOT / kind / f"{sym}.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not refresh:
            out.append(-1)
            continue
        try:
            d = fn(sym)
            d.to_parquet(p, index=False)
            out.append(len(d))
        except Exception:  # noqa: BLE001
            out.append(0)
    return sym, out[0], out[1]


def top_symbols(n: int) -> list[str]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib import panel as pn
    p = pn.load_daily(start="2024-01-01")
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    qv = p["quote_volume"].loc["2025-01-01":]
    med = qv[[c for c in qv.columns if c.endswith("USDT") and c not in nps]].median().sort_values(ascending=False)
    tickers = {x["symbol"] for x in _get("/v5/market/tickers?category=linear")["list"]}
    return [s for s in med.index if s in tickers][:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    syms = a.symbols.split(",") if a.symbols else top_symbols(a.top or 60)
    print(f"{len(syms)} symbols", flush=True)
    with ThreadPoolExecutor(4) as ex:
        for s, nf, nk in ex.map(lambda x: fetch(x, a.refresh), syms):
            print(s, nf, nk, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
