"""E52 — H4 stablecoin-supply impulse and crypto beta (PRE-REGISTERED 2026-11-26).

Mechanism: net issuance of USD stablecoins is new dollar liquidity that mostly enters through exchanges (Griffin &
Shams 2020 on Tether; later evidence mixed). A directional sleeve would diversify the market-neutral F1.
Data: DefiLlama total USD-pegged stablecoin circulating supply (daily, free); market = equal-weight basket of the
V1 live-like universe (daily lake closes) with its funding.
Rule (fixed): every 7 days from the window start, z = (7-day % change of supply - mean) / std, mean/std over the
previous 365 days (causal). If z > 1: long the basket for the next 7 days, else flat.
Costs: 0.14 % of capital per switch (fee + slippage both ways averaged); funding paid while long (basket mean).
Benchmarks: ALWAYS (always long, same costs) and MOM (long when the basket's 28-day return > 0; same schedule/costs).
Windows: DEV 2020-06-01..2024-12-31; TEST 2025-01-01..2026-10-31 (read once).
PASS: H4 Sharpe > ALWAYS Sharpe and > MOM Sharpe in BOTH windows. Otherwise reject (low power stated: ~95 weekly
decisions in TEST).
Usage: cd research/v2 && python experiments/e52_stablecoin_impulse.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "lake" / "stablecoins_total_daily.parquet"
P = S.PARAMS
DEV = ("2020-06-01", "2024-12-31")
TEST = ("2025-01-01", "2026-10-31")
SWITCH = 0.0014


def supply() -> pd.Series:
    if not CACHE.exists():
        d = json.loads(urllib.request.urlopen("https://stablecoins.llama.fi/stablecoincharts/all", timeout=60).read())
        df = pd.DataFrame({"t": [int(x["date"]) for x in d],
                           "usd": [float((x.get("totalCirculatingUSD") or {}).get("peggedUSD") or 0) for x in d]})
        df.to_parquet(CACHE, index=False)
    df = pd.read_parquet(CACHE)
    return pd.Series(df.usd.to_numpy(), index=pd.to_datetime(df.t, unit="s", utc=True)).sort_index()


def stats(y):
    eq = (1 + y).cumprod()
    return {"ann": round(y.mean() * 365, 4), "sharpe": round(y.mean() / y.std() * np.sqrt(365), 3) if y.std() > 0 else np.nan,
            "mdd": round(float((eq / eq.cummax() - 1).min()), 4), "exposure": round(float((y != 0).mean()), 3)}


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    mret = fr.where(mask).mean(1) - p["funding_fwd"].where(mask).mean(1).fillna(0)   # long basket pays funding
    lvl = (1 + fr.where(mask).mean(1).fillna(0)).cumprod()
    sup = supply().reindex(mret.index).ffill()
    g7 = sup.pct_change(7)
    z = (g7 - g7.rolling(365, min_periods=200).mean()) / g7.rolling(365, min_periods=200).std()
    mom = lvl / lvl.shift(28) - 1
    out = {}
    for name, (a, b) in (("DEV", DEV), ("TEST", TEST)):
        idx = mret.loc[a:b].index
        dec = idx[::7]
        pos = {k: pd.Series(0.0, index=idx) for k in ("H4", "ALWAYS", "MOM")}
        for d in dec:
            span = idx[(idx >= d) & (idx < d + pd.Timedelta(days=7))]
            pos["H4"].loc[span] = 1.0 if z.get(d, np.nan) > 1 else 0.0
            pos["ALWAYS"].loc[span] = 1.0
            pos["MOM"].loc[span] = 1.0 if mom.get(d, np.nan) > 0 else 0.0
        res = {}
        for k, ps in pos.items():
            sw = ps.diff().abs().fillna(ps.iloc[0])
            y = ps * mret.loc[idx].fillna(0) - sw * SWITCH
            res[k] = stats(y)
        out[name] = res
        print(name, res)
    ok = all(out[w]["H4"]["sharpe"] > max(out[w]["ALWAYS"]["sharpe"], out[w]["MOM"]["sharpe"]) for w in out)
    print("E52", "PASS" if ok else "REJECT")


if __name__ == "__main__":
    main()
