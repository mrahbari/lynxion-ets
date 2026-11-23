"""E13 — XS-COMBO-V1 per-name risk: can every leg follow the platform's "bounded loss per position" rule
without killing the carry edge?

Why: 2026-11-22 AKEUSDT closed at -147 USDT (-30 % of a 500 USDT leg) under the 50 % disaster stop. E5 (DEV only)
showed tight FIXED stops destroy the strategy (10 % stop: SR 1.94 -> 0.43). The platform's rule is about the loss
per position, which can be bounded by SIZING (notional = risk budget / stop distance) instead of a tight stop.

Pre-registered before running (2026-11-23):
  Book: frozen XS-COMBO-V1 names (top/bottom 20 %), weekly, gross 1.0 (0.5 / 0.5). Same loop as E5: per-name stop
  on daily high/low, stopped leg books -stop and an extra 30 bp; funding only while held; delisted -> last close.
  sigma_i = std of the last 30 daily log returns known at the decision (row t0 = completed day), floored at 2 %.
  Variants:
    EW_none   equal weight, no stop                     EW_50  equal weight, 50 % stop (live today)
    EW_20     equal weight, 20 % stop                   ER_50  equal-risk weights (w ~ 1/sigma per side), 50 % stop
    ER_k{2,3,4}  equal-risk weights, stop = k * sigma * sqrt(7) (capped at 50 %) -> every leg risks the same
                 fraction of the book at its stop
  Metrics: weekly SR, ann, maxDD, worst week, and TAIL = worst single-leg loss in a week as % of gross book
  (the AKE question), p99 leg loss.
  Decision rule (DEV 2020-2024): a variant replaces EW_50 only if SR_dev >= 0.9 * SR(EW_50) AND TAIL_dev <= 0.5 *
  TAIL(EW_50). If several pass, the highest SR_dev. HOLDOUT 2025-01-01..2026-10-31 is then read for EW_50 and the
  chosen variant only: chosen must have SR_hold > 0.75 and SR_hold >= SR_hold(EW_50) - 0.3. Other holdout numbers
  are printed for transparency, not used for choice.

Usage: python research/v2/experiments/e13_xs_combo_risk_sizing.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

OUT = Path(__file__).resolve().parents[3] / "docs" / "v2" / "reports"
P = S.PARAMS
VARIANTS = {"EW_none": ("ew", None), "EW_50": ("ew", 0.50), "EW_20": ("ew", 0.20), "ER_50": ("er", 0.50),
            "ER_k2": ("er", 2.0), "ER_k3": ("er", 3.0), "ER_k4": ("er", 4.0)}
WINDOWS = {"dev": ("2020-01-01", "2024-12-31"), "holdout": ("2025-01-01", "2026-10-31")}


def run(start: str, end: str) -> tuple[pd.DataFrame, dict]:
    p = pn.load_daily(1, (pd.Timestamp(start) - pd.Timedelta(days=150)).strftime("%Y-%m-%d"), end)
    m = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
    w = bt.rank_long_short(S.signal(p, m), m, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
    idx = p["close"].index
    t_start = idx.searchsorted(pd.Timestamp(start, tz="UTC"))
    px, hi, lo, fu = (p[k].values for k in ("exec_px", "high", "low", "funding_fwd"))
    sig = np.log(p["close"]).diff().rolling(30, min_periods=20).std().values
    W = w.values
    res = {v: [] for v in VARIANTS}
    legs = {v: [] for v in VARIANTS}
    nstop = {v: 0 for v in VARIANTS}
    dates = []
    for t0 in range(t_start, len(idx) - 7, 7):
        wt = np.nan_to_num(W[t0])
        names = np.nonzero(wt)[0]
        if len(names) == 0:
            continue
        dates.append(idx[t0])
        e = px[t0, names]
        s_i = np.clip(np.nan_to_num(sig[t0, names], nan=0.05), 0.02, None)
        er = np.zeros(len(names))
        for side in (1, -1):
            k = np.sign(wt[names]) == side
            if k.any():
                er[k] = side * 0.5 * (1 / s_i[k]) / (1 / s_i[k]).sum()
        for v, (mode, stop) in VARIANTS.items():
            ws = wt[names] if mode == "ew" else er
            pnl = 0.0
            for j, c in enumerate(names):
                ww = ws[j]
                sign = np.sign(ww)
                if stop is None:
                    sd = None
                elif stop > 1:
                    sd = min(stop * s_i[j] * np.sqrt(7), 0.5)
                else:
                    sd = stop
                exit_ret, held = None, 7
                if sd is not None and np.isfinite(e[j]):
                    for kk in range(1, 8):
                        adverse = (lo[t0 + kk, c] / e[j] - 1) if sign > 0 else -(hi[t0 + kk, c] / e[j] - 1)
                        if np.isfinite(adverse) and adverse <= -sd:
                            exit_ret, held = -sd, kk
                            nstop[v] += 1
                            break
                if exit_ret is None:
                    end_px = px[t0 + 7, c]
                    if not np.isfinite(end_px):
                        col = px[t0:t0 + 8, c]
                        col = col[np.isfinite(col)]
                        end_px = col[-1] if len(col) else np.nan
                    r = end_px / e[j] - 1 if np.isfinite(e[j]) and np.isfinite(end_px) else 0.0
                    leg = ww * r
                else:
                    leg = abs(ww) * exit_ret - abs(ww) * 0.003
                leg -= ww * np.nansum(fu[t0:t0 + held, c])
                legs[v].append(leg)
                pnl += leg
            res[v].append(pnl)
    df = pd.DataFrame(res, index=dates)
    df = df[df.index <= pd.Timestamp(end, tz="UTC")]
    return df, {"legs": legs, "nstop": nstop}


def summarize(df: pd.DataFrame, extra: dict, window: str) -> pd.DataFrame:
    rows = []
    for v in VARIANTS:
        x = df[v]
        eq = (1 + x).cumprod()
        lg = np.asarray(extra["legs"][v])
        rows.append({"window": window, "variant": v, "weeks": len(x), "SR": round(x.mean() / x.std() * np.sqrt(52), 2),
                     "ann": round(x.mean() * 52, 3), "maxDD": round((eq / eq.cummax() - 1).min(), 3),
                     "worst_week": round(x.min(), 3), "stops_hit": extra["nstop"][v],
                     "tail_leg_pct_book": round(-lg.min() * 100, 2),
                     "p99_leg_loss_pct_book": round(-np.percentile(lg, 1) * 100, 2)})
    return pd.DataFrame(rows)


def main() -> None:
    out = []
    for wname, (a, b) in WINDOWS.items():
        df, extra = run(a, b)
        out.append(summarize(df, extra, wname))
    r = pd.concat(out)
    dev = r[r.window == "dev"].set_index("variant")
    base = dev.loc["EW_50"]
    ok = dev[(dev.SR >= 0.9 * base.SR) & (dev.tail_leg_pct_book <= 0.5 * base.tail_leg_pct_book)
             & (dev.index != "EW_50")]
    chosen = ok.SR.idxmax() if len(ok) else None
    r["dev_pass"] = r.variant.isin(ok.index) & (r.window == "dev")
    print(r.to_string(index=False))
    print("chosen on DEV:", chosen)
    if chosen:
        hold = r[r.window == "holdout"].set_index("variant")
        hp = bool(hold.loc[chosen, "SR"] > 0.75 and hold.loc[chosen, "SR"] >= hold.loc["EW_50", "SR"] - 0.3)
        print("holdout pass:", hp, "| chosen SR", hold.loc[chosen, "SR"], "vs EW_50", hold.loc["EW_50", "SR"])
    r.to_csv(OUT / "E13_xs_combo_risk_sizing.csv", index=False)


if __name__ == "__main__":
    main()
