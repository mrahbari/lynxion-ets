"""E39 — R6b: time XS-COMBO-V1 rebalance trades with 1-day cross-sectional reversal (PRE-REGISTERED, 2026-11-25).

Status: registered only. Not run. No live change is part of this experiment; adopting it would need an operator
decision after the prospective shadow stage.

Idea (E31): 1-day cross-sectional reversal is positive GROSS (DEV Sharpe +0.67, HOLDOUT +0.39) but costs kill it as a
stand-alone strategy. Here it adds NO turnover: the same XS-COMBO-V1 trades are executed, some one day later.
Rule (fixed, nothing estimated): on a rebalance day D, for each name with a weight change dw_i = W_D,i - held_i:
  defer the trade by exactly one day (execute at exec(D+1) at the then-target weight W_D,i) if
    dw_i > 0 and the name's 1-day return (row D, known at D) is in the cross-sectional TOP tercile of eligible names
    (we would buy after a jump; reversal expects a give-back), or
    dw_i < 0 and it is in the BOTTOM tercile (we would sell after a drop).
  All other trades execute at exec(D) as now. Deferred names keep their drifted held weight for that one day.
Costs: identical cost model (fee + ADV half-spread + sqrt impact); deferred trades pay their cost on D+1.

Known contamination: the reversal signal was already observed on 2020-2024 and 2025-2026 (E31), so no historical window
is clean. Historical results are therefore NECESSARY, not sufficient; the decisive stage is prospective.

Phase control (E38 finding): the holdout Sharpe of the frozen strategy ranges 0.50-1.77 across the 7 possible weekly
rebalance phases (live-like universe). Any timing effect must be measured PAIRED within each phase.
  For each window W in {2020-01..2024-12, 2025-01..2026-10} and each phase k in 0..6 (start offset k days):
    delta_k = annual net return (E39 rule) - annual net return (baseline), same phase.
Historical PASS (all required): in BOTH windows mean(delta_k) >= +1.0 %/yr AND delta_k > 0 in >= 6 of 7 phases AND
  mean turnover not higher than baseline AND max drawdown not worse than baseline by more than 2 percentage points.
Prospective stage (only after a historical PASS): 8 weekly rebalances computed in shadow from live Binance data (both
  rules, no orders); report the paired delta. Live adoption is an operator decision (changes the live strategy).
Universe: live-like (non-perpetual symbols excluded, as live/parity_check.py).
Usage: cd research/v2 && python experiments/e39_reversal_timed_rebalance.py [--selfcheck | --run]
  --selfcheck runs a synthetic mechanics check only (no market data, no results).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt  # noqa: E402

WINDOWS = {"DEV": ("2020-01-01", "2024-12-31"), "HOLDOUT_USED": ("2025-01-01", "2026-10-31")}


def run_timed(weights, fwd_ret, p, defer_up, defer_dn, cost=None, rebalance_every=7):
    """bt.run with one-day deferral of flagged trades. defer_up/defer_dn: bool frames (row D known at D).
    With no flags it must equal bt.run exactly (checked by --selfcheck)."""
    cost = cost or bt.CostModel()
    idx, cols = weights.index, weights.columns
    W = weights.fillna(0.0).values
    R = fwd_ret.reindex(index=idx, columns=cols).values
    F = p["funding_fwd"].reindex(index=idx, columns=cols).fillna(0.0).values
    adv = p["quote_volume"].rolling(30, min_periods=10).median().reindex(index=idx, columns=cols).values
    vol = np.log(p["close"]).diff().rolling(30, min_periods=10).std().reindex(index=idx, columns=cols).values
    UP = defer_up.reindex(index=idx, columns=cols).fillna(False).values
    DN = defer_dn.reindex(index=idx, columns=cols).fillna(False).values
    n, m = W.shape
    net, turn = np.zeros(n), np.zeros(n)
    held = np.zeros(m)
    pending = None                                   # (mask, weights) to execute on the next day
    for t in range(n):
        if t % rebalance_every == 0:
            target = W[t].copy()
            dw = target - held
            defer = ((dw > 0) & UP[t]) | ((dw < 0) & DN[t])
            target[defer] = held[defer]
            pending = (defer, W[t].copy()) if defer.any() else None
        else:
            target = held.copy()
            if pending is not None:
                target[pending[0]] = pending[1][pending[0]]
                pending = None
        r = R[t]
        bad = ~np.isfinite(r)
        target = np.where(bad, 0.0, target)
        d = np.abs(target - held)
        a = np.where(np.isfinite(adv[t]) & (adv[t] > 0), adv[t], 1e6)
        s = np.where(np.isfinite(vol[t]), vol[t], 0.05)
        unit = cost.fee + cost.half_spread(a) + cost.impact_y * s * np.sqrt(d * cost.capital / a)
        c = float(np.sum(d * unit)) * cost.cost_mult
        r0 = np.where(bad, 0.0, r)
        g, f = float(np.sum(target * r0)), -float(np.sum(target * F[t]))
        net[t], turn[t] = g + f - c, float(d.sum())
        denom = 1.0 + g + f - c
        held = target * (1.0 + r0) / denom if denom > 0 else np.zeros(m)
    return pd.Series(net, index=idx), pd.Series(turn, index=idx)


def selfcheck():
    rng = np.random.default_rng(0)
    idx = pd.date_range("2024-01-01", periods=60, freq="D", tz="UTC")
    cols = [f"S{i}" for i in range(12)]
    close = pd.DataFrame(np.exp(np.cumsum(rng.normal(0, 0.03, (60, 12)), 0)), idx, cols)
    p = {"close": close, "quote_volume": pd.DataFrame(5e7, idx, cols),
         "funding_fwd": pd.DataFrame(rng.normal(0, 1e-4, (60, 12)), idx, cols)}
    fr = close.pct_change().shift(-1)
    sig = pd.DataFrame(rng.normal(size=(60, 12)), idx, cols)
    w = bt.rank_long_short(sig, pd.DataFrame(True, idx, cols), frac=0.25, min_names=4)
    none = pd.DataFrame(False, idx, cols)
    ref = bt.run(w, fr, p, bt.CostModel(), rebalance_every=7)
    net, turn = run_timed(w, fr, p, none, none)
    assert np.allclose(net.values, ref.net.values) and np.allclose(turn.values, ref.turnover.values)
    allf = pd.DataFrame(True, idx, cols)
    net2, turn2 = run_timed(w, fr, p, allf, allf)
    assert abs(turn2.sum() - ref.turnover.sum()) / ref.turnover.sum() < 0.25   # same trades, one day later
    print("selfcheck OK: no-deferral run equals lib.backtest.run; deferral keeps turnover comparable")


def main():
    from lib import panel as pn
    from strategies import xs_combo_v1 as S
    P = S.PARAMS
    p = pn.load_daily(start="2019-10-01", end="2026-10-31")
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    w = bt.rank_long_short(S.signal(p, mask), mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
    r1 = np.log(p["close"]).diff().where(mask).rank(axis=1, pct=True)
    up, dn = r1 > 2 / 3, r1 <= 1 / 3
    rows = []
    for win, (a0, b0) in WINDOWS.items():
        for k in range(7):
            a = pd.Timestamp(a0, tz="UTC") + pd.Timedelta(days=k)
            ww = w[(w.index >= a) & (w.index <= b0)]
            none = pd.DataFrame(False, ww.index, ww.columns)
            out = {}
            for arm, (u, d) in {"BASE": (none, none), "E39": (up, dn)}.items():
                net, turn = run_timed(ww, fr.reindex(ww.index), p, u, d, rebalance_every=P["rebalance_every"])
                y = net.iloc[:-1]
                eq = (1 + y).cumprod()
                out[arm] = {"ann": float(y.mean() * 365), "turn": float(turn.mean() * 365),
                            "mdd": float((eq / eq.cummax() - 1).min()), "sharpe": float(y.mean() / y.std() * np.sqrt(365))}
            rows.append({"window": win, "phase": k, **{f"{a}_{kk}": round(v, 4) for a, o in out.items() for kk, v in o.items()},
                         "delta_ann": round(out["E39"]["ann"] - out["BASE"]["ann"], 4)})
    r = pd.DataFrame(rows)
    r.to_csv(Path(__file__).resolve().parents[3] / "docs/v2/reports/E39_reversal_timed_rebalance.csv", index=False)
    pd.set_option("display.width", 220)
    print(r.to_string(index=False))
    ok = True
    for win, g in r.groupby("window"):
        c = (g.delta_ann.mean() >= 0.01 and (g.delta_ann > 0).sum() >= 6 and g.E39_turn.mean() <= g.BASE_turn.mean()
             and (g.E39_mdd - g.BASE_mdd).min() >= -0.02)
        print(win, "mean delta", round(g.delta_ann.mean(), 4), "phases +", int((g.delta_ann > 0).sum()), "PASS" if c else "FAIL")
        ok &= c
    print("HISTORICAL", "PASS -> prospective shadow stage" if ok else "FAIL")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    elif "--run" in sys.argv:
        main()
    else:
        raise SystemExit("E39 is registered; run with --run only after R5 is closed (operator scope 2026-11-25).")
