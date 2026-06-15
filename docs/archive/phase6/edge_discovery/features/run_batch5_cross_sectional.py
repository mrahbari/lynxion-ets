"""Step-7 edge discovery (batch 5): cross-sectional / relative-value hypotheses
on the 24-symbol multi-year 8h universe — the blueprint's favoured class, now with
real breadth (vs the earlier 3-symbol test).

Pre-registered, FROZEN params. Cross-sectional reversal/momentum (relative to the
universe mean) + a BTC lead-lag test. Lookahead-safe (past returns + contemporaneous
cross-section). Cumulative multiple-testing. Signal quality only.

Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/run_batch5_cross_sectional.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "measurement"))

import hypotheses as HY                              # noqa: E402
import harness as H                                  # noqa: E402
import feature_library as F                          # noqa: E402
from feature_library import cross_sectional_demean   # noqa: E402
from universe_loader import load_universe            # noqa: E402

PRICE_8H = os.path.join("data", "research_cache", "8h")
HORIZONS = [1, 3, 9]             # 8h, 1d, 3d
REPORT = os.path.join("docs", "reports", "phase6", "phase6-step7-cross-sectional.md")


def _load_close(store):
    p = os.path.join(PRICE_8H, f"{store}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p)
    if len(df) < 200:
        return None
    return pd.Series(df["close"].values, index=pd.to_datetime(df["timestamp"], unit="s")).sort_index()


def main():
    closes = {}
    for s in load_universe("sync"):
        store = f"{s[:-4]}-USDT" if s.endswith("USDT") else s
        c = _load_close(store)
        if c is not None:
            closes[store] = c
    syms = sorted(closes)
    n_sym = len(syms)

    def xs(k, sign):
        def build(_):
            rets = {s: F.past_return(closes[s], k) for s in syms}
            return {s: sign * v for s, v in cross_sectional_demean(rets).items()}
        return build

    def btc_leadlag(k):
        def build(_):
            btc = closes.get("BTC-USDT")
            if btc is None:
                return {}
            br = F.past_return(btc, k)
            return {s: br.reindex(closes[s].index) for s in syms if s != "BTC-USDT"}
        return build

    batch = [
        ("xs_reversal_3",   xs(3, -1)),
        ("xs_reversal_9",   xs(9, -1)),
        ("xs_momentum_9",   xs(9, +1)),
        ("xs_momentum_30",  xs(30, +1)),
        ("btc_leadlag_1",   btc_leadlag(1)),
    ]
    n_trials = (len(HY.REGISTRY) + len(HY.REGISTRY_BATCH2)) * 3 * 4 \
        + 3 * n_sym * 3 \
        + len(batch) * n_sym * len(HORIZONS)        # cumulative family across the program

    rows = []
    for name, builder in batch:
        sig = builder(None)
        res = H.evaluate_across_symbols(sig, closes, HORIZONS, n_trials=n_trials)
        # breadth at each horizon: best mean-|IC| horizon + significance count
        best_h, best_mic = None, 0.0
        per_h_mic = {}
        for h in HORIZONS:
            ics = [res["per_symbol"][s]["per_horizon"][h]["ic"]["ic"]
                   for s in sig if res["per_symbol"].get(s)]
            ics = [x for x in ics if x == x]
            mic = float(np.mean(ics)) if ics else float("nan")
            per_h_mic[h] = mic
            if abs(mic) > abs(best_mic):
                best_mic, best_h = mic, h
        sig_h = best_h or HORIZONS[-1]
        cells = [(s, res["per_symbol"][s]["per_horizon"][sig_h]["ic"]) for s in sig
                 if res["per_symbol"].get(s)]
        same_sign_sig = sum(1 for _, r in cells
                            if r["ic"] == r["ic"] and np.sign(r["ic"]) == np.sign(best_mic)
                            and r["p_value"] < 0.05)
        prom = sum(1 for v in res["symbol_verdicts"].values() if v["verdict"] == "PROMOTE")
        rows.append((name, res["overall_verdict"], sig_h, best_mic, same_sign_sig, len(cells), prom))
        print(f"{name:16} -> {res['overall_verdict']} | mean_IC@{sig_h}={best_mic:+.3f} "
              f"same-sign&sig={same_sign_sig}/{len(cells)} promoted={prom}")

    L = ["# Phase 6 · Step 7 — Cross-Sectional / Relative-Value Hypotheses (24-symbol)", "",
         f"_Blueprint's favoured class on the {n_sym}-symbol multi-year 8h universe. "
         f"Pre-registered, frozen. Horizons {HORIZONS} (8h/1d/3d). **Cumulative** family "
         f"= {n_trials}, BH-FDR, default REJECT. Signal quality only — no SL/TP/cost/sim._",
         "", "## Breadth (read these, not just the verdict)", "",
         "| hypothesis | overall | best horizon | mean IC | same-sign & sig | promoted |",
         "|---|---|---:|---:|---|---:|"]
    for name, verdict, h, mic, ss, nc, prom in rows:
        L.append(f"| {name} | **{verdict}** | {h} | {mic:+.3f} | {ss}/{nc} | {prom}/{nc} |")
    promoted = [r for r in rows if r[1] == "PROMOTE"]
    prov = [r for r in rows if r[1] == "PROVISIONAL"]
    L += ["",
          f"**PROMOTE: {len(promoted)}** — {', '.join(r[0] for r in promoted) or 'none'}",
          f"**PROVISIONAL: {len(prov)}** — {', '.join(r[0] for r in prov) or 'none'}",
          f"**ARCHIVE: {len(rows) - len(promoted) - len(prov)}**", "",
          "_A real cross-sectional effect would show a clear-signed mean IC with a "
          "majority of symbols same-sign-and-significant. Mean IC near 0 or mixed signs "
          "⇒ no relative-value edge in this universe at these horizons. No tuning, no "
          "execution simulation._"]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        f.write("\n".join(L) + "\n")
    print("WROTE", REPORT, f"| promote={len(promoted)} provisional={len(prov)}")


if __name__ == "__main__":
    main()
