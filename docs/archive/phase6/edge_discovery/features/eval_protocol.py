"""Shared full-protocol evaluator + cumulative edge ledger for Roadmap A.

Every hypothesis class runs the IDENTICAL rigorous protocol:
  harness IC (HAC) + decile + purged/embargoed CV  →  explicit OOS split (70/30)
  →  cost gate (non-overlapping sign-strategy, net-of-cost with t-stat).

Default verdict REJECT. PROMOTE only if: harness verdict ∈ {PROMOTE, PROVISIONAL}
with cross-symbol breadth, AND OOS mean-IC keeps the IS sign, AND the cost gate is
robustly net-positive (net>0, ≥500 trades, t(net)≥2). No optimization/sweeps.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "measurement"))

import harness as H                                  # noqa: E402
from forward_labels import vol_normalized_forward_returns  # noqa: E402
from predictive_power import information_coefficient       # noqa: E402

LEDGER_JSON = os.path.join(HERE, "..", "measurement", "results", "roadmapA_ledger.json")
LEDGER_MD = os.path.join("docs", "reports", "phase6", "PHASE6.6-roadmapA-edge-ledger.md")
COST_BPS = 10
MIN_N, MIN_T = 500, 2.0


def _cost_gate(signal_by, close_by, horizon, cost_bps=COST_BPS):
    """Non-overlapping sign-strategy at `horizon` bars, pooled across symbols."""
    pooled = []
    for s, sig in signal_by.items():
        c = close_by.get(s)
        if c is None:
            continue
        vals = sig.reindex(c.index).values
        px = c.values
        n = len(px)
        t = 0
        while t < n - horizon:
            v = vals[t]
            if v == v and v != 0:
                pooled.append(np.sign(v) * (px[t + horizon] / px[t] - 1.0))
                t += horizon
            else:
                t += 1
    arr = np.array(pooled)
    if len(arr) == 0:
        return {"n": 0, "gross_bps": float("nan"), "net_bps": float("nan"),
                "t_net": 0.0, "win": float("nan")}
    gross = float(arr.mean()) * 1e4
    net = gross - cost_bps
    se = float(arr.std(ddof=1)) * 1e4 / np.sqrt(len(arr)) if len(arr) > 1 else float("inf")
    return {"n": len(arr), "gross_bps": gross, "net_bps": net,
            "t_net": (net / se if se > 0 else 0.0), "win": float((arr > 0).mean()) * 100}


def _oos_split_ic(signal_by, close_by, horizon, oos_frac=0.30):
    is_ics, oos_ics = [], []
    for s, sig in signal_by.items():
        c = close_by.get(s)
        if c is None:
            continue
        label = vol_normalized_forward_returns(c, [horizon])[f"fwd_{horizon}"]
        cut = int(len(c) * (1 - oos_frac))
        idx = c.index
        a = information_coefficient(sig.reindex(idx[:cut]), label.reindex(idx[:cut]), horizon)
        b = information_coefficient(sig.reindex(idx[cut:]), label.reindex(idx[cut:]), horizon)
        if a["ic"] == a["ic"]:
            is_ics.append(a["ic"])
        if b["ic"] == b["ic"]:
            oos_ics.append(b["ic"])
    return (float(np.mean(is_ics)) if is_ics else float("nan"),
            float(np.mean(oos_ics)) if oos_ics else float("nan"))


def full_eval(name, hclass, signal_by, close_by, horizons, n_trials, cost_bps=COST_BPS):
    res = H.evaluate_across_symbols(signal_by, close_by, horizons, n_trials=n_trials)
    # best horizon by |mean IC|
    best_h, best_mic = horizons[-1], 0.0
    for h in horizons:
        ics = [res["per_symbol"][s]["per_horizon"][h]["ic"]["ic"]
               for s in signal_by if res["per_symbol"].get(s)]
        ics = [x for x in ics if x == x]
        mic = float(np.mean(ics)) if ics else 0.0
        if abs(mic) > abs(best_mic):
            best_mic, best_h = mic, h
    cells = [res["per_symbol"][s]["per_horizon"][best_h]["ic"] for s in signal_by
             if res["per_symbol"].get(s)]
    nval = sum(1 for r in cells if r["ic"] == r["ic"])
    breadth = sum(1 for r in cells if r["ic"] == r["ic"]
                  and np.sign(r["ic"]) == np.sign(best_mic) and r["p_value"] < 0.05)
    is_ic, oos_ic = _oos_split_ic(signal_by, close_by, best_h)
    cg = _cost_gate(signal_by, close_by, best_h, cost_bps)

    breadth_ok = nval > 0 and breadth >= max(2, int(0.4 * nval))
    oos_ok = oos_ic == oos_ic and np.sign(oos_ic) == np.sign(best_mic) and best_mic != 0
    cost_ok = cg["net_bps"] > 0 and cg["n"] >= MIN_N and cg["t_net"] >= MIN_T
    harness_ok = res["overall_verdict"] in ("PROMOTE", "PROVISIONAL")
    promote = harness_ok and breadth_ok and oos_ok and cost_ok
    reasons = []
    if not harness_ok: reasons.append(f"harness={res['overall_verdict']}")
    if not breadth_ok: reasons.append(f"breadth {breadth}/{nval}")
    if not oos_ok: reasons.append(f"OOS IC {oos_ic:+.3f} vs IS {is_ic:+.3f}")
    if not cost_ok: reasons.append(f"cost net {cg['net_bps']:+.1f}bps t={cg['t_net']:+.1f} n={cg['n']}")

    entry = {"class": name, "taxonomy": hclass, "symbols": nval,
             "best_horizon": best_h, "mean_ic": round(best_mic, 4),
             "breadth_sig": f"{breadth}/{nval}", "is_ic": round(is_ic, 4),
             "oos_ic": round(oos_ic, 4), "gross_bps": round(cg["gross_bps"], 1),
             "net_bps": round(cg["net_bps"], 1), "t_net": round(cg["t_net"], 1),
             "n_trades": cg["n"], "harness_verdict": res["overall_verdict"],
             "verdict": "PROMOTE" if promote else "REJECT",
             "reject_reasons": "; ".join(reasons) if not promote else ""}
    print(f"  {name}: {entry['verdict']} | IC@{best_h}={best_mic:+.3f} breadth={breadth}/{nval} "
          f"OOS={oos_ic:+.3f} net={cg['net_bps']:+.1f}bps t={cg['t_net']:+.1f} n={cg['n']}")
    return entry


def append_ledger(entry):
    os.makedirs(os.path.dirname(LEDGER_JSON), exist_ok=True)
    entries = []
    if os.path.exists(LEDGER_JSON):
        entries = json.load(open(LEDGER_JSON))
    entries.append(entry)
    json.dump(entries, open(LEDGER_JSON, "w"), indent=2)
    # rewrite cumulative markdown
    L = ["# Phase 6.6 — Roadmap A Cumulative Edge Ledger", "",
         "_Free-data hypothesis classes run through the full Phase-6 protocol "
         "(HAC IC · purged/embargoed CV · multiple-testing · OOS split · cost gate). "
         "Default REJECT. PROMOTE only if significant + cross-symbol + OOS-stable + "
         "robustly net-positive after 10 bps. No optimization/sweeps._", "",
         "| # | class | taxonomy | IC@h | breadth sig | OOS IC | gross bps | net@10 | t(net) | n | verdict |",
         "|---|---|---|---:|---|---:|---:|---:|---:|---:|---|"]
    for i, e in enumerate(entries, 1):
        L.append(f"| {i} | {e['class']} | {e['taxonomy']} | {e['mean_ic']:+.3f}@{e['best_horizon']} | "
                 f"{e['breadth_sig']} | {e['oos_ic']:+.3f} | {e['gross_bps']:+.1f} | "
                 f"{e['net_bps']:+.1f} | {e['t_net']:+.1f} | {e['n_trades']} | **{e['verdict']}** |")
    promoted = [e for e in entries if e["verdict"] == "PROMOTE"]
    L += ["", f"**Classes evaluated:** {len(entries)} · **PROMOTED:** {len(promoted)} "
          f"({', '.join(e['class'] for e in promoted) or 'none'})", ""]
    for e in entries:
        if e["verdict"] == "REJECT":
            L.append(f"- ❌ **{e['class']}** rejected: {e['reject_reasons']}")
        else:
            L.append(f"- ✅ **{e['class']}** PROMOTED — tradeable-edge candidate.")
    os.makedirs(os.path.dirname(LEDGER_MD), exist_ok=True)
    open(LEDGER_MD, "w").write("\n".join(L) + "\n")
    return LEDGER_MD
