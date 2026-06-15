"""Step-6: re-test the funding-reversion LEAD on a wider universe + multi-year
history (8h bars = native funding cadence). Confirmation of the pre-specified
batch-3 hypotheses (funding_revert / z / xs) with more independent windows and
real cross-symbol breadth.

Inputs: data/research_cache/8h/{SYM}.csv (price) + data/history/raw/funding/{SYM}.csv
(multi-year funding). Lookahead-safe asof-align (settlement <= bar). Signal quality
only — no SL/TP, cost, or simulation.

Run from repo root after both backfills complete:
    .venv/bin/python3 research/edge_discovery/features/run_batch4_funding_wide.py
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
from feature_library import cross_sectional_demean   # noqa: E402
from universe_loader import load_universe            # noqa: E402

PRICE_8H = os.path.join("data", "research_cache", "8h")
FUNDING = os.path.join("data", "history", "raw", "funding")
HORIZONS = [3, 9, 12]            # 1d, 3d, 4d in 8h bars; the lead lives at 4d (=12)
LEAD_H = 12
ZWIN = 90                        # ~30d rolling window for funding z (8h bars)
REPORT = os.path.join("docs", "reports", "phase6", "phase6-step6-funding-wide-retest.md")


def _load_close(sym: str):
    p = os.path.join(PRICE_8H, f"{sym}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p)
    if len(df) < 200:
        return None
    return pd.Series(df["close"].values, index=pd.to_datetime(df["timestamp"], unit="s")).sort_index()


def _load_funding_aligned(sym: str, index: pd.DatetimeIndex):
    p = os.path.join(FUNDING, f"{sym}.csv")
    if not os.path.exists(p):
        return None
    f = pd.read_csv(p)
    fr = pd.Series(f["funding_rate"].values,
                   index=pd.to_datetime(f["timestamp"], unit="s")).sort_index()
    return fr.reindex(fr.index.union(index)).ffill().reindex(index)


def main():
    universe = load_universe("sync")
    close_by, funding_by = {}, {}
    for s in universe:
        store = f"{s[:-4]}-USDT" if s.endswith("USDT") else s
        c = _load_close(store)
        if c is None:
            continue
        fa = _load_funding_aligned(store, c.index)
        if fa is None or fa.notna().sum() < 200:
            continue
        close_by[store], funding_by[store] = c, fa
    syms = sorted(close_by)
    n_sym = len(syms)
    bars = {s: len(close_by[s]) for s in syms}

    def revert(fund):
        return {s: -fund[s] for s in fund}

    def z_revert(fund):
        out = {}
        for s, v in fund.items():
            out[s] = -(v - v.rolling(ZWIN).mean()) / v.rolling(ZWIN).std()
        return out

    def xs_revert(fund):
        return {s: -d for s, d in cross_sectional_demean(fund).items()}

    batch = [("funding_revert", revert), ("funding_z_revert", z_revert),
             ("xs_funding_revert", xs_revert)]
    n_trials = (len(HY.REGISTRY) + len(HY.REGISTRY_BATCH2)) * 3 * 4 \
        + len(batch) * n_sym * len(HORIZONS)        # cumulative family

    rows = []
    for name, builder in batch:
        sig = builder(funding_by)
        res = H.evaluate_across_symbols(sig, close_by, HORIZONS, n_trials=n_trials)
        # breadth at the lead horizon (4d): per-symbol IC sign + significance
        ics = []
        for s in syms:
            r = res["per_symbol"][s]["per_horizon"][LEAD_H]["ic"]
            ics.append((s, r["ic"], r["p_value"]))
        valid = [(s, ic, p) for s, ic, p in ics if ic == ic]
        pos_sig = sum(1 for _, ic, p in valid if ic > 0 and p < 0.05)
        neg_sig = sum(1 for _, ic, p in valid if ic < 0 and p < 0.05)
        mean_ic = float(np.mean([ic for _, ic, _ in valid])) if valid else float("nan")
        rows.append((name, res["overall_verdict"], mean_ic, pos_sig, neg_sig, len(valid),
                     sum(1 for v in res["symbol_verdicts"].values() if v["verdict"] == "PROMOTE")))
        print(f"{name:20} -> {res['overall_verdict']} | mean_IC@4d={mean_ic:+.3f} "
              f"pos_sig={pos_sig}/{len(valid)} promoted_syms={rows[-1][6]}")

    L = ["# Phase 6 · Step 6 — Funding-Reversion Lead, Wider-Universe Re-test", "",
         f"_Pre-specified batch-3 funding hypotheses re-tested on {n_sym} symbols, "
         f"multi-year **8h** bars (native funding cadence; ~{int(np.median(list(bars.values())))} "
         f"bars/sym median). Horizons {HORIZONS} (1d/3d/4d); lead = 4d. Lookahead-safe "
         f"asof align. **Cumulative** family = {n_trials}, BH-FDR, default REJECT._", "",
         "## Lead breadth @ 4d horizon (the key question: does it generalise?)", "",
         "| hypothesis | overall | mean IC@4d | +IC & sig | symbols promoted |",
         "|---|---|---:|---|---:|"]
    for name, verdict, mic, pos, neg, nval, prom in rows:
        L.append(f"| {name} | **{verdict}** | {mic:+.3f} | {pos}/{nval} (neg-sig {neg}) | {prom}/{n_sym} |")
    fr_row = next(r for r in rows if r[0] == "funding_revert")
    L += ["",
          f"**Universe:** {n_sym} symbols with ≥200 aligned 8h funding+price bars.", "",
          ("**Lead holds / strengthens.**" if fr_row[1] == "PROMOTE" else
           "**Lead does NOT clear the gate even on wider/longer data.**")
          + f" funding_revert: mean IC@4d {fr_row[2]:+.3f}, {fr_row[3]}/{fr_row[5]} symbols "
          f"positive-and-significant, {fr_row[6]}/{n_sym} individually promoted, overall "
          f"{fr_row[1]}.",
          "",
          "_Honest read: a true funding-crowding reversion edge should show a positive "
          "mean IC@4d with a clear majority of symbols positive-and-significant. Read the "
          "breadth columns, not just the verdict. If breadth is weak/mixed, the BTC@4d "
          "result from batch 3 was likely idiosyncratic/sample-driven. No tuning, no "
          "execution simulation._"]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        f.write("\n".join(L) + "\n")
    print("WROTE", REPORT)


if __name__ == "__main__":
    main()
