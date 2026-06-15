#!/usr/bin/env python3
"""Generate per-strategy edge reports, diagnosis, and a comparative ranking
from the eval matrix (eval_matrix.json). Diagnosis-first (not elimination):
for each losing strategy, surface regime mismatch / signal-quality / execution
/ trade-mgmt / risk hypotheses and improvement/redesign opportunities.

Run from repo root:  .venv/bin/python tasks/phase5-evaluate/eval_report.py
"""
import json
import os
from collections import defaultdict
from statistics import mean, pstdev

IN = os.path.join("data", "results_storage", "eval_matrix.json")
OUT_DIR = os.path.join("tasks", "phase5-evaluate")

# Each strategy's intended "home" regime(s) — the conditions its hypothesis
# targets. Used to flag regime mismatch (losing in its home regime, or only
# losing away from it).
HYPOTHESIS = {
    "trend_following": ("ride established trends", {"trending_up", "trending_down"}),
    "mean_reversion": ("fade extremes back to mean", {"ranging"}),
    "momentum": ("follow strong directional momentum", {"trending_up", "trending_down"}),
    "scalping": ("many small short-horizon edges", set()),
    "breakout": ("enter on range/volatility breakouts", {"trending_up", "trending_down"}),
    "crypto_breakout": ("enter on range/volatility breakouts", {"trending_up", "trending_down"}),
    "liquidity": ("exploit liquidity sweeps / ranges", {"ranging"}),
    "mtf_trend": ("multi-timeframe trend alignment", {"trending_up", "trending_down"}),
    "oi_footprint": ("open-interest footprint (needs OI data — proxy/stub)", set()),
    "sweep_scalper": ("microstructure sweeps (needs L2 — proxy/stub)", set()),
    "vwap_reversal": ("revert to VWAP from extension", {"ranging"}),
    "volatility_breakout": ("expansion from low to high volatility", {"trending_up", "trending_down"}),
}
PROXY_STUB = {"oi_footprint", "sweep_scalper"}  # depend on data we don't have (OHLCV-only)


def _f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def load():
    rows = json.load(open(IN))
    return [r for r in rows if r.get("status") == "ok"]


def per_strategy(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["strategy"]].append(r)
    return by


def regime_totals(runs):
    agg = defaultdict(float)
    for r in runs:
        for reg, pnl in (r.get("by_regime") or {}).items():
            agg[reg] += _f(pnl)
    return dict(agg)


def diagnose(strat, runs):
    """Return (verdict_summary, diagnosis_lines, scores)."""
    wins = [r for r in runs]
    win_rates = [_f(r.get("win_rate")) for r in runs if r.get("win_rate") is not None]
    sharpes = [_f(r.get("sharpe")) for r in runs if r.get("sharpe") is not None]
    sortinos = [_f(r.get("sortino")) for r in runs if r.get("sortino") is not None]
    mdds = [_f(r.get("max_drawdown")) for r in runs if r.get("max_drawdown") is not None]
    pnls = [_f(r.get("total_pnl")) for r in runs]
    trades = [_f(r.get("closed_trades")) for r in runs]
    fees = [_f(r.get("total_fees")) for r in runs]
    avg_win_rate = mean(win_rates) if win_rates else 0.0
    avg_sharpe = mean(sharpes) if sharpes else 0.0
    avg_mdd = mean(mdds) if mdds else 0.0
    total_pnl = sum(pnls)
    total_trades = sum(trades)
    total_fees = sum(fees)
    reg = regime_totals(runs)
    worst_reg = min(reg.items(), key=lambda kv: kv[1]) if reg else (None, 0)
    best_reg = max(reg.items(), key=lambda kv: kv[1]) if reg else (None, 0)
    hyp_text, home = HYPOTHESIS.get(strat, ("(unspecified)", set()))

    lines = []
    lines.append(f"- **Hypothesis:** {hyp_text}")
    if strat in PROXY_STUB:
        lines.append("- **DATA LIMITATION:** depends on order-flow/microstructure data not available "
                     "(OHLCV-only). Its signal is a proxy/stub → results reflect the proxy, not the hypothesis. "
                     "**Redesign/needs-data**, not invalid hypothesis.")
    # regime mismatch
    if home and worst_reg[0] in home:
        lines.append(f"- **Regime mismatch (severe):** loses MOST in its target regime "
                     f"`{worst_reg[0]}` ({worst_reg[1]:.0f}) — the hypothesis's home ground. "
                     f"Signal/timing or directional bias likely inverted there.")
    elif home and best_reg[0] in home and best_reg[1] < 0:
        lines.append(f"- **Regime alignment present but unprofitable:** least-bad in its target "
                     f"regime `{best_reg[0]}` ({best_reg[1]:.0f}) yet still negative → edge too weak "
                     f"to overcome costs; needs filters/threshold tuning.")
    elif home:
        lines.append(f"- **Regime:** worst `{worst_reg[0]}` ({worst_reg[1]:.0f}), best `{best_reg[0]}` "
                     f"({best_reg[1]:.0f}); target regimes {sorted(home)}.")
    else:
        lines.append(f"- **Regime:** worst `{worst_reg[0]}` ({worst_reg[1]:.0f}), best `{best_reg[0]}` ({best_reg[1]:.0f}).")
    # signal quality
    if avg_win_rate < 0.40:
        lines.append(f"- **Signal quality:** low win rate ({avg_win_rate:.0%}) → entries poorly timed / "
                     f"insufficient confirmation. Add confirmation filters (volume, MTF, regime gate).")
    else:
        lines.append(f"- **Signal quality:** win rate {avg_win_rate:.0%}.")
    # cost / execution
    if total_trades and total_fees > abs(total_pnl) * 0.25:
        lines.append(f"- **Execution/cost weakness:** fees ({total_fees:.0f}) are large vs net P&L "
                     f"({total_pnl:.0f}) → over-trading / cost drag. Widen entries, raise conviction threshold.")
    # trade management / risk
    if avg_mdd < -0.5:
        lines.append(f"- **Risk/trade-mgmt:** deep max drawdown ({avg_mdd:.0%}) → SL/TP or sizing too loose; "
                     f"tighten stops / cap exposure.")
    elif avg_mdd < -0.2:
        lines.append(f"- **Risk:** notable drawdown ({avg_mdd:.0%}); review SL/TP placement.")
    # trade frequency
    avg_trades = mean(trades) if trades else 0
    if avg_trades and avg_trades < 8:
        lines.append(f"- **Evidence:** low trade count (~{avg_trades:.0f}/run) → discipline-throttled or "
                     f"rare signals; conclusions tentative, gather more data.")

    # improvement / redesign default
    if strat in PROXY_STUB:
        verdict_line = "needs-data / redesign (proxy signal)"
    elif avg_win_rate < 0.35 or (home and worst_reg[0] in home):
        verdict_line = "redesign signal/regime-gating (loses in home regime or weak entries)"
    else:
        verdict_line = "tune filters & thresholds (edge present but below costs)"
    lines.append(f"- **Default action:** {verdict_line}. (Do NOT remove — hypothesis not shown invalid.)")

    scores = {
        "strategy": strat, "total_pnl": total_pnl, "avg_sharpe": avg_sharpe,
        "avg_win_rate": avg_win_rate, "avg_mdd": avg_mdd, "total_trades": total_trades,
        "regime_spread": (max(reg.values()) - min(reg.values())) if reg else 0.0,
        "best_pnl_run": max(pnls) if pnls else 0.0,
        "verdicts": [r.get("verdict") for r in runs],
    }
    return lines, scores


def main():
    rows = load()
    if not rows:
        print("no ok rows yet"); return
    by = per_strategy(rows)
    n_sym = len({r["symbol"] for r in rows}); n_win = len({r["window"] for r in rows})
    hdr = (f"_Generated from eval_matrix.json — {len(rows)} runs "
           f"({n_sym} symbols x {n_win} windows x {len(by)} strategies, partial if matrix still running)._")

    # ---- Per-strategy edge + diagnosis report ----
    L = ["# Multi-Window / Multi-Symbol Strategy Edge & Diagnosis Report", "", hdr, "",
         "Metrics are averaged across symbols and windows; P&L summed. "
         "Diagnosis is hypothesis-preserving (improve/redesign, not eliminate).", ""]
    all_scores = []
    for strat in HYPOTHESIS:
        if strat not in by:
            continue
        runs = by[strat]
        lines, scores = diagnose(strat, runs)
        all_scores.append(scores)
        from collections import Counter
        vt = Counter(scores["verdicts"])
        L.append(f"## {strat}")
        L.append("")
        L.append(f"total P&L {scores['total_pnl']:.0f} | avg sharpe {scores['avg_sharpe']:.2f} | "
                 f"avg win-rate {scores['avg_win_rate']:.0%} | avg maxDD {scores['avg_mdd']:.0%} | "
                 f"trades {scores['total_trades']:.0f} | verdicts {dict(vt)}")
        L.append("")
        L.extend(lines)
        L.append("")
        # per (symbol,window) line
        L.append("| symbol | window | verdict | P&L | sharpe | sortino | win% | maxDD | trades |")
        L.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
        for r in sorted(runs, key=lambda r: (r["symbol"], r["window"])):
            L.append(f"| {r['symbol']} | {r['window']}d | {r.get('verdict')} | {_f(r.get('total_pnl')):.0f} | "
                     f"{_f(r.get('sharpe')):.2f} | {_f(r.get('sortino')):.2f} | {_f(r.get('win_rate')):.0%} | "
                     f"{_f(r.get('max_drawdown')):.0%} | {_f(r.get('closed_trades')):.0f} |")
        L.append("")
    open(os.path.join(OUT_DIR, "strategy-edge-diagnosis-report.md"), "w").write("\n".join(L) + "\n")

    # ---- Comparative ranking ----
    R = ["# Strategy Comparative Ranking", "", hdr, ""]
    if all_scores:
        by_pnl = sorted(all_scores, key=lambda s: s["total_pnl"], reverse=True)
        closest = sorted(all_scores, key=lambda s: s["total_pnl"], reverse=True)
        by_sharpe = sorted(all_scores, key=lambda s: s["avg_sharpe"], reverse=True)
        most_regime = sorted(all_scores, key=lambda s: s["regime_spread"], reverse=True)
        R.append(f"- **Strongest (highest aggregate P&L):** {by_pnl[0]['strategy']} ({by_pnl[0]['total_pnl']:.0f})")
        R.append(f"- **Weakest (lowest aggregate P&L):** {by_pnl[-1]['strategy']} ({by_pnl[-1]['total_pnl']:.0f})")
        R.append(f"- **Closest to profitability (least-negative / best sharpe):** "
                 f"{closest[0]['strategy']} (P&L {closest[0]['total_pnl']:.0f}, sharpe {by_sharpe[0]['avg_sharpe']:.2f} "
                 f"-> {by_sharpe[0]['strategy']})")
        R.append(f"- **Most regime-sensitive (widest P&L spread across regimes):** "
                 f"{most_regime[0]['strategy']} (spread {most_regime[0]['regime_spread']:.0f})")
        # highest redesign potential = proxy/stub or loses in home regime, but with some structure
        redesign = [s for s in all_scores if s["strategy"] in PROXY_STUB] or most_regime[:1]
        R.append(f"- **Highest redesign potential:** {', '.join(s['strategy'] for s in redesign)} "
                 f"(proxy/stub signal or strong regime sensitivity to exploit).")
        R.append("")
        R.append("## Full ranking by aggregate P&L")
        R.append("")
        R.append("| rank | strategy | total P&L | avg sharpe | avg win% | avg maxDD | trades |")
        R.append("|---:|---|---:|---:|---:|---:|---:|")
        for i, s in enumerate(by_pnl, 1):
            R.append(f"| {i} | {s['strategy']} | {s['total_pnl']:.0f} | {s['avg_sharpe']:.2f} | "
                     f"{s['avg_win_rate']:.0%} | {s['avg_mdd']:.0%} | {s['total_trades']:.0f} |")
    open(os.path.join(OUT_DIR, "strategy-ranking-report.md"), "w").write("\n".join(R) + "\n")
    print("WROTE strategy-edge-diagnosis-report.md + strategy-ranking-report.md "
          f"({len(rows)} runs, {len(by)} strategies)")


if __name__ == "__main__":
    main()
