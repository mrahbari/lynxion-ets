"""E56 — Binance vs Hyperliquid funding spread with a state-based exit (PRE-REGISTERED 2026-11-27; REPO_STUDY s.6).

Source idea: CrossVenueFundingArbitrage (abailey81/Crypto-Statistical-Arbitrage, strategies/funding_rate_arb/
cross_venue.py): enter on a large annualised spread when expected carry beats 2x costs, exit when the spread
compresses or inverts. E50 (Binance vs Bybit, fixed 7-day hold, taker) found a real but too-small spread; Hyperliquid
is an on-chain venue with a different user base and hourly funding, plausibly larger / longer dislocations.
Data: Hyperliquid public `info` API fundingHistory (hourly rate + premium vs oracle, free, from 2023-06) cached to
data/lake/hyperliquid/funding; Binance funding + 1h premium index from the lake. Coins: Binance top-60 by 2025-26
volume that Hyperliquid lists (1000X <-> kX). Hyperliquid historical candles are not available, so the price leg is
modelled through the two venues' premia: long-Binance/short-HL price P&L ~ dPremium_Binance - dPremium_HL (both
perps vs their spot-based index/oracle) -- stated limitation.
Rule (fixed): daily at 00:00 UTC, spread = annualised difference of funding sums over the previous 3 days
(HL - Binance) x 365/3. ENTER if |spread| >= 20 %/yr and spread x 30/365 > 2 x round-trip cost: short the higher-
funding venue, long the other. EXIT at the first daily check where the same-direction 3-day spread < 2 %/yr (or
inverted), or after 60 days. Round-trip cost = 2 x (5 + 2) bp Binance + 2 x (2.5 + 2) bp Hyperliquid = 23 bp.
Yield while invested = sum of net P&L / (2 x notional x invested years); also total-period yield per coin slot.
Windows: DEV 2023-07-01..2024-12-31, TEST 2025-01-01..2026-10-31 (new data, never read).
PASS: yield while invested >= 8 %/yr in BOTH windows, trade-level t >= 2 (clustered by entry week) in both, worst
single-trade price-basis P&L > -5 %.
Usage: cd research/v2 && python experiments/e56_hyperliquid_funding.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
HL = ROOT / "data" / "lake" / "hyperliquid" / "funding"
D0, SPLIT, D1 = pd.Timestamp("2023-07-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-10-31", tz="UTC")
COST = 2 * (0.0005 + 0.0002) + 2 * (0.00025 + 0.0002)
ENTER, EXIT, LOOK, MAXH = 0.20, 0.02, 3, 60


def _post(body):
    for i in range(5):
        try:
            req = urllib.request.Request("https://api.hyperliquid.xyz/info", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception:  # noqa: BLE001
            time.sleep(2 + 2 * i)
    raise RuntimeError(body)


def hl_funding(coin: str) -> pd.DataFrame:
    f = HL / f"{coin}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows, start = [], int(pd.Timestamp("2023-05-01", tz="UTC").timestamp() * 1000)
    end = int(D1.timestamp() * 1000) + 86_400_000
    while start < end:
        d = _post({"type": "fundingHistory", "coin": coin, "startTime": start})
        if not d:
            break
        rows += d
        nxt = max(int(x["time"]) for x in d) + 1
        if nxt <= start or len(d) < 2:
            break
        start = nxt
        time.sleep(0.15)
    df = pd.DataFrame({"t": [int(x["time"]) for x in rows], "rate": [float(x["fundingRate"]) for x in rows],
                       "premium": [float(x["premium"]) for x in rows]}).drop_duplicates("t").sort_values("t")
    HL.mkdir(parents=True, exist_ok=True)
    df.to_parquet(f, index=False)
    return df


def coins() -> list:
    meta = {x["name"] for x in _post({"type": "meta"})["universe"]}
    p = pn.load_daily(start="2025-01-01")
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    qv = p["quote_volume"]
    med = qv[[c for c in qv.columns if c.endswith("USDT") and c not in nps]].median().sort_values(ascending=False)
    out = []
    for s in med.index:
        base = s[:-4]
        hl = "k" + base[4:] if base.startswith("1000") else base
        if hl in meta:
            out.append((s, hl))
        if len(out) >= 60:
            break
    return out


def series(t_ms, v):
    return pd.Series(np.asarray(v, float), index=pd.to_datetime(np.asarray(t_ms), unit="ms", utc=True)).sort_index()


def run_coin(sym, hl):
    h = hl_funding(hl)
    fp, pp = pn.LAKE / "funding" / f"{sym}.parquet", pn.LAKE / "premium_1h" / f"{sym}.parquet"
    if h.empty or not fp.exists() or not pp.exists():
        return []
    fb = pd.read_parquet(fp)
    fbn = series(fb.calc_time, fb.funding_rate.fillna(0))
    fhl = series(h.t, h.rate)
    phl = series(h.t, h.premium).resample("1h").last().ffill()
    pb = pd.read_parquet(pp, columns=["open_time", "close"])
    pbn = series(pb.open_time + 3_600_000, pb.close).resample("1h").last().ffill()     # premium known at bar close
    days = pd.date_range(max(D0, fhl.index.min().ceil("D")), D1, freq="D", tz="UTC")
    cb = fbn.groupby(fbn.index.ceil("D")).sum().reindex(days, fill_value=0)
    ch = fhl.groupby(fhl.index.ceil("D")).sum().reindex(days, fill_value=0)
    spread = (ch.rolling(LOOK).sum() - cb.rolling(LOOK).sum()) * 365 / LOOK
    trades, open_ = [], None
    for D in days:
        sp = spread.get(D, np.nan)
        if not np.isfinite(sp):
            continue
        if open_ is None:
            if abs(sp) >= ENTER and abs(sp) * 30 / 365 > 2 * COST:
                open_ = {"D": D, "dir": 1 if sp > 0 else -1}        # dir +1: short HL, long Binance
            continue
        same = open_["dir"] * sp
        if same < EXIT or (D - open_["D"]).days >= MAXH or D == days[-1]:
            a, b, s = open_["D"], D, open_["dir"]
            f_hl = float(fhl[(fhl.index > a) & (fhl.index <= b)].sum())
            f_bn = float(fbn[(fbn.index > a) & (fbn.index <= b)].sum())
            fund = s * (f_hl - f_bn)                                   # short receives its venue's funding
            try:
                basis = s * ((pbn.asof(b) - pbn.asof(a)) - (phl.asof(b) - phl.asof(a)))
            except Exception:  # noqa: BLE001
                basis = np.nan
            if np.isfinite(basis):
                trades.append({"sym": sym, "hl": hl, "entry": a, "exit": b, "days": (b - a).days, "dir": s,
                               "funding": fund, "basis": basis, "net": fund + basis - COST})
            open_ = None
    return trades


def main():
    cs = coins()
    print("coins:", len(cs))
    tr = []
    for sym, hl in cs:
        tr += run_coin(sym, hl)
    ev = pd.DataFrame(tr)
    ev.to_csv(ROOT / "data/research_cache/E56_hyperliquid_trades.csv", index=False)
    res = {}
    for win, (a, b) in (("DEV", (D0, SPLIT)), ("TEST", (SPLIT, D1))):
        x = ev[(ev.entry >= a) & (ev.entry < b)]
        if len(x) < 10:
            res[win] = {"n": len(x)}
            print(win, res[win])
            continue
        wk = x.groupby(x.entry.dt.to_period("W")).net.mean()
        t = wk.mean() / (wk.std(ddof=1) / np.sqrt(len(wk)))
        inv_years = x.days.sum() / 365
        yrs = (b - a).days / 365
        res[win] = {"trades": len(x), "mean_days": round(x.days.mean(), 1), "mean_net_pct": round(x.net.mean() * 100, 3),
                    "funding_pct": round(x.funding.mean() * 100, 3), "basis_pct": round(x.basis.mean() * 100, 3),
                    "t_week": round(float(t), 2), "win": round(float((x.net > 0).mean()), 3),
                    "worst_basis_pct": round(x.basis.min() * 100, 2),
                    "yield_invested": round(x.net.sum() / (2 * inv_years), 4) if inv_years > 0 else np.nan,
                    "yield_per_slot": round(x.net.sum() / (2 * len(cs) * yrs), 4)}
        print(win, res[win])
    ok = all(r.get("yield_invested", -1) >= 0.08 and r.get("t_week", 0) >= 2 and r.get("worst_basis_pct", -99) > -5
             for r in res.values())
    print("E56", "PASS -> prospective shadow (operator decision on a Hyperliquid account)" if ok else "FAIL")


if __name__ == "__main__":
    main()
