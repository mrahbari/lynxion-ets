"""Predictive-power harness orchestrator (Phase-6, Step 1).

Evaluates a candidate signal's QUALITY only: forward-return labelling -> IC (HAC)
-> decile spread -> event-study (optional) -> purged/embargoed walk-forward OOS
-> block stability -> regime-conditional IC -> multiple-testing-corrected verdict.

NO SL/TP, NO sizing, NO cost, NO trading simulation, NO optimization. A promoted
signal is later handed to the (separate, existing) execution/edge-gate stack —
not here.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from forward_labels import vol_normalized_forward_returns
from predictive_power import (
    information_coefficient, decile_analysis, event_study, block_ic)
from cv import purged_walk_forward, assert_no_leakage
from multiple_testing import benjamini_hochberg

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# promotion thresholds (conservative; default posture is REJECT)
ALPHA = 0.05
MIN_ABS_IC = 0.02            # economic-relevance floor
MIN_MONOTONICITY = 0.6       # decile monotonicity (|rho| of bin index vs mean)
MIN_OOS_SIGN_CONSISTENCY = 0.6
MIN_BLOCK_SIGN_CONSISTENCY = 0.6


def _oos_fold_ics(signal, label, horizon, n_splits, embargo):
    """IC on each walk-forward test fold (temporal generalisation, leakage-proof)."""
    df = pd.concat([signal.rename("s"), label.rename("y")], axis=1).replace(
        [np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    splits = purged_walk_forward(len(df), n_splits=n_splits, embargo=embargo)
    if not splits:
        return {"fold_ics": [], "mean_oos_ic": np.nan, "sign_consistency": np.nan,
                "n_folds": 0}
    assert_no_leakage(splits, embargo, walk_forward=True)
    full = information_coefficient(df["s"], df["y"], horizon)["ic"]
    sign = np.sign(full) if full else 1.0
    ics = []
    for _, te in splits:
        r = information_coefficient(df["s"].iloc[te], df["y"].iloc[te], horizon)
        if np.isfinite(r["ic"]):
            ics.append(r["ic"])
    if not ics:
        return {"fold_ics": [], "mean_oos_ic": np.nan, "sign_consistency": np.nan,
                "n_folds": 0}
    cons = float(np.mean([np.sign(v) == sign for v in ics]))
    return {"fold_ics": ics, "mean_oos_ic": float(np.mean(ics)),
            "sign_consistency": cons, "n_folds": len(ics)}


def evaluate_signal(
    signal: pd.Series, close: pd.Series, horizons: list[int],
    regime: pd.Series | None = None, event: bool = False,
    n_splits: int = 5, embargo: int | None = None, n_blocks: int = 6,
) -> dict:
    """Full signal-quality evaluation for ONE symbol across the horizon grid.

    `signal[t]` must use only information <= t (caller's responsibility); labels
    are forward by construction. `embargo` defaults to max(horizons) so test
    labels cannot overlap training observations.
    """
    embargo = embargo if embargo is not None else max(horizons)
    labels = vol_normalized_forward_returns(close, horizons)
    per_h = {}
    for h in horizons:
        y = labels[f"fwd_{h}"]
        ic = information_coefficient(signal, y, horizon=h)
        dec = decile_analysis(signal, y)
        oos = _oos_fold_ics(signal, y, h, n_splits, embargo)
        stab = block_ic(signal, y, n_blocks=n_blocks)
        rec = {"horizon": h, "ic": ic, "decile": dec, "oos": oos, "stability": stab}
        if event:
            rec["event_study"] = event_study(signal, y)
        per_h[h] = rec
    # regime-conditional IC at every horizon (no significance gate, descriptive)
    regimes = {}
    if regime is not None:
        for rv in pd.Series(regime).dropna().unique():
            mask = (regime == rv)
            regimes[str(rv)] = {
                h: information_coefficient(signal[mask], labels[f"fwd_{h}"][mask], h)["ic"]
                for h in horizons}
    return {"per_horizon": per_h, "regime_ic": regimes, "embargo": embargo,
            "horizons": horizons}


def _symbol_verdict(per_h: dict, adj_p: dict) -> dict:
    """Per-symbol promote/archive across horizons using BH-adjusted p-values."""
    best, best_key = None, None
    for h, rec in per_h.items():
        ic = rec["ic"]["ic"]
        if not np.isfinite(ic):
            continue
        if best is None or abs(ic) > abs(best["ic"]["ic"]):
            best, best_key = rec, h
    if best is None:
        return {"verdict": "INSUFFICIENT_DATA", "reasons": ["no valid IC"], "best_horizon": None}
    ic = best["ic"]["ic"]
    dec, oos, stab = best["decile"], best["oos"], best["stability"]
    reasons, ok = [], True
    if adj_p.get(best_key, 1.0) > ALPHA:
        ok = False; reasons.append(f"IC not BH-significant (adj_p={adj_p.get(best_key):.3f})")
    if abs(ic) < MIN_ABS_IC:
        ok = False; reasons.append(f"|IC|={abs(ic):.3f} below floor {MIN_ABS_IC}")
    if not (np.isfinite(dec["monotonicity"]) and abs(dec["monotonicity"]) >= MIN_MONOTONICITY
            and np.sign(dec["spread"]) == np.sign(ic)):
        ok = False; reasons.append("decile not monotone / spread sign mismatch")
    if not (np.isfinite(oos["sign_consistency"]) and oos["sign_consistency"] >= MIN_OOS_SIGN_CONSISTENCY):
        ok = False; reasons.append(f"OOS sign-consistency {oos['sign_consistency']}")
    if not (np.isfinite(stab["sign_consistency"]) and stab["sign_consistency"] >= MIN_BLOCK_SIGN_CONSISTENCY):
        ok = False; reasons.append(f"block sign-consistency {stab['sign_consistency']}")
    return {"verdict": "PROMOTE" if ok else "ARCHIVE", "reasons": reasons or ["all gates passed"],
            "best_horizon": best_key, "best_ic": ic, "best_adj_p": adj_p.get(best_key)}


def evaluate_across_symbols(
    signal_by_symbol: dict, close_by_symbol: dict, horizons: list[int],
    regime_by_symbol: dict | None = None, n_trials: int = 1, **kw,
) -> dict:
    """Run per-symbol evaluation, apply BH across all (symbol x horizon) p-values
    (scaled by n_trials for program-level FDR), and require cross-symbol sign
    agreement for an overall PROMOTE.
    """
    per_symbol = {}
    for sym, sig in signal_by_symbol.items():
        rg = (regime_by_symbol or {}).get(sym)
        per_symbol[sym] = evaluate_signal(sig, close_by_symbol[sym], horizons,
                                          regime=rg, **kw)
    # gather p-values across symbol x horizon; pad the family by n_trials
    keys, pvals = [], []
    for sym, res in per_symbol.items():
        for h, rec in res["per_horizon"].items():
            p = rec["ic"]["p_value"]
            keys.append((sym, h)); pvals.append(p if np.isfinite(p) else 1.0)
    # inflate the tested family to the pre-registered n_trials so BH-FDR accounts
    # for hypotheses counted in the research program (extra slots -> p=1)
    family = pvals + [1.0] * max(0, n_trials - len(pvals))
    rej, adj = benjamini_hochberg(family, ALPHA)
    adj_by_key = {keys[i]: float(adj[i]) for i in range(len(keys))}
    sym_verdicts = {}
    for sym, res in per_symbol.items():
        adj_p = {h: adj_by_key.get((sym, h), 1.0) for h in res["per_horizon"]}
        sym_verdicts[sym] = _symbol_verdict(res["per_horizon"], adj_p)
    # cross-symbol consistency: promoted symbols must agree in sign
    promoted = {s: v for s, v in sym_verdicts.items() if v["verdict"] == "PROMOTE"}
    signs = {np.sign(v["best_ic"]) for v in promoted.values()}
    n_sym = len(signal_by_symbol)
    if len(promoted) >= max(2, (n_sym + 1) // 2) and len(signs) == 1:
        overall = "PROMOTE"
    elif promoted:
        overall = "PROVISIONAL"  # edge in some symbols, not cross-symbol robust
    else:
        overall = "ARCHIVE"
    return {"overall_verdict": overall, "symbol_verdicts": sym_verdicts,
            "per_symbol": per_symbol, "n_trials": n_trials,
            "cross_symbol_sign_agreement": len(signs) == 1 if promoted else None}


@dataclass
class EdgeLedger:
    """Append-only ledger of tested signal hypotheses (the Phase-6 analogue of the
    Phase-5 blocker ledger). Records verdicts; never trading results."""
    entries: list = field(default_factory=list)

    def record(self, name: str, hypothesis_class: str, result: dict) -> None:
        self.entries.append({
            "name": name, "hypothesis_class": hypothesis_class,
            "overall_verdict": result.get("overall_verdict"),
            "symbol_verdicts": {s: {k: v for k, v in sv.items() if k != "reasons"}
                                for s, sv in result.get("symbol_verdicts", {}).items()},
        })

    def save(self, path: str | None = None) -> str:
        path = path or os.path.join(RESULTS_DIR, "edge_ledger.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.entries, f, indent=2, default=str)
        return path
