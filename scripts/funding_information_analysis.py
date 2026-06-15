"""Phase-14 funding information analysis (analysis only; NO signals/strategy/profitability).

Tests whether funding-rate data carries predictive information not in OHLCV:
 - descriptive stats for all 24 funding symbols (distribution, persistence, regime frequency);
 - predictive: for symbols with overlapping 1h price (BTC/ETH/SOL), conditional forward-return
   expectancy by funding regime at 4h/12h/24h/72h, correlation/IC, and 4-fold walk-forward stability.
No trading signals, no cost, no profitability — pure information content.
"""
from __future__ import annotations
import bisect, json, os, sys
import numpy as np, pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUND = os.path.join(REPO, "data", "history", "raw", "funding")
PRICE_SYMS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]   # have ~1yr 1h price overlapping funding
HORIZONS_H = [4, 12, 24, 72]


def load_funding(sym):
    df = pd.read_csv(os.path.join(FUND, f"{sym}.csv"))
    df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return df


def descriptive(sym):
    df = load_funding(sym)
    fr = df["funding_rate"].values.astype(float)
    if len(fr) < 50:
        return {"n": len(fr)}
    # persistence: lag-1 and lag-3 autocorrelation
    def ac(x, k):
        a, b = x[:-k], x[k:]
        if a.std() == 0 or b.std() == 0: return None
        return float(np.corrcoef(a, b)[0, 1])
    p10, p90 = np.percentile(fr, 10), np.percentile(fr, 90)
    return {
        "n": len(fr), "mean": float(fr.mean()), "std": float(fr.std()),
        "p1": float(np.percentile(fr, 1)), "p10": float(p10), "p50": float(np.percentile(fr, 50)),
        "p90": float(p90), "p99": float(np.percentile(fr, 99)),
        "pct_positive": float((fr > 0).mean()), "pct_negative": float((fr < 0).mean()),
        "pct_zero": float((fr == 0).mean()),
        "autocorr_lag1": ac(fr, 1), "autocorr_lag3": ac(fr, 3),
        "regime_freq": {"extreme_pos(>p90)": float((fr >= p90).mean()),
                        "extreme_neg(<p10)": float((fr <= p10).mean()),
                        "normal": float(((fr > p10) & (fr < p90)).mean())},
    }


def load_price_1h(sym):
    p = os.path.join(REPO, "data", "history", "raw", "1h", f"{sym}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return df["timestamp"].values.astype(int), df["close"].values.astype(float)


def price_at(ts_arr, close_arr, target):
    # close of the most recent bar at or before target
    i = bisect.bisect_right(ts_arr, target) - 1
    if i < 0:
        return None
    # require the bar to be within 2h of target (avoid stale)
    if target - ts_arr[i] > 2 * 3600:
        return None
    return float(close_arr[i])


def predictive(sym):
    fdf = load_funding(sym)
    pr = load_price_1h(sym)
    if pr is None:
        return {"error": "no 1h price"}
    ts_arr, close_arr = pr
    fr = fdf["funding_rate"].values.astype(float)
    fts = fdf["timestamp"].values.astype(int)
    # restrict to funding points within price coverage
    lo, hi = ts_arr[0], ts_arr[-1]
    mask = (fts >= lo) & (fts <= hi - max(HORIZONS_H) * 3600)
    fr, fts = fr[mask], fts[mask]
    if len(fr) < 100:
        return {"error": f"overlap too small ({len(fr)})"}
    p10, p90 = np.percentile(fr, 10), np.percentile(fr, 90)
    dfr = np.diff(fr, prepend=fr[0])           # funding change vs previous point
    sign = np.sign(fr); prev_sign = np.sign(np.roll(fr, 1)); prev_sign[0] = sign[0]

    records = []
    for j in range(len(fr)):
        t = int(fts[j]); p0 = price_at(ts_arr, close_arr, t)
        if p0 is None or p0 <= 0:
            continue
        fwd = {}
        ok = True
        for h in HORIZONS_H:
            ph = price_at(ts_arr, close_arr, t + h * 3600)
            if ph is None:
                ok = False; break
            fwd[h] = (ph - p0) / p0
        if not ok:
            continue
        regimes = []
        if fr[j] >= p90: regimes.append("extreme_pos")
        if fr[j] <= p10: regimes.append("extreme_neg")
        if dfr[j] > 0: regimes.append("expansion")
        if dfr[j] < 0: regimes.append("contraction")
        if sign[j] != prev_sign[j]: regimes.append("transition")
        records.append({"t": t, "fr": fr[j], "regimes": regimes, "fwd": fwd})

    out = {"n_aligned": len(records),
           "window": [int(fts[0]), int(fts[-1])],
           "overlap_days": (fts[-1] - fts[0]) / 86400}
    regs = ["extreme_pos", "extreme_neg", "expansion", "contraction", "transition"]

    def stats(vals):
        if len(vals) < 10:
            return {"n": len(vals), "mean": None, "win": None}
        a = np.array(vals)
        return {"n": len(a), "mean": float(a.mean()), "win": float((a > 0).mean()),
                "std": float(a.std())}

    # baseline (unconditional) forward returns + correlation funding vs fwd
    out["baseline"] = {h: stats([r["fwd"][h] for r in records]) for h in HORIZONS_H}
    out["correlation"] = {}
    for h in HORIZONS_H:
        x = np.array([r["fr"] for r in records]); y = np.array([r["fwd"][h] for r in records])
        out["correlation"][h] = {
            "pearson": float(np.corrcoef(x, y)[0, 1]) if x.std() and y.std() else None,
            "spearman_IC": float(pd.Series(x).corr(pd.Series(y), method="spearman")),
        }
    # conditional expectancy by regime x horizon
    out["conditional"] = {}
    for rg in regs:
        sub = [r for r in records if rg in r["regimes"]]
        out["conditional"][rg] = {h: stats([r["fwd"][h] for r in sub]) for h in HORIZONS_H}
    # walk-forward: 4 folds, conditional mean per regime/horizon per fold (stability of sign)
    out["walkforward"] = {}
    nrec = len(records); folds = [records[k * nrec // 4:(k + 1) * nrec // 4] for k in range(4)]
    for rg in regs:
        out["walkforward"][rg] = {}
        for h in HORIZONS_H:
            fold_means = []
            for fk in folds:
                sub = [r["fwd"][h] for r in fk if rg in r["regimes"]]
                fold_means.append(float(np.mean(sub)) if len(sub) >= 5 else None)
            valid = [m for m in fold_means if m is not None]
            pos = sum(1 for m in valid if m > 0)
            out["walkforward"][rg][h] = {"fold_means": fold_means,
                                          "folds_with_data": len(valid),
                                          "sign_consistent": (pos == len(valid) or pos == 0) if valid else None}
    return out


def main():
    syms = sorted(f.replace("-USDT.csv", "") for f in os.listdir(FUND) if f.endswith(".csv"))
    res = {"descriptive": {}, "predictive": {}}
    for s in syms:
        res["descriptive"][s] = descriptive(f"{s}-USDT")
    for s in PRICE_SYMS:
        res["predictive"][s.replace("-USDT", "")] = predictive(s)
        print(f"predictive done {s}", file=sys.stderr)
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
