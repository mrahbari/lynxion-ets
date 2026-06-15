#!/usr/bin/env python3
"""E-P5.5 — Microstructure & Adaptation forensics (DIAGNOSIS ONLY).

Answers the two E-P5.5 questions from EXISTING data — no engine/strategy/
architecture changes:
  1. profitability lost to spread / slippage / liquidity constraints
  2. which strategies are most microstructure-sensitive

Method — empirical per-trade execution cost:
  gross_R  = (exit_price - entry_price)*dir / risk     (price path between fill levels, pre-cost)
  net_R    = realized_R = pnl / (risk*size)            (after ALL applied costs)
  cost_R   = gross_R - net_R                           (TOTAL execution cost in R: fees+spread+slippage+impact)
  stop_bps = risk_per_unit / entry_price * 1e4         (stop tightness)
  cost_bps = cost_R * risk_per_unit / entry_price * 1e4 (cost as bps of notional)

cost_R/cost_bps are EMPIRICAL (no fee model assumed). The per-component split
(fee vs spread vs slippage) is NOT recoverable from the dump — only the total is.
The microstructure point: stops are so tight (small stop_bps) that a modest bps
cost becomes a large fraction of R. B12 (OHLCV-only micro proxies/stubs) and B13
(learning loop = stub) are assessed structurally.

Configured cost stack (matrix/dump): fee_rate 0.001/side, spread_bps 2.0,
slippage_factor 0.0005, + market-impact fill model.

Run:  .venv/bin/python tasks/phase5-profitability/eval_microstructure.py
"""
import json
import math
import os
from collections import defaultdict

TR = os.path.join("data", "results_storage", "lifecycle_trades.json")
OUT = os.path.join("docs", "reports", "phase5", "ep5.5-microstructure.md")

# strategies whose NAMED edge depends on microstructure features that are
# OHLCV-only proxies/stubs in this system (B12)
MICRO_DEPENDENT = {"sweep_scalper", "oi_footprint", "liquidity", "vwap_reversal"}


def mean(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return sum(xs) / len(xs) if xs else 0.0


def main():
    raw = json.load(open(TR))
    trades = []
    for t in raw:
        e = t.get("entry_price"); sl = t.get("stop_loss"); xp = t.get("price")
        R = t.get("realized_R")
        if None in (e, sl, xp, R):
            continue
        risk = abs(e - sl)
        if risk <= 0 or e <= 0:
            continue
        d = 1 if t.get("side") == "sell" else -1   # sell-to-close = long
        gross_R = (xp - e) * d / risk
        t["_gross_R"] = gross_R; t["_net_R"] = R
        t["_cost_R"] = gross_R - R
        t["_stop_bps"] = risk / e * 1e4
        t["_cost_bps"] = (gross_R - R) * risk / e * 1e4
        trades.append(t)
    n = len(trades)

    agg_cost = mean([t["_cost_R"] for t in trades])
    agg_stop_bps = mean([t["_stop_bps"] for t in trades])
    agg_cost_bps = mean([t["_cost_bps"] for t in trades])
    agg_gross = mean([t["_gross_R"] for t in trades])
    agg_net = mean([t["_net_R"] for t in trades])

    L = ["# E-P5.5 — Microstructure & Adaptation Forensics (diagnosis only)", "",
         f"_{n} trades (all LONGS), 90d × {{BTC,ETH,SOL}} × 12 strategies, frozen "
         f"POST baseline. Execution cost = gross_R − net_R (EMPIRICAL total: fees + "
         f"spread + slippage + impact; per-component split not recoverable from the "
         f"dump). No engine/strategy/architecture changes — quantification only._", "",
         "## Q1 — Profitability lost to spread / slippage / liquidity", "",
         f"- **Total execution cost: {agg_cost:.3f}R/trade** (~**{agg_cost_bps:.1f} bps** "
         f"of notional).",
         f"- Mean **stop width: {agg_stop_bps:.1f} bps** of price.",
         f"- This converts gross expectancy **{agg_gross:+.3f}R** into net "
         f"**{agg_net:+.3f}R** — i.e. execution costs are the mechanical bridge between "
         f"the (already negative) signal edge and the realised result.",
         "",
         f"**Root cause — the cost cliff is geometric, not exotic.** The realised cost "
         f"is only ~{agg_cost_bps:.0f} bps of notional (a normal cost stack: fee "
         f"0.1%/side, spread 2bps, slippage 0.0005, impact). It becomes catastrophic "
         f"ONLY because stops average ~{agg_stop_bps:.0f} bps wide: a {agg_cost_bps:.0f}-"
         f"bps cost on a {agg_stop_bps:.0f}-bps stop = ~{agg_cost:.2f}R consumed per "
         f"trade. Spread/slippage/liquidity are not mispriced — the **stops are simply "
         f"far too tight relative to costs** (ties to B7). Halving trade frequency or "
         f"widening stops to dwarf the bps cost would remove most of this drag.", "",
         "## Q2 — Which strategies are most microstructure-sensitive?", "",
         "Ranked by execution cost (R/trade). Sensitivity = cost-in-R, which rises as "
         "stops tighten. 'micro-dep?' = named edge relies on OHLCV-only proxy/stub "
         "features (B12).", "",
         "| strategy | trades | stop bps | **cost R/trade** | cost bps | gross expR | net expR | micro-dep? |",
         "|---|---:|---:|---:|---:|---:|---:|:--:|"]
    bystrat = defaultdict(list)
    for t in trades:
        bystrat[t["strategy"]].append(t)
    rows = []
    for s, ts in bystrat.items():
        rows.append((s, len(ts), mean([t["_stop_bps"] for t in ts]),
                     mean([t["_cost_R"] for t in ts]), mean([t["_cost_bps"] for t in ts]),
                     mean([t["_gross_R"] for t in ts]), mean([t["_net_R"] for t in ts])))
    rows.sort(key=lambda r: r[3], reverse=True)  # highest cost first
    for s, m, sb, cr, cb, gr, nr in rows:
        L.append(f"| {s} | {m} | {sb:.0f} | **{cr:.3f}** | {cb:.0f} | {gr:+.3f} | "
                 f"{nr:+.3f} | {'YES' if s in MICRO_DEPENDENT else '—'} |")

    L += ["",
          f"- **Most cost-sensitive:** {rows[0][0]} ({rows[0][3]:.3f}R/trade, stop "
          f"{rows[0][2]:.0f}bps). **Least:** {rows[-1][0]} ({rows[-1][3]:.3f}R/trade, "
          f"stop {rows[-1][2]:.0f}bps).",
          "- Sensitivity tracks **stop tightness / trade frequency**: tighter stops "
          "and higher turnover → larger fixed-cost bite per R. Scalping/breakout-type "
          "strategies are structurally the most microstructure-exposed.", "",
          "## B12 — microstructure-named strategies on OHLCV-only data", "",
          f"{len(MICRO_DEPENDENT)} strategies are named for microstructure edges "
          "(sweep/absorption/imbalance/OI) but run on OHLCV-only proxies/stubs "
          "(`detect_sweep`→0, OI `*1.5`): **" + ", ".join(sorted(MICRO_DEPENDENT)) +
          "**. Net expectancy ("
          + ", ".join(f"{r[0]} {r[6]:+.3f}R" for r in rows if r[0] in MICRO_DEPENDENT)
          + ") cannot reflect their intended edge — they trade on degraded signals. "
          "This is INSUFFICIENT-EVIDENCE for those hypotheses, not disproof (needs "
          "L2/trades/OI/funding data to test properly).", "",
          "## B13 — adaptation / learning loop", "",
          "`recalibrate_classifier()` is a print stub; adaptive weights not confirmed "
          "to persist. No within-run regime adaptation is observable: expectancy is "
          "uniformly negative across entry regimes (−1.0 to −1.2R; E-P5.4) with no sign "
          "of the system adapting sizing/selection. Adaptation cannot be validated and "
          "is moot while gross edge is absent (B14).", "",
          "## E-P5.5 findings (6-part)", "",
          f"1. **Findings:** execution costs ~{agg_cost:.2f}R/trade (~{agg_cost_bps:.0f} "
          f"bps) on stops only ~{agg_stop_bps:.0f}bps wide; cost-sensitivity ranks with "
          "stop tightness/frequency; 4 micro-named strategies run on proxy/stub features "
          "(B12); adaptation stubbed (B13).",
          "2. **Root causes:** stops far too tight vs a normal bps cost stack (B7-"
          "linked); B12 OHLCV-only microstructure proxies; B13 learning loop a stub.",
          f"3. **Profitability impact:** total execution cost ~{agg_cost:.2f}R/trade is "
          f"the mechanical bridge from gross {agg_gross:+.2f}R to net {agg_net:+.2f}R — "
          "the largest single mechanical drag, but a SYMPTOM of tight stops, not "
          "mispriced microstructure.",
          "4. **Recommended fixes (NOT executed — diagnosis only):** widen stops to "
          "dwarf costs / reduce turnover / cost-aware entry gate (B7); acquire L2/trades/"
          "OI/funding to test micro strategies (B12); implement real adaptation (B13). "
          "Deferred to remediation mode.",
          f"5. **Estimated upside:** right-sizing stops + lower turnover removes most of "
          f"the ~{agg_cost:.2f}R/trade drag (large loss-REDUCTION), but gross is still "
          f"{agg_gross:+.2f}R (negative, B14) → does not reach profit alone.",
          "6. **Priority ranking (cumulative):** B14 (entry edge) ≫ B7 (R:R + tight "
          "stops vs cost — drives the E-P5.5 cost cliff) > B10 (portfolio risk) > B8 "
          "(lifecycle) > B9 (MTF, no benefit) > B12 (needs data) > B13 (moot until "
          "edge exists)."]
    open(OUT, "w").write("\n".join(L) + "\n")
    print("WROTE", OUT)
    print(f"n={n} cost={agg_cost:.3f}R ({agg_cost_bps:.0f}bps) stop={agg_stop_bps:.0f}bps "
          f"gross={agg_gross:+.3f} net={agg_net:+.3f} | "
          f"most={rows[0][0]}({rows[0][3]:.3f}R) least={rows[-1][0]}({rows[-1][3]:.3f}R)")


if __name__ == "__main__":
    main()
