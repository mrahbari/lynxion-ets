"""Phase 17 — Microstructure Alpha Discovery (analysis only; NO strategy/tuning/optimization).

Builds a non-OHLCV microstructure feature layer from FUTURES klines order-flow fields
(num_trades, taker_buy_base) and tests two a-priori signal families + a funding×flow
interaction for predictive information OHLCV does not contain.

Signal families (a-priori, NOT tuned):
  A. Flow imbalance  : aggressor imbalance imb=(2*taker_buy-vol)/vol; flow_k = mean(imb, last K)
  B. Liquidity exp/con: trade-intensity z-score (num_trades) + avg-trade-size z-score
  Interaction        : funding regime (8h, ffill, no-lookahead) x flow sign

Metrics: (1) Spearman IC of each feature vs FORWARD return / forward |return| — cost-free
information content (the phase question); (2) cost-adjusted net expectancy of acting on the
signal sign (round-trip 0.30%, unchanged); (3) 4-fold walk-forward sign stability; per-symbol
BTC/ETH/SOL. OHLCV recent-return IC reported alongside ONLY as a baseline to show incremental
info — never as an entry driver.

Run: .venv/bin/python scripts/phase17_microstructure_analysis.py
"""
from __future__ import annotations
import json, os, sys
import numpy as np, pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEE_RATE = 0.001; SLIPPAGE = 0.0005
ROUND_TRIP_COST = 2 * (FEE_RATE + SLIPPAGE)   # 0.30%, unchanged from prior phases
SYMBOLS = ["BTC", "ETH", "SOL"]
TF = "5m"
K = 6              # a-priori lookback (30 min of 5m bars)
HORIZON = 6        # a-priori forward horizon (30 min)
Z_WIN = 100        # a-priori rolling window for z-scores / percentiles
WFO_FOLDS = 4


def load_micro(sym):
    p = os.path.join(REPO, "data", "history", "micro", TF, f"{sym}-USDT.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    for c in ["open", "high", "low", "close", "volume", "num_trades", "taker_buy_base"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["volume"] > 0].reset_index(drop=True)
    return df


def load_funding(sym):
    p = os.path.join(REPO, "data", "history", "raw", "funding", f"{sym}-USDT.csv")
    if not os.path.exists(p):
        return None
    f = pd.read_csv(p).sort_values("timestamp").reset_index(drop=True)
    return f


def spearman(x, y):
    s = pd.Series(x); t = pd.Series(y)
    m = s.notna() & t.notna()
    if m.sum() < 30 or s[m].std() == 0 or t[m].std() == 0:
        return None
    return float(s[m].corr(t[m], method="spearman"))


def features(df):
    vol = df["volume"].values
    tbb = df["taker_buy_base"].values
    delta = 2 * tbb - vol
    imb = np.where(vol > 0, delta / vol, 0.0)               # per-bar aggressor imbalance
    flow_k = pd.Series(imb).rolling(K).mean().values        # smoothed flow (Family A)
    ntr = df["num_trades"].values.astype(float)
    avg_trade = np.where(ntr > 0, vol / ntr, np.nan)
    def z(a):
        s = pd.Series(a)
        return ((s - s.rolling(Z_WIN).mean()) / s.rolling(Z_WIN).std()).values
    intensity_z = z(ntr)                                    # liquidity expansion (Family B)
    avgtrade_z = z(avg_trade)
    close = df["close"].values
    ret1 = pd.Series(close).pct_change().values             # contemporaneous bar return (baseline only)
    recent_ret = pd.Series(close).pct_change(K).values      # OHLCV momentum baseline
    return dict(imb=imb, flow_k=flow_k, intensity_z=intensity_z, avgtrade_z=avgtrade_z,
                recent_ret=recent_ret, close=close)


def fwd_returns(close, h):
    n = len(close)
    fr = np.full(n, np.nan)
    fr[:n - h] = (close[h:] - close[:n - h]) / close[:n - h]
    return fr


def stats(r):
    r = np.asarray([x for x in r if np.isfinite(x)])
    if len(r) < 10:
        return {"n": int(len(r)), "expectancy": None, "win": None}
    return {"n": int(len(r)), "expectancy": float(r.mean()), "win": float((r > 0).mean())}


def wfo_sign(idx_signed_rets, n):
    """idx_signed_rets: list of (i, net_ret). Return fold expectancies + sign-consistency."""
    bounds = [(k * n // WFO_FOLDS, (k + 1) * n // WFO_FOLDS) for k in range(WFO_FOLDS)]
    fes = []
    for a, b in bounds:
        rr = [r for (i, r) in idx_signed_rets if a <= i < b]
        fes.append(float(np.mean(rr)) if len(rr) >= 20 else None)
    valid = [e for e in fes if e is not None]
    pos = sum(1 for e in valid if e > 0)
    return {"fold_exp": [round(e, 6) if e is not None else None for e in fes],
            "folds_pos": pos, "folds_n": len(valid),
            "all_pos": len(valid) >= 3 and pos == len(valid),
            "all_neg": len(valid) >= 3 and pos == 0}


def analyze(sym):
    df = load_micro(sym)
    if df is None or len(df) < 5000:
        return {"error": f"insufficient micro data ({0 if df is None else len(df)})"}
    f = features(df)
    close = f["close"]; n = len(close)
    fr = fwd_returns(close, HORIZON)
    afr = np.abs(fr)
    span = f"{pd.to_datetime(df.timestamp.min(),unit='s').date()}->{pd.to_datetime(df.timestamp.max(),unit='s').date()}"
    out = {"bars": n, "span": span, "horizon_bars": HORIZON, "tf": TF}

    # ---- Information content (cost-free IC vs forward return) ----
    out["IC_forward_return"] = {
        "flow_k (FlowImbalance)": spearman(f["flow_k"], fr),
        "imb_1bar": spearman(f["imb"], fr),
        "intensity_z (Liquidity)": spearman(f["intensity_z"], fr),
        "avgtrade_z": spearman(f["avgtrade_z"], fr),
        "OHLCV_recent_ret (baseline)": spearman(f["recent_ret"], fr),
    }
    out["IC_forward_absreturn(volatility)"] = {
        "intensity_z (Liquidity)": spearman(f["intensity_z"], afr),
        "flow_k_abs": spearman(np.abs(f["flow_k"]), afr),
        "OHLCV_recent_absret (baseline)": spearman(np.abs(f["recent_ret"]), afr),
    }
    # redundancy check: is flow_k just contemporaneous OHLCV return?
    out["flow_vs_OHLCV_redundancy"] = {
        "corr(flow_k, recent_ret)": spearman(f["flow_k"], f["recent_ret"]),
    }

    # ---- Family A: act on flow sign, cost-adjusted ----
    flow = f["flow_k"]
    sigA = []
    for i in range(n):
        if not np.isfinite(flow[i]) or not np.isfinite(fr[i]):
            continue
        side = 1 if flow[i] > 0 else -1
        net = side * fr[i] - ROUND_TRIP_COST
        sigA.append((i, net))
    out["familyA_flow"] = {"signals": len(sigA), **stats([r for _, r in sigA]),
                           "wfo": wfo_sign(sigA, n)}
    # contrarian variant (flow exhaustion) — same magnitude, opposite sign expectancy pre-cost
    sigAc = [(i, (-1 if flow[i] > 0 else 1) * fr[i] - ROUND_TRIP_COST)
             for i in range(n) if np.isfinite(flow[i]) and np.isfinite(fr[i])]
    out["familyA_flow_contrarian"] = {**stats([r for _, r in sigAc]), "wfo": wfo_sign(sigAc, n)}

    # ---- Family B: flow sign gated by liquidity expansion (intensity_z>0) ----
    iz = f["intensity_z"]
    sigB_exp, sigB_con = [], []
    for i in range(n):
        if not (np.isfinite(flow[i]) and np.isfinite(fr[i]) and np.isfinite(iz[i])):
            continue
        side = 1 if flow[i] > 0 else -1
        net = side * fr[i] - ROUND_TRIP_COST
        (sigB_exp if iz[i] > 0 else sigB_con).append((i, net))
    out["familyB_flow_in_expansion"] = {"signals": len(sigB_exp),
                                        **stats([r for _, r in sigB_exp]), "wfo": wfo_sign(sigB_exp, n)}
    out["familyB_flow_in_contraction"] = {"signals": len(sigB_con),
                                          **stats([r for _, r in sigB_con]), "wfo": wfo_sign(sigB_con, n)}

    # ---- Funding x Flow interaction ----
    fund = load_funding(sym)
    if fund is not None:
        ft = fund["timestamp"].values; fv = fund["funding_rate"].values.astype(float)
        # forward-fill last known funding to each 5m bar (no lookahead)
        bt = df["timestamp"].values
        idx = np.searchsorted(ft, bt, side="right") - 1
        cur_fund = np.where(idx >= 0, fv[np.clip(idx, 0, len(fv) - 1)], np.nan)
        valid = np.isfinite(cur_fund)
        if valid.sum() > 1000:
            p10, p90 = np.nanpercentile(cur_fund, 10), np.nanpercentile(cur_fund, 90)
            inter = {}
            for label, fmask in [("extreme_pos_funding", cur_fund >= p90),
                                 ("extreme_neg_funding", cur_fund <= p10)]:
                for fl_label, fl_mask in [("flow_buy", flow > 0), ("flow_sell", flow < 0)]:
                    m = fmask & fl_mask & np.isfinite(fr) & np.isfinite(flow)
                    inter[f"{label}|{fl_label}"] = stats(fr[m])  # raw forward return (info, no side)
            out["funding_x_flow_fwdreturn"] = inter
        else:
            out["funding_x_flow_fwdreturn"] = {"error": "funding overlap too small"}
    return out


def main():
    res = {}
    for s in SYMBOLS:
        try:
            res[s] = analyze(s)
        except Exception as e:
            res[s] = {"error": str(e)}
        print(f"done {s}", file=sys.stderr)
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
