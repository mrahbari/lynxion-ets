"""Step-5 edge discovery (batch 3): funding-positioning (carry) hypotheses.

Hypothesis class: high/crowded funding → positioning extreme → mean reversion in
forward return. Now testable with the 1-year funding backfill (BTC/ETH/SOL).

Alignment (NO lookahead): funding settles ~every 8h; each settled rate is known
AT its settlement time, so we forward-fill the last settlement with ts <= bar t
onto the 15m price grid. A bar never sees a future settlement.

Horizons are funding-appropriate (4h/1d/4d), not 15m. Cumulative multiple-testing
family across all batches. Signal quality only — no SL/TP, cost, or simulation.

Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/run_batch3_funding.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "measurement"))

import hypotheses as HY          # noqa: E402  (for cumulative family size)
import harness as H              # noqa: E402
from feature_library import cross_sectional_demean  # noqa: E402
from run_discovery import load_ohlcv, SYMBOLS        # noqa: E402

FUNDING_RAW = os.path.join("data", "history", "raw", "funding")
HORIZONS = [16, 96, 384]         # 4h, 1d, 4d (in 15m bars) — funding reversion timescale
ZWIN = 960                       # ~10d rolling window for funding z-score
REPORT = os.path.join("docs", "reports", "phase6", "phase6-step5-funding-hypotheses.md")


def load_funding_aligned(symbol: str, index: pd.DatetimeIndex) -> pd.Series:
    """Last SETTLED funding (settlement ts <= bar) forward-filled onto `index`."""
    f = pd.read_csv(os.path.join(FUNDING_RAW, f"{symbol}.csv"))
    fr = pd.Series(f["funding_rate"].values,
                   index=pd.to_datetime(f["timestamp"], unit="s")).sort_index()
    # union → ffill → reindex: each bar gets the most recent settlement <= bar
    return fr.reindex(fr.index.union(index)).ffill().reindex(index)


# ---- pre-registered funding hypotheses (FROZEN) ----
def h_funding_revert(funding):
    return {s: -v for s, v in funding.items()}                       # high funding -> expect down

def h_funding_z_revert(funding):
    out = {}
    for s, v in funding.items():
        z = (v - v.rolling(ZWIN).mean()) / v.rolling(ZWIN).std()
        out[s] = -z                                                  # extreme funding z -> revert
    return out

def h_xs_funding_revert(funding):
    return {s: -d for s, d in cross_sectional_demean(funding).items()}  # relatively crowded -> revert


BATCH3 = [
    ("funding_revert",      "carry", h_funding_revert),
    ("funding_z_revert",    "carry", h_funding_z_revert),
    ("xs_funding_revert",   "carry", h_xs_funding_revert),
]


def main():
    prices = {s: load_ohlcv(s) for s in SYMBOLS}
    close_by = {s: prices[s]["close"] for s in SYMBOLS}
    funding = {s: load_funding_aligned(s, prices[s].index) for s in SYMBOLS}
    cov = {s: int(funding[s].notna().sum()) for s in SYMBOLS}
    # cumulative family: batch1(10) + batch2(3) over 4 horizons + batch3 over 3 horizons
    n_trials = (len(HY.REGISTRY) + len(HY.REGISTRY_BATCH2)) * len(SYMBOLS) * 4 \
        + len(BATCH3) * len(SYMBOLS) * len(HORIZONS)

    rows = []
    for name, hclass, builder in BATCH3:
        res = H.evaluate_across_symbols(builder(funding), close_by, HORIZONS, n_trials=n_trials)
        detail = {}
        for sym, ph in res["per_symbol"].items():
            bh = max(ph["per_horizon"].values(),
                     key=lambda r: abs(r["ic"]["ic"]) if r["ic"]["ic"] == r["ic"]["ic"] else -1)
            detail[sym] = (bh["horizon"], bh["ic"]["ic"], bh["ic"]["p_value"],
                           bh["decile"]["monotonicity"])
        rows.append((name, hclass, res["overall_verdict"], res["symbol_verdicts"], detail))
        print(f"{name:22} -> {res['overall_verdict']}")

    L = ["# Phase 6 · Step 5 — Funding-Positioning (Carry) Hypotheses", "",
         f"_Funding-crowding → reversion. 1-year funding (BTC/ETH/SOL) forward-filled "
         f"onto 15m bars (lookahead-safe: settlement ≤ bar). Horizons {HORIZONS} "
         f"(4h/1d/4d). Aligned funding coverage: {cov}. **Cumulative** family = "
         f"{n_trials}, BH-FDR, default REJECT. Signal quality only._", "",
         "## Verdicts", "",
         "| hypothesis | overall | best IC (sym@h) | monotonicity@best | per-symbol |",
         "|---|---|---|---|---|"]
    for name, hclass, verdict, sv, detail in rows:
        bs = max(detail.items(), key=lambda kv: abs(kv[1][1]) if kv[1][1] == kv[1][1] else -1)
        sym, (h, ic, p, mono) = bs
        svstr = ", ".join(f"{s}:{v['verdict'][:4]}" for s, v in sv.items())
        L.append(f"| {name} | **{verdict}** | {sym}@{h}: {ic:+.3f} (p={p:.3f}) | "
                 f"{mono:+.2f} | {svstr} |")
    promoted = [r for r in rows if r[2] == "PROMOTE"]
    prov = [r for r in rows if r[2] == "PROVISIONAL"]
    L += ["",
          f"**PROMOTE: {len(promoted)}** — {', '.join(r[0] for r in promoted) or 'none'}",
          f"**PROVISIONAL: {len(prov)}** — {', '.join(r[0] for r in prov) or 'none'}",
          f"**ARCHIVE: {len(rows) - len(promoted) - len(prov)}**", "",
          "_Caveat: only 3 highly-correlated majors over 1 year (~1095 funding points "
          "each) → low cross-sectional breadth and limited independent samples; treat "
          "any signal as provisional pending a wider universe + longer history. No "
          "tuning, no execution simulation._"]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        f.write("\n".join(L) + "\n")
    print("WROTE", REPORT, f"| promote={len(promoted)} provisional={len(prov)}")


if __name__ == "__main__":
    main()
