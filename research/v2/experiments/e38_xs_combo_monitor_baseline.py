"""E38 — R5 XS-COMBO-V1 degradation monitor: baseline thresholds + pre-registered validation (2026-11-25).

Purpose: the live monitor (research/v2/live/monitor.py) is OBSERVATIONAL. Its thresholds must come from the frozen
strategy's own history, not from chosen numbers. This script replays the frozen XS-COMBO-V1 backtest
(strategies/xs_combo_v1.py, lib/backtest.py; Binance panel 2020-01-01..2026-10-31, non-perpetual symbols excluded as
in live/parity_check.py) and computes, for each indicator, the same quantity the live monitor computes:

  ex_ante_carry    daily: sum_i -w_i * (21-day funding sum_i) * 365/21, w = last rebalance target (gross 1)
  adverse_share    daily: share of target names whose 21-day funding works against the position
  realized_carry   daily: rolling 28-day mean of funding P&L / gross exposure, annualised
  ret_56d          daily: rolling 56-day mean net return, annualised (the R5 "8-week" decay window)
  drawdown         daily: net equity / running peak - 1
  beta_btc         daily: rolling 28-day beta of net return to BTC daily return
  turnover         per rebalance: sum |w_new - w_old| of targets
  max_share, top5_share, net_exposure   daily, from weights drifted with returns inside the week
  model_exec_cost  per rebalance: backtest (cost - fee x turnover) / turnover = assumed half-spread + impact per unit

Threshold rule (fixed now, no tuning): WARN at the 10th percentile and ALERT at the 2.5th percentile on the BAD side
of each indicator's full-history distribution (low side for carry/return/drawdown; high side for adverse_share,
turnover, concentration, |net_exposure|, |beta|). Slippage: WARN above the model execution cost, ALERT above 2x it
(2x is the cost stress already validated in E2-E4; beyond it nothing was validated).

Pre-registered validation (walk-forward, thresholds from CALIBRATION 2020-01..2022-12 only, applied to
OOS 2023-01..2026-10):
  V-a false-alarm rate: share of OOS days in ALERT per daily indicator <= 10 % -> indicator usable as an alarm.
  V-b predictive value: weekly non-overlapping samples; mean NEXT-28-day net return after WARN-or-worse vs after OK,
      for ex_ante_carry, realized_carry, ret_56d. Called "leading" only if lower after WARN with Welch t <= -2.0.
      Otherwise the indicator is reported as descriptive only (it states what happened, not what will happen).
Output: research/v2/results/xs_combo_monitor_thresholds.json (used live), docs/v2/reports/E38_monitor_validation.csv.
Usage: cd research/v2 && python experiments/e38_xs_combo_monitor_baseline.py [--cluster-baseline]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
THRESH = Path(__file__).resolve().parents[1] / "results" / "xs_combo_monitor_thresholds.json"
P = S.PARAMS
START, END, CAL_END = "2020-01-01", "2026-10-31", "2022-12-31"
LOW_BAD = ["ex_ante_carry", "realized_carry", "ret_56d", "drawdown"]
HIGH_BAD = ["adverse_share", "turnover", "max_share", "top5_share", "abs_net_exposure", "abs_beta_btc"]
DAILY = ["ex_ante_carry", "adverse_share", "realized_carry", "ret_56d", "drawdown", "abs_beta_btc", "max_share",
         "top5_share", "abs_net_exposure"]
LEADING = ["ex_ante_carry", "realized_carry", "ret_56d"]


def series():
    p = pn.load_daily(start="2019-10-01", end=END)
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    fr = pn.forward_returns(p)
    w = bt.rank_long_short(S.signal(p, mask), mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
    w = w[(w.index >= START) & (w.index <= END)]
    r = bt.run(w, fr.reindex(w.index), p, bt.CostModel(), rebalance_every=P["rebalance_every"])
    idx = w.index
    reb = idx[np.arange(len(idx)) % P["rebalance_every"] == 0]
    tgt = w.loc[reb].reindex(idx, method="ffill")                       # last rebalance target, held all week
    c21 = p["funding_past"].rolling(21, min_periods=1).sum().reindex(index=idx, columns=w.columns).fillna(0)
    d = pd.DataFrame(index=idx)
    d["ex_ante_carry"] = -(tgt * c21).sum(1) * 365 / 21
    held = tgt != 0
    adverse = ((np.sign(tgt) * c21) > 0) & held
    d["adverse_share"] = adverse.sum(1) / held.sum(1).replace(0, np.nan)
    net = r.net.iloc[:-1]
    d["realized_carry"] = (r.funding / r.gross_exposure.replace(0, np.nan)).rolling(28).mean() * 365
    d["ret_56d"] = net.rolling(56).mean() * 365
    eq = (1 + net.fillna(0)).cumprod()
    d["drawdown"] = eq / eq.cummax() - 1
    btc = fr["BTCUSDT"].reindex(idx)
    d["abs_beta_btc"] = (net.rolling(28).cov(btc) / btc.rolling(28).var()).abs()
    # weights drifted with returns inside each week (shares are ratios, normalisation cancels)
    grow = (1 + fr.reindex(index=idx, columns=w.columns).fillna(0))
    block = pd.Series(np.arange(len(idx)) // P["rebalance_every"], index=idx)
    cum = grow.groupby(block.values).cumprod() / grow          # growth up to (not incl.) day t within the week
    hw = tgt * cum
    gross = hw.abs().sum(1).replace(0, np.nan)
    sh = hw.abs().div(gross, axis=0)
    d["max_share"] = sh.max(1)
    d["top5_share"] = sh.apply(lambda x: x.nlargest(5).sum(), axis=1)
    d["abs_net_exposure"] = (hw.sum(1) / gross).abs()
    d["net"] = net
    d["fwd28"] = net[::-1].rolling(28).sum()[::-1].shift(-1)
    rb = pd.DataFrame(index=reb[1:])
    rb["turnover"] = (w.loc[reb].diff().abs().sum(1)).iloc[1:]
    tv = r.turnover.loc[reb[1:]]
    rb["model_exec_cost"] = ((r.cost.loc[reb[1:]] - bt.CostModel().fee * tv) / tv.replace(0, np.nan))
    return d, rb


def thresholds(d, rb, lo, hi):
    out = {}
    for k in LOW_BAD + HIGH_BAD:
        src = rb if k == "turnover" else d
        x = src.loc[lo:hi, k].dropna()
        if k in LOW_BAD:
            out[k] = {"warn": float(x.quantile(0.10)), "alert": float(x.quantile(0.025)), "bad": "low",
                      "median": float(x.median()), "n": int(len(x))}
        else:
            out[k] = {"warn": float(x.quantile(0.90)), "alert": float(x.quantile(0.975)), "bad": "high",
                      "median": float(x.median()), "n": int(len(x))}
    mc = float(rb.loc[lo:hi, "model_exec_cost"].median())
    out["slippage_bp"] = {"warn": mc * 1e4, "alert": 2 * mc * 1e4, "bad": "high", "median": None,
                          "n": int(rb.loc[lo:hi, "model_exec_cost"].notna().sum())}
    return out


def status(x, t):
    if x is None or not np.isfinite(x):
        return "NA"
    if t["bad"] == "low":
        return "ALERT" if x <= t["alert"] else "WARN" if x <= t["warn"] else "OK"
    return "ALERT" if x >= t["alert"] else "WARN" if x >= t["warn"] else "OK"


def main():
    d, rb = series()
    cal = thresholds(d, rb, START, CAL_END)
    oos = d.loc["2023-01-01":END]
    rows = []
    for k in DAILY:
        st_ = oos[k].map(lambda x: status(x, cal[k]))
        row = {"indicator": k, "oos_days": int((st_ != "NA").sum()), "alert_rate": round(float((st_ == "ALERT").mean()), 3),
               "warn_or_worse_rate": round(float(st_.isin(["WARN", "ALERT"]).mean()), 3),
               "usable_alarm": bool((st_ == "ALERT").mean() <= 0.10)}
        if k in LEADING:
            wk = oos.iloc[::7]
            s = wk[k].map(lambda x: status(x, cal[k]))
            a, b = wk.fwd28[s.isin(["WARN", "ALERT"])].dropna(), wk.fwd28[s == "OK"].dropna()
            tv = float((a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))) if len(a) > 2 and len(b) > 2 else np.nan
            row.update({"n_warn_weeks": len(a), "fwd28_after_warn": round(float(a.mean()), 4) if len(a) else None,
                        "fwd28_after_ok": round(float(b.mean()), 4), "welch_t": round(tv, 2),
                        "leading": bool(np.isfinite(tv) and tv <= -2.0)})
        rows.append(row)
    v = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print(v.to_string(index=False))
    v.to_csv(ROOT / "docs/v2/reports/E38_monitor_validation.csv", index=False)
    full = thresholds(d, rb, START, END)
    for k in DAILY:
        full[k]["validated_alarm"] = bool(v.set_index("indicator").loc[k, "usable_alarm"])
        if k in LEADING:
            full[k]["leading"] = bool(v.set_index("indicator").loc[k, "leading"])
    full["_meta"] = {"source": "e38_xs_combo_monitor_baseline.py", "window": [START, END],
                     "rule": "WARN p10 / ALERT p2.5 on the bad side; slippage WARN > model cost, ALERT > 2x",
                     "holdout_summary": {"ann_net": round(float(d.net.loc["2025":].mean() * 365), 4),
                                         "ann_funding_on_gross_median": round(float(d.realized_carry.loc["2025":].median()), 4)}}
    THRESH.write_text(json.dumps(full, indent=1))
    print(json.dumps({k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in t.items()}
                      for k, t in full.items() if k != "_meta"}, indent=1))
    print(full["_meta"])


def avg_pair_corr(rets: pd.DataFrame) -> float:
    """Mean off-diagonal correlation of the columns (names with a full window only); NaN if < 3 names."""
    r = rets.dropna(axis=1)
    if r.shape[1] < 3:
        return float("nan")
    c = np.corrcoef(r.values.T)
    return float(c[np.triu_indices_from(c, 1)].mean())


def cluster_baseline():
    """Added 2026-11-25 (after E40, operator-approved R5 addition): distribution of the average pairwise 30-day
    daily-return correlation inside the long leg and inside the short leg of each weekly target book. INFO only in
    the live monitor (not validated as an alarm); appended to the thresholds file without touching other keys."""
    p = pn.load_daily(start="2019-10-01", end=END)
    mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    mask.loc[:, [c for c in mask.columns if c in nps]] = False
    w = bt.rank_long_short(S.signal(p, mask), mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
    w = w[(w.index >= START) & (w.index <= END)]
    lr = np.log(p["close"]).diff()
    rows = []
    for d in w.index[::P["rebalance_every"]]:
        win = lr.loc[:d].iloc[-30:]
        row = w.loc[d]
        rows.append({"date": d, "corr_long": avg_pair_corr(win[row[row > 0].index]),
                     "corr_short": avg_pair_corr(win[row[row < 0].index])})
    c = pd.DataFrame(rows).set_index("date")
    th = json.loads(THRESH.read_text())
    for k in ("corr_long", "corr_short"):
        x = c[k].dropna()
        th[k] = {"warn": float(x.quantile(0.90)), "alert": float(x.quantile(0.975)), "bad": "high",
                 "median": float(x.median()), "n": int(len(x)), "validated_alarm": False}
        print(k, {kk: round(v, 3) if isinstance(v, float) else v for kk, v in th[k].items()})
    THRESH.write_text(json.dumps(th, indent=1))


if __name__ == "__main__":
    cluster_baseline() if "--cluster-baseline" in sys.argv else main()
