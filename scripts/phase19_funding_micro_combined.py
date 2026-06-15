"""Phase 19 — Funding + Microstructure Combined Signal Validation (analysis only; NO tuning).

Combines the two WEAK threads from prior phases:
  * funding regime (Phase 14: extreme-neg funding -> BTC/ETH bounce at 24-72h, WEAK/UNSTABLE)
  * microstructure order flow (Phase 17: aggressor imbalance; funding x flow capitulation +0.011%, sub-cost)

Evaluation points = funding update times (8h cadence, matching Phase 14 sampling) within the
microstructure window. At each point: funding regime (from funding's own distribution) + flow_k
(mean 5m aggressor imbalance over the prior hour) + liquidity state. Forward returns at 4/12/24/72h
from 5m closes, net of 0.30% round-trip cost. Per-symbol BTC/ETH/SOL, 4-fold walk-forward.

Question: does the COMBINATION produce a deployable, stable, cross-symbol edge that neither the
funding-only nor flow-only component does? A-priori signals; no parameters tuned.

Run: .venv/bin/python scripts/phase19_funding_micro_combined.py
"""
from __future__ import annotations
import bisect, json, os, sys
import numpy as np, pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND_TRIP_COST = 2 * (0.001 + 0.0005)   # 0.30%, unchanged
SYMBOLS = ["BTC", "ETH", "SOL"]
HORIZONS_H = [4, 12, 24, 72]
K_FLOW_BARS = 12        # a-priori: 1h of 5m bars for flow_k
Z_WIN = 100             # a-priori liquidity z-window (bars)
WFO_FOLDS = 4


def load_micro(sym):
    p = os.path.join(REPO, "data", "history", "micro", "5m", f"{sym}-USDT.csv")
    df = pd.read_csv(p).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    for c in ["close", "volume", "num_trades", "taker_buy_base"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["volume"] > 0].reset_index(drop=True)
    vol = df["volume"].values; tbb = df["taker_buy_base"].values
    df["imb"] = np.where(vol > 0, (2 * tbb - vol) / vol, 0.0)
    df["flow_k"] = df["imb"].rolling(K_FLOW_BARS).mean()
    ntr = df["num_trades"].values.astype(float)
    df["intensity_z"] = ((pd.Series(ntr) - pd.Series(ntr).rolling(Z_WIN).mean())
                         / pd.Series(ntr).rolling(Z_WIN).std())
    return df


def load_funding(sym):
    p = os.path.join(REPO, "data", "history", "raw", "funding", f"{sym}-USDT.csv")
    return pd.read_csv(p).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)


def at_or_before(ts_arr, target):
    i = bisect.bisect_right(ts_arr, target) - 1
    return i if i >= 0 else None


def build(sym):
    micro = load_micro(sym); fund = load_funding(sym)
    mts = micro["timestamp"].values
    close = micro["close"].values
    flow = micro["flow_k"].values
    liq = micro["intensity_z"].values
    lo, hi = mts[0], mts[-1]
    fts = fund["timestamp"].values; fr = fund["funding_rate"].values.astype(float)
    # funding points inside the micro window (leave room for 72h forward)
    mask = (fts >= lo + K_FLOW_BARS * 300) & (fts <= hi - 72 * 3600)
    fts, fr = fts[mask], fr[mask]
    if len(fr) < 200:
        return None
    p10, p90 = np.percentile(fr, 10), np.percentile(fr, 90)
    recs = []
    for j in range(len(fr)):
        t = int(fts[j]); i = at_or_before(mts, t)
        if i is None or not np.isfinite(flow[i]):
            continue
        p0 = close[i]
        fwd = {}
        ok = True
        for h in HORIZONS_H:
            k = at_or_before(mts, t + h * 3600)
            if k is None or close[k] <= 0:
                ok = False; break
            fwd[h] = (close[k] - p0) / p0
        if not ok:
            continue
        recs.append({"t": t, "fr": fr[j], "flow": flow[i],
                     "liq": liq[i] if np.isfinite(liq[i]) else 0.0,
                     "ext_neg": fr[j] <= p10, "ext_pos": fr[j] >= p90, "fwd": fwd})
    return recs


def stats(rows):
    if len(rows) < 10:
        return {"n": len(rows), "net": None, "win": None}
    a = np.array(rows)
    return {"n": len(a), "gross": float(a.mean()),
            "net": float(a.mean() - ROUND_TRIP_COST), "win": float((a > 0).mean())}


def wfo(idx_rets, n):
    bounds = [(k * n // WFO_FOLDS, (k + 1) * n // WFO_FOLDS) for k in range(WFO_FOLDS)]
    fes = []
    for a, b in bounds:
        rr = [r for (i, r) in idx_rets if a <= i < b]
        fes.append(float(np.mean(rr) - ROUND_TRIP_COST) if len(rr) >= 8 else None)
    valid = [e for e in fes if e is not None]
    pos = sum(1 for e in valid if e > 0)
    return {"fold_net": [round(e, 5) if e is not None else None for e in fes],
            "folds_pos": pos, "folds_n": len(valid),
            "all_pos": len(valid) >= 3 and pos == len(valid)}


def signal_eval(recs, selector, side_fn, horizon):
    """selector(rec)->bool ; side_fn(rec)->+1/-1 ; returns net expectancy stats + wfo at horizon."""
    n = len(recs)
    chosen = [(idx, side_fn(r) * r["fwd"][horizon]) for idx, r in enumerate(recs) if selector(r)]
    rr = [r for _, r in chosen]
    s = stats(rr)
    s["wfo"] = wfo(chosen, n)
    return s


def analyze(sym):
    recs = build(sym)
    if not recs:
        return {"error": "no records"}
    out = {"n_funding_points": len(recs),
           "span": f"{pd.to_datetime(recs[0]['t'],unit='s').date()}->{pd.to_datetime(recs[-1]['t'],unit='s').date()}"}
    for h in HORIZONS_H:
        out[f"h{h}"] = {
            # components
            "funding_only_extneg_long": signal_eval(recs, lambda r: r["ext_neg"], lambda r: 1, h),
            "funding_only_extpos_short": signal_eval(recs, lambda r: r["ext_pos"], lambda r: -1, h),
            "flow_only_contrarian": signal_eval(recs, lambda r: r["flow"] != 0,
                                                lambda r: (-1 if r["flow"] > 0 else 1), h),
            # combined (the phase's hypotheses)
            "COMBO_capitulation(extneg&sellflow->long)":
                signal_eval(recs, lambda r: r["ext_neg"] and r["flow"] < 0, lambda r: 1, h),
            "COMBO_exhaustion(extpos&buyflow->short)":
                signal_eval(recs, lambda r: r["ext_pos"] and r["flow"] > 0, lambda r: -1, h),
            "COMBO_capit+liqexp(extneg&sellflow&liq>0->long)":
                signal_eval(recs, lambda r: r["ext_neg"] and r["flow"] < 0 and r["liq"] > 0, lambda r: 1, h),
        }
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
