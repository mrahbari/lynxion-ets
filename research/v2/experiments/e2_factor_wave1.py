"""E2 — factor wave 1: classic cross-sectional signals on the full Binance USDT-M universe.

DEVELOPMENT PERIOD ONLY (2020-01-01 .. 2024-12-31). The holdout (2025+) is never loaded here.
Every (signal, rebalance) pair is a trial; both signs are counted as trials for the DSR because
the sign is chosen after seeing the result.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt  # noqa: E402
from lib import panel as pn  # noqa: E402
from lib import stats as st  # noqa: E402

DEV_START, DEV_END = "2020-01-01", "2024-12-31"
OUT = Path(__file__).resolve().parents[3] / "docs" / "v2" / "reports"


def signals(p: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    c = p["close"]
    lr = np.log(c).diff()
    qv = p["quote_volume"]
    S: dict[str, pd.DataFrame] = {}
    for L in (1, 3, 7, 14, 28, 56):
        S[f"mom_{L}d"] = np.log(c / c.shift(L))
    S["mom_28d_skip7"] = np.log(c.shift(7) / c.shift(28))
    S["mom_56d_skip7"] = np.log(c.shift(7) / c.shift(56))
    S["mom_voladj_28d"] = S["mom_28d"] / lr.rolling(28, min_periods=14).std()
    for L in (1, 3, 7, 21):
        S[f"carry_funding_{L}d"] = -p["funding_past"].rolling(L, min_periods=1).sum()   # short high funding
    S["funding_change_7d"] = -(p["funding_past"].rolling(7).sum() - p["funding_past"].shift(7).rolling(7).sum())
    for L in (1, 3, 7):
        S[f"premium_{L}d"] = -p["premium_mean"].rolling(L, min_periods=1).mean()           # short rich perp
    S["premium_change_3d"] = -(p["premium_mean"].rolling(3).mean() - p["premium_mean"].shift(3).rolling(3).mean())
    S["lowvol_30d"] = -lr.rolling(30, min_periods=20).std()
    btc = lr["BTCUSDT"]
    cov = lr.rolling(60, min_periods=40).cov(btc)
    beta = cov.div(btc.rolling(60, min_periods=40).var(), axis=0)
    S["lowbeta_60d"] = -beta
    resid = lr.sub(beta.mul(btc, axis=0))
    S["low_idiovol_30d"] = -resid.rolling(30, min_periods=20).std()
    S["amihud_illiq_30d"] = (lr.abs() / qv).rolling(30, min_periods=20).mean()
    S["volume_shock_3v30"] = np.log(qv.rolling(3).mean() / qv.rolling(30, min_periods=20).mean())
    tb = p["taker_buy_quote"] / qv - 0.5
    S["taker_imb_1d"] = tb
    S["taker_imb_7d"] = tb.rolling(7, min_periods=4).mean()
    S["lottery_max_30d"] = -lr.rolling(30, min_periods=20).max()
    S["skew_30d"] = -lr.rolling(30, min_periods=20).skew()
    S["young_age"] = -np.log(c.notna().cumsum().where(c.notna()))
    S["range_vol_7d"] = -np.log(p["high"] / p["low"]).rolling(7, min_periods=4).mean()
    S["dist_high_56d"] = c / c.rolling(56, min_periods=28).max()
    return S


def main() -> None:
    p = pn.load_daily(start=DEV_START, end=DEV_END)
    mask = pn.universe_mask(p)
    fr = pn.forward_returns(p)
    fr.iloc[-1] = np.nan  # last dev row would earn a holdout-day return
    print("universe size (median/min/max):", int(mask.sum(1).median()), int(mask.sum(1).min()), int(mask.sum(1).max()))
    S = signals(p)
    rows, nets = [], {}
    for name, sig in S.items():
        for reb in (1, 7):
            w = bt.rank_long_short(sig, mask, frac=0.2, min_names=30)
            r = bt.run(w, fr, p, rebalance_every=reb)
            r2 = bt.run(w, fr, p, bt.CostModel(cost_mult=2.0), rebalance_every=reb)
            s = st.summary(r.net, r.gross, r.turnover)
            s["sharpe_net_2xcost"] = st.sharpe(r2.net)
            top = r.sym_pnl.abs().sort_values(ascending=False)
            s["top_symbol_share"] = float(top.iloc[0] / r.sym_pnl.abs().sum()) if top.sum() else None
            s["top_symbol"] = top.index[0]
            key = f"{name}|reb{reb}"
            st.log_trial("E2_wave1", key, {"frac": 0.2, "reb": reb, "period": [DEV_START, DEV_END]}, s, r.net)
            nets[key] = r.net
            nets[key + "|neg"] = -r.gross - r.cost + (-r.funding)  # opposite sign, same costs
            rows.append({"trial": key, **{k: s[k] for k in ("sharpe_gross", "sharpe", "sharpe_net_2xcost",
                                                            "ann_ret", "max_dd", "avg_daily_turnover",
                                                            "pos_years", "n_years", "top_symbol_share")},
                         "by_year": json.dumps(s["sharpe_by_year"])})
            print(f"{key:28s} grossSR={s['sharpe_gross']:+.2f} netSR={s['sharpe']:+.2f} "
                  f"2x={s['sharpe_net_2xcost']:+.2f} turn={s['avg_daily_turnover']:.2f} yrs+={s['pos_years']}/{s['n_years']}",
                  flush=True)
    df = pd.DataFrame(rows)
    d = st.deflate_all(nets)  # n_trials = all signals x reb x 2 signs
    df = df.merge(d.rename(columns={"name": "trial"}), on="trial", how="left", suffixes=("", "_d"))
    neg = d[d["name"].str.endswith("|neg")].copy()
    OUT.mkdir(parents=True, exist_ok=True)
    df.sort_values("sharpe", ascending=False).to_csv(OUT / "E2_wave1_trials.csv", index=False)
    neg.to_csv(OUT / "E2_wave1_reversed_sign.csv", index=False)
    print("\nDSR threshold SR:", d["sr_threshold"].iloc[0], " n_trials:", len(nets))
    print(df.sort_values("sharpe", ascending=False).head(15)[["trial", "sharpe", "sharpe_net_2xcost", "dsr", "pos_years"]])
    print(neg.head(8))


if __name__ == "__main__":
    main()
