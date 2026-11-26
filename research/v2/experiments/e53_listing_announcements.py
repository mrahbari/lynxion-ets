"""E53 — H5 listing-announcement demand shock (PRE-REGISTERED 2026-11-26, before any announcement or price is read).

Mechanism: a spot listing on a large retail venue (Upbit KRW market, Binance spot) gives a token a new buyer base;
the token's Binance USDT-M perp reprices within minutes. Question: is anything left after OUR latency?
Data (free, public):
  Upbit notices API (category 거래 / trade): titles containing "신규 거래지원" (new trading support); tickers parsed from
  the parentheses; time = first_listed_at (KST -> UTC).
  Binance CMS catalog 48 (New Cryptocurrency Listing): titles starting "Binance Will List" (spot listing); tickers
  parsed from the parentheses; time = releaseDate. Futures-only / delisting / Alpha / margin / TradFi titles excluded.
  Prices: Binance USDT-M perp 1m klines via REST around each event. Event kept only if the perp existed >= 1 day
  before the announcement (its 1m data starts >= 24 h earlier).
Trade (fixed): LONG at the close of the 1m bar that contains announcement + 60 s; exit at +15 min (PRIMARY) and +60 min
(reported). Costs 2 x (5 bp fee + 5 bp slippage) = 20 bp (volatile minutes). Also reported: move already made from
t-5 min to t+60 s (what our latency gives away).
Windows: DEV announcements before 2025-01-01; TEST 2025-01-01..2026-11-20 (read once). Same token on both venues
within 24 h: only the first announcement counts.
PASS: PRIMARY mean net >= +30 bp, t >= 2 and >= 55 % positive in BOTH windows -> prospective live-latency shadow
(operator decision). Positive at +60 s only before costs -> "latency race, not for us". Otherwise reject.
Usage: cd research/v2 && python experiments/e53_listing_announcements.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live import binance_live_panel as lp  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "lake" / "announcements"
SPLIT = pd.Timestamp("2025-01-01", tz="UTC")
END = pd.Timestamp("2026-11-20", tz="UTC")
COST = 2 * (0.0005 + 0.0005)
UA = {"User-Agent": "Mozilla/5.0"}
TICK = re.compile(r"\(([A-Z0-9]{2,12})\)")


def _json(url):
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
        except Exception:  # noqa: BLE001
            time.sleep(2 + 2 * i)
    raise RuntimeError(url)


def upbit() -> list:
    f = CACHE / "upbit_trade_notices.json"
    if not f.exists():
        out, page = [], 1
        while True:
            d = _json(f"https://api-manager.upbit.com/api/v1/announcements?os=web&page={page}&per_page=20&category=trade")["data"]
            out += d["notices"]
            if page >= d["total_pages"]:
                break
            page += 1
            time.sleep(0.3)
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(out))
    ev = []
    for n in json.loads(f.read_text()):
        if "신규 거래지원" not in n["title"]:
            continue
        t = pd.Timestamp(n["first_listed_at"]).tz_convert("UTC")
        for tk in set(TICK.findall(n["title"])):
            ev.append({"venue": "upbit", "t": t, "ticker": tk, "title": n["title"]})
    return ev


def binance() -> list:
    f = CACHE / "binance_listing_articles.json"
    if not f.exists():
        out, page = [], 1
        while True:
            d = _json(f"https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo={page}&pageSize=50")
            arts = d["data"]["catalogs"][0]["articles"]
            if not arts:
                break
            out += arts
            page += 1
            time.sleep(0.3)
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(out))
    ev = []
    skip = re.compile(r"Futures|Perpetual|Delist|Alpha|Margin|TradFi|Options|Earn|Convert|Pre-Market|HODLer", re.I)
    for a in json.loads(f.read_text()):
        title = a["title"]
        if not title.startswith("Binance Will List") or skip.search(title):
            continue
        t = pd.Timestamp(int(a["releaseDate"]), unit="ms", tz="UTC")
        for tk in set(TICK.findall(title)):
            ev.append({"venue": "binance", "t": t, "ticker": tk, "title": title})
    return ev


def minute_path(sym: str, t: pd.Timestamp):
    start = int((t - pd.Timedelta(minutes=30)).timestamp() * 1000)
    k = lp._get(f"/fapi/v1/klines?symbol={sym}&interval=1m&startTime={start}&limit=120")
    if not k:
        return None
    d = pd.DataFrame([{"t": pd.Timestamp(int(r[0]), unit="ms", tz="UTC"), "close": float(r[4])} for r in k]).set_index("t")
    first = lp._get(f"/fapi/v1/klines?symbol={sym}&interval=1d&startTime=0&limit=1")
    listed = pd.Timestamp(int(first[0][0]), unit="ms", tz="UTC") if first else None
    return d, listed


def main():
    ev = pd.DataFrame(upbit() + binance()).sort_values("t")
    ev = ev[ev.t <= END]
    keep, last = [], {}
    for _, e in ev.iterrows():                               # first announcement per ticker within 24 h
        if e.ticker in last and (e.t - last[e.ticker]) < pd.Timedelta(hours=24):
            continue
        last[e.ticker] = e.t
        keep.append(e)
    ev = pd.DataFrame(keep)
    print("announcements (deduplicated):", len(ev), ev.venue.value_counts().to_dict())
    rows = []
    for _, e in ev.iterrows():
        for sym in (e.ticker + "USDT", "1000" + e.ticker + "USDT"):
            try:
                res = minute_path(sym, e.t)
            except Exception:  # noqa: BLE001
                res = None
            if res is None:
                continue
            d, listed = res
            if listed is None or listed > e.t - pd.Timedelta(days=1):
                break
            t_in = (e.t + pd.Timedelta(seconds=60)).floor("min")
            need = [t_in, t_in + pd.Timedelta(minutes=15), t_in + pd.Timedelta(minutes=60), e.t.floor("min") - pd.Timedelta(minutes=5)]
            if not all(x in d.index for x in need):
                break
            p_in = d.close[t_in]
            rows.append({"venue": e.venue, "ticker": e.ticker, "sym": sym, "t": e.t,
                         "pre_move": p_in / d.close[need[3]] - 1,
                         "net15": d.close[need[1]] / p_in - 1 - COST, "net60": d.close[need[2]] / p_in - 1 - COST})
            break
        time.sleep(0.1)
    r = pd.DataFrame(rows)
    r.to_csv(ROOT / "data/research_cache/E53_listing_announcements.csv", index=False)
    print("events with a pre-existing Binance perp:", len(r), r.venue.value_counts().to_dict() if len(r) else {})
    res = {}
    for win, m in (("DEV", r.t < SPLIT), ("TEST", r.t >= SPLIT)):
        x = r[m]
        if len(x) < 10:
            res[win] = {"n": len(x)}
            print(win, res[win])
            continue
        t15 = x.net15.mean() / (x.net15.std(ddof=1) / np.sqrt(len(x)))
        res[win] = {"n": len(x), "pre_move_bp": round(x.pre_move.mean() * 1e4, 1), "net15_bp": round(x.net15.mean() * 1e4, 1),
                    "median15_bp": round(x.net15.median() * 1e4, 1), "t15": round(float(t15), 2), "pos15": round(float((x.net15 > 0).mean()), 3),
                    "net60_bp": round(x.net60.mean() * 1e4, 1), "by_venue15_bp": x.groupby("venue").net15.mean().mul(1e4).round(1).to_dict()}
        print(win, res[win])
    ok = all(res[w].get("net15_bp", -1) >= 30 and res[w].get("t15", 0) >= 2 and res[w].get("pos15", 0) >= 0.55 for w in res)
    print("E53", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
