"""E37 — Continuation after stretch / CVD-divergence / capitulation events, 72 h (follow-up of E36, 2026-11-25).

Why: E36 (DEV) found no reversal edge; the opposite was visible instead: after F1 STRETCH, F7 CVDDIV and F8 CAPIT
the 72 h gross move CONTINUED (-79.5 / -139.9 / -109.5 bp in the reversal direction). That pattern was found on
DEV, so DEV is the hypothesis source, not evidence. The test is HOLDOUT 2025-01..2026-10, never read in E36.
Pre-registered (committed before any run). Same event definitions, data and costs as E36 (imported, unchanged).
  Direction: WITH the event (d = -E36 reversal direction). Entry next 4h open; exit close of bar i+18 (72 h);
  5 bp fee + 2 bp slippage per side; real funding over the hold. No stops (event study). Non-overlap 18 bars.
  Families: F1_STRETCH, F7_CVDDIV, F8_CAPIT, condition C0_ALL only (3 tests, Holm).
  PASS per family (HOLDOUT): net mean >= +15 bp, Holm-adjusted p < 0.05 (day-clustered t), excess over drift > 0,
  >= 6/10 symbols positive. DEV is printed for reference only.
  Decision: PASS -> E38 designs a tradable rule (stops, sizing, overlap with TrendFollow) and compares it with
  the live TrendFollow; FAIL -> event-driven continuation rejected too; record and move on.
Usage: python research/v2/experiments/e37_event_continuation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e36_reversal_conditions as e36  # noqa: E402

FAMS = ["F1_STRETCH", "F7_CVDDIV", "F8_CAPIT"]
_events = e36.events
e36.HOLD = 18
e36.FAMILIES = FAMS
e36.CONDS = ["C0_ALL"]
e36.events = lambda g, q: {k: -v for k, v in _events(g, q).items() if k in FAMS}


def main():
    q = e36.dev_quantiles()
    evs, bases = zip(*(e36.outcomes(s, q) for s in e36.SYMS))
    ev, base = pd.concat(evs, ignore_index=True), pd.concat(bases, ignore_index=True)
    cols = ["family", "n", "net_bp", "gross_bp", "excess_bp", "t_day", "win", "sym_pos", "mfe_atr", "mae_atr"]
    pd.set_option("display.width", 200)
    dev = e36.table(ev, e36.drift_table(base, e36.DEV0, e36.HOLD0), e36.DEV0, e36.HOLD0)
    print("DEV (hypothesis source, not evidence)\n", dev[cols + ["h1_bp", "h2_bp"]].to_string(index=False))
    ho = e36.table(ev, e36.drift_table(base, e36.HOLD0, e36.END), e36.HOLD0, e36.END)
    ho["p_holm"] = e36.holm(ho.p)
    ho["pass"] = (ho.net_bp >= 15) & (ho.p_holm < 0.05) & (ho.excess_bp > 0) & (ho.sym_pos_n >= 6)
    print("HOLDOUT (the test)\n", ho[cols + ["p_holm", "pass"]].to_string(index=False))
    pd.concat([dev.assign(window="DEV"), ho.assign(window="HOLDOUT")]).to_csv(
        e36.e23.OUT / "E37_event_continuation.csv", index=False)


if __name__ == "__main__":
    main()
