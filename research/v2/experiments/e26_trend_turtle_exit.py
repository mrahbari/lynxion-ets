"""E26 — TrendFollow exit design: live (2 ATR stop, 6 ATR target, BE/trail) vs canonical Turtle exit (2026-11-24).

Entry identical in both arms: the live setup (infrastructure/strategies/trend_donchian.py — Donchian-20 breakout
with EMA50/200 filter, closed 1h bars, last 400), next-bar-open entry, one position per symbol.
Universe / windows / costs as E9: 10 liquid USDT-M perps; DEV 2025-11-01..2026-06-30, HOLDOUT 2026-07-01..
2026-10-31; 5 bp fee + 2 bp slippage per side; stops checked on High/Low first.
  A (live):   stop 2 x ATR, target 6 x ATR; break-even (+0.15 %) at 1.5 R; trail 1.5 R behind the best price after 2 R.
  B (Turtle): stop 2 x ATR (fixed); NO target; exit at the next bar open after a CLOSE beyond the opposite
              10-bar channel (long: close < lowest low of the previous 10 bars; short mirror).
Rationale: trend following earns from a few large winners; a fixed 3 R target caps them (Turtle rules,
Faith 2007; Clenow 2013). No parameter search: 20/10 channels and 2 ATR are the textbook values.
Pre-registered (committed before any run):
  ADOPT B if mean net R(B) > mean net R(A) on DEV AND on HOLDOUT (operator rule: better definition).
  EDGE if mean net R(B) >= +0.05 with n >= 100 on DEV and > 0 on HOLDOUT.
Usage: python research/v2/experiments/e26_trend_turtle_exit.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import e9_strategy_backtest as e9  # noqa: E402
from infrastructure.strategies.trend_donchian import donchian_trend_setup  # noqa: E402

FEE, SLIP = e9.FEE, e9.SLIP
DEV0 = int(e9.DEV_START.timestamp() * 1000)
HOLD0 = int(e9.HOLDOUT_START.timestamp() * 1000)
H = 3_600_000


def signals(k: pd.DataFrame):
    bars = [{"timestamp": int(t // 1000), "open": o, "high": h, "low": l, "close": c, "volume": v}
            for t, o, h, l, c, v in zip(k.t, k.o, k.h, k.l, k.c, k.v)]
    out = {}
    for i in range(400, len(bars)):
        if k.t.iloc[i] < DEV0 - H:
            continue
        s = donchian_trend_setup(bars[i - 399:i + 1], None, now_s=bars[i]["timestamp"] + 3600)
        if s is not None:
            out[i] = (1 if s.direction == "BUY" else -1, float(s.stop_loss_level), float(s.take_profit_level))
    return out


def simulate(k, sig, arm):
    t, o, h, l, c = (k[x].to_numpy() for x in ("t", "o", "h", "l", "c"))
    trades, pos, i = [], None, 0
    n = len(t)
    while i < n:
        if pos is not None:
            sgn = pos["sgn"]
            hit_sl = l[i] <= pos["sl"] if sgn > 0 else h[i] >= pos["sl"]
            hit_tp = arm == "A" and (h[i] >= pos["tp"] if sgn > 0 else l[i] <= pos["tp"])
            px = None
            if pos.get("exit_next"):
                px = o[i]
            elif hit_sl:
                gap = (o[i] < pos["sl"]) if sgn > 0 else (o[i] > pos["sl"])
                px = o[i] if gap else pos["sl"]
            elif hit_tp:
                px = pos["tp"]
            if px is not None:
                px = px * (1 - sgn * SLIP) if not hit_tp or pos.get("exit_next") or hit_sl else px
                ret = sgn * (px - pos["entry"]) / pos["entry"] - 2 * FEE
                trades.append({"t_in": pos["t_in"], "ret": ret, "R": ret * pos["entry"] / pos["risk"], "side": sgn})
                pos = None
            else:
                if arm == "A":
                    pos["peak"] = max(pos["peak"], h[i]) if sgn > 0 else min(pos["peak"], l[i])
                    mfe = sgn * (pos["peak"] - pos["entry"])
                    tgt = None
                    if mfe >= e9.BE_R * pos["risk"]:
                        tgt = pos["entry"] * (1 + sgn * e9.BE_BUF)
                    if mfe >= e9.TRAIL_AFTER_R * pos["risk"]:
                        tr = pos["peak"] - sgn * e9.TRAIL_R * pos["risk"]
                        tgt = tr if tgt is None or sgn * (tr - tgt) > 0 else tgt
                    if tgt is not None:
                        tgt = min(tgt, c[i] * 0.998) if sgn > 0 else max(tgt, c[i] * 1.002)
                        if sgn * (tgt - pos["sl"]) > 0:
                            pos["sl"] = tgt
                elif i >= 10:
                    if (sgn > 0 and c[i] < l[i - 10:i].min()) or (sgn < 0 and c[i] > h[i - 10:i].max()):
                        pos["exit_next"] = True
        if pos is None and (i - 1) in sig and i < n:
            sgn, sl, tp = sig[i - 1]
            entry = o[i] * (1 + sgn * SLIP)
            risk = abs(entry - sl)
            if risk > 0 and sgn * (entry - sl) > 0:
                pos = {"sgn": sgn, "entry": entry, "sl": sl, "tp": tp, "risk": risk, "peak": entry, "t_in": int(t[i])}
                i += 0
        i += 1
    return trades


def main():
    rows = []
    for sym in e9.SYMBOLS:
        k = e9.klines(sym, "1h").sort_values("t").reset_index(drop=True)
        sig = signals(k)
        for arm in ("A", "B"):
            for tr in simulate(k, sig, arm):
                rows.append({"arm": arm, "symbol": sym, **tr})
    d = pd.DataFrame(rows)
    d = d[d.t_in >= DEV0]
    d.to_csv(e9.OUT / "E26_trend_turtle_exit_trades.csv", index=False)
    out = []
    for (arm, win), g in d.assign(window=np.where(d.t_in >= HOLD0, "HOLDOUT", "DEV")).groupby(["arm", "window"]):
        out.append({"arm": arm, "window": win, "n": len(g), "mean_R": round(g.R.mean(), 3),
                    "mean_bp": round(g.ret.mean() * 1e4, 1), "win": round((g.ret > 0).mean(), 3),
                    "PF": round(g.ret[g.ret > 0].sum() / -g.ret[g.ret < 0].sum(), 2),
                    "max_R": round(g.R.max(), 1), "symbols_pos": f"{int((g.groupby('symbol').ret.sum() > 0).sum())}/10"})
    r = pd.DataFrame(out)
    r.to_csv(e9.OUT / "E26_trend_turtle_exit.csv", index=False)
    print(r.to_string(index=False))
    m = r.set_index(["arm", "window"]).mean_R
    adopt = m["B", "DEV"] > m["A", "DEV"] and m["B", "HOLDOUT"] > m["A", "HOLDOUT"]
    nb = r[(r.arm == "B") & (r.window == "DEV")].n.iloc[0]
    edge = nb >= 100 and m["B", "DEV"] >= 0.05 and m["B", "HOLDOUT"] > 0
    print("B:", "ADOPT" if adopt else "KEEP A", "|", "EDGE" if edge else "NO EDGE")


if __name__ == "__main__":
    main()
