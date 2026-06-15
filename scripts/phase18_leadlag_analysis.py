"""Phase 18 — Cross-Exchange & Lead-Lag Microstructure (analysis only; NO strategy/tuning).

Tests whether cross-venue / cross-asset *temporal precedence* (who moves first) carries
predictive information that single-venue OHLCV does not. Three a-priori tests on 1m data:
  T1 cross-asset : does BTC lead ETH / SOL (binance futures)?
  T2 perp-spot   : who leads (binance fut vs binance spot)? does basis predict fwd return?
  T3 cross-venue : who leads (binance fut vs mexc spot)? does dispersion predict reversion?

Metrics: lagged cross-correlation (cost-free lead-lag information); plus cost-adjusted (0.30%
round-trip) directional expectancy of the leader->laggard signal, 4-fold walk-forward, per-symbol.
Gross expectancy reported separately so information is visible apart from the cost verdict.

Run: .venv/bin/python scripts/phase18_leadlag_analysis.py
"""
from __future__ import annotations
import json, os, sys
import numpy as np, pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND_TRIP_COST = 2 * (0.001 + 0.0005)   # 0.30%, unchanged
SYMBOLS = ["BTC", "ETH", "SOL"]
MAXLAG = 3
WFO_FOLDS = 4


def load(venue, sym):
    p = os.path.join(REPO, "data", "history", "xvenue", venue, f"{sym}-USDT.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p).sort_values("timestamp").drop_duplicates("timestamp")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df[["timestamp", "close"]].dropna()


def aligned_returns(series_map):
    """series_map: {name: df}. Inner-join on timestamp; return DataFrame of 1m returns."""
    merged = None
    for name, df in series_map.items():
        s = df.rename(columns={"close": name})[["timestamp", name]]
        merged = s if merged is None else merged.merge(s, on="timestamp", how="inner")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    rets = {"timestamp": merged["timestamp"].values}
    for name in series_map:
        rets[name] = merged[name].pct_change().values
    return merged, pd.DataFrame(rets)


def ccf(a, b, maxlag=MAXLAG):
    """corr(a[t-k], b[t]) for k=0..maxlag  (a leads b by k when high at k>0)."""
    out = {}
    sa, sb = pd.Series(a), pd.Series(b)
    for k in range(0, maxlag + 1):
        x = sa.shift(k); y = sb
        m = x.notna() & y.notna()
        out[k] = float(x[m].corr(y[m])) if m.sum() > 100 and x[m].std() and y[m].std() else None
    return out


def stats(r):
    r = np.asarray([x for x in r if np.isfinite(x)])
    if len(r) < 20:
        return {"n": int(len(r)), "gross": None, "net": None, "win": None}
    return {"n": int(len(r)), "gross": float(r.mean()),
            "net": float(r.mean() - ROUND_TRIP_COST), "win": float((r > 0).mean())}


def wfo(idx_rets, n):
    bounds = [(k * n // WFO_FOLDS, (k + 1) * n // WFO_FOLDS) for k in range(WFO_FOLDS)]
    fes = []
    for a, b in bounds:
        rr = [r for (i, r) in idx_rets if a <= i < b]
        fes.append(float(np.mean(rr) - ROUND_TRIP_COST) if len(rr) >= 20 else None)
    valid = [e for e in fes if e is not None]
    pos = sum(1 for e in valid if e > 0)
    return {"fold_net": [round(e, 6) if e is not None else None for e in fes],
            "folds_pos": pos, "folds_n": len(valid),
            "all_pos": len(valid) >= 3 and pos == len(valid)}


def leader_signal(leader_ret, laggard_ret):
    """Trade laggard[t] in the direction of leader[t-1] (1-bar lead). Net of cost."""
    n = len(laggard_ret)
    rows = []
    for t in range(1, n):
        lr = leader_ret[t - 1]; fr = laggard_ret[t]
        if not (np.isfinite(lr) and np.isfinite(fr)) or lr == 0:
            continue
        side = 1 if lr > 0 else -1
        rows.append((t, side * fr))
    return rows


def main():
    res = {}

    # ---- T1 cross-asset (binance futures): BTC leads ETH/SOL? ----
    fut = {s: load("binance_fut", s) for s in SYMBOLS}
    if all(v is not None for v in fut.values()):
        merged, R = aligned_returns(fut)
        n = len(R)
        t1 = {"n_bars": n, "span_days": round((merged.timestamp.iloc[-1]-merged.timestamp.iloc[0])/86400,1)}
        for alt in ["ETH", "SOL"]:
            sig = leader_signal(R["BTC"].values, R[alt].values)
            t1[f"BTC->{alt}"] = {
                "ccf_BTC_leads(corr at k=0,1,2,3)": ccf(R["BTC"].values, R[alt].values),
                "ccf_{}_leads_BTC".format(alt): ccf(R[alt].values, R["BTC"].values),
                "leader_signal": {**stats([r for _, r in sig]), "wfo": wfo(sig, n)},
            }
        res["T1_cross_asset"] = t1

    # ---- T2 perp-spot (binance fut vs binance spot) ----
    t2 = {}
    for s in SYMBOLS:
        fdf, sdf = load("binance_fut", s), load("binance_spot", s)
        if fdf is None or sdf is None:
            t2[s] = {"error": "missing series"}; continue
        merged, R = aligned_returns({"perp": fdf, "spot": sdf})
        n = len(R)
        # basis = (perp-spot)/spot on aligned closes
        basis = (merged["perp"].values - merged["spot"].values) / merged["spot"].values
        fwd_perp = pd.Series(merged["perp"].values).pct_change().shift(-1).values  # next-bar perp return
        bsr = pd.Series(basis); fsr = pd.Series(fwd_perp); m = bsr.notna() & fsr.notna()
        sig = leader_signal(R["perp"].values, R["spot"].values)   # does perp lead spot?
        sig_rev = leader_signal(R["spot"].values, R["perp"].values)
        t2[s] = {
            "n_bars": n,
            "perp_leads_spot_ccf": ccf(R["perp"].values, R["spot"].values),
            "spot_leads_perp_ccf": ccf(R["spot"].values, R["perp"].values),
            "basis_mean_pct": float(np.nanmean(basis) * 100),
            "IC_basis_vs_fwd_perp_ret": (float(bsr[m].corr(fsr[m], method="spearman"))
                                         if m.sum() > 100 else None),
            "perp->spot_signal": {**stats([r for _, r in sig]), "wfo": wfo(sig, n)},
            "spot->perp_signal": {**stats([r for _, r in sig_rev]), "wfo": wfo(sig_rev, n)},
        }
    res["T2_perp_spot"] = t2

    # ---- T3 cross-venue (binance fut vs mexc spot) ----
    t3 = {}
    for s in SYMBOLS:
        bdf, mdf = load("binance_fut", s), load("mexc_spot", s)
        if bdf is None or mdf is None:
            t3[s] = {"error": "missing series"}; continue
        merged, R = aligned_returns({"binance": bdf, "mexc": mdf})
        n = len(R)
        disp = (merged["binance"].values - merged["mexc"].values) / merged["mexc"].values
        fwd_mexc = pd.Series(merged["mexc"].values).pct_change().shift(-1).values
        dsr = pd.Series(disp); fsr = pd.Series(fwd_mexc); m = dsr.notna() & fsr.notna()
        sig = leader_signal(R["binance"].values, R["mexc"].values)
        sig_rev = leader_signal(R["mexc"].values, R["binance"].values)
        t3[s] = {
            "n_bars": n,
            "binance_leads_mexc_ccf": ccf(R["binance"].values, R["mexc"].values),
            "mexc_leads_binance_ccf": ccf(R["mexc"].values, R["binance"].values),
            "dispersion_std_pct": float(np.nanstd(disp) * 100),
            "IC_dispersion_vs_fwd_mexc_ret": (float(dsr[m].corr(fsr[m], method="spearman"))
                                              if m.sum() > 100 else None),
            "binance->mexc_signal": {**stats([r for _, r in sig]), "wfo": wfo(sig, n)},
            "mexc->binance_signal": {**stats([r for _, r in sig_rev]), "wfo": wfo(sig_rev, n)},
        }
    res["T3_cross_venue"] = t3

    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
