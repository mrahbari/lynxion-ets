"""Step-3 first-pass edge discovery: run the pre-registered hypotheses through the
Step-1 predictive-power harness and report honest, multiple-testing-corrected
verdicts. Signal quality only — no SL/TP, sizing, cost, or trading simulation.

Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/run_discovery.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "measurement"))

import hypotheses as HY          # noqa: E402
import harness as H              # noqa: E402

SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
RAW_1M = os.path.join("data", "history", "raw", "1m")
RESAMPLE = "15min"
HORIZONS = [1, 4, 16, 96]        # 15m, 1h, 4h, 1d (in resampled bars)
REPORT = os.path.join("docs", "reports", "phase6", "phase6-step3-first-hypotheses.md")


def load_ohlcv(symbol: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(RAW_1M, f"{symbol}.csv"))
    df["dt"] = pd.to_datetime(df["timestamp"], unit="s")
    df = df.set_index("dt")
    ohlc = df.resample(RESAMPLE).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum")).dropna()
    return ohlc


def main():
    prices = {s: load_ohlcv(s) for s in SYMBOLS}
    bars = {s: len(df) for s, df in prices.items()}
    close_by = {s: df["close"] for s, df in prices.items()}
    n_trials = len(HY.REGISTRY) * len(SYMBOLS) * len(HORIZONS)  # program-wide family

    ledger = H.EdgeLedger()
    rows = []
    for name, hclass, builder in HY.REGISTRY:
        sig_by = builder(prices)
        res = H.evaluate_across_symbols(sig_by, close_by, HORIZONS, n_trials=n_trials)
        ledger.record(name, hclass, res)
        # best per-symbol IC for the table
        best = {}
        for sym, ph in res["per_symbol"].items():
            bh = max(ph["per_horizon"].values(),
                     key=lambda r: abs(r["ic"]["ic"]) if r["ic"]["ic"] == r["ic"]["ic"] else -1)
            best[sym] = (bh["horizon"], bh["ic"]["ic"], bh["ic"]["p_value"])
        rows.append((name, hclass, res["overall_verdict"], res["symbol_verdicts"], best))
        print(f"{name:26} {hclass:22} -> {res['overall_verdict']}")
    ledger.save()

    # ----- report -----
    L = ["# Phase 6 · Step 3 — First Signal Hypotheses (predictive-power results)",
         "",
         f"_Pre-registered batch of {len(HY.REGISTRY)} hypotheses, FROZEN params, run "
         f"ONCE through the Step-1 harness. BTC/ETH/SOL, 1m→{RESAMPLE} bars "
         f"({', '.join(f'{s}:{bars[s]}' for s in SYMBOLS)} bars), horizons {HORIZONS} "
         f"(15m/1h/4h/1d). Multiple-testing family = {n_trials} "
         f"({len(HY.REGISTRY)}×{len(SYMBOLS)}×{len(HORIZONS)}); BH-FDR, default "
         f"posture REJECT. Signal quality only — no SL/TP, cost, or simulation._", "",
         "## Verdicts", "",
         "| hypothesis | class | overall | best IC (sym@horizon) | per-symbol verdicts |",
         "|---|---|---|---|---|"]
    for name, hclass, verdict, sv, best in rows:
        bs = max(best.items(), key=lambda kv: abs(kv[1][1]) if kv[1][1] == kv[1][1] else -1)
        sym, (h, ic, p) = bs
        svstr = ", ".join(f"{s}:{v['verdict'][:4]}" for s, v in sv.items())
        L.append(f"| {name} | {hclass} | **{verdict}** | {sym}@{h}: IC={ic:+.3f} (p={p:.3f}) | {svstr} |")
    promoted = [r for r in rows if r[2] == "PROMOTE"]
    provisional = [r for r in rows if r[2] == "PROVISIONAL"]
    L += ["",
          f"**PROMOTE: {len(promoted)}** — {', '.join(r[0] for r in promoted) or 'none'}",
          f"**PROVISIONAL: {len(provisional)}** — {', '.join(r[0] for r in provisional) or 'none'}",
          f"**ARCHIVE: {sum(1 for r in rows if r[2] == 'ARCHIVE')}**", "",
          "Edge ledger: `research/edge_discovery/measurement/results/edge_ledger.json`.", "",
          "_Interpretation note: these are conventional OHLCV signals on a "
          "1-year sample. A PROMOTE here means a statistically robust, "
          "multiple-testing-corrected, cross-symbol-consistent predictive edge at "
          "the SIGNAL level — it does NOT yet imply tradeable profit (cost/geometry "
          "are evaluated later by the separate execution stack). PROVISIONAL = edge "
          "in some symbols but not cross-symbol robust. Funding/OI hypotheses are "
          "deferred until a longer history is backfilled (OI capped at ~30d)._"]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        f.write("\n".join(L) + "\n")
    print("WROTE", REPORT, f"| promote={len(promoted)} provisional={len(provisional)}")


if __name__ == "__main__":
    main()
