"""Step-4 edge discovery (batch 2): test the batch-1 lead — short-horizon
reversion was BH-significant cross-symbol but failed MONOTONICITY, so its edge is
at the extremes. Batch 2 emphasises the tails. Cumulative multiple-testing family
(batch1 + batch2). IN-SAMPLE-MOTIVATED → flagged for OOS confirmation.

Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/run_batch2.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "measurement"))

import hypotheses as HY          # noqa: E402
import harness as H              # noqa: E402
from run_discovery import load_ohlcv, SYMBOLS, HORIZONS  # noqa: E402

REPORT = os.path.join("docs", "reports", "phase6", "phase6-step4-hypothesis-batch2.md")


def main():
    prices = {s: load_ohlcv(s) for s in SYMBOLS}
    close_by = {s: prices[s]["close"] for s in SYMBOLS}
    # CUMULATIVE family: all hypotheses tested across the program so far.
    n_trials = (len(HY.REGISTRY) + len(HY.REGISTRY_BATCH2)) * len(SYMBOLS) * len(HORIZONS)

    rows = []
    for name, hclass, builder in HY.REGISTRY_BATCH2:
        res = H.evaluate_across_symbols(builder(prices), close_by, HORIZONS, n_trials=n_trials)
        detail = {}
        for sym, ph in res["per_symbol"].items():
            bh = max(ph["per_horizon"].values(),
                     key=lambda r: abs(r["ic"]["ic"]) if r["ic"]["ic"] == r["ic"]["ic"] else -1)
            detail[sym] = (bh["horizon"], bh["ic"]["ic"], bh["ic"]["p_value"],
                           bh["decile"]["monotonicity"])
        rows.append((name, hclass, res["overall_verdict"], res["symbol_verdicts"], detail))
        print(f"{name:26} {hclass:30} -> {res['overall_verdict']}")

    L = ["# Phase 6 · Step 4 — Hypothesis Batch 2 (extreme-reversion lead)", "",
         f"_Batch-1 found short-horizon reversion BH-significant cross-symbol but "
         f"NON-monotonic (edge at the extremes). Batch 2 tests extreme-emphasis forms "
         f"(zero in the middle band). BTC/ETH/SOL, 15m bars, horizons {HORIZONS}. "
         f"**Cumulative** multiple-testing family = {n_trials} (batch1+batch2), BH-FDR, "
         f"default REJECT._", "",
         "⚠️ **In-sample-motivated:** these forms were derived from batch-1 on the SAME "
         "1-year data, so a PROMOTE here is weaker evidence and REQUIRES true "
         "out-of-sample confirmation on a later, untouched period before any reliance.",
         "",
         "## Verdicts (does emphasising extremes fix the monotonicity?)", "",
         "| hypothesis | overall | best IC (sym@h) | decile monotonicity@best | per-symbol |",
         "|---|---|---|---|---|"]
    for name, hclass, verdict, sv, detail in rows:
        bs = max(detail.items(), key=lambda kv: abs(kv[1][1]) if kv[1][1] == kv[1][1] else -1)
        sym, (h, ic, p, mono) = bs
        svstr = ", ".join(f"{s}:{v['verdict'][:4]}" for s, v in sv.items())
        L.append(f"| {name} | **{verdict}** | {sym}@{h}: {ic:+.3f} (p={p:.3f}) | "
                 f"{mono:+.2f} | {svstr} |")
    promoted = [r for r in rows if r[2] == "PROMOTE"]
    L += ["",
          f"**PROMOTE: {len(promoted)}** — {', '.join(r[0] for r in promoted) or 'none'}",
          f"**ARCHIVE/PROVISIONAL: {len(rows) - len(promoted)}**", "",
          "Edge ledger: `research/edge_discovery/measurement/results/edge_ledger.json`.", "",
          "_If extreme-emphasis raised decile monotonicity above the gate (≥0.6, sign "
          "matching IC) AND it stayed BH-significant cross-symbol under the cumulative "
          "family, the lead survives as a candidate — still pending OOS confirmation. "
          "Otherwise the reversion lead is rejected and the search continues with new "
          "hypothesis classes (cross-sectional / carry once funding history is "
          "backfilled). No tuning, no execution simulation._"]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        f.write("\n".join(L) + "\n")
    print("WROTE", REPORT, f"| promote={len(promoted)}")


if __name__ == "__main__":
    main()
