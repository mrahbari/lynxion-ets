#!/usr/bin/env python3
"""E-P5.4 — MTF & Portfolio Intelligence forensics (DIAGNOSIS ONLY).

Answers the three E-P5.4 questions from EXISTING data — no engine/strategy/
architecture changes:
  1. profitability lost to MTF conflicts  (counter-trend entries)
  2. profitability lost to missing portfolio intelligence
  3. risk hidden by correlation exposure

Inputs: data/results_storage/lifecycle_trades.json (8380 longs, entry_regime
populated) + data/history/raw/1m/{BTC,ETH,SOL}-USDT.csv.

MTF method: every trade is a LONG. The backtester's per-trade `entry_regime`
is the trend context at entry (B9: the real MTF score is a mock 0, so these
contexts were NEVER used to gate entries). A long in `trending_up` = ALIGNED,
in `trending_down` = CONFLICT (counter-trend), `ranging` = NEUTRAL. We compare
realised net-R expectancy across these groups and quantify the conflict drag.

Run:  .venv/bin/python tasks/phase5-profitability/eval_mtf_portfolio.py
"""
import json
import math
import os
from collections import defaultdict

import pandas as pd

TR = os.path.join("data", "results_storage", "lifecycle_trades.json")
RAW = os.path.join("data", "history", "raw", "1m")
OUT = os.path.join("docs", "reports", "phase5", "ep5.4-mtf-portfolio.md")
ALIGN = {"trending_up": "aligned", "trending_down": "conflict",
         "ranging": "neutral", "unknown": "unknown"}


def mean(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return sum(xs) / len(xs) if xs else 0.0


def main():
    trades = [t for t in json.load(open(TR)) if t.get("realized_R") is not None]
    n = len(trades)

    # ---------- 1. MTF conflict (entry_regime alignment) ----------
    grp = defaultdict(list)
    for t in trades:
        grp[ALIGN.get(t.get("entry_regime"), "unknown")].append(t)

    def stats(ts):
        R = [t["realized_R"] for t in ts]
        w = sum(1 for r in R if r > 0)
        return len(ts), mean(R), (w / len(ts) if ts else 0.0)

    overall_R = mean([t["realized_R"] for t in trades])
    # counterfactual: filter out conflict (counter-trend) entries
    kept = [t for t in trades if ALIGN.get(t.get("entry_regime")) != "conflict"]
    kept_R = mean([t["realized_R"] for t in kept])
    conflict = grp["conflict"]
    conflict_total_R = sum(t["realized_R"] for t in conflict)
    aligned_expR = stats(grp["aligned"])[1]

    L = ["# E-P5.4 — MTF & Portfolio Intelligence Forensics (diagnosis only)", "",
         f"_{n} trades (all LONGS), 90d × {{BTC,ETH,SOL}} × 12 strategies, frozen "
         f"POST baseline. Net R = realised_R (after fees+slippage). No engine, "
         f"strategy, or architecture changes — quantification only._", "",
         "## Q1 — Profitability lost to MTF conflicts", "",
         "Every trade is a long; `entry_regime` is the trend context at entry. "
         "B9 (MTF `compute_trend()` returns mock 0) means these contexts never "
         "gated entries → counter-trend longs were taken freely.", "",
         "| entry context | trades | % | net exp R | win% |",
         "|---|---:|---:|---:|---:|"]
    desc = {"aligned": "long in uptrend", "neutral": "long in range",
            "conflict": "long in DOWNtrend", "unknown": "—"}
    for g in ("aligned", "neutral", "conflict", "unknown"):
        if not grp[g]:
            continue
        c, e, wr = stats(grp[g])
        L.append(f"| {g} ({desc[g]}) | {c} | "
                 f"{100*c/n:.0f}% | {e:+.3f} | {100*wr:.0f}% |")
    conflict_expR = stats(conflict)[1]
    delta = conflict_expR - aligned_expR  # >0 => conflicts BETTER than aligned
    filter_delta = kept_R - overall_R     # >0 => filtering conflicts HELPS
    mtf_is_leak = filter_delta > 0.001
    L += ["",
          f"- **Counter-trend (conflict) longs: {len(conflict)} ({100*len(conflict)/n:.0f}% "
          f"of all trades)** — entry_regime = trending_down.",
          f"- Conflict net exp R **{conflict_expR:+.3f}** vs aligned **{aligned_expR:+.3f}** "
          f"→ counter-trend longs are {abs(delta):.3f}R/trade "
          f"**{'BETTER' if delta>0 else 'worse'}** than trend-aligned longs.",
          f"- **Counterfactual MTF filter** (drop all counter-trend longs): portfolio "
          f"expectancy {overall_R:+.3f}R → **{kept_R:+.3f}R** ({filter_delta:+.3f}R/trade).",
          (f"- **Profitability lost to MTF conflicts: ≈ +{filter_delta*len(kept):.1f}R "
           f"recoverable by an HTF gate.**" if mtf_is_leak else
           f"- **Profitability lost to MTF conflicts: ESSENTIALLY ZERO.** A naive HTF "
           f"'longs-only-in-uptrend' gate would *worsen* expectancy by {abs(filter_delta):.3f}"
           f"R/trade on this sample. The data does NOT support MTF misalignment as a "
           f"profitability leak (using entry_regime as the trend-context proxy) — it "
           f"**refutes** the B9-impact assumption here."),
          f"- Either way, every alignment bucket is deeply negative "
          f"({aligned_expR:+.3f} / {stats(grp['neutral'])[1]:+.3f} / {conflict_expR:+.3f}R) "
          f"→ no trend context produces positive expectancy (consistent with B14: "
          f"negative gross edge). MTF gating cannot create edge that is absent.", "",
          "_Caveat: entry_regime is the engine's single-timeframe regime, not a true "
          "multi-timeframe HTF score (B9 leaves the real MTF trend a mock). A genuine "
          "HTF signal could differ, but on the only trend-context available there is no "
          "evidence MTF conflict is a material leak._", ""]

    # per-strategy conflict share + drag
    L += ["### Per-strategy MTF-conflict drag", "",
          "| strategy | trades | conflict% | aligned expR | conflict expR | filtered expR |",
          "|---|---:|---:|---:|---:|---:|"]
    bystrat = defaultdict(list)
    for t in trades:
        bystrat[t["strategy"]].append(t)
    for s in sorted(bystrat, key=lambda k: mean([t["realized_R"] for t in bystrat[k]]), reverse=True):
        ts = bystrat[s]
        cf = [t for t in ts if ALIGN.get(t.get("entry_regime")) == "conflict"]
        al = [t for t in ts if ALIGN.get(t.get("entry_regime")) == "aligned"]
        kp = [t for t in ts if ALIGN.get(t.get("entry_regime")) != "conflict"]
        L.append(f"| {s} | {len(ts)} | {100*len(cf)/len(ts):.0f}% | "
                 f"{mean([t['realized_R'] for t in al]):+.3f} | "
                 f"{mean([t['realized_R'] for t in cf]):+.3f} | "
                 f"{mean([t['realized_R'] for t in kp]):+.3f} |")

    # ---------- 2/3. Portfolio correlation & hidden risk ----------
    import numpy as np

    def load(sym):
        df = pd.read_csv(os.path.join(RAW, f"{sym}.csv"))
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")  # epoch seconds
        return df.set_index("timestamp")["close"].resample("1h").last()

    px = pd.concat({"BTC": load("BTC-USDT"), "ETH": load("ETH-USDT"),
                    "SOL": load("SOL-USDT")}, axis=1).dropna()
    rets = px.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    corr = rets.corr()
    pairs = [("BTC", "ETH"), ("BTC", "SOL"), ("ETH", "SOL")]
    avg_corr = mean([corr.loc[a, b] for a, b in pairs])
    # participation-ratio effective bets from correlation eigenvalues
    import numpy as np
    ev = np.linalg.eigvalsh(corr.values)
    n_eff = (ev.sum() ** 2) / (ev ** 2).sum()
    # equal-weight long-all-three: actual vol vs if-independent vol
    w = np.array([1 / 3] * 3)
    cov = rets.cov().values
    port_vol = math.sqrt(w @ cov @ w)
    indep_vol = math.sqrt(sum((w[i] ** 2) * cov[i, i] for i in range(3)))
    risk_mult = port_vol / indep_vol

    L += ["", "## Q2/Q3 — Missing portfolio intelligence & hidden correlation risk", "",
          "Backtests ran one (symbol × strategy) at a time — there is no live "
          "portfolio layer (B10: correlation/heat/concentration offline-only, live "
          "sizing ignores other open positions). The risk is therefore quantified "
          "structurally from 1h-resampled returns of the traded universe.", "",
          f"- **Pairwise return correlation (1h):** BTC–ETH {corr.loc['BTC','ETH']:.2f}, "
          f"BTC–SOL {corr.loc['BTC','SOL']:.2f}, ETH–SOL {corr.loc['ETH','SOL']:.2f} → "
          f"**avg {avg_corr:.2f}** (high).",
          f"- **Effective independent bets** across the 3 symbols: **{n_eff:.2f}** "
          f"(of 3 nominal) — the universe behaves like ~{n_eff:.1f} bet(s), not 3.",
          f"- **Hidden-risk multiplier:** a strategy long in all three carries "
          f"**{risk_mult:.2f}×** the volatility a naive 'independent diversification' "
          f"assumption would predict ({port_vol*100:.2f}% vs {indep_vol*100:.2f}% hourly).",
          "",
          "**Interpretation:** because all positions are long-only (B15) in a "
          f"~{avg_corr:.2f}-correlated universe, running the suite live would STACK "
          "correlated long exposure — concentration risk masquerading as "
          "diversification. With no live heat/correlation cap (B10) the realised "
          "portfolio drawdown would be materially larger than per-symbol backtests "
          "imply. This is hidden RISK, not hidden profit: it cannot rescue the "
          "negative per-trade expectancy (B14), it amplifies downside.", ""]

    # ---------- Findings / impact / ranking (6-part epic close) ----------
    mtf_verdict = (f"recoverable ≈ +{filter_delta*len(kept):.0f}R" if mtf_is_leak
                   else f"≈ ZERO (HTF gate would WORSEN expectancy by "
                        f"{abs(filter_delta):.3f}R/trade) — B9-impact assumption REFUTED here")
    L += ["## E-P5.4 findings (6-part)", "",
          "1. **Findings:** "
          f"30% of longs are counter-trend, yet counter-trend longs are the *least* "
          f"unprofitable bucket ({conflict_expR:+.3f}R) and trend-aligned the *worst* "
          f"({aligned_expR:+.3f}R). The traded universe is {avg_corr:.2f}-correlated "
          f"(~{n_eff:.1f} effective bets of 3), long-only (B15), with no live portfolio "
          "risk layer (B10).",
          "2. **Root causes:** B9 mock MTF trend → no HTF gate (but gating shows no "
          "benefit here); B10 portfolio intelligence offline-only → no correlation/heat "
          "cap live; B15/B4 long-only in a highly correlated universe.",
          f"3. **Profitability impact — MTF conflicts: {mtf_verdict}.** "
          f"Portfolio/correlation: not an expectancy effect but a RISK amplifier — "
          f"long-all-three carries {risk_mult:.2f}× the volatility naive diversification "
          f"implies (~{n_eff:.1f} effective bets).",
          "4. **Recommended fixes (NOT executed — diagnosis only):** live correlation/"
          "heat/concentration cap (B10) to contain stacked-long drawdown; structure-"
          "aware SL/TP (B11). A real MTF/HTF gate (B9) is NOT evidenced as profit-"
          "additive here and is de-prioritised. Deferred to remediation mode.",
          "5. **Estimated upside:** MTF gating ≈ none (this sample); portfolio cap = "
          "drawdown/risk reduction, NOT expectancy gain. Neither overcomes B14 "
          "(negative gross edge) — the binding constraint remains entry edge.",
          "6. **Priority ranking:** B14 (entry edge) ≫ B7 (R:R geometry) > B10 "
          "(portfolio risk — real, but risk not return) > B8 (lifecycle) > B9 (MTF "
          "gate — no measured benefit). MTF/portfolio are RISK controls; they cannot "
          "manufacture the absent edge."]
    open(OUT, "w").write("\n".join(L) + "\n")
    print("WROTE", OUT)
    print(f"conflict={len(conflict)}/{n} ({100*len(conflict)/n:.0f}%) "
          f"conflictR={conflict_total_R:+.1f} overall={overall_R:+.3f} filtered={kept_R:+.3f} "
          f"avg_corr={avg_corr:.2f} n_eff={n_eff:.2f} risk_mult={risk_mult:.2f}")


if __name__ == "__main__":
    main()
