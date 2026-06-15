"""Roadmap A — free-data edge discovery, all 6 classes through the full protocol.

Sequential: (1) spot-perp basis, (2) cointegration/stat-arb, (3) multi-factor,
(4) ML signal-combination, (5) advanced regimes, (6) seasonality/calendar. Each
candidate runs eval_protocol.full_eval (HAC IC · CV · OOS · cost gate) and is
appended to the cumulative ledger. Default REJECT. Stops early if a class promotes.

No strategies, no optimization, no parameter sweeps. Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/run_roadmapA.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "measurement"))

import feature_library as F                                   # noqa: E402
from feature_library import cross_sectional_demean            # noqa: E402
from universe_loader import load_universe                     # noqa: E402
from eval_protocol import full_eval, append_ledger, _cost_gate  # noqa: E402
from forward_labels import vol_normalized_forward_returns      # noqa: E402
from predictive_power import information_coefficient           # noqa: E402

FUT = os.path.join("data", "research_cache", "8h")
SPOT = os.path.join("data", "research_cache", "8h_spot")
FUNDING = os.path.join("data", "history", "raw", "funding")
N_TRIALS = 1500          # conservative cumulative multiple-testing family for Roadmap A
ZWIN = 90


def _store(s):
    return f"{s[:-4]}-USDT" if s.endswith("USDT") else s


def _load(dirpath, store, col="close"):
    p = os.path.join(dirpath, f"{store}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p)
    if len(df) < 300:
        return None
    return pd.Series(df[col].values, index=pd.to_datetime(df["timestamp"], unit="s")).sort_index()


UNIV = [_store(s) for s in load_universe("sync")]
PERP = {s: _load(FUT, s) for s in UNIV}
PERP = {s: v for s, v in PERP.items() if v is not None}
SYMS = sorted(PERP)


def _zscore(x, w):
    return (x - x.rolling(w).mean()) / x.rolling(w).std()


# ---------------- Class 1: Spot-Perp Basis ----------------
def class1_basis():
    spot = {s: _load(SPOT, s) for s in SYMS}
    basis, close_by = {}, {}
    for s in SYMS:
        sp = spot.get(s)
        if sp is None:
            continue
        idx = PERP[s].index.intersection(sp.index)
        if len(idx) < 300:
            continue
        p = PERP[s].reindex(idx); spx = sp.reindex(idx)
        basis[s] = (p - spx) / spx
        close_by[s] = p
    rev = {s: -basis[s] for s in basis}
    z = {s: -_zscore(basis[s], ZWIN) for s in basis}
    return [("basis_revert", "C3_basis", rev, close_by, [1, 3, 9]),
            ("basis_zscore_revert", "C3_basis", z, close_by, [1, 3, 9])]


# ---------------- Class 2: Cointegration / Stat-Arb ----------------
def class2_cointegration(top_n=12):
    logp = {s: np.log(PERP[s]) for s in SYMS}
    mat = pd.DataFrame(logp).dropna()
    if len(mat) < 300:
        return []
    corr = mat.corr()
    pairs = []
    for i, a in enumerate(SYMS):
        for b in SYMS[i + 1:]:
            if a in corr and b in corr.columns:
                pairs.append((a, b, corr.loc[a, b]))
    pairs = sorted([p for p in pairs if p[2] == p[2]], key=lambda x: -x[2])[:top_n]
    sig, close_by = {}, {}
    for a, b, _ in pairs:
        idx = PERP[a].index.intersection(PERP[b].index)
        ratio = PERP[a].reindex(idx) / PERP[b].reindex(idx)
        key = f"{a[:-5]}_{b[:-5]}"
        close_by[key] = ratio                       # ratio is a valid positive "price"
        sig[key] = -_zscore(np.log(ratio), ZWIN)    # mean-revert the log-spread
    return [("coint_spread_revert", "C2_coint", sig, close_by, [1, 3, 9])]


# ---------------- Class 3: Multi-Factor (cross-sectional) ----------------
def class3_factors():
    vol = {s: PERP[s].pct_change().rolling(30).std() for s in SYMS}
    dvol = {s: (PERP[s] * _load(FUT, s, "volume")).rolling(30).mean() for s in SYMS}
    btc = PERP.get("BTC-USDT")
    beta = {}
    if btc is not None:
        br = btc.pct_change()
        for s in SYMS:
            r = PERP[s].pct_change()
            cov = r.rolling(90).cov(br.reindex(r.index))
            beta[s] = cov / br.reindex(r.index).rolling(90).var()
    low_vol = {s: -v for s, v in cross_sectional_demean(vol).items()}
    small = {s: -v for s, v in cross_sectional_demean({s: np.log(dvol[s]) for s in SYMS if dvol[s] is not None}).items()}
    low_beta = {s: -v for s, v in cross_sectional_demean(beta).items()} if beta else {}
    out = [("factor_low_vol", "C2_factor", low_vol, PERP, [3, 9, 21]),
           ("factor_illiquidity", "C2_factor", small, PERP, [3, 9, 21])]
    if low_beta:
        out.append(("factor_low_beta", "C2_factor", low_beta, PERP, [3, 9, 21]))
    return out


# ---------------- Class 4: ML signal combination (custom IS-fit / OOS-eval) ----------------
def class4_ml_combination():
    from sklearn.linear_model import LogisticRegression
    feats_by, fwd_by = {}, {}
    for s in SYMS:
        c = PERP[s]
        df = pd.DataFrame({
            "rev3": -F.past_return(c, 3), "rev9": -F.past_return(c, 9),
            "mom9": F.past_return(c, 9), "rsi": -(F.rsi(c, 14) - 50),
            "rangepos": -(F.range_position(_full_ohlc(s), 48) - 0.5),
            "volz": F.volume_zscore(_load(FUT, s, "volume"), 48),
        }, index=c.index)
        y = vol_normalized_forward_returns(c, [1])["fwd_1"]
        feats_by[s] = df; fwd_by[s] = y
    # pooled IS fit (first 70% by time), OOS predict (last 30%) per symbol
    combined = {}
    for s in SYMS:
        df = feats_by[s].join(fwd_by[s].rename("y")).replace([np.inf, -np.inf], np.nan).dropna()
        if len(df) < 400:
            continue
        cut = int(len(df) * 0.7)
        Xtr, ytr = df.iloc[:cut, :-1].values, np.sign(df.iloc[:cut, -1].values)
        Xte = df.iloc[cut:, :-1].values
        if len(np.unique(ytr)) < 2:
            continue
        m = LogisticRegression(max_iter=200)
        m.fit(Xtr, ytr)
        pred = m.predict_proba(Xte)[:, 1] - 0.5      # >0 => predict up
        combined[s] = pd.Series(pred, index=df.index[cut:])
    # evaluate the OOS combined signal directly (it is OOS by construction)
    ics, cells = [], []
    for s, sig in combined.items():
        lab = vol_normalized_forward_returns(PERP[s], [1])["fwd_1"]
        r = information_coefficient(sig, lab.reindex(sig.index), 1)
        if r["ic"] == r["ic"]:
            ics.append(r["ic"]); cells.append((r["ic"], r["p_value"]))
    mean_ic = float(np.mean(ics)) if ics else float("nan")
    breadth = sum(1 for ic, p in cells if np.sign(ic) == np.sign(mean_ic) and p < 0.05)
    cg = _cost_gate(combined, PERP, 1)
    cost_ok = cg["net_bps"] > 0 and cg["n"] >= 500 and cg["t_net"] >= 2.0
    promote = (mean_ic == mean_ic and breadth >= max(2, int(0.4 * len(cells)))
               and cost_ok)
    entry = {"class": "ml_logit_combination", "taxonomy": "C8_ml", "symbols": len(cells),
             "best_horizon": 1, "mean_ic": round(mean_ic, 4),
             "breadth_sig": f"{breadth}/{len(cells)}", "is_ic": float("nan"),
             "oos_ic": round(mean_ic, 4), "gross_bps": round(cg["gross_bps"], 1),
             "net_bps": round(cg["net_bps"], 1), "t_net": round(cg["t_net"], 1),
             "n_trades": cg["n"], "harness_verdict": "OOS-only",
             "verdict": "PROMOTE" if promote else "REJECT",
             "reject_reasons": "" if promote else
             f"breadth {breadth}/{len(cells)}; net {cg['net_bps']:+.1f}bps t={cg['t_net']:+.1f}"}
    print(f"  ml_logit_combination: {entry['verdict']} | OOS IC={mean_ic:+.3f} "
          f"breadth={breadth}/{len(cells)} net={cg['net_bps']:+.1f}bps t={cg['t_net']:+.1f}")
    return ("CUSTOM", entry)


_OHLC_CACHE = {}
def _full_ohlc(store):
    if store not in _OHLC_CACHE:
        df = pd.read_csv(os.path.join(FUT, f"{store}.csv"))
        df.index = pd.to_datetime(df["timestamp"], unit="s")
        _OHLC_CACHE[store] = df.sort_index()
    return _OHLC_CACHE[store]


# ---------------- Class 5: Advanced regimes (rule-based, richer than vol-median) ----------------
def class5_regime():
    out = {}
    close_by = {}
    for s in SYMS:
        c = PERP[s]
        ret = c.pct_change()
        vol = ret.rolling(30).std()
        vol_hi = vol > vol.rolling(MED := 90).median()
        trend = F.past_return(c, 9)
        trend_up = trend > 0
        out[s] = (vol_hi, trend_up, c)
        close_by[s] = c
    # regime A: reversion in high-vol + counter-trend (panic overreaction)
    revA = {s: (-F.past_return(PERP[s], 3)).where(out[s][0] & (~out[s][1])) for s in SYMS}
    # regime B: momentum in low-vol + uptrend (quiet trending)
    momB = {s: (F.past_return(PERP[s], 9)).where((~out[s][0]) & out[s][1]) for s in SYMS}
    return [("regime_revert_highvol_downtrend", "C5_regime", revA, close_by, [1, 3, 9]),
            ("regime_momentum_lowvol_uptrend", "C5_regime", momB, close_by, [1, 3, 9])]


# ---------------- Class 6: Seasonality / calendar ----------------
def class6_seasonality():
    # trailing (expanding, lookahead-safe) mean next-bar return per 8h-slot-of-day
    sig, close_by = {}, {}
    for s in SYMS:
        c = PERP[s]
        fwd1 = c.pct_change().shift(-1)              # next-bar return (target proxy)
        slot = pd.Series(c.index.hour // 8, index=c.index)   # 0,1,2 (00/08/16 UTC)
        # expanding mean by slot, SHIFTED so bar t uses only history < t
        df = pd.DataFrame({"slot": slot, "r": c.pct_change()})
        exp_by_slot = df.groupby("slot")["r"].transform(
            lambda x: x.shift(1).expanding().mean())
        sig[s] = exp_by_slot                          # predicted seasonal bias
        close_by[s] = c
    return [("seasonality_slot_of_day", "C6_seasonal", sig, close_by, [1, 3])]


CLASSES = [
    ("1. Spot-Perp Basis", class1_basis),
    ("2. Cointegration / Stat-Arb", class2_cointegration),
    ("3. Multi-Factor Portfolio", class3_factors),
    ("4. ML Signal Combination", class4_ml_combination),
    ("5. Advanced Regimes", class5_regime),
    ("6. Seasonality / Calendar", class6_seasonality),
]


def main():
    candidate_found = None
    for label, fn in CLASSES:
        print(f"\n=== {label} ===", flush=True)
        try:
            result = fn()
        except Exception as e:  # noqa: BLE001 — isolate a failing class, keep going
            import traceback; traceback.print_exc()
            append_ledger({"class": label, "taxonomy": "ERROR", "symbols": 0,
                           "best_horizon": 0, "mean_ic": 0.0, "breadth_sig": "-",
                           "is_ic": 0.0, "oos_ic": 0.0, "gross_bps": 0.0, "net_bps": 0.0,
                           "t_net": 0.0, "n_trades": 0, "harness_verdict": "ERROR",
                           "verdict": "REJECT", "reject_reasons": f"error: {str(e)[:120]}"})
            continue
        if isinstance(result, tuple) and result[0] == "CUSTOM":     # class 4
            entry = result[1]; append_ledger(entry)
            if entry["verdict"] == "PROMOTE":
                candidate_found = entry["class"]; break
            continue
        best = None
        for name, hclass, sig, close_by, horizons in result:
            if not sig:
                continue
            e = full_eval(name, hclass, sig, close_by, horizons, N_TRIALS)
            if best is None or e["net_bps"] > best["net_bps"]:
                best = e
            if e["verdict"] == "PROMOTE":
                best = e; break
        if best is not None:
            append_ledger(best)
            if best["verdict"] == "PROMOTE":
                candidate_found = best["class"]; break
    print(f"\nROADMAP_A_DONE candidate={candidate_found or 'NONE — fully exhausted'}")


if __name__ == "__main__":
    main()
