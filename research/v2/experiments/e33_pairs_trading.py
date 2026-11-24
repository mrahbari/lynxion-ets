"""E33 — statistical-arbitrage pairs on liquid perps (operator link: orangepineapple/mean_reversion_strategies,
after E. P. Chan, "Algorithmic Trading", 2013) (2026-11-24).

Not tested before here or by Codex (C-01..C-35). Perps allow both legs natively.
Pre-registered (committed before any run). Textbook values, no search.
  Data: Binance USDT-M 1h -> UTC daily closes + funding (data/research_cache/e23); 10 liquid perps
    (BTC ETH SOL XRP DOGE AVAX LINK SUI ADA LTC) -> all 45 pairs, each from when both have >= 120 days of history.
  Hedge ratio: rolling OLS of log(A) on log(B) over the previous 60 days (no look-ahead; Chan's rolling regression).
  Spread s = log A - beta log B - alpha; z = (s - mean_20) / std_20 of the spread over the previous 20 days.
  Entry: z <= -2 -> long A / short beta B; z >= +2 -> short A / long beta B (decided at day t close, filled
    at day t close + 1 day's return accrual, i.e. held from t to t+1 onward).
  Exit: |z| <= 0.5, or |z| >= 4 (divergence stop), or 20 days held.
  Sizing: each open pair = 1 unit gross (A leg 1/(1+|beta|), B leg |beta|/(1+|beta|)); portfolio return = mean over
    open pairs (equal weight), zero when none open.
  Costs: 10 bp per unit of turnover per leg traded (fee + slippage); real funding on each leg.
  DEV 2020-01-01..2024-12-31; HOLDOUT 2025-01-01..2026-10-31 (read once).
  PASS: net Sharpe >= 0.75 on DEV and > 0.4 on HOLDOUT, both 2025 and 2026 positive; >= 100 trades on DEV.
  Decision: PASS -> build as a market-neutral daily sleeve (shadow first).
Usage: python research/v2/experiments/e33_pairs_trading.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e23_funding_extreme as e23  # noqa: E402
from e29_daily_trend_ensemble import daily, SYMS  # noqa: E402

COST = 0.0010
WINDOWS = {"DEV": ("2020-01-01", "2024-12-31"), "HOLDOUT": ("2025-01-01", "2026-10-31")}


def pair_returns(a, b, C, F):
    la, lb = np.log(C[a]), np.log(C[b])
    ok = la.notna() & lb.notna()
    la, lb = la[ok], lb[ok]
    if len(la) < 200:
        return None, 0
    ra, rb = C[a][ok].pct_change().fillna(0), C[b][ok].pct_change().fillna(0)
    fa, fb = F[a].reindex(la.index).fillna(0), F[b].reindex(la.index).fillna(0)
    cov = la.rolling(60).cov(lb).shift(1)
    var = lb.rolling(60).var().shift(1)
    beta = cov / var
    alpha = (la.rolling(60).mean() - beta * lb.rolling(60).mean().shift(0)).shift(0)
    alpha = la.rolling(60).mean().shift(1) - beta * lb.rolling(60).mean().shift(1)
    s = la - beta * lb - alpha
    z = (s - s.rolling(20).mean().shift(1)) / s.rolling(20).std().shift(1)
    pos, held, b_pos = 0, 0, 0.0
    out, trades = [], 0
    for i, t in enumerate(la.index):
        r = 0.0
        if pos != 0:                                   # position decided yesterday, earns today
            wa, wb = 1 / (1 + abs(b_pos)), abs(b_pos) / (1 + abs(b_pos))
            sb = np.sign(b_pos) if b_pos != 0 else 1
            r = pos * (wa * ra.iloc[i] - sb * wb * rb.iloc[i]) - pos * (wa * fa.iloc[i] - sb * wb * fb.iloc[i])
            held += 1
        zi, bi = z.iloc[i], beta.iloc[i]
        new = pos
        if pos == 0 and np.isfinite(zi) and np.isfinite(bi) and abs(bi) < 5:
            if zi <= -2:
                new = 1
            elif zi >= 2:
                new = -1
        elif pos != 0 and (not np.isfinite(zi) or abs(zi) <= 0.5 or abs(zi) >= 4 or held >= 20):
            new = 0
        if new != pos:
            r -= COST * (1 if pos == 0 or new == 0 else 2)   # one unit gross per open or close
            if new != 0:
                b_pos, held, trades = bi, 0, trades + 1
            pos = new
        out.append((t, r, 1 if pos != 0 or r != 0 else 0))
    df = pd.DataFrame(out, columns=["t", "r", "open"]).set_index("t")
    return df, trades


def main():
    C, F = {}, {}
    for s in SYMS:
        C[s], F[s] = daily(s)
    C, F = pd.DataFrame(C).sort_index(), pd.DataFrame(F).sort_index()
    rets, opens, ntr = [], [], {}
    for a, b in itertools.combinations(SYMS, 2):
        df, n = pair_returns(a, b, C, F)
        if df is None:
            continue
        rets.append(df.r.rename(f"{a}/{b}"))
        opens.append(df.open.rename(f"{a}/{b}"))
        ntr[f"{a}/{b}"] = df
    R, O = pd.concat(rets, axis=1).fillna(0), pd.concat(opens, axis=1).fillna(0)
    port = R.sum(axis=1) / O.sum(axis=1).replace(0, np.nan)
    port = port.fillna(0.0)
    rows = []
    for win, (a, b) in WINDOWS.items():
        m = (port.index >= pd.Timestamp(a, tz="UTC")) & (port.index <= pd.Timestamp(b, tz="UTC"))
        y = port[m]
        n_tr = sum(int(((df.index >= pd.Timestamp(a, tz="UTC")) & (df.index <= pd.Timestamp(b, tz="UTC")) & (df.open.diff() > 0)).sum()) for df in ntr.values())
        eq = (1 + y).cumprod()
        rows.append({"window": win, "net_sharpe": round(y.mean() / y.std() * np.sqrt(365), 2) if y.std() > 0 else 0,
                     "ann_ret": round(y.mean() * 365, 3), "max_dd": round((eq / eq.cummax() - 1).min(), 3),
                     "trades": n_tr, "pct_days_invested": round(float((O[m].sum(axis=1) > 0).mean()), 2),
                     "by_year": {str(k): round(g.mean() / g.std() * np.sqrt(365), 2) if g.std() > 0 else 0 for k, g in y.groupby(y.index.year)}})
    t = pd.DataFrame(rows)
    t.to_csv(e23.OUT / "E33_pairs_trading.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print(t.to_string(index=False))
    g = t.set_index("window")
    ok = (g.loc["DEV", "net_sharpe"] >= 0.75 and g.loc["HOLDOUT", "net_sharpe"] > 0.4 and g.loc["DEV", "trades"] >= 100
          and all(v > 0 for v in g.loc["HOLDOUT", "by_year"].values()))
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
