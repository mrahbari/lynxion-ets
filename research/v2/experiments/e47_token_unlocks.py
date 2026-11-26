"""E47 — Token unlock event study: short large INSIDER cliff unlocks (PRE-REGISTERED 2026-11-26).

Source idea: Keyrock, "From Locked to Liquidity: what 16,000+ token unlocks teach us" (secondary coverage: ~90 % of
unlocks show negative price pressure, starting ~30 days ahead; team unlocks worst, ecosystem unlocks ~neutral).
Schedules are public in advance, so a perp short is a tradable, non-price information source. New family for Lynxion.

Data: free DefiLlama emissions dataset (data/lake/defillama_emissions, 375 tokens, downloaded 2026-11-26), mapped to
Binance USDT-M perps via CoinGecko id -> symbol (195 tokens map). Prices / funding: daily lake panel.
Limitations stated up front: the dataset is today's version of the schedules (later revisions possible); ticker
mapping via CoinGecko symbol can be wrong for rare collisions.

Events: cliff unlocks (metadata.unlockEvents[].cliffAllocations).
  INSIDER allocation: category in {insiders, privateSale}, or category "Uncategorized" with a recipient matching
  team|investor|advisor|contributor|core|seed|private|strategic|backer|founder|series|early.
  size = cliff amount / circulating supply the day before (sum of all categories' cumulative unlocked).
  INSIDER_BIG: insider cliff size >= 1 %. NONINSIDER_BIG (contrast only): non-insider cliff >= 1 % and no insider part.
  Eligibility: perp has daily closes from T-30 to T+14 and 30-day median volume >= $5M at T-30; one event per token
  per 44 days (first kept).
Trade (primary): SHORT the token perp from the close of T-30 to the close of T+14 (T = unlock day), hedged with a long
  equal-weight basket of liquid perps (same universe as V1) -> excess return.
  net = -(r_token - r_market) - 4 x (5 bp fee + 2 bp slippage) + funding received on the token short.
  Reported also: sub-windows T-30 -> T-1 and T -> T+14.
Windows: DEV events 2022-01-01..2024-12-31, TEST 2025-01-01..2026-10-15 (read once).
PASS (INSIDER_BIG): DEV mean net >= +2 % per event, t >= 2 (events clustered by calendar week), >= 55 % positive;
  TEST mean net > 0 and >= 50 % of DEV.
Decision: PASS -> design a pre-registered live shadow (calendar-driven) for operator decision; FAIL -> record.
Usage: cd research/v2 && python experiments/e47_token_unlocks.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
EM = ROOT / "data" / "lake" / "defillama_emissions"
INSIDER_RX = re.compile(r"team|investor|advisor|contributor|core|seed|private|strategic|backer|founder|series|early", re.I)
COST = 4 * (0.0005 + 0.0002)
DEV0, SPLIT, END = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-10-15", tz="UTC")


def mapping() -> dict:
    cg = {c["id"]: c["symbol"].upper() for c in json.loads((EM / "_coingecko_coins_list.json").read_text())}
    lake = {p.stem for p in (pn.LAKE / "klines_1h").glob("*.parquet")}
    out = {}
    for f in EM.glob("*.json"):
        if f.name.startswith("_"):
            continue
        d = json.loads(f.read_text())
        s = cg.get(d.get("gecko_id"))
        if not s:
            continue
        for cand in (s + "USDT", "1000" + s + "USDT", "1000000" + s + "USDT", "10000" + s + "USDT"):
            if cand in lake:
                out[f.stem] = cand
                break
    return out


def events_for(name: str) -> list:
    d = json.loads((EM / f"{name}.json").read_text())
    circ = None
    for cat in d.get("documentedData", {}).get("data", []):
        s = pd.Series({pd.Timestamp(x["timestamp"], unit="s", tz="UTC").normalize(): float(x.get("unlocked") or 0)
                       for x in cat.get("data", [])})
        circ = s if circ is None else circ.add(s, fill_value=0)
    if circ is None or circ.empty:
        return []
    circ = circ.sort_index()
    out = []
    for e in d["metadata"].get("unlockEvents", []):
        T = pd.Timestamp(e["timestamp"], unit="s", tz="UTC").normalize()
        ins = oth = 0.0
        for a in e.get("cliffAllocations", []):
            amt = float(a.get("amount") or 0)
            cat, rec = str(a.get("category")), str(a.get("recipient"))
            if cat in ("insiders", "privateSale") or (cat == "Uncategorized" and INSIDER_RX.search(rec)):
                ins += amt
            elif cat != "burned":
                oth += amt
        before = circ[circ.index < T]
        c0 = float(before.iloc[-1]) if len(before) else 0.0
        if c0 <= 0:
            continue
        out.append({"T": T, "ins_size": ins / c0, "oth_size": oth / c0})
    return out


def main():
    p = pn.load_daily(start="2021-06-01", end="2026-10-31")
    close, ffwd = p["close"], p["funding_fwd"].fillna(0)
    adv = p["quote_volume"].rolling(30, min_periods=15).median()
    mask = pn.universe_mask(p)
    mret = close.pct_change().where(mask.shift(1, fill_value=False)).mean(1).fillna(0)
    mkt = (1 + mret).cumprod()
    rows = []
    for name, sym in mapping().items():
        if sym not in close.columns:
            continue
        last_kept = {}
        for e in sorted(events_for(name), key=lambda x: x["T"]):
            fam = ("INSIDER_BIG" if e["ins_size"] >= 0.01 else
                   "NONINSIDER_BIG" if e["oth_size"] >= 0.01 and e["ins_size"] == 0 else None)
            T = e["T"]
            if fam is None or T < DEV0 or T > END:
                continue
            if fam in last_kept and (T - last_kept[fam]).days < 44:
                continue
            a, z, b = T - pd.Timedelta(days=30), T - pd.Timedelta(days=1), T + pd.Timedelta(days=14)
            try:
                ca, cz, ct, cb = close.at[a, sym], close.at[z, sym], close.at[T, sym], close.at[b, sym]
                ma, mz, mt, mb = mkt.at[a], mkt.at[z], mkt.at[T], mkt.at[b]
            except KeyError:
                continue
            if not all(np.isfinite([ca, cz, ct, cb])) or not (adv.at[a, sym] >= 5e6):
                continue
            fund = float(ffwd.loc[a:b - pd.Timedelta(days=1), sym].sum())
            rows.append({"family": fam, "name": name, "sym": sym, "T": T, "size": e["ins_size"] if fam == "INSIDER_BIG" else e["oth_size"],
                         "net": -(cb / ca - 1 - (mb / ma - 1)) - COST + fund,
                         "pre": -(cz / ca - 1 - (mz / ma - 1)), "post": -(cb / ct - 1 - (mb / mt - 1)), "funding": fund})
            last_kept[fam] = T
    ev = pd.DataFrame(rows)
    ev.to_csv(ROOT / "data/research_cache/E47_unlock_events.csv", index=False)

    def st(x):
        if len(x) < 10:
            return {"n": len(x)}
        wk = x.groupby(x["T"].dt.to_period("W")).net.mean()
        return {"n": len(x), "mean_net": round(x.net.mean(), 4), "median_net": round(x.net.median(), 4),
                "t_week": round(wk.mean() / (wk.std(ddof=1) / np.sqrt(len(wk))), 2), "pos": round((x.net > 0).mean(), 3),
                "pre": round(x.pre.mean(), 4), "post": round(x.post.mean(), 4), "funding": round(x.funding.mean(), 4)}
    pd.set_option("display.width", 200)
    res = {}
    for fam in ("INSIDER_BIG", "NONINSIDER_BIG"):
        for win, m in (("DEV", ev["T"] < SPLIT), ("TEST", ev["T"] >= SPLIT)):
            x = ev[(ev.family == fam) & m]
            res[(fam, win)] = st(x)
            print(fam, win, res[(fam, win)])
            if fam == "INSIDER_BIG":
                for lo, hi in ((0.01, 0.03), (0.03, 0.10), (0.10, 10)):
                    y = x[(x["size"] >= lo) & (x["size"] < hi)]
                    print(f"   size {lo:.0%}-{hi:.0%}: n={len(y)} mean_net={y.net.mean():.4f}" if len(y) else f"   size {lo:.0%}+: n=0")
    d, t = res[("INSIDER_BIG", "DEV")], res[("INSIDER_BIG", "TEST")]
    ok = (d.get("mean_net", -1) >= 0.02 and d.get("t_week", 0) >= 2 and d.get("pos", 0) >= 0.55
          and t.get("mean_net", -1) > 0 and t.get("mean_net", -1) >= 0.5 * d["mean_net"])
    print("INSIDER_BIG", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
