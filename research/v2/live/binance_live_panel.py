"""Build the same point-in-time daily panel as research/v2/lib/panel.py from Binance public REST.

Row D = Binance 1d kline with open_time D-1d (bars [D-1d, D)), known at D.
funding_past on row D = sum of funding events in (D-1d, D].
Only fully closed klines are used. No API key needed.
Rate limits: klines (limit<100) weight 1, fundingRate 500 req / 5 min / IP -> throttled.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

BASE = "https://fapi.binance.com"
DAY = 86_400_000


def _get(path: str, retries: int = 5):
    for i in range(retries):
        try:
            with urllib.request.urlopen(BASE + urllib.parse.quote(path, safe='/?&=-_.'), timeout=30) as r:
                return json.loads(r.read())
        except Exception:  # noqa: BLE001
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def universe_symbols() -> pd.DataFrame:
    info = _get("/fapi/v1/exchangeInfo")
    rows = [{"symbol": s["symbol"], "onboard": s.get("onboardDate")} for s in info["symbols"]
            if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING"]
    return pd.DataFrame(rows)


def _klines(sym: str, end_ms: int, days: int):
    k = _get(f"/fapi/v1/klines?symbol={sym}&interval=1d&endTime={end_ms - 1}&limit={min(days, 99)}")
    out = []
    for r in k:
        if int(r[6]) >= end_ms:  # not closed by end_ms
            continue
        out.append({"date": int(r[0]) + DAY, "close": float(r[4]), "open": float(r[1]), "high": float(r[2]),
                    "low": float(r[3]), "quote_volume": float(r[7]), "trades": float(r[8]),
                    "taker_buy_quote": float(r[10])})
    return sym, out


def _funding(sym: str, start_ms: int, end_ms: int):
    out, s = [], start_ms
    while True:
        d = _get(f"/fapi/v1/fundingRate?symbol={sym}&startTime={s}&endTime={end_ms}&limit=1000")
        out += d
        if len(d) < 1000:
            break
        s = int(d[-1]["fundingTime"]) + 1
    return sym, [(int(x["fundingTime"]), float(x["fundingRate"])) for x in out]


def build(asof: pd.Timestamp, days: int = 60, symbols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Panel with rows up to and including `asof` (UTC midnight)."""
    end_ms = int(asof.value // 10**6)
    if symbols is None:
        symbols = universe_symbols()["symbol"].tolist()
    with ThreadPoolExecutor(8) as ex:
        kl = dict(ex.map(lambda s: _klines(s, end_ms, days), symbols))
    start_f = end_ms - (days + 1) * DAY
    fund = {}
    for i, s in enumerate(symbols):           # fundingRate: 500 / 5min -> ~1.6 req/s
        fund[s] = _funding(s, start_f, end_ms)[1]
        time.sleep(0.62)
    long = []
    for s, rows in kl.items():
        for r in rows:
            r["symbol"] = s
            long.append(r)
    df = pd.DataFrame(long)
    df["date"] = pd.to_datetime(df["date"], unit="ms", utc=True)
    p = {f: df.pivot(index="date", columns="symbol", values=f).sort_index()
         for f in ("close", "open", "high", "low", "quote_volume", "trades", "taker_buy_quote")}
    idx = pd.date_range(p["close"].index.min(), asof, freq="1D", tz="UTC")
    p = {f: v.reindex(idx) for f, v in p.items()}
    days_ms = (idx.view("int64") // 10**6)
    fp = pd.DataFrame(0.0, index=idx, columns=p["close"].columns)
    for s, ev in fund.items():
        if not ev or s not in fp.columns:
            continue
        t = np.array([e[0] for e in ev]); r = np.array([e[1] for e in ev])
        lab = -(-t // DAY) * DAY
        fp[s] = pd.Series(r).groupby(lab).sum().reindex(days_ms).fillna(0).values
    p["funding_past"] = fp
    p["exec_px"] = p["close"]  # only used by universe_mask (validity); live execution is at market
    return p
