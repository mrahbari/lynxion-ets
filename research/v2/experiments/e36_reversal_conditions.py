"""E36 — When do reversals happen? Event study of reversal vs continuation (operator research brief, 2026-11-25).

Why: E34/E35 (and E9-E28) failed. This is NOT a strategy test. It asks under which observable conditions a
price event is followed by reversal rather than continuation, net of costs, before any strategy is designed.
Pre-registered (committed before any run). Thresholds are textbook values or DEV-bar quantiles (computed from
features only, never from outcomes). No parameter search.

Data: Binance USDT-M 1h klines WITH volume and taker-buy volume (new cache data/research_cache/e36), aggregated to
  4h bars (UTC 00/04/...); real funding (data/research_cache/e23). Universe BTC ETH SOL XRP DOGE AVAX LINK SUI ADA LTC.
  DEV 2020-01-01..2024-12-31; HOLDOUT 2025-01-01..2026-10-31 (read once, only for families that pass DEV).
Outcome for an event at the CLOSE of 4h bar i with reversal direction d (+1 long, -1 short):
  entry = open of bar i+1 (+2 bp slippage), exit = close of bar i+6 (24 h hold, PRIMARY; -2 bp slippage);
  net = d * return - 2 x 5 bp fee - d * funding paid over the hold. No stops (we measure the conditional
  distribution, not a trading rule). Reported too: 4h/12h/72h gross, MFE/MAE in ATR units.
  Non-overlap: after an event, same family + symbol ignored for 6 bars.
Event families (all causal, bar i closed):
  F1 STRETCH   close beyond SMA20 +/- 2 std20; d = against the stretch (the E35 base).
  F2 WICK      high (low) beyond the band but close back inside; d = against the wick.
  F3 REENTRY   bar i-1 closed beyond the band, bar i closes back inside; d = toward SMA.
  F4 SWEEP     high > max(high[i-20..i-1]) and close < that level (liquidity sweep + reclaim); d = -1. Mirror.
  F5 FAILBRK   close[i-1] > max(high[i-21..i-2]) (breakout) and close[i] < that level; d = -1. Mirror.
  F6 ABSORB    volume >= 2 x mean volume(30), |close-open| <= 0.3 ATR14, taker-buy share >= DEV 80th pct -> d=-1
               (aggressive buyers absorbed); <= DEV 20th pct -> d=+1.
  F7 CVDDIV    close = 20-bar closing high and sum of taker delta (2*takerbuy - volume) over 20 bars < 0 -> d=-1.
               Mirror (closing low, delta > 0 -> d=+1).
  F8 CAPIT     range >= 3 x ATR14 and volume >= 3 x mean volume(30) (liquidation-cascade proxy);
               d = -sign(close - open).
Conditions (each applied to every family; feature at bar i):
  C0 ALL; C1 RANGE ADX14 < 20; C2 LOWER efficiency ratio(20) < DEV 33rd pct; C3 WITH_HTF d equals the sign of
  (close - EMA300) (pullback within the ~50-day trend); C4 CONTRACT ATR14/ATR100 < 0.9; C5 FIRST no same-family,
  same-direction event in the previous 6 bars (computed before the non-overlap filter).
Statistics: per-day clustering (mean net per event day, t on day means); excess = net minus the mean net of ALL
  bars in the same symbol/direction/window (drift control). 8 x 6 = 48 DEV tests, Holm at alpha 0.05.
PASS (DEV): net mean >= +15 bp, Holm-significant, excess > 0, n >= 150, >= 6/10 symbols positive, both DEV halves
  (2020-22, 2023-24) positive. HOLDOUT (read once for DEV passers): net > 0, >= 50 % of DEV, >= 5/10 symbols positive.
Decision: a cell that passes both -> design a strategy (E37) on exactly that condition. None -> reversal-family
  hypothesis rejected on this data; research moves on. Diagnostics H1-H4 (regime / timing / signal / exit) are
  read off the F1 rows and MFE/MAE and reported regardless.
Limits: no liquidation or order-book history is available (Binance stopped liquidation snapshots; OBI only live);
  F6-F8 use taker-volume and range/volume proxies. OI was tested in E20/E24 (fail).
Usage: python research/v2/experiments/e36_reversal_conditions.py [--holdout]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e23_funding_extreme as e23  # noqa: E402

CACHE = e23.ROOT / "data" / "research_cache" / "e36"
SYMS = e23.SYMBOLS
H4 = 4 * 3_600_000
FEE, SLIP, HOLD = 0.0005, 0.0002, 6
DEV0, HOLD0, END = e23.DEV0, e23.HOLD0, e23.END
SPLIT = int(pd.Timestamp("2023-01-01", tz="UTC").timestamp() * 1000)
FAMILIES = ["F1_STRETCH", "F2_WICK", "F3_REENTRY", "F4_SWEEP", "F5_FAILBRK", "F6_ABSORB", "F7_CVDDIV", "F8_CAPIT"]
CONDS = ["C0_ALL", "C1_RANGE", "C2_LOWER", "C3_WITH_HTF", "C4_CONTRACT", "C5_FIRST"]


def klines_flow(sym):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{sym}_1h.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows, t = [], e23.T0
    while t < END:
        b = e23._get(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1h&startTime={t}&limit=1500")
        if not b:
            break
        rows += b
        t = b[-1][0] + 3_600_000
        time.sleep(0.1)
    d = pd.DataFrame(rows).iloc[:, [0, 1, 2, 3, 4, 5, 9]]
    d.columns = ["t", "o", "h", "l", "c", "v", "tb"]
    d = d.astype({"t": "int64", "o": float, "h": float, "l": float, "c": float, "v": float, "tb": float})
    d = d.drop_duplicates("t")
    d = d[d.t < END].reset_index(drop=True)
    d.to_parquet(f)
    return d


def adx(h, l, c, n=14):
    up, dn = h.diff(), -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum(h - l, np.maximum((h - c.shift()).abs(), (l - c.shift()).abs()))
    a = 1.0 / n
    atr = tr.ewm(alpha=a, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=h.index).ewm(alpha=a, adjust=False).mean() / atr
    mdi = 100 * pd.Series(mdm, index=h.index).ewm(alpha=a, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=a, adjust=False).mean()


def bars4(sym):
    k = klines_flow(sym)
    k["b"] = k.t // H4
    g = k.groupby("b").agg(t=("t", "first"), o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                           v=("v", "sum"), tb=("tb", "sum"), n=("c", "size"))
    g = g[g.n == 4].reset_index(drop=True)
    g["sma"], g["sd"] = g.c.rolling(20).mean(), g.c.rolling(20).std()
    g["up"], g["lo"] = g.sma + 2 * g.sd, g.sma - 2 * g.sd
    tr = np.maximum(g.h - g.l, np.maximum((g.h - g.c.shift()).abs(), (g.l - g.c.shift()).abs()))
    g["atr"], g["atr100"] = tr.rolling(14).mean(), tr.rolling(100).mean()
    g["adx"] = adx(g.h, g.l, g.c)
    g["er"] = (g.c - g.c.shift(20)).abs() / g.c.diff().abs().rolling(20).sum()
    g["ema300"] = g.c.ewm(span=300, adjust=False).mean()
    g["vratio"] = g.v / g.v.shift(1).rolling(30).mean()
    g["tbr"] = g.tb / g.v.replace(0, np.nan)
    g["delta20"] = (2 * g.tb - g.v).rolling(20).sum()
    return g


def funding_paid(fr, t_in, t_out):
    ft, fv = fr.fundingTime.to_numpy(), fr.fundingRate.to_numpy()
    return fv[(ft > t_in) & (ft <= t_out)].sum()


def events(g, q):
    """Raw (pre non-overlap) events: dict family -> array of directions per bar (0 = none)."""
    c, o, h, l = g.c, g.o, g.h, g.l
    n = len(g)
    ev = {}
    ev["F1_STRETCH"] = np.where(c < g.lo, 1, np.where(c > g.up, -1, 0))
    ev["F2_WICK"] = np.where((l < g.lo) & (c >= g.lo), 1, np.where((h > g.up) & (c <= g.up), -1, 0))
    ev["F3_REENTRY"] = np.where((c.shift() < g.lo.shift()) & (c >= g.lo), 1,
                                np.where((c.shift() > g.up.shift()) & (c <= g.up), -1, 0))
    hh, ll = h.shift(1).rolling(20).max(), l.shift(1).rolling(20).min()
    ev["F4_SWEEP"] = np.where((h > hh) & (c < hh), -1, np.where((l < ll) & (c > ll), 1, 0))
    hb, lb = h.shift(2).rolling(20).max(), l.shift(2).rolling(20).min()
    ev["F5_FAILBRK"] = np.where((c.shift() > hb) & (c < hb), -1, np.where((c.shift() < lb) & (c > lb), 1, 0))
    quiet = (g.vratio >= 2) & ((c - o).abs() <= 0.3 * g.atr)
    ev["F6_ABSORB"] = np.where(quiet & (g.tbr >= q["tbr80"]), -1, np.where(quiet & (g.tbr <= q["tbr20"]), 1, 0))
    chi, clo = c.shift(1).rolling(19).max(), c.shift(1).rolling(19).min()
    ev["F7_CVDDIV"] = np.where((c >= chi) & (g.delta20 < 0), -1, np.where((c <= clo) & (g.delta20 > 0), 1, 0))
    cap = ((h - l) >= 3 * g.atr.shift()) & (g.vratio >= 3)
    ev["F8_CAPIT"] = np.where(cap, -np.sign(c - o), 0).astype(int)
    for k in ev:
        ev[k] = np.asarray(ev[k], dtype=int)
        ev[k][:300] = 0                      # warm-up (EMA300, ATR100)
        assert len(ev[k]) == n
    return ev


def outcomes(sym, q):
    g = bars4(sym)
    fr = e23.funding(sym).sort_values("fundingTime")
    t, o, h, l, c, atr = (g[x].to_numpy() for x in ("t", "o", "h", "l", "c", "atr"))
    n = len(g)
    ev = events(g, q)
    htf = np.sign(g.c - g.ema300).to_numpy()
    cond_base = {"C1_RANGE": (g.adx < 20).to_numpy(), "C2_LOWER": (g.er < q["er33"]).to_numpy(),
                 "C4_CONTRACT": (g.atr / g.atr100 < 0.9).to_numpy()}
    rows = []
    # drift control: every bar, both directions
    base = []
    for i in range(300, n - HOLD - 1):
        e, x = i + 1, i + HOLD
        base.append((t[i], (c[x] * (1 - SLIP)) / (o[e] * (1 + SLIP)) - 1, (c[x] * (1 + SLIP)) / (o[e] * (1 - SLIP)) - 1,
                     funding_paid(fr, t[e], t[x] + H4)))
    b = pd.DataFrame(base, columns=["t", "rl", "rs", "fp"])
    b["net_long"] = b.rl - 2 * FEE - b.fp
    b["net_short"] = -b.rs - 2 * FEE + b.fp
    b["symbol"] = sym
    for fam, dirs in ev.items():
        nz = np.flatnonzero(dirs)
        first = np.ones(n, bool)
        for i in nz:
            prev = dirs[max(0, i - 6):i]
            first[i] = not (prev == dirs[i]).any()
        last = -10
        for i in nz:
            if i - last < HOLD or i + HOLD >= n or not np.isfinite(atr[i]):
                continue
            last = i
            d = dirs[i]
            e, x = i + 1, i + HOLD
            entry = o[e] * (1 + d * SLIP)
            fp = funding_paid(fr, t[e], t[x] + H4)
            gross = d * ((c[x] * (1 - d * SLIP)) / entry - 1)
            seg_h, seg_l = h[e:x + 1].max(), l[e:x + 1].min()
            mfe = (seg_h - entry) / atr[i] if d > 0 else (entry - seg_l) / atr[i]
            mae = (entry - seg_l) / atr[i] if d > 0 else (seg_h - entry) / atr[i]
            g_k = {f"gross_{k * 4}h": d * (c[min(i + k, n - 1)] / entry - 1) for k in (1, 3, 18)}
            rows.append({"symbol": sym, "family": fam, "t": int(t[i]), "d": d, "gross": gross,
                         "net": gross - 2 * FEE - d * fp, "mfe_atr": mfe, "mae_atr": mae,
                         "C1_RANGE": bool(cond_base["C1_RANGE"][i]), "C2_LOWER": bool(cond_base["C2_LOWER"][i]),
                         "C3_WITH_HTF": bool(htf[i] == d), "C4_CONTRACT": bool(cond_base["C4_CONTRACT"][i]),
                         "C5_FIRST": bool(first[i]), "touch_sma": bool(
                             (d > 0 and seg_h >= g.sma.iat[i]) or (d < 0 and seg_l <= g.sma.iat[i])), **g_k})
    return pd.DataFrame(rows), b


def dev_quantiles():
    tbr, er = [], []
    for s in SYMS:
        g = bars4(s)
        m = (g.t >= DEV0) & (g.t < HOLD0)
        tbr.append(g.tbr[m]); er.append(g.er[m])
    tbr, er = pd.concat(tbr).dropna(), pd.concat(er).dropna()
    return {"tbr80": tbr.quantile(0.8), "tbr20": tbr.quantile(0.2), "er33": er.quantile(1 / 3)}


def stats(d, drift):
    n = len(d)
    if n < 20:
        return {"n": n}
    day = d.assign(day=d.t // 86_400_000).groupby("day").net.mean()
    tval = day.mean() / (day.std(ddof=1) / np.sqrt(len(day)))
    from scipy.stats import t as tdist
    p = float(2 * tdist.sf(abs(tval), len(day) - 1))
    dm = d.merge(drift, on=["symbol", "d"], how="left")
    sp = d.groupby("symbol").net.mean()
    return {"n": n, "net_bp": round(d.net.mean() * 1e4, 1), "gross_bp": round(d.gross.mean() * 1e4, 1),
            "excess_bp": round((dm.net - dm.drift).mean() * 1e4, 1), "t_day": round(tval, 2), "p": p,
            "win": round((d.net > 0).mean(), 3), "sym_pos": f"{int((sp > 0).sum())}/{len(sp)}",
            "sym_pos_n": int((sp > 0).sum()),
            "h1_bp": round(d[d.t < SPLIT].net.mean() * 1e4, 1), "h2_bp": round(d[d.t >= SPLIT].net.mean() * 1e4, 1),
            "g4h_bp": round(d.gross_4h.mean() * 1e4, 1), "g12h_bp": round(d.gross_12h.mean() * 1e4, 1),
            "g72h_bp": round(d.gross_72h.mean() * 1e4, 1), "mfe_atr": round(d.mfe_atr.median(), 2),
            "mae_atr": round(d.mae_atr.median(), 2), "touch_sma": round(d.touch_sma.mean(), 3)}


def table(ev, drift, lo, hi):
    w = ev[(ev.t >= lo) & (ev.t < hi)]
    out = []
    for fam in FAMILIES:
        f = w[w.family == fam]
        for cnd in CONDS:
            sub = f if cnd == "C0_ALL" else f[f[cnd]]
            out.append({"family": fam, "cond": cnd, **stats(sub, drift)})
    return pd.DataFrame(out)


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    m, adj, run = len(p), np.empty(len(p)), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * p[i]))
        adj[i] = run
    return adj


def drift_table(base, lo, hi):
    w = base[(base.t >= lo) & (base.t < hi)]
    return pd.concat([w.groupby("symbol").net_long.mean().rename("drift").reset_index().assign(d=1),
                      w.groupby("symbol").net_short.mean().rename("drift").reset_index().assign(d=-1)])


def main():
    q = dev_quantiles()
    print("DEV quantiles:", {k: round(v, 4) for k, v in q.items()})
    evs, bases = zip(*(outcomes(s, q) for s in SYMS))
    ev, base = pd.concat(evs, ignore_index=True), pd.concat(bases, ignore_index=True)
    ev.to_csv(CACHE / "E36_events.csv", index=False)
    dev = table(ev, drift_table(base, DEV0, HOLD0), DEV0, HOLD0)
    ok = dev.p.notna()
    dev.loc[ok, "p_holm"] = holm(dev.loc[ok, "p"])
    dev["dev_pass"] = (dev.net_bp >= 15) & (dev.p_holm < 0.05) & (dev.excess_bp > 0) & (dev.n >= 150) & \
        (dev.sym_pos_n >= 6) & (dev.h1_bp > 0) & (dev.h2_bp > 0)
    pd.set_option("display.width", 250)
    cols = ["family", "cond", "n", "net_bp", "gross_bp", "excess_bp", "t_day", "p_holm", "win", "sym_pos", "h1_bp",
            "h2_bp", "g4h_bp", "g12h_bp", "g72h_bp", "mfe_atr", "mae_atr", "touch_sma", "dev_pass"]
    print(dev[cols].to_string(index=False))
    dev.to_csv(e23.OUT / "E36_reversal_conditions_dev.csv", index=False)
    passers = dev[dev.dev_pass]
    print(f"DEV passers: {len(passers)}")
    if "--holdout" in sys.argv and len(passers):
        ho = table(ev, drift_table(base, HOLD0, END), HOLD0, END)
        ho = ho.merge(passers[["family", "cond", "net_bp"]].rename(columns={"net_bp": "dev_bp"}), on=["family", "cond"])
        ho["holdout_pass"] = (ho.net_bp > 0) & (ho.net_bp >= 0.5 * ho.dev_bp) & (ho.sym_pos_n >= 5)
        print(ho[["family", "cond", "n", "net_bp", "dev_bp", "excess_bp", "t_day", "sym_pos", "holdout_pass"]].to_string(index=False))
        ho.to_csv(e23.OUT / "E36_reversal_conditions_holdout.csv", index=False)


if __name__ == "__main__":
    main()
