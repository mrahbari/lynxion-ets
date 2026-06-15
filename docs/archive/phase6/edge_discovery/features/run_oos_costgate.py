"""Step-9: OOS confirmation + cost gate for the one lead — revert_highvol_3
(short-horizon reversion gated to high-vol regime), the only breadth-backed signal.

(1) OOS: split each symbol's 8h series into IS (first 70%) / OOS (last 30%, never
    used to select the hypothesis). Does the IC + cross-symbol breadth persist OOS?
(2) Cost gate: trade sign(signal) on each active (high-vol) bar, hold 1 bar (8h);
    gross vs NET expectancy after realistic round-trip cost; breakeven cost. A small
    IC may not survive costs — that is the Phase-5 lesson (signal edge != profit).

Lookahead-safe (signal[t] uses <= t; forward returns are future). No SL/TP ladder,
sizing, or full simulation — a decoupled cost-adjusted expectancy check.

Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/run_oos_costgate.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "measurement"))

import feature_library as F                          # noqa: E402
from forward_labels import vol_normalized_forward_returns  # noqa: E402
from predictive_power import information_coefficient       # noqa: E402
from universe_loader import load_universe            # noqa: E402

PRICE_8H = os.path.join("data", "research_cache", "8h")
VOL_WIN, MED_WIN, LOOKBACK = 30, 90, 3
OOS_FRAC = 0.30
COSTS_BPS = [5, 10, 20]          # round-trip cost scenarios
REPORT = os.path.join("docs", "reports", "phase6", "phase6-step9-oos-costgate.md")


def _load_close(store):
    p = os.path.join(PRICE_8H, f"{store}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p)
    return pd.Series(df["close"].values, index=pd.to_datetime(df["timestamp"], unit="s")).sort_index() \
        if len(df) >= 300 else None


def _signal(close):
    """revert_highvol_3: -ret(3), active only in high-vol regime (trailing, no lookahead)."""
    vol = close.pct_change().rolling(VOL_WIN).std()
    med = vol.rolling(MED_WIN).median()
    high = (vol > med) & med.notna()
    return (-F.past_return(close, LOOKBACK)).where(high)


def main():
    closes = {}
    for s in load_universe("sync"):
        store = f"{s[:-4]}-USDT" if s.endswith("USDT") else s
        c = _load_close(store)
        if c is not None:
            closes[store] = c
    syms = sorted(closes)

    # ---------- (1) OOS confirmation ----------
    is_ics, oos_ics = [], []
    is_pos = oos_pos = 0
    for s in syms:
        c = closes[s]
        sig = _signal(c)
        label = vol_normalized_forward_returns(c, [1])["fwd_1"]
        cut = int(len(c) * (1 - OOS_FRAC))
        idx = c.index
        is_slice, oos_slice = idx[:cut], idx[cut:]
        ic_is = information_coefficient(sig.reindex(is_slice), label.reindex(is_slice), 1)
        ic_oos = information_coefficient(sig.reindex(oos_slice), label.reindex(oos_slice), 1)
        if ic_is["ic"] == ic_is["ic"]:
            is_ics.append(ic_is["ic"]); is_pos += (ic_is["ic"] > 0 and ic_is["p_value"] < 0.05)
        if ic_oos["ic"] == ic_oos["ic"]:
            oos_ics.append(ic_oos["ic"]); oos_pos += (ic_oos["ic"] > 0 and ic_oos["p_value"] < 0.05)
    mean_is, mean_oos = float(np.mean(is_ics)), float(np.mean(oos_ics))

    # ---------- (2) Cost gate (on OOS bars; raw forward 8h return) ----------
    pooled = []
    for s in syms:
        c = closes[s]
        sig = _signal(c)
        fwd_raw = c.shift(-1) / c - 1.0                # forward 8h return (raw, for $ costs)
        cut = int(len(c) * (1 - OOS_FRAC))
        oos = c.index[cut:]
        sub = pd.concat([sig.reindex(oos).rename("s"), fwd_raw.reindex(oos).rename("y")],
                        axis=1).dropna()
        sub = sub[sub["s"] != 0]
        if len(sub):
            pooled.append(pd.DataFrame({"pos": np.sign(sub["s"]), "fwd": sub["y"]}))
    allt = pd.concat(pooled, ignore_index=True) if pooled else pd.DataFrame(columns=["pos", "fwd"])
    n_tr = len(allt)
    gross = float((allt["pos"] * allt["fwd"]).mean()) if n_tr else float("nan")
    net = {c: gross - c / 1e4 for c in COSTS_BPS}
    win = float(((allt["pos"] * allt["fwd"]) > 0).mean()) if n_tr else float("nan")
    breakeven_bps = gross * 1e4

    oos_strengthens = mean_oos > 0 and oos_pos >= len(syms) * 0.4
    survives_10 = net[10] > 0

    L = ["# Phase 6 · Step 9 — OOS Confirmation + Cost Gate (revert_highvol_3)", "",
         f"_The only breadth-backed lead. {len(syms)} symbols, 8h bars. OOS = last "
         f"{int(OOS_FRAC*100)}% of each series (untouched by hypothesis selection). "
         f"Cost gate trades sign(signal) on each high-vol bar, holds 8h. Signal-"
         f"decoupled cost-adjusted expectancy — no SL/TP ladder or full sim._", "",
         "## (1) Out-of-sample confirmation (IC@8h)", "",
         "| segment | mean IC | symbols +IC & sig |",
         "|---|---:|---:|",
         f"| in-sample (first 70%) | {mean_is:+.3f} | {is_pos}/{len(syms)} |",
         f"| **OOS (last 30%)** | **{mean_oos:+.3f}** | **{oos_pos}/{len(syms)}** |",
         "",
         ("✅ **Edge persists OOS.**" if oos_strengthens else
          "❌ **Edge does NOT hold OOS** (mean IC collapses / breadth drops) — the "
          "full-sample result was period-dependent."),
         "",
         "## (2) Cost gate (OOS, per-trade expectancy)", "",
         f"- **Trades** (high-vol active bars, OOS): {n_tr:,}",
         f"- **Gross** mean return/trade: **{gross*1e4:+.1f} bps** (win rate {win*100:.1f}%)",
         f"- **Breakeven round-trip cost:** {breakeven_bps:.1f} bps",
         f"- **Net @ 5 bps:** {net[5]*1e4:+.1f} bps · **@ 10 bps:** {net[10]*1e4:+.1f} bps "
         f"· **@ 20 bps:** {net[20]*1e4:+.1f} bps",
         "",
         ("✅ **Survives a 10 bps round-trip cost.**" if survives_10 else
          "❌ **Does NOT survive realistic costs** — gross edge is smaller than the "
          "~10 bps round-trip cost (Phase-5's cost cliff). Signal-level edge, but not "
          "tradeable at 8h turnover."),
         "",
         "## Verdict", "",
         (("**CONFIRMED candidate** — edge persists OOS AND clears 10 bps. Next: proper "
           "execution evaluation (SL/TP, sizing, slippage) via the Phase-5 stack, then "
           "paper trading.") if (oos_strengthens and survives_10) else
          ("**REJECTED at the cost gate** — " + ("OOS edge held but " if oos_strengthens
           else "OOS edge weak and ") + "net-of-cost expectancy is not positive at "
           "realistic 8h-turnover costs. A real signal-level effect that is not "
           "tradeable as-is; would need lower turnover (longer hold), a wider-spread-"
           "free venue, or larger gross edge.")),
         "",
         "_No tuning, no curve-fitting. Honest read regardless of outcome._"]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"OOS mean IC: IS {mean_is:+.3f} -> OOS {mean_oos:+.3f} ({oos_pos}/{len(syms)} sig)")
    print(f"COST GATE: gross {gross*1e4:+.1f}bps | net@10 {net[10]*1e4:+.1f}bps | "
          f"breakeven {breakeven_bps:.1f}bps | trades {n_tr}")
    print("WROTE", REPORT)


if __name__ == "__main__":
    main()
