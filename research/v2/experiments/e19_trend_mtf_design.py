"""E19 — TrendMTF redesign (roadmap E16-U1): compare standard multi-timeframe trend designs on their claim.

Ideas from the reviewed indicators (2026-11-23): identityKa "Ultimate MTF Trend Dashboard" (HMA 14 vs 50 per
timeframe, 15m/1h/4h/1D, previous closed higher-TF bar, all-aligned = LONG/SHORT else "Dangerous"),
lost_sol "Trend MTF" (SMMA(close) vs SMMA(open)), DaHarley "MTF Market Bias+" (EMA slope, majority vote),
SuperTrend/ADX dashboards (ADX >= 20 = trending), MacroRegime ideas (Choppiness Index).

Claim of an MTF trend STATE (what dashboards use it for: trade with alignment, stand aside on conflict):
  when timeframes are aligned the market over the next 4 h is more DIRECTIONAL than when they conflict.
  Metric: forward efficiency ratio ER = |sum of the next 48 five-minute log returns| / sum of their |.|.
Pre-registered (2026-11-24, before any run):
  Variants (all on CLOSED bars; higher-TF value = last closed bar, like request.security(...)[1]):
    V0 current watcher: drift t-stat >= 1.0 on 15m/1h/4h, all same sign.
    V1 HMA(14) vs HMA(50) on 15m/1h/4h/1D, all same sign (identityKa).
    V2 V1 + trending filter: ADX(14) >= 20 on 1h and 4h.
    V3 per-TF majority vote of {HMA cross, SMMA(close,14) vs SMMA(open,14), drift sign} on 15m/1h/4h/1D,
       all TF same sign + ADX(14) >= 20 on 1h and 4h.
  States per variant: aligned (all up or all down) / conflict (both up and down TFs present) / other.
  PASS (per variant): mean fwd ER(aligned) >= 1.15 x mean fwd ER(conflict), n(aligned) >= 200, on DEV AND
  HOLDOUT. Also reported (no rule): signed fwd 4 h return of aligned states, share of time aligned.
  Choice: among passing variants the one with the largest DEV ratio; ties -> simplest. HOLDOUT read once.

Usage: python research/v2/experiments/e19_trend_mtf_design.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402

OUT = e9.OUT
DEV0 = int(datetime(2025, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)
HOLD0 = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000)
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT", "LINKUSDT"]
H = 3_600_000


def wma(x: pd.Series, n: int) -> pd.Series:
    w = np.arange(1, n + 1, dtype=float)
    return x.rolling(n).apply(lambda a: np.dot(a, w) / w.sum(), raw=True)


def hma(x: pd.Series, n: int) -> pd.Series:
    return wma(2 * wma(x, n // 2) - wma(x, n), int(np.sqrt(n)))


def smma(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(alpha=1.0 / n, adjust=False).mean()


def adx(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14) -> pd.Series:
    up, dn = h.diff(), -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = smma(tr, n)
    pdi = 100 * smma(pd.Series(pdm, index=c.index), n) / atr
    mdi = 100 * smma(pd.Series(mdm, index=c.index), n) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return smma(dx, n)


def drift_t(c: pd.Series, n: int = 20) -> pd.Series:
    r = np.log(c).diff()
    return r.rolling(n - 1).mean() / (r.rolling(n - 1).std() / np.sqrt(n - 1))


def resample(k1h: pd.DataFrame, hours: int) -> pd.DataFrame:
    g = k1h.assign(b=k1h.t // (hours * H)).groupby("b")
    d = g.agg(t=("t", "first"), o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), n=("c", "size"))
    return d[d.n == hours].reset_index(drop=True)


def tf_features(k: pd.DataFrame, tf_ms: int) -> pd.DataFrame:
    c, o = k.c.astype(float), k.o.astype(float)
    f = pd.DataFrame({"close_t": k.t + tf_ms})
    f["hma"] = np.sign(hma(c, 14) - hma(c, 50))
    f["smma"] = np.sign(smma(c, 14) - smma(o, 14))
    f["drift"] = np.sign(drift_t(c))
    f["drift_t"] = drift_t(c)
    f["adx"] = adx(k.h.astype(float), k.l.astype(float), c)
    vote = f[["hma", "smma", "drift"]].sum(axis=1)
    f["vote"] = np.sign(vote)
    return f


def build(sym: str) -> pd.DataFrame:
    k15 = e9.klines(sym, "15m").sort_values("t").reset_index(drop=True)
    k1 = e9.klines(sym, "1h").sort_values("t").reset_index(drop=True)
    k4, kd = resample(k1, 4), resample(k1, 24)
    tfs = {"15m": tf_features(k15, 900_000), "1h": tf_features(k1, H), "4h": tf_features(k4, 4 * H),
           "1d": tf_features(kd, 24 * H)}
    grid = pd.DataFrame({"t": np.arange((k1.t.iloc[0] // (4 * H) + 60) * 4 * H, k1.t.iloc[-1] - 5 * H, 4 * H)})
    for name, f in tfs.items():
        f = f.sort_values("close_t").rename(columns={c: f"{name}_{c}" for c in f.columns if c != "close_t"})
        grid = pd.merge_asof(grid, f, left_on="t", right_on="close_t", direction="backward").drop(columns="close_t")
    m1 = e9.klines(sym, "1m").sort_values("t")
    c5 = m1.assign(b=m1.t // 300_000).groupby("b").agg(t=("t", "first"), c=("c", "last")).reset_index(drop=True)
    lr = np.log(c5.c.to_numpy())
    r5 = np.diff(lr)
    t5 = c5.t.to_numpy()
    er, fwd = [], []
    for t in grid.t:
        i = np.searchsorted(t5, t)
        seg = r5[i:i + 48]
        if len(seg) < 48:
            er.append(np.nan)
            fwd.append(np.nan)
            continue
        er.append(abs(seg.sum()) / np.abs(seg).sum() if np.abs(seg).sum() > 0 else np.nan)
        fwd.append(seg.sum())
    grid["fwd_er"], grid["fwd_ret"], grid["symbol"] = er, fwd, sym
    return grid


def states(g: pd.DataFrame) -> dict:
    out = {}
    dirs0 = np.sign(g[["15m_drift_t", "1h_drift_t", "4h_drift_t"]].where(
        g[["15m_drift_t", "1h_drift_t", "4h_drift_t"]].abs() >= 1.0, 0.0))
    for name, d in (("V0", dirs0),
                    ("V1", g[["15m_hma", "1h_hma", "4h_hma", "1d_hma"]]),
                    ("V2", g[["15m_hma", "1h_hma", "4h_hma", "1d_hma"]]),
                    ("V3", g[["15m_vote", "1h_vote", "4h_vote", "1d_vote"]])):
        up, dn = (d == 1).all(axis=1), (d == -1).all(axis=1)
        conflict = (d == 1).any(axis=1) & (d == -1).any(axis=1)
        if name in ("V2", "V3"):
            trending = (g["1h_adx"] >= 20) & (g["4h_adx"] >= 20)
            up, dn = up & trending, dn & trending
        out[name] = np.where(up, "aligned_up", np.where(dn, "aligned_down", np.where(conflict, "conflict", "other")))
    return out


def score(g: pd.DataFrame, lab: np.ndarray) -> dict:
    aligned = np.isin(lab, ["aligned_up", "aligned_down"])
    conflict = lab == "conflict"
    sign = np.where(lab == "aligned_up", 1, np.where(lab == "aligned_down", -1, 0))
    signed = (g.fwd_ret * sign)[aligned]
    er_a, er_c = g.fwd_er[aligned].mean(), g.fwd_er[conflict].mean()
    return {"n_aligned": int(aligned.sum()), "n_conflict": int(conflict.sum()),
            "share_aligned": round(float(aligned.mean()), 3), "er_aligned": round(float(er_a), 4),
            "er_conflict": round(float(er_c), 4), "ratio": round(float(er_a / er_c), 3) if er_c else None,
            "signed_fwd_bp": round(float(signed.mean() * 1e4), 2) if len(signed) else None,
            "hit": round(float((signed > 0).mean()), 3) if len(signed) else None,
            "passed": bool(aligned.sum() >= 200 and er_c and er_a >= 1.15 * er_c)}


def main() -> None:
    g = pd.concat([build(s) for s in SYMBOLS]).dropna(subset=["fwd_er"])
    g.to_parquet(e9.CACHE / "E19_trend_mtf_grid.parquet")
    labs = states(g)
    rows = []
    for name, lab in labs.items():
        for period, m in (("DEV", (g.t >= DEV0) & (g.t < HOLD0)), ("HOLDOUT", g.t >= HOLD0)):
            rows.append({"variant": name, "period": period, **score(g[m.to_numpy()], lab[m.to_numpy()])})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "E19_trend_mtf_design.csv", index=False)
    pd.set_option("display.width", 250)
    print(r.to_string(index=False))


if __name__ == "__main__":
    main()
