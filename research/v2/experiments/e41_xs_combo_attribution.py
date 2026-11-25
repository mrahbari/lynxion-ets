"""E41 — XS-COMBO-V1 performance attribution (PRE-REGISTERED, 2026-11-25). Evidence only; no strategy change.

Question: what actually drives XS-COMBO-V1 returns — cross-sectional selection, market exposure, structural funding,
a size tilt, or the interaction of its three factors?

Books (frozen V1 definitions, live-like universe, 20 %/20 %, gross 1, weekly, lib.backtest cost model, funding, drift):
  D  = V1 (carry + illiq + taker, rank-sum)          A = carry only     I = illiq only     T = taker only
  EQ3 = equal mix of the A, I and T target books, rescaled to gross 1 at each rebalance (diversification only, no
        signal interaction)
  SZ = size reference: long the 20 % smallest / short the 20 % largest names by 30-day median dollar volume
       (to see whether "illiquidity" is a size premium). Not a candidate strategy.
All 7 weekly rebalance phases, results averaged over phases (no phase selected).
Windows: DEV 2020-01..2024-12, HOLDOUT_USED 2025-01..2026-10 — both EXPLORATORY (D was designed on DEV; the holdout has
been read several times). Attribution is descriptive; only the predefined tests below carry p-values.

Decomposition per book and day (target weights t, forward return r, funding f):
  price  = sum t*r, split into long leg / short leg;  funding = -sum t*f, split by leg;  cost = model cost
  market = book beta x equal-weight universe forward return (name beta: 60-day rolling, known at D)
  selection = price - market
  size tilt = sum t * cross-sectional z(log ADV)  (negative = small-cap tilt)
  BTC beta of daily net (whole window); overlap: mean Jaccard of long/short name sets of A, I, T books on rebalance days.
Predefined tests (Holm over 8 = 4 x 2 windows; t on non-overlapping weekly sums of the phase-averaged daily series):
  T1 integration gain   D - EQ3 net > 0
  T2 market component   mean(market) of D != 0
  T3 selection          mean(selection) of D > 0
  T4 funding            mean(funding) of D > 0
Survivorship: the Binance lake includes delisted symbols; delisting closes at the last price (lib.panel). BingX
  availability is not modelled here (E2: BingX-only SR 0.96 vs 1.39) — stated as a limitation, not re-run.
Usage: cd research/v2 && python experiments/e41_xs_combo_attribution.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
P = S.PARAMS
WINDOWS = {"DEV": ("2020-01-01", "2024-12-31"), "HOLDOUT_USED": ("2025-01-01", "2026-10-31")}


def run_detail(W, R, F, adv, vol, beta, mkt, z_size, rebalance_every=7, cost=bt.CostModel()):
    """lib.backtest.run loop (identical arithmetic) that also returns the per-day attribution."""
    n, m = W.shape
    out = {k: np.zeros(n) for k in ("net", "price_long", "price_short", "fund_long", "fund_short", "cost", "turnover",
                                    "gross", "net_exp", "beta", "market", "size_tilt")}
    held = np.zeros(m)
    for t in range(n):
        target = W[t] if t % rebalance_every == 0 else held
        r = R[t]
        bad = ~np.isfinite(r)
        target = np.where(bad, 0.0, target)
        dw = np.abs(target - held)
        a = np.where(np.isfinite(adv[t]) & (adv[t] > 0), adv[t], 1e6)
        s = np.where(np.isfinite(vol[t]), vol[t], 0.05)
        unit = cost.fee + cost.half_spread(a) + cost.impact_y * s * np.sqrt(dw * cost.capital / a)
        c = float(np.sum(dw * unit)) * cost.cost_mult
        r0 = np.where(bad, 0.0, r)
        L, Sh = target > 0, target < 0
        pl, ps = float(np.sum(target[L] * r0[L])), float(np.sum(target[Sh] * r0[Sh]))
        fl, fs = -float(np.sum(target[L] * F[t][L])), -float(np.sum(target[Sh] * F[t][Sh]))
        g, f = pl + ps, fl + fs
        b = float(np.nansum(target * np.where(np.isfinite(beta[t]), beta[t], 1.0)))
        out["net"][t] = g + f - c
        out["price_long"][t], out["price_short"][t], out["fund_long"][t], out["fund_short"][t] = pl, ps, fl, fs
        out["cost"][t], out["turnover"][t], out["gross"][t] = c, float(dw.sum()), float(np.abs(target).sum())
        out["net_exp"][t], out["beta"][t] = float(target.sum()), b
        out["market"][t] = b * (mkt[t] if np.isfinite(mkt[t]) else 0.0)
        out["size_tilt"][t] = float(np.nansum(target * np.where(np.isfinite(z_size[t]), z_size[t], 0.0)))
        denom = 1.0 + g + f - c
        held = target * (1.0 + r0) / denom if denom > 0 else np.zeros(m)
    return out


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else np.nan


def ttest(x):
    wk = x.groupby(np.arange(len(x)) // 7).sum()
    tv = wk.mean() / (wk.std(ddof=1) / np.sqrt(len(wk)))
    return float(tv), float(2 * tdist.sf(abs(tv), len(wk) - 1))


def holm(p):
    p = np.asarray(p, float)
    order, m, adj, run = np.argsort(p), len(p), np.empty(len(p)), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * p[i]))
        adj[i] = run
    return adj


def main():
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    lr = np.log(p["close"]).diff()
    qv = p["quote_volume"]
    carry = S._rk(-p["funding_past"].rolling(P["funding_window"], min_periods=1).sum(), mask)
    illiq = S._rk((lr.abs() / qv).rolling(P["illiq_window"], min_periods=20).mean(), mask)
    taker = S._rk((p["taker_buy_quote"] / qv - 0.5).rolling(P["taker_window"], min_periods=4).mean(), mask)
    adv = qv.rolling(30, min_periods=10).median()
    rk = lambda s: bt.rank_long_short(s, mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])  # noqa: E731
    books = {"D": rk(carry + illiq + taker), "A": rk(carry), "I": rk(illiq), "T": rk(taker), "SZ": rk(-np.log(adv))}
    assert np.allclose(books["D"].values, rk(S.signal(p, mask)).values)
    eq = (books["A"] + books["I"] + books["T"]) / 3
    books["EQ3"] = eq.div(eq.abs().sum(1).replace(0, np.nan), axis=0).fillna(0.0)

    idx, cols = books["D"].index, books["D"].columns
    frm = fr.reindex(index=idx, columns=cols)
    mkt = frm.where(mask.reindex(index=idx, columns=cols)).mean(1)
    beta = (frm.rolling(60, min_periods=30).cov(mkt) .div(mkt.rolling(60, min_periods=30).var(), axis=0)).shift(1)
    la = np.log(adv.reindex(index=idx, columns=cols)).where(mask.reindex(index=idx, columns=cols))
    z = la.sub(la.mean(1), axis=0).div(la.std(1), axis=0)
    F = p["funding_fwd"].reindex(index=idx, columns=cols).fillna(0.0)
    A = adv.reindex(index=idx, columns=cols)
    V = lr.rolling(30, min_periods=10).std().reindex(index=idx, columns=cols)
    btc = frm["BTCUSDT"]

    rows, tests, daily = [], [], {}
    for win, (a0, b0) in WINDOWS.items():
        for name, w in books.items():
            parts = []
            for k in range(7):
                a = pd.Timestamp(a0, tz="UTC") + pd.Timedelta(days=k)
                sel = (idx >= a) & (idx <= pd.Timestamp(b0, tz="UTC"))
                o = run_detail(w.values[sel], frm.values[sel], F.values[sel], A.values[sel], V.values[sel],
                               beta.values[sel], mkt.values[sel], z.values[sel], P["rebalance_every"])
                if name == "D" and k == 0 and win == "DEV":     # mechanics check: identical to lib.backtest.run
                    ref = bt.run(w[sel], fr.reindex(idx[sel]), p, bt.CostModel(), rebalance_every=P["rebalance_every"])
                    assert np.allclose(ref.net.values, o["net"], atol=1e-12)
                parts.append(pd.DataFrame(o, index=idx[sel]).iloc[:-1])
            d = pd.concat(parts).groupby(level=0).mean()          # phase-averaged daily attribution
            daily[(win, name)] = d
            price = d.price_long + d.price_short
            eqc = (1 + d.net).cumprod()
            b_btc = float(np.cov(d.net, btc.reindex(d.index).fillna(0))[0, 1] / btc.reindex(d.index).var())
            rows.append({"window": win, "book": name, "net": d.net.mean() * 365, "sharpe": d.net.mean() / d.net.std() * np.sqrt(365),
                         "price": price.mean() * 365, "price_long": d.price_long.mean() * 365,
                         "price_short": d.price_short.mean() * 365, "market": d.market.mean() * 365,
                         "selection": (price - d.market).mean() * 365, "funding": (d.fund_long + d.fund_short).mean() * 365,
                         "fund_long": d.fund_long.mean() * 365, "fund_short": d.fund_short.mean() * 365,
                         "cost": d.cost.mean() * 365, "turnover": d.turnover.mean() * 365, "gross": d.gross.mean(),
                         "net_exp": d.net_exp.mean(), "book_beta": d.beta.mean(), "btc_beta": b_btc,
                         "size_tilt": d.size_tilt.mean(), "mdd": float((eqc / eqc.cummax() - 1).min())})
        D, E = daily[(win, "D")], daily[(win, "EQ3")]
        Dp = D.price_long + D.price_short
        for tname, x in (("T1_integration_D_minus_EQ3", D.net - E.net.reindex(D.index)), ("T2_market_component", D.market),
                         ("T3_selection", Dp - D.market), ("T4_funding", D.fund_long + D.fund_short)):
            tv, pv = ttest(x.dropna())
            tests.append({"window": win, "test": tname, "mean_ann": round(float(x.mean() * 365), 4), "t_weekly": round(tv, 2), "p": pv})
        # name overlap of the single-factor books on rebalance days (phase 0)
        reb = idx[(idx >= a0) & (idx <= b0)][::7]
        for x, y in (("A", "I"), ("A", "T"), ("I", "T"), ("D", "A")):
            jl = np.nanmean([jaccard(books[x].loc[d][books[x].loc[d] > 0].index, books[y].loc[d][books[y].loc[d] > 0].index) for d in reb])
            js = np.nanmean([jaccard(books[x].loc[d][books[x].loc[d] < 0].index, books[y].loc[d][books[y].loc[d] < 0].index) for d in reb])
            tests.append({"window": win, "test": f"overlap_{x}_{y}", "mean_ann": None, "jaccard_long": round(jl, 3), "jaccard_short": round(js, 3)})
        nets = pd.DataFrame({k: daily[(win, k)].net for k in ("A", "I", "T", "SZ")})
        cm = nets.corr().round(2)
        print(win, "daily net correlation of standalone books\n", cm.to_string())
        Xr = np.column_stack([np.ones(len(nets)), nets[["A", "I", "T", "SZ"]].values])
        coef, *_ = np.linalg.lstsq(Xr, D.net.reindex(nets.index).values, rcond=None)
        resid = D.net.reindex(nets.index).values - Xr @ coef
        tests.append({"window": win, "test": "regress_D_on_A_I_T_SZ", "mean_ann": round(float(coef[0] * 365), 4),
                      "coef_A_I_T_SZ": [round(float(c), 2) for c in coef[1:]],
                      "r2": round(float(1 - resid.var() / D.net.var()), 3)})
    res = pd.DataFrame(rows).round(4)
    t = pd.DataFrame(tests)
    m = t.p.notna()
    t.loc[m, "p_holm"] = holm(t.loc[m, "p"]).round(4)
    res.to_csv(ROOT / "docs/v2/reports/E41_attribution_books.csv", index=False)
    t.to_csv(ROOT / "docs/v2/reports/E41_attribution_tests.csv", index=False)
    pd.set_option("display.width", 260)
    print(res.to_string(index=False))
    print(t.drop(columns="p").to_string(index=False))


if __name__ == "__main__":
    main()
