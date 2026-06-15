"""Step-8 edge discovery (batch 6): regime-conditional hypotheses (blueprint §3B) —
the last free-data class. Reversion is often expressed in high-volatility regimes,
momentum in low-vol/trending regimes. Signals are masked to their regime (NaN
elsewhere) so IC is measured only on in-regime bars.

24-symbol multi-year 8h universe. Trailing-vol regime (lookahead-safe). Pre-
registered, frozen. Cumulative multiple-testing. Signal quality only.

Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/run_batch6_regime.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "measurement"))

import harness as H                                  # noqa: E402
import feature_library as F                          # noqa: E402
from universe_loader import load_universe            # noqa: E402

PRICE_8H = os.path.join("data", "research_cache", "8h")
HORIZONS = [1, 3, 9]
VOL_WIN, MED_WIN = 30, 90        # ~10d vol, ~30d trailing median (8h bars)
PRIOR_CELLS = 120 + 36 + 27 + 216 + 360   # batches 1-5
REPORT = os.path.join("docs", "reports", "phase6", "phase6-step8-regime-conditional.md")


def _load_close(store):
    p = os.path.join(PRICE_8H, f"{store}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p)
    if len(df) < 200:
        return None
    return pd.Series(df["close"].values, index=pd.to_datetime(df["timestamp"], unit="s")).sort_index()


def _high_vol_mask(close):
    """Trailing-vol regime: True where trailing vol > its trailing median (no lookahead)."""
    vol = close.pct_change().rolling(VOL_WIN).std()
    med = vol.rolling(MED_WIN).median()
    return vol > med, med.notna()


def main():
    closes = {}
    for s in load_universe("sync"):
        store = f"{s[:-4]}-USDT" if s.endswith("USDT") else s
        c = _load_close(store)
        if c is not None:
            closes[store] = c
    syms = sorted(closes)
    n_sym = len(syms)
    masks = {s: _high_vol_mask(closes[s]) for s in syms}

    def revert_highvol(k):
        def build(_):
            out = {}
            for s in syms:
                high, valid = masks[s]
                out[s] = (-F.past_return(closes[s], k)).where(high & valid)
            return out
        return build

    def momentum_lowvol(k):
        def build(_):
            out = {}
            for s in syms:
                high, valid = masks[s]
                out[s] = (F.past_return(closes[s], k)).where((~high) & valid)
            return out
        return build

    batch = [
        ("revert_highvol_3",   revert_highvol(3)),
        ("revert_highvol_9",   revert_highvol(9)),
        ("momentum_lowvol_9",  momentum_lowvol(9)),
        ("momentum_lowvol_30", momentum_lowvol(30)),
    ]
    n_trials = PRIOR_CELLS + len(batch) * n_sym * len(HORIZONS)

    rows = []
    for name, builder in batch:
        sig = builder(None)
        res = H.evaluate_across_symbols(sig, closes, HORIZONS, n_trials=n_trials)
        best_h, best_mic = HORIZONS[-1], 0.0
        for h in HORIZONS:
            ics = [res["per_symbol"][s]["per_horizon"][h]["ic"]["ic"] for s in syms]
            ics = [x for x in ics if x == x]
            mic = float(np.mean(ics)) if ics else 0.0
            if abs(mic) > abs(best_mic):
                best_mic, best_h = mic, h
        cells = [res["per_symbol"][s]["per_horizon"][best_h]["ic"] for s in syms]
        ss = sum(1 for r in cells if r["ic"] == r["ic"]
                 and np.sign(r["ic"]) == np.sign(best_mic) and r["p_value"] < 0.05)
        nval = sum(1 for r in cells if r["ic"] == r["ic"])
        prom = sum(1 for v in res["symbol_verdicts"].values() if v["verdict"] == "PROMOTE")
        rows.append((name, res["overall_verdict"], best_h, best_mic, ss, nval, prom))
        print(f"{name:18} -> {res['overall_verdict']} | mean_IC@{best_h}={best_mic:+.3f} "
              f"same-sign&sig={ss}/{nval} promoted={prom}")

    L = ["# Phase 6 · Step 8 — Regime-Conditional Hypotheses (vol-gated, 24-symbol)", "",
         f"_Last free-data class (blueprint §3B). Reversion gated to high-vol bars, "
         f"momentum to low-vol bars (signal=NaN outside regime → IC on in-regime bars "
         f"only). {n_sym} symbols, multi-year 8h, trailing-vol regime (lookahead-safe). "
         f"Horizons {HORIZONS}. **Cumulative** family = {n_trials}, BH-FDR, default "
         f"REJECT. Signal quality only._", "",
         "## Breadth", "",
         "| hypothesis | overall | best horizon | mean IC (in-regime) | same-sign & sig | promoted |",
         "|---|---|---:|---:|---|---:|"]
    for name, verdict, h, mic, ss, nval, prom in rows:
        L.append(f"| {name} | **{verdict}** | {h} | {mic:+.3f} | {ss}/{nval} | {prom}/{nval} |")
    promoted = [r for r in rows if r[1] == "PROMOTE"]
    prov = [r for r in rows if r[1] == "PROVISIONAL"]
    L += ["",
          f"**PROMOTE: {len(promoted)}** — {', '.join(r[0] for r in promoted) or 'none'}",
          f"**PROVISIONAL: {len(prov)}** — {', '.join(r[0] for r in prov) or 'none'}",
          f"**ARCHIVE: {len(rows) - len(promoted) - len(prov)}**", "",
          "_Conditioning on volatility regime is the standard refinement that rescues "
          "reversion/momentum when it exists. Near-zero in-regime mean IC ⇒ no "
          "regime-conditional edge here either. No tuning, no execution simulation._"]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        f.write("\n".join(L) + "\n")
    print("WROTE", REPORT, f"| promote={len(promoted)} provisional={len(prov)}")


if __name__ == "__main__":
    main()
