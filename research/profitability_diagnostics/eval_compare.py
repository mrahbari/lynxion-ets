#!/usr/bin/env python3
"""Compare PRE-fix vs POST-fix evaluation matrices (E-P5.2 Priority-1).

PRE  = data/results_storage/eval_matrix_PRE.json (before exit-layer fixes)
POST = data/results_storage/eval_matrix.json     (after both fixes)

Writes tasks/phase5-evaluate/exit-fix-pre-post-comparison.md.
Run from repo root:  .venv/bin/python tasks/phase5-evaluate/eval_compare.py
"""
import json
import os
from collections import defaultdict
from statistics import mean

PRE = "data/results_storage/eval_matrix_PRE.json"
POST = "data/results_storage/eval_matrix.json"
OUT = os.path.join("docs", "reports", "phase5", "exit-fix-pre-post-comparison.md")


def load(p):
    rows = [r for r in json.load(open(p)) if r.get("status") == "ok"]
    return rows


def _key(r):
    return (r["symbol"], r["window"], r["strategy"])


def agg(rows, keys=None):
    by = defaultdict(list)
    for r in rows:
        if keys is not None and _key(r) not in keys:
            continue
        by[r["strategy"]].append(r)
    out = {}
    for s, rs in by.items():
        wr = [r["win_rate"] for r in rs if r.get("win_rate") is not None]
        out[s] = {
            "win_rate": mean(wr) if wr else 0.0,
            "total_pnl": sum(r.get("total_pnl", 0) or 0 for r in rs),
            "sharpe": mean([r["sharpe"] for r in rs if r.get("sharpe") is not None] or [0]),
            "trades": sum(r.get("closed_trades", 0) or 0 for r in rs),
            "verdicts": [r.get("verdict") for r in rs],
        }
    return out


def main():
    if not os.path.exists(POST):
        print("POST matrix not found"); return
    pre_rows, post_rows = load(PRE), load(POST)
    # Fair comparison: only cells present in BOTH (handles a partial POST run).
    common = {_key(r) for r in pre_rows} & {_key(r) for r in post_rows}
    pre, post = agg(pre_rows, common), agg(post_rows, common)
    syms = sorted({k[0] for k in common}); wins = sorted({k[1] for k in common})
    from collections import Counter
    L = ["# Exit-Layer Fix — PRE vs POST Comparison", "",
         f"_Compared on {len(common)} matching (symbol,window,strategy) cells — "
         f"symbols {syms}, windows {wins}d. PRE = before exit-layer fixes; "
         f"POST = after market-impact + SL/TP-geometry fixes. "
         f"({'FULL 108-cell matrix' if len(common)>=108 else 'PARTIAL — POST run still in progress'})._", "",
         "| strategy | win% PRE→POST | total P&L PRE→POST | sharpe PRE→POST | verdicts POST |",
         "|---|---|---|---|---|"]
    pre_wr, post_wr, pre_pnl, post_pnl = [], [], 0.0, 0.0
    for s in sorted(post):
        a, b = pre.get(s, {}), post[s]
        vt = Counter(b["verdicts"])
        L.append(f"| {s} | {a.get('win_rate',0)*100:.1f}%→{b['win_rate']*100:.1f}% | "
                 f"{a.get('total_pnl',0):.0f}→{b['total_pnl']:.0f} | "
                 f"{a.get('sharpe',0):.2f}→{b['sharpe']:.2f} | {dict(vt)} |")
        pre_wr.append(a.get("win_rate", 0)); post_wr.append(b["win_rate"])
        pre_pnl += a.get("total_pnl", 0); post_pnl += b["total_pnl"]
    L += ["",
          f"**Aggregate win rate:** {mean(pre_wr)*100:.1f}% → {mean(post_wr)*100:.1f}%",
          f"**Aggregate total P&L:** {pre_pnl:.0f} → {post_pnl:.0f}",
          "",
          "**GO/positive-edge strategies POST:** " +
          (", ".join(s for s in sorted(post) if any(v == "GO" for v in post[s]["verdicts"])) or "none"),
          "",
          "Interpretation: the win-rate lift quantifies how much edge the exit-layer "
          "bugs were destroying. Strategies still net-negative POST are genuine "
          "signal/edge questions (now measurable); proceed to per-strategy refinement."]
    open(OUT, "w").write("\n".join(L) + "\n")
    print("WROTE", OUT)
    print(f"win% {mean(pre_wr)*100:.1f}->{mean(post_wr)*100:.1f} | pnl {pre_pnl:.0f}->{post_pnl:.0f}")


if __name__ == "__main__":
    main()
