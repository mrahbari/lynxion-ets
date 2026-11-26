"""E46 — Cash-and-carry: long spot + short USDT-M perp, collect funding (PRE-REGISTERED 2026-11-26).

Why: funding is the only robust return source found (E2-E4, E41), but carried through a long/short perp book it brings
price risk (E40: carry alone -78 %/yr on price in 2025-26). Cash-and-carry earns the same funding with (almost) no
price risk: P&L = funding received on the short perp + change of the perp-spot basis - trading costs.
Literature: Schmeling, Schrimpf & Todorov, "Crypto Carry" (BIS WP 1087); He, Manela et al., "Fundamentals of
Perpetual Futures".

Data: daily panel (lib.panel): funding_past / funding_fwd (real Binance funding), premium_close = last hourly premium
index of the day ((perp - index) / index), 30-day median quote volume. Spot leg approximated by the index (spot
composite). Universe: perps whose base asset has a Binance USDT spot pair today (survivorship approximation, stated).
Decision on row D (known at D), position earns D -> D+1:
  signal = trailing 7-day funding sum x 365/7 (annualised, positive = shorts are paid).
  ENTER when signal >= 20 %/yr and 30-day median volume >= $50M; EXIT when signal < 5 %/yr or volume < $25M.
  At most 10 names, equal notional; capital per position = notional x (1 + 1/3) (spot fully paid + perp margin at 3x).
  Daily P&L per position (fraction of notional): funding_fwd (short receives) - (premium_close[D+1] - premium_close[D]).
  Costs per side of a position change: spot taker 10 bp + perp taker 5 bp + 2 x 2 bp slippage = 19 bp of notional.
  Idle capital earns nothing (conservative).
Variants: CC_TOP (rule above); CC_MAJORS (BTC + ETH, always held, no switching).
Also reported: worst next-day high vs close while held (squeeze risk for the perp margin at 3x).
Windows: DEV 2020-01..2024-12, HOLDOUT 2025-01..2026-10 (funding history was studied before, the construction is new).
PASS (CC_TOP): net annual return on capital >= 8 % in BOTH windows (above ~5 % stablecoin yield with margin for
operations), HOLDOUT Sharpe >= 1.5 and HOLDOUT max drawdown >= -10 %.
Decision: PASS -> design a live version (needs a spot account; VST cannot hold spot) for an operator decision.
Usage: cd research/v2 && python experiments/e46_cash_and_carry.py
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

ROOT = Path(__file__).resolve().parents[3]
WINDOWS = {"DEV": ("2020-01-01", "2024-12-31"), "HOLDOUT": ("2025-01-01", "2026-10-31")}
ENTER, EXIT, MAXN, LEV = 0.20, 0.05, 10, 3.0
SIDE_COST = 0.0010 + 0.0005 + 2 * 0.0002


def spot_bases() -> set:
    d = json.loads(urllib.request.urlopen("https://api.binance.com/api/v3/exchangeInfo?permissions=SPOT", timeout=60).read())
    return {x["baseAsset"] for x in d["symbols"] if x["quoteAsset"] == "USDT"}


def simulate(p, cols, rule_top: bool):
    fpast = p["funding_past"][cols].fillna(0)
    sig = fpast.rolling(7, min_periods=7).sum() * 365 / 7
    adv = p["quote_volume"][cols].rolling(30, min_periods=20).median()
    ffwd = p["funding_fwd"][cols].fillna(0)
    prem = p["premium_close"][cols]
    dprem = prem.shift(-1) - prem
    idx = sig.index
    held: list = []
    rows = []
    for t in idx:
        if rule_top:
            s, a = sig.loc[t], adv.loc[t]
            held = [c for c in held if s.get(c, -1) >= EXIT and a.get(c, 0) >= 25e6 and np.isfinite(prem.at[t, c])]
            cand = s[(s >= ENTER) & (a >= 50e6) & prem.loc[t].notna()].drop(held, errors="ignore").sort_values(ascending=False)
            new = list(cand.index[:max(0, MAXN - len(held))])
        else:
            new = [c for c in cols if c not in held and np.isfinite(prem.at[t, c])]
        prev = set(held)
        held = held + new
        w = 1.0 / (MAXN if rule_top else len(cols)) / (1 + 1 / LEV)       # notional per position / capital
        exited = prev - set(held)
        cost = SIDE_COST * w * (len(new) + len(exited))
        fund = float(sum(ffwd.at[t, c] for c in held)) * w
        basis = float(-np.nansum([dprem.at[t, c] for c in held])) * w
        rows.append({"t": t, "fund": fund, "basis": basis, "cost": cost, "n": len(held), "net": fund + basis - cost,
                     "names": ",".join(held)})
    return pd.DataFrame(rows).set_index("t")


def summ(d):
    y = d.net.iloc[:-1]
    eq = (1 + y).cumprod()
    return {"ann_net": round(y.mean() * 365, 4), "sharpe": round(y.mean() / y.std() * np.sqrt(365), 2) if y.std() > 0 else np.nan,
            "max_dd": round(float((eq / eq.cummax() - 1).min()), 4), "funding": round(d.fund.mean() * 365, 4),
            "basis": round(d.basis.mean() * 365, 4), "cost": round(d.cost.mean() * 365, 4),
            "avg_names": round(d.n.mean(), 1), "days_invested": round(float((d.n > 0).mean()), 3)}


def squeeze(d, p, a, b):
    """Daily squeeze risk of the short perp leg: next-day high / today's close - 1 for every held position-day."""
    up = (p["high"].shift(-1) / p["close"] - 1)
    x = [up.at[t, c] for t, names in d.loc[a:b, "names"].items() for c in filter(None, names.split(","))
         if c in up.columns and np.isfinite(up.at[t, c])]
    x = np.array(x)
    return {"pos_days": len(x), "worst_up": round(float(x.max()), 3) if len(x) else np.nan,
            "share_up_gt_20pct": round(float((x > 0.20).mean()), 4) if len(x) else np.nan}


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    bases = spot_bases()
    cols = [c for c in p["close"].columns if c.endswith("USDT") and c[:-4] in bases]
    res = []
    for name, rule_top, cc in (("CC_TOP", True, cols), ("CC_MAJORS", False, ["BTCUSDT", "ETHUSDT"])):
        d = simulate(p, cc, rule_top)
        d.to_csv(ROOT / f"data/research_cache/E46_{name}_daily.csv")
        for win, (a, b) in WINDOWS.items():
            res.append({"variant": name, "window": win, **summ(d.loc[a:b]), **squeeze(d, p, a, b)})
    r = pd.DataFrame(res)
    pd.set_option("display.width", 200)
    print(f"universe with spot: {len(cols)}")
    print(r.to_string(index=False))
    r.to_csv(ROOT / "docs/v2/reports/E46_cash_and_carry.csv", index=False)
    g = r.set_index(["variant", "window"])
    ok = (g.loc[("CC_TOP", "DEV"), "ann_net"] >= 0.08 and g.loc[("CC_TOP", "HOLDOUT"), "ann_net"] >= 0.08
          and g.loc[("CC_TOP", "HOLDOUT"), "sharpe"] >= 1.5 and g.loc[("CC_TOP", "HOLDOUT"), "max_dd"] >= -0.10)
    print("CC_TOP", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
