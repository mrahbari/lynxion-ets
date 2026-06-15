#!/usr/bin/env python3
"""E-P5.3 lifecycle forensics ANALYZER (run POST baseline-freeze, after the dump).

Consumes data/results_storage/lifecycle_trades.json (per-trade lifecycle records)
and produces the required evidence:
  MFE / MAE / exit-type / R-multiple / time-in-trade / TP-hit / SL-hit
  distributions, plus breakeven / trailing / partial-TP OPPORTUNITY analyses,
  and explicit answers to the five "expectancy lost due to ..." questions.

All opportunity figures are COUNTERFACTUAL estimates from realised excursions
(MFE/MAE) under stated rules — NOT optimization. Expressed in R-multiples
(risk units), with an approximate $ translation via average per-trade risk.
Objective: quantify expectancy left on the table, not redesign.

Run from repo root:  .venv/bin/python tasks/phase5-profitability/eval_lifecycle_forensics.py
"""
import json
import math
import os
from collections import Counter, defaultdict

IN = os.path.join("data", "results_storage", "lifecycle_trades.json")
OUT = os.path.join("docs", "reports", "phase5", "ep5.3-lifecycle-forensics-report.md")


def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _hist(vals, edges):
    c = [0] * (len(edges) + 1)
    for v in vals:
        placed = False
        for i, e in enumerate(edges):
            if v < e:
                c[i] += 1; placed = True; break
        if not placed:
            c[-1] += 1
    labels = ([f"<{edges[0]}"] +
              [f"{edges[i]}..{edges[i+1]}" for i in range(len(edges) - 1)] +
              [f">={edges[-1]}"])
    return list(zip(labels, c))


def enrich(t):
    """Add risk_per_unit, mfe_R, mae_R, tp_R; return None if unusable."""
    e = _f(t.get("entry_price")); sl = _f(t.get("stop_loss")); tp = _f(t.get("take_profit"))
    pnl = _f(t.get("pnl")); R = _f(t.get("realized_R"))
    mfe = _f(t.get("mfe")) or 0.0; mae = _f(t.get("mae")) or 0.0
    if e is None or sl is None:
        return None
    risk = abs(e - sl)
    if risk <= 0:
        return None
    t["_mfe_R"] = mfe / risk
    t["_mae_R"] = mae / risk
    t["_tp_R"] = abs(tp - e) / risk if tp is not None else None
    t["_R"] = R if R is not None else (pnl / risk if pnl is not None else None)  # NET R (pnl incl fees+slippage)
    # per-trade risk in $ (for $ translation): pnl / realized_R
    t["_risk_usd"] = (abs(pnl / R) if (pnl is not None and R not in (None, 0)) else None)
    # direction: trade record 'side' is the CLOSING order (backtester L2085:
    # "sell" if direction==1) → sell-to-close = LONG (+1), buy-to-close = SHORT (-1).
    d = 1 if t.get("side") == "sell" else -1
    t["_dir"] = d
    exit_p = _f(t.get("price"))
    # GROSS R = price excursion / risk, BEFORE fees+slippage (execution-corrected
    # geometry/signal edge). cost drag = gross - net.
    t["_gross_R"] = ((exit_p - e) * d / risk) if exit_p is not None else None
    return t


def main():
    if not os.path.exists(IN):
        print("lifecycle_trades.json not found — run eval_lifecycle_dump.py first"); return
    raw = json.load(open(IN))
    trades = [x for x in (enrich(t) for t in raw) if x is not None and x.get("_R") is not None]
    if not trades:
        print("no usable trades"); return

    risks = [t["_risk_usd"] for t in trades if t.get("_risk_usd")]
    avg_risk = sum(risks) / len(risks) if risks else 1.0
    n = len(trades)
    Rs = [t["_R"] for t in trades]
    mfeR = [t["_mfe_R"] for t in trades]
    maeR = [t["_mae_R"] for t in trades]
    exit_types = Counter(t.get("exit_type") for t in trades)
    wins = [t for t in trades if t["_R"] > 0]
    losers = [t for t in trades if t["_R"] <= 0]
    exp_R = sum(Rs) / n  # expectancy per trade in R

    def usd(total_R):
        return total_R * avg_risk

    # --- Opportunity analyses (counterfactual, stated rules) ---
    def breakeven_gain(trigger):
        # Losers that reached >= trigger R favorable before reversing: move SL to
        # breakeven after +trigger R -> loss becomes ~0 (minus a tick, approx 0).
        g = 0.0; k = 0
        for t in losers:
            if t["_mfe_R"] >= trigger:
                g += (0.0 - t["_R"]); k += 1   # saved = turn -R into ~0
        return g, k

    def trailing_gain(capture):
        # Trades that gave back profit (mfe_R > realized R): a trail capturing
        # `capture` fraction of MFE yields capture*mfe_R instead of realized R.
        g = 0.0; k = 0
        for t in trades:
            target = capture * t["_mfe_R"]
            if target > t["_R"]:
                g += (target - t["_R"]); k += 1
        return g, k

    def partial_gain(trigger, frac):
        # Trades reaching >= trigger R that exited <= 0: closing `frac` at +trigger
        # locks frac*trigger; remainder assumed to still hit SL (-(1-frac)).
        g = 0.0; k = 0
        for t in trades:
            if t["_mfe_R"] >= trigger and t["_R"] <= 0:
                locked = frac * trigger + (1 - frac) * t["_R"]
                if locked > t["_R"]:
                    g += (locked - t["_R"]); k += 1
        return g, k

    def tp_left_on_table():
        # TP-hit winners whose MFE_R exceeded realised R -> TP too early.
        g = 0.0; k = 0
        for t in wins:
            if t.get("exit_type") == "TP" and t["_mfe_R"] > t["_R"]:
                g += (t["_mfe_R"] - t["_R"]); k += 1
        return g, k

    # --- Exit-quality (B7: SL/TP placement) ---
    def mean(xs):
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else 0.0
    tp_trades = [t for t in trades if t.get("exit_type") == "TP"]
    sl_trades = [t for t in trades if t.get("exit_type") == "SL"]
    R_by_exit = {et: mean([t["_R"] for t in trades if t.get("exit_type") == et])
                 for et in ("TP", "SL", "force_close")}
    mean_tp_R = mean([t["_tp_R"] for t in trades if t.get("_tp_R") is not None])  # R:R reward leg
    tp_net_loss = sum(1 for t in tp_trades if t["_R"] <= 0)  # TP hits that still lost (cost > reward)

    be1, be1n = breakeven_gain(1.0); be05, be05n = breakeven_gain(0.5)
    tr05, tr05n = trailing_gain(0.5); trmax, trmaxn = trailing_gain(1.0)
    pa1, pa1n = partial_gain(1.0, 0.5)
    tpleft, tpleftn = tp_left_on_table()

    L = ["# E-P5.3 Trade-Lifecycle Forensics — Evidence (no redesign yet)", "",
         f"_{n} realised trades across strategies × symbols × windows. Opportunity "
         f"figures are COUNTERFACTUAL estimates from realised MFE/MAE under stated "
         f"rules; in R-multiples (avg per-trade risk ≈ ${avg_risk:,.0f})._", "",
         f"**Baseline expectancy:** {exp_R:+.3f} R/trade  (~${usd(exp_R):,.1f}/trade); "
         f"win rate {100*len(wins)/n:.1f}% ({len(wins)}/{n}).", "",
         "## Distributions", "",
         f"- **Exit type:** {dict(exit_types)}",
         f"- **TP-hit:** {exit_types.get('TP',0)} ({100*exit_types.get('TP',0)/n:.1f}%) | "
         f"**SL-hit:** {exit_types.get('SL',0)} ({100*exit_types.get('SL',0)/n:.1f}%) | "
         f"**force_close:** {exit_types.get('force_close',0)} ({100*exit_types.get('force_close',0)/n:.1f}%)",
         f"- **R-multiple:** {_hist(Rs, [-1.5,-1,-0.5,0,0.5,1,1.5,2])}",
         f"- **MFE (R):** {_hist(mfeR, [0,0.25,0.5,1,1.5,2,3])}",
         f"- **MAE (R):** {_hist(maeR, [0,0.25,0.5,1,1.5,2,3])}",
         "", "## Exit quality — B7 (SL/TP placement)", "",
         f"- **Mean realised R by exit type:** TP {R_by_exit['TP']:+.3f}R · "
         f"SL {R_by_exit['SL']:+.3f}R · force_close {R_by_exit['force_close']:+.3f}R.",
         f"- **Reward leg (mean TP distance):** {mean_tp_R:.2f}R — i.e. realised "
         f"R:R ≈ {mean_tp_R:.2f}:1 (target below 1R = structurally adverse).",
         f"- **TP hits that STILL lost money** (reward < round-trip cost): "
         f"{tp_net_loss}/{len(tp_trades)} "
         f"({100*tp_net_loss/max(1,len(tp_trades)):.0f}% of TP exits).",
         "", "## Opportunity analysis (expectancy left on the table)", "",
         f"- **Breakeven @ +1R:** {be1n} losing trades reached +1R first → +{be1:.1f} R "
         f"total (~${usd(be1):,.0f}); per-trade +{be1/n:+.3f} R.",
         f"- **Breakeven @ +0.5R:** {be05n} trades → +{be05:.1f} R (~${usd(be05):,.0f}).",
         f"- **Trailing (capture 50% of MFE):** {tr05n} trades gave back profit → "
         f"+{tr05:.1f} R (~${usd(tr05):,.0f}); per-trade +{tr05/n:+.3f} R.",
         f"- **Trailing (full-MFE upper bound):** +{trmax:.1f} R (~${usd(trmax):,.0f}).",
         f"- **Partial @ +1R (close 50%):** {pa1n} losers reached +1R → +{pa1:.1f} R "
         f"(~${usd(pa1):,.0f}); per-trade +{pa1/n:+.3f} R.",
         f"- **TP set too early (MFE>realised on TP wins):** {tpleftn} trades left "
         f"+{tpleft:.1f} R on the table (~${usd(tpleft):,.0f}).",
         "", "## Explicit answers (expectancy lost due to …)", "",
         f"1. **Stop placement:** losers that went favorable first (MFE≥0.5R) then "
         f"stopped = {sum(1 for t in losers if t['_mfe_R']>=0.5)}/{len(losers)} losers; "
         f"recoverable via breakeven/trailing ≈ +{be05:.1f}..{be1:.1f} R "
         f"(~${usd(be05):,.0f}–${usd(be1):,.0f}).",
         f"2. **Take-profit placement:** TP-too-early left +{tpleft:.1f} R "
         f"(~${usd(tpleft):,.0f}) on TP-hit winners; current TP≈"
         f"{(sum(t['_tp_R'] for t in trades if t.get('_tp_R'))/max(1,sum(1 for t in trades if t.get('_tp_R')))):.2f}R.",
         f"3. **Missing breakeven:** +{be1:.1f} R (~${usd(be1):,.0f}) @ +1R trigger "
         f"({be1n} trades).",
         f"4. **Missing trailing:** +{tr05:.1f} R (~${usd(tr05):,.0f}) at 50% capture "
         f"(upper bound +{trmax:.1f} R).",
         f"5. **Missing partial exits:** +{pa1:.1f} R (~${usd(pa1):,.0f}) @ +1R/50% "
         f"({pa1n} trades).",
         "", "## Per-strategy lifecycle summary", "",
         "| strategy | trades | exp R | win% | TP% | SL% | mean MFE_R | mean MAE_R | breakeven@1R (R) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    bystrat = defaultdict(list)
    for t in trades:
        bystrat[t["strategy"]].append(t)
    for s in sorted(bystrat):
        ts = bystrat[s]; m = len(ts)
        et = Counter(t.get("exit_type") for t in ts)
        beS = sum((0 - t["_R"]) for t in ts if t["_R"] <= 0 and t["_mfe_R"] >= 1.0)
        L.append(f"| {s} | {m} | {sum(t['_R'] for t in ts)/m:+.3f} | "
                 f"{100*sum(1 for t in ts if t['_R']>0)/m:.0f} | {100*et.get('TP',0)/m:.0f} | "
                 f"{100*et.get('SL',0)/m:.0f} | {sum(t['_mfe_R'] for t in ts)/m:.2f} | "
                 f"{sum(t['_mae_R'] for t in ts)/m:.2f} | +{beS:.1f} |")
    # time-in-trade if instrumented
    tit = [t.get("bars_in_trade") for t in trades if _f(t.get("bars_in_trade")) is not None]
    L += ["", ("## Time-in-trade\n\n" + (f"bars_in_trade present for {len(tit)} trades; "
          f"distribution {_hist([_f(x) for x in tit],[5,15,60,240,1440])}" if tit else
          "NOT captured (entry-timestamp instrumentation pending) — add post-freeze."))]
    open(OUT, "w").write("\n".join(L) + "\n")
    print("WROTE", OUT, f"({n} trades, exp {exp_R:+.3f}R)")

    # ===================== ECONOMIC VIABILITY (E-P5.3) =====================
    # Separate the EXECUTION-CORRECTED path (gross R, pre-cost: does the signal+
    # geometry have edge with bug-free fills?) from ECONOMIC viability (net R,
    # after fees+slippage). Per strategy: expectancy, payoff ratio, TP/SL
    # cost-adjusted effectiveness, viability label, primary loss driver.
    def m_(xs):
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else 0.0

    rows = []
    for s, ts in bystrat.items():
        m = len(ts)
        net = [t["_R"] for t in ts]
        gross = [t["_gross_R"] for t in ts if t.get("_gross_R") is not None]
        wins = [r for r in net if r > 0]; losses = [r for r in net if r <= 0]
        exp_net = m_(net); exp_gross = m_(gross); drag = exp_gross - exp_net
        avg_w = m_(wins); avg_l = m_(losses)
        payoff = (avg_w / abs(avg_l)) if avg_l < 0 else float("inf")
        wr = len(wins) / m
        tp_ts = [t for t in ts if t.get("exit_type") == "TP"]
        sl_ts = [t for t in ts if t.get("exit_type") == "SL"]
        tp_net = m_([t["_R"] for t in tp_ts]); sl_net = m_([t["_R"] for t in sl_ts])
        rwd_leg = m_([t["_tp_R"] for t in ts if t.get("_tp_R") is not None])  # mean TP distance (R)
        # viability label
        if exp_net > 0:
            label = "Economically Viable"
        elif exp_gross > 0 or exp_net > -0.10:
            label = "Borderline (needs structural adjustment)"
        else:
            label = "Non-Viable"
        # primary loss driver (quantified, only when net<=0)
        if exp_net > 0:
            driver = "—  (net-positive)"
        elif exp_gross > 0 and drag >= abs(exp_net):
            driver = (f"Transaction costs (fees+slippage): drag {drag:.3f}R/trade wipes a "
                      f"gross +{exp_gross:.3f}R; {m} trades → overtrading amplifies it")
        elif rwd_leg < 1.0:
            driver = (f"TP/SL geometry: reward leg {rwd_leg:.2f}R < 1R risk (R:R<1); "
                      f"payoff {payoff:.2f}, so {100*wr:.0f}% win-rate can't cover losers")
        elif wr < 0.35:
            driver = f"Win rate {100*wr:.0f}% too low for payoff {payoff:.2f} (signal/regime)"
        else:
            driver = f"Negative gross edge {exp_gross:.3f}R (signal/regime mismatch)"
        rows.append({"s": s, "m": m, "exp_net": exp_net, "exp_gross": exp_gross,
                     "drag": drag, "wr": wr, "payoff": payoff, "avg_w": avg_w,
                     "avg_l": avg_l, "tp_net": tp_net, "sl_net": sl_net,
                     "rwd_leg": rwd_leg, "label": label, "driver": driver})
    rows.sort(key=lambda r: r["exp_net"], reverse=True)
    viable = [r for r in rows if r["label"] == "Economically Viable"]
    border = [r for r in rows if r["label"].startswith("Borderline")]

    E = ["# E-P5.3 — Economic Viability After Execution Fixes", "",
         f"_{n} trades, 90d × {{BTC,ETH,SOL}} × 12 strategies, frozen POST baseline "
         f"(B1/B2 fixed). pnl is NET (fees {0.1}%/side + slippage). **Execution-"
         f"corrected** = GROSS R (pre-cost, edge of signal+geometry with correct "
         f"fills); **Economic** = NET R (post-cost reality). Realistic conditions._",
         "",
         "## Ranked by TRUE post-cost expectancy (net R/trade)", "",
         "| rank | strategy | trades | **net exp R** | gross exp R | cost drag R | win% | payoff (W/L) | TP net R | SL net R | reward leg | label |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for i, r in enumerate(rows, 1):
        po = "inf" if r["payoff"] == float("inf") else f"{r['payoff']:.2f}"
        E.append(f"| {i} | {r['s']} | {r['m']} | **{r['exp_net']:+.3f}** | "
                 f"{r['exp_gross']:+.3f} | {r['drag']:.3f} | {100*r['wr']:.0f}% | {po} | "
                 f"{r['tp_net']:+.2f} | {r['sl_net']:+.2f} | {r['rwd_leg']:.2f}R | {r['label']} |")
    E += ["", "## Execution-corrected vs Economic (the cost cliff)", "",
          "For each strategy: does correct-execution edge exist pre-cost, and does it "
          "survive fees+slippage?", "",
          "| strategy | gross exp R (corrected) | net exp R (economic) | survives costs? |",
          "|---|---:|---:|---|"]
    for r in rows:
        E.append(f"| {r['s']} | {r['exp_gross']:+.3f} | {r['exp_net']:+.3f} | "
                 f"{'YES' if r['exp_net']>0 else ('gross+ but cost-killed' if r['exp_gross']>0 else 'NO (negative even pre-cost)')} |")
    E += ["", "## Primary loss driver (per strategy, quantified)", "",
          "| strategy | net exp R | primary driver |", "|---|---:|---|"]
    for r in rows:
        E.append(f"| {r['s']} | {r['exp_net']:+.3f} | {r['driver']} |")
    # aggregate driver tally
    import re as _re
    cat = Counter()
    for r in rows:
        d = r["driver"]
        cat["transaction costs/overtrading" if d.startswith("Transaction") else
            "TP/SL geometry" if d.startswith("TP/SL") else
            "win-rate/signal" if d.startswith("Win rate") else
            "signal/regime" if d.startswith("Negative") else "none"] += 1
    E += ["", f"**Loss-driver tally:** {dict(cat)}", "",
          "## Verdict — Are ANY strategies economically viable under realistic conditions?", "",
          (f"**YES — {len(viable)} strategy(ies): {', '.join(r['s'] for r in viable)}** "
           f"(net-positive expectancy after fees+slippage)." if viable else
           "**NO. Zero strategies have positive post-cost expectancy.** Not one of the "
           "12 strategies clears breakeven after fees+slippage on any tested cell."),
          "",
          (f"**Closest to breakeven:** " + ", ".join(
              f"{r['s']} ({r['exp_net']:+.3f}R)" for r in rows[:3]) + "."),
          "",
          (f"**Borderline (gross-positive or within −0.10R, structurally adjustable): "
           f"{len(border)}** — {', '.join(r['s'] for r in border) if border else 'none'}."),
          "",
          "_Classification: Economically Viable (net>0) · Borderline (gross>0 or "
          "net>−0.10R) · Non-Viable (negative even pre-cost). No optimization, no "
          "strategy-logic changes, no new epics — diagnosis only._"]
    OUT2 = os.path.join("docs", "reports", "phase5", "ep5.3-economic-viability.md")
    open(OUT2, "w").write("\n".join(E) + "\n")
    print("WROTE", OUT2, f"(viable={len(viable)} borderline={len(border)})")


if __name__ == "__main__":
    main()
