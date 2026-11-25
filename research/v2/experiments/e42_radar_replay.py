"""E42 — Radar timing: replay the live Radar and three pre-defined changes on history (PRE-REGISTERED, 2026-11-25).

Operator brief: Radar finds the right direction but late (28-day momentum + efficiency + 4h EMA all confirm a move
already made). Turn it from "rank past trend strength" into "detect a change of behaviour" without losing trend
confirmation. Radar is a manual tool: a change is adopted if it signals EARLIER with better trade outcomes than the
current Radar (BASE); it does not need to prove a stand-alone edge.

Data: Binance USDT-M 1h lake (data/lake/binance_um, delisted symbols included) -> 1d and 4h bars. Snapshots every 4h
(at each 4h close) 2023-01-01 .. 2026-10-28. Universe per snapshot: 30-day median daily quote volume >= $10M,
stablecoins / non-perpetual symbols excluded (BingX listing history is not available: limitation).
Exploratory: 28-day momentum was studied on 2020-2024 (E2); 2023-2026 overlaps.

Variants (fixed definitions, no tuning):
  BASE  live Radar: percentile ranks of momentum28 (vol-adjusted), signed efficiency ratio(20d), short-term
        (close - EMA20_4h)/ATR14_4h; score = mean rank; LONG list = top 7 with all three > 0; SHORT = bottom 7, all < 0.
  A     28-day momentum becomes context only (not used); no all-three gate. Direction: momentum7 and short-term
        agree in sign. Quality = mean rank of momentum7, efficiency, short-term and acceleration
        (acceleration = 24h return - 7d return / 7). Top 7 by quality per direction.
  B     A + a fresh TRIGGER in the same direction within the last 2 bars (8 h) is required:
        range breakout: 4h close beyond the previous 20 bars' high/low with 4h volume >= 1.5 x their mean, or
        compression -> expansion: ATR5/ATR50 < 0.7 on the previous bar and the bar's true range >= 1.5 x ATR14.
  C     BASE, but extended coins (|short-term| > 2 ATR, the live "late" flag) are removed from the list.
Events: a coin ENTERING a variant's list (not in it at the previous snapshot), per side.
Outcome per event (the live Radar levels, from 1h data; 15m buffer approximated as 0.25 ATR1h):
  limit = pullback to EMA20(1h) or 1 ATR(1h); stop beyond the 12-hour 1h swing, distance in [ATR1h, ATR4h];
  TP1 = 1.5 R. Limit must fill within 24 h; then SL vs TP1 on 1h High/Low (SL first in the same bar, also on the
  fill bar), else close at 72 h. Net R after 2 x (5 bp fee + 2 bp slippage). Also MFE / MAE over 72 h (ATR4h units)
  and past72 = move already made in the previous 72 h (ATR4h; lower = earlier).
PASS for A, B, C vs BASE (all required):
  1. mean net R higher, Welch t >= 2 on day-averaged R (Holm over the 3 variants), and higher in both halves
     (2023-24 and 2025-26);  2. median past72 lower (earlier);  3. mean MAE not worse than BASE by > 10 %;
  4. >= 300 filled trades.
Next (only for passers): combined variant = passing changes together, then 2 weeks of live shadow logging next to
BASE before any change to the Telegram Radar. FAIL -> Radar unchanged.
Usage: cd research/v2 && python experiments/e42_radar_replay.py
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
H, H4, DAY = 3_600_000, 4 * 3_600_000, 86_400_000
T0 = int(pd.Timestamp("2023-01-01", tz="UTC").timestamp() * 1000)
T1 = int(pd.Timestamp("2026-10-28", tz="UTC").timestamp() * 1000)
WARM = int(pd.Timestamp("2022-09-01", tz="UTC").timestamp() * 1000)
SPLIT = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp() * 1000)
MIN_ADV, N_PICK, COST = 10e6, 7, 2 * (0.0005 + 0.0002)
EXCLUDE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "EURUSDT", "XAUTUSDT", "PAXGUSDT"}


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def _tr(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    return np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))


def symbol_frame(sym):
    """4h-snapshot features + compact 1h arrays for one symbol (None if never liquid)."""
    kp = pn.LAKE / "klines_1h" / f"{sym}.parquet"
    k = pd.read_parquet(kp, columns=["open_time", "open", "high", "low", "close", "quote_volume"])
    k = k[(k.open_time >= WARM) & (k.close > 0)].drop_duplicates("open_time").sort_values("open_time")
    if len(k) < 24 * 120:
        return None
    # daily
    k["d"] = k.open_time // DAY
    d = k.groupby("d").agg(c=("close", "last"), qv=("quote_volume", "sum"), n=("close", "size"))
    d = d[d.n >= 20]
    dc, dqv = d.c.to_numpy(), d.qv.to_numpy()
    if len(d) < 60:
        return None
    lr = np.r_[np.nan, np.diff(np.log(dc))]
    vol28 = pd.Series(lr).rolling(28).std().to_numpy()
    ld = np.log(dc)
    mom28 = (ld - pd.Series(ld).shift(28).to_numpy()) / (vol28 * np.sqrt(28))
    mom7 = (ld - pd.Series(ld).shift(7).to_numpy()) / (vol28 * np.sqrt(7))
    ret7 = dc / pd.Series(dc).shift(7).to_numpy() - 1
    ch20 = dc - pd.Series(dc).shift(20).to_numpy()
    path = pd.Series(np.abs(np.diff(dc, prepend=np.nan))).rolling(20).sum().to_numpy()
    er = np.abs(ch20) / path * np.sign(ch20)
    adv30 = pd.Series(dqv).rolling(30).median().to_numpy()
    dclose = (d.index.to_numpy() + 1) * DAY                          # daily row known at its close
    daily = pd.DataFrame({"t": dclose, "mom28": mom28, "mom7": mom7, "ret7": ret7, "er": er, "adv30": adv30})
    # 4h
    k["b"] = k.open_time // H4
    g = k.groupby("b").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"),
                           v=("quote_volume", "sum"), n=("close", "size"))
    g = g[g.n == 4]
    o, h, l, c, v = (g[x].to_numpy() for x in ("o", "h", "l", "c", "v"))
    tr = _tr(h, l, c)
    atr14 = pd.Series(tr).rolling(14).mean().to_numpy()
    atr5 = pd.Series(tr).rolling(5).mean().to_numpy()
    atr50 = pd.Series(tr).rolling(50).mean().to_numpy()
    e20 = _ema(c, 20)
    st = (c - e20) / atr14
    hh = pd.Series(h).shift(1).rolling(20).max().to_numpy()
    ll = pd.Series(l).shift(1).rolling(20).min().to_numpy()
    vm = pd.Series(v).shift(1).rolling(20).mean().to_numpy()
    brk = np.where((c > hh) & (v >= 1.5 * vm), 1, np.where((c < ll) & (v >= 1.5 * vm), -1, 0))
    comp_prev = pd.Series(atr5 / atr50).shift(1).to_numpy() < 0.7
    exp_ = tr >= 1.5 * pd.Series(atr14).shift(1).to_numpy()
    ce = np.where(comp_prev & exp_, np.sign(c - o), 0)
    trig = np.where(brk != 0, brk, ce)
    trig2 = np.where(trig != 0, trig, pd.Series(trig).shift(1).fillna(0).to_numpy())   # fresh: this or last bar
    ret24 = c / pd.Series(c).shift(6).to_numpy() - 1
    past72 = (c - pd.Series(c).shift(18).to_numpy()) / atr14
    T = (g.index.to_numpy() + 1) * H4
    f4 = pd.DataFrame({"t": T, "c4": c, "atr4": atr14, "st": st, "trig": trig2, "ret24": ret24, "past72": past72})
    f = pd.merge_asof(f4, daily, on="t", direction="backward")
    f = f[(f.t >= T0) & (f.t <= T1) & (f.adv30 >= MIN_ADV)].dropna(subset=["mom28", "mom7", "er", "st", "atr4"])
    if f.empty:
        return None
    f["accel"] = f.ret24 - f.ret7 / 7
    f["sym"] = sym
    h1 = {"t": k.open_time.to_numpy(), "o": k.open.to_numpy(np.float64), "h": k.high.to_numpy(np.float64),
          "l": k.low.to_numpy(np.float64), "c": k.close.to_numpy(np.float64)}
    return f, h1


def picks(snap: pd.DataFrame) -> dict:
    """Lists per variant/side for one snapshot (cross-section)."""
    r = {x: snap[x].rank(pct=True) for x in ("mom28", "er", "st", "mom7", "accel")}
    out = {}
    base = (r["mom28"] + r["er"] + r["st"]) / 3
    bl = snap[(snap.mom28 > 0) & (snap.er > 0) & (snap.st > 0)].index
    bs = snap[(snap.mom28 < 0) & (snap.er < 0) & (snap.st < 0)].index
    out[("BASE", 1)] = base[bl].sort_values(ascending=False).index[:N_PICK]
    out[("BASE", -1)] = base[bs].sort_values().index[:N_PICK]
    ext = snap.st.abs() > 2
    out[("C", 1)] = base[bl.difference(snap[ext].index)].sort_values(ascending=False).index[:N_PICK]
    out[("C", -1)] = base[bs.difference(snap[ext].index)].sort_values().index[:N_PICK]
    q = (r["mom7"] + r["er"] + r["st"] + r["accel"]) / 4
    al = snap[(snap.mom7 > 0) & (snap.st > 0)].index
    as_ = snap[(snap.mom7 < 0) & (snap.st < 0)].index
    out[("A", 1)] = q[al].sort_values(ascending=False).index[:N_PICK]
    out[("A", -1)] = q[as_].sort_values().index[:N_PICK]
    out[("B", 1)] = q[al.intersection(snap[snap.trig == 1].index)].sort_values(ascending=False).index[:N_PICK]
    out[("B", -1)] = q[as_.intersection(snap[snap.trig == -1].index)].sort_values().index[:N_PICK]
    return out


def outcome(h1, T, side, atr4, past72):
    t = h1["t"]
    j = int(np.searchsorted(t, T))
    if j < 40 or j + 72 > len(t) or t[j] != T:
        return None
    o, h, l, c = h1["o"], h1["h"], h1["l"], h1["c"]
    tr = _tr(h[j - 40:j], l[j - 40:j], c[j - 40:j])
    a1 = float(tr[-14:].mean())
    e1 = float(_ema(c[j - 40:j], 20)[-1])
    px = float(c[j - 1])
    if a1 <= 0 or not np.isfinite(atr4) or atr4 <= 0:
        return None
    if side > 0:
        lim = max(e1, px - a1) if e1 < px else px
        sl = min(float(l[j - 12:j].min()), lim - a1) - 0.25 * a1
        dist = min(max(lim - sl, a1), atr4)
    else:
        lim = min(e1, px + a1) if e1 > px else px
        sl = max(float(h[j - 12:j].max()), lim + a1) + 0.25 * a1
        dist = min(max(sl - lim, a1), atr4)
    sl, tp1 = lim - side * dist, lim + side * 1.5 * dist
    fwd = slice(j, j + 72)
    mfe = (h[fwd].max() - px) / atr4 if side > 0 else (px - l[fwd].min()) / atr4
    mae = (px - l[fwd].min()) / atr4 if side > 0 else (h[fwd].max() - px) / atr4
    res = {"mfe": mfe, "mae": mae, "past72": side * past72, "filled": False, "R": np.nan, "risk_pct": dist / lim}
    f = None
    for i in range(j, j + 24):
        if lim == px and i == j:
            f, entry = i, o[i]
            break
        if (side > 0 and l[i] <= lim) or (side < 0 and h[i] >= lim):
            entry = min(o[i], lim) if side > 0 else max(o[i], lim)
            f = i
            break
    if f is None:
        return res
    entry *= 1 + side * 0.0002
    risk = abs(entry - sl)
    if risk <= 0:
        return res
    R = None
    for i in range(f, j + 72):
        if (side > 0 and l[i] <= sl) or (side < 0 and h[i] >= sl):
            R = (sl - entry) / risk * side
            break
        if i > f and ((side > 0 and h[i] >= tp1) or (side < 0 and l[i] <= tp1)):
            R = (tp1 - entry) / risk * side
            break
    if R is None:
        R = (c[j + 71] - entry) / risk * side
    res.update({"filled": True, "R": R - COST * entry / risk})
    return res


def _sym_list():
    syms = sorted(p.stem for p in (pn.LAKE / "klines_1h").glob("*.parquet"))
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    return [s for s in syms if s.endswith("USDT") and s not in nps and s not in EXCLUDE]


def main():
    syms = _sym_list()
    frames, h1s = [], {}
    with ProcessPoolExecutor(8) as ex:
        for s, res in zip(syms, ex.map(symbol_frame, syms, chunksize=8)):
            if res is not None:
                frames.append(res[0]); h1s[s] = res[1]
    panel = pd.concat(frames, ignore_index=True)
    print("symbols", len(h1s), "rows", len(panel), "snapshots", panel.t.nunique())
    prev = {}
    events = []
    for T, snap in panel.groupby("t"):
        snap = snap.set_index("sym")
        for key, lst in picks(snap).items():
            new = set(lst) - prev.get(key, set())
            prev[key] = set(lst)
            for s in new:
                events.append((key[0], key[1], s, int(T), float(snap.at[s, "atr4"]), float(snap.at[s, "past72"])))
    print("events", len(events))
    rows = []
    for var, side, s, T, a4, p72 in events:
        o = outcome(h1s[s], T, side, a4, p72)
        if o is not None:
            rows.append({"variant": var, "side": side, "sym": s, "t": T, **o})
    ev = pd.DataFrame(rows)
    ev.to_csv(ROOT / "data/research_cache/E42_radar_events.csv", index=False)
    report(ev)


def _day_means(x):
    return x.assign(day=x.t // DAY).groupby("day").R.mean()


def report(ev):
    out = []
    fil = ev[ev.filled]
    for var in ("BASE", "A", "B", "C"):
        e, f = ev[ev.variant == var], fil[fil.variant == var]
        out.append({"variant": var, "events": len(e), "filled": len(f), "fill_rate": round(len(f) / max(1, len(e)), 3),
                    "mean_R": round(f.R.mean(), 3), "R_2023_24": round(f[f.t < SPLIT].R.mean(), 3),
                    "R_2025_26": round(f[f.t >= SPLIT].R.mean(), 3), "tp1_rate": round((f.R > 0).mean(), 3),
                    "median_past72": round(e.past72.median(), 2), "mean_mfe": round(e.mfe.mean(), 2),
                    "mean_mae": round(e.mae.mean(), 2), "median_risk_pct": round(e.risk_pct.median(), 4),
                    "long_R": round(f[f.side > 0].R.mean(), 3), "short_R": round(f[f.side < 0].R.mean(), 3)})
    res = pd.DataFrame(out).set_index("variant")
    b = res.loc["BASE"]
    bd = _day_means(fil[fil.variant == "BASE"])
    tests = []
    for var in ("A", "B", "C"):
        xd = _day_means(fil[fil.variant == var])
        tv = (xd.mean() - bd.mean()) / np.sqrt(xd.var() / len(xd) + bd.var() / len(bd))
        tests.append({"variant": var, "t": tv, "p": float(tdist.sf(tv, min(len(xd), len(bd)) - 1))})
    tt = pd.DataFrame(tests).set_index("variant")
    p = tt.p.to_numpy(); order = np.argsort(p); adj = np.empty(3); run = 0
    for rnk, i in enumerate(order):
        run = max(run, min(1.0, (3 - rnk) * p[i])); adj[i] = run
    tt["p_holm"] = adj
    for var in ("A", "B", "C"):
        x = res.loc[var]
        res.loc[var, "t_vs_base"] = round(tt.loc[var, "t"], 2)
        res.loc[var, "p_holm"] = round(tt.loc[var, "p_holm"], 4)
        res.loc[var, "PASS"] = bool(x.mean_R > b.mean_R and tt.loc[var, "t"] >= 2 and tt.loc[var, "p_holm"] < 0.05
                                    and x.R_2023_24 > b.R_2023_24 and x.R_2025_26 > b.R_2025_26
                                    and x.median_past72 < b.median_past72 and x.mean_mae <= 1.10 * b.mean_mae
                                    and x.filled >= 300)
    pd.set_option("display.width", 250)
    print(res.to_string())
    res.to_csv(ROOT / "docs/v2/reports/E42_radar_replay.csv")


if __name__ == "__main__":
    main()
