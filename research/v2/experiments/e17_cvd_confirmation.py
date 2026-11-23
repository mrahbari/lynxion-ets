"""E17 — CVD (aggressive buy - sell volume) as the entry confirmation of the platform strategies (roadmap E13-1).

Why: the platform's execution-confirmation stage (DecisionPipeline: OBI + CVD) never received data before
2026-11-23; with real values in shadow mode it would block about 2/3 of entries. Before enabling it
(E14-3, fail-closed), test offline whether CVD-confirmed trades are better. OBI cannot be tested offline
(no historical order book); CVD can, from Binance kline taker-buy volume.

Pre-registered before running (2026-11-23); nothing changed after seeing results.
  Trades: E9 trades (8 strategies, 10 perps, live-equivalent execution, net of fees, R units).
  CVD at entry: Binance USD-M 5m klines CLOSED before the entry time t_in (bar open + 5 min <= t_in).
    delta_w = sum over the last w minutes of (2 x taker_buy_quote - quote_volume) = buy - sell quote volume.
    Windows w in {5, 15, 60} min (5 min = the live shadow window).
  States vs trade side: confirm (BUY & delta > 0, or SELL & delta < 0) / oppose (otherwise) — the live rule
    (cvd >= 0 for BUY, <= 0 for SELL) up to the zero case.
  DEV (2025-11-01..2026-06-30) cell pass, per strategy x window x state (same as E12): n >= 100, mean R >= +0.05,
    PF >= 1.2, both time halves > 0, >= 6/10 symbols positive. HOLDOUT (2026-07-01..10-31) read only for DEV
    passes: mean R > 0, PF >= 1.1.
  Platform decision (E14-3): the CVD confirmation is useful only if, for the 5 min window, the pooled lift of
    "confirm" (mean R minus the strategy's mean R) is >= +0.03 R with t >= 2 on DEV AND > 0 with t >= 1.5 on
    HOLDOUT. Otherwise enabling it would only cut trades.

Usage: python research/v2/experiments/e17_cvd_confirmation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402
import e12_watcher_role_filters as e12  # noqa: E402
from e17_cvd_data import klines5  # noqa: E402

OUT = e9.OUT
DEV0, HOLD0 = e12.DEV0, e12.HOLD0
BAR = 300_000
WINDOWS = (5, 15, 60)


def tag(tr: pd.DataFrame) -> pd.DataFrame:
    out = []
    for sym, g in tr.groupby("symbol"):
        k = klines5(sym)
        k = k.assign(delta=2 * k.tbq - k.qv, close_t=k.t + BAR)
        for w in WINDOWS:
            n = w // 5
            k[f"d{w}"] = k.delta.rolling(n, min_periods=n).sum()
        g = pd.merge_asof(g.sort_values("t_in"), k[["close_t"] + [f"d{w}" for w in WINDOWS]],
                          left_on="t_in", right_on="close_t", direction="backward")
        out.append(g)
    d = pd.concat(out)
    buy = d.side == "BUY"
    for w in WINDOWS:
        x = d[f"d{w}"]
        d[f"cvd{w}"] = np.where(x.isna(), "na", np.where((buy & (x > 0)) | (~buy & (x < 0)), "confirm", "oppose"))
    return d


def lift(d: pd.DataFrame, col: str) -> pd.DataFrame:
    d = d.assign(l=d.R - d.groupby("strategy").R.transform("mean"))
    g = d.groupby(col).l.agg(["size", "mean", "std"])
    return pd.DataFrame({"n": g["size"], "lift_R": g["mean"].round(4),
                         "t": (g["mean"] / (g["std"] / np.sqrt(g["size"]))).round(2)})


def main() -> None:
    d = tag(pd.read_csv(OUT / "E9_strategy_backtest_trades.csv"))
    dev, hold = d[(d.t_in >= DEV0) & (d.t_in < HOLD0)], d[d.t_in >= HOLD0]
    rows = []
    for strat, g in dev.groupby("strategy"):
        base = g.R.mean()
        for w in WINDOWS:
            col = f"cvd{w}"
            for state, gg in g[g[col] != "na"].groupby(col):
                s = e12.stats(gg)
                s.update(strategy=strat, window_min=w, state=state, lift_R=round(gg.R.mean() - base, 3))
                s["dev_pass"] = bool(s["n"] >= 100 and s["mean_R"] >= 0.05 and s["PF"] >= 1.2 and s["h1_R"] > 0
                                     and s["h2_R"] > 0 and s["symbols_positive"] >= 6)
                if s["dev_pass"]:
                    hh = hold[(hold.strategy == strat) & (hold[col] == state)]
                    hs = e12.stats(hh) if len(hh) > 1 else {"n": len(hh)}
                    s.update({f"holdout_{k}": v for k, v in hs.items()})
                    s["holdout_pass"] = bool(len(hh) > 1 and hs["mean_R"] > 0 and hs["PF"] >= 1.1)
                rows.append(s)
    r = pd.DataFrame(rows)
    cols = ["strategy", "window_min", "state", "n", "mean_R", "lift_R", "PF", "h1_R", "h2_R", "symbols_positive",
            "dev_pass"]
    r = r[cols + [c for c in r.columns if c not in cols]]
    r.to_csv(OUT / "E17_cvd_confirmation.csv", index=False)
    pooled = []
    for name, part in (("DEV", dev), ("HOLDOUT", hold)):
        for w in WINDOWS:
            col = f"cvd{w}"
            pooled.append(lift(part[part[col] != "na"], col).reset_index().rename(columns={col: "state"})
                          .assign(period=name, window_min=w))
    pooled = pd.concat(pooled)[["period", "window_min", "state", "n", "lift_R", "t"]]
    pooled.to_csv(OUT / "E17_cvd_confirmation_pooled.csv", index=False)
    c = pooled[(pooled.window_min == 5) & (pooled.state == "confirm")].set_index("period")
    useful = bool(c.loc["DEV", "lift_R"] >= 0.03 and c.loc["DEV", "t"] >= 2
                  and c.loc["HOLDOUT", "lift_R"] > 0 and c.loc["HOLDOUT", "t"] >= 1.5)
    share = {w: round(float((d[f"cvd{w}"] == "confirm").mean()), 3) for w in WINDOWS}
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(f"trades: DEV {len(dev)}, HOLDOUT {len(hold)}; confirm share {share}")
    print(f"cells: {len(r)}; DEV passes: {int(r.dev_pass.sum())}")
    print(r.to_string(index=False))
    print(pooled.to_string(index=False))
    print(f"PLATFORM DECISION (5 min CVD confirmation useful): {useful}")


if __name__ == "__main__":
    main()
