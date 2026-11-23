"""E10 — volatility_breakout redesign, pre-registered variants (fixed before any result was seen).

Why: E9 volatility_breakout (15m, close > 20-bar high + 1.5 ATR, SL at the opposite 20-bar extreme -> clamped
to 3%, TP fixed 2%) had TP < SL (reward/risk 0.67) and chased extended moves. DEV PF 1.01.

Variants (all: one position per symbol, next-bar-open entry +2 bp, sanitize_sltp_levels exactly as live,
SL before TP on the same bar, live R-mode stop management, 0.05% fee per side, 2 bp slippage on stops):
  A squeeze_1h      1h bars. Compression on the PRIOR bar: ATR14/ATR100 < 0.75. Breakout: close > highest high of
                    the previous 20 bars (BUY) / close < lowest low (SELL). Trend filter: last CLOSED 4h close vs
                    its EMA50 (long only above, short only below). SL 2xATR14, TP 4xATR14.
  B donchian_1h     A without the compression condition.
  C donchian_4h     4h bars (resampled from closed 1h bars), Donchian 20 breakout, filter close vs EMA50 (4h),
                    SL 2xATR14, TP 4xATR14.
  D squeeze_15m     15m bars, compression as A, Donchian 20 breakout, filter = last closed 1h close vs EMA50 (1h),
                    SL 2xATR14, TP 4xATR14.
Selection on DEV (2025-11-01..2026-06-30) with the S2 rule: trades >= 100, PF >= 1.2, mean R >= +0.05, both
halves > 0, >= 6/10 symbols positive. If several pass: highest mean R. HOLDOUT (2026-07-01..2026-10-31) is
evaluated only for the selected variant, once (`--holdout NAME`): mean R > 0 and PF >= 1.1.
Disclosure: the ORIGINAL volatility_breakout holdout row was visible in the E9 summary CSV before this design.

Usage: python research/v2/experiments/e10_vol_breakout_redesign.py            # DEV, all variants
       python research/v2/experiments/e10_vol_breakout_redesign.py --holdout B # holdout, one variant
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402

from shared.utils import sanitize_sltp_levels  # noqa: E402

OUT = e9.OUT
FEE, SLIP = e9.FEE, e9.SLIP
DEV0 = int(e9.DEV_START.timestamp() * 1000)
HOLD0 = int(e9.HOLDOUT_START.timestamp() * 1000)
VARIANTS = {
    "A": dict(name="squeeze_1h", tf="1h", squeeze=True, filt="4h"),
    "B": dict(name="donchian_1h", tf="1h", squeeze=False, filt="4h"),
    "C": dict(name="donchian_4h", tf="4h", squeeze=False, filt="same"),
    "D": dict(name="squeeze_15m", tf="15m", squeeze=True, filt="1h"),
}
MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000}


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Closed higher-TF bars from 1h bars (only complete buckets)."""
    g = df.assign(b=df.t // MS[tf] * MS[tf]).groupby("b")
    out = pd.DataFrame({"t": g.t.first().index, "o": g.o.first().values, "h": g.h.max().values,
                        "l": g.l.min().values, "c": g.c.last().values, "v": g.v.sum().values,
                        "n": g.size().values})
    return out[out.n == MS[tf] // MS["1h"]].drop(columns="n").reset_index(drop=True)


def atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df.c.shift(1)
    tr = pd.concat([df.h - df.l, (df.h - pc).abs(), (df.l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def signals(sym: str, v: dict) -> pd.DataFrame:
    base = e9.klines(sym, "1h")
    df = resample(base, "4h") if v["tf"] == "4h" else e9.klines(sym, v["tf"])
    df = df.copy()
    df["atr"] = atr(df, 14)
    hh = df.h.shift(1).rolling(20).max()
    ll = df.l.shift(1).rolling(20).min()
    sig = np.where(df.c > hh, 1, np.where(df.c < ll, -1, 0))
    if v["squeeze"]:
        ratio = (df.atr / atr(df, 100)).shift(1)          # compression measured BEFORE the breakout bar
        sig = np.where(ratio < 0.75, sig, 0)
    # trend filter from the last CLOSED filter-TF bar at this bar's close
    ftf = v["tf"] if v["filt"] == "same" else v["filt"]
    f = df if ftf == v["tf"] else (resample(base, ftf) if ftf == "4h" else e9.klines(sym, ftf))
    f = pd.DataFrame({"close_t": f.t + MS[ftf], "fup": (f.c > f.c.ewm(span=50, adjust=False).mean()).astype(int)})
    m = pd.merge_asof(pd.DataFrame({"close_t": df.t + MS[v["tf"]]}), f, on="close_t", direction="backward")
    up = m.fup.values
    ok = ~np.isnan(up)
    sig = np.where(ok & (((sig == 1) & (up == 1)) | ((sig == -1) & (up == 0))), sig, 0)
    df["sig"] = sig
    return df


def simulate(sym: str, key: str) -> list:
    v = VARIANTS[key]
    df = signals(sym, v)
    o, h, l, c, t, a, sg = (df[k].values for k in ("o", "h", "l", "c", "t", "atr", "sig"))
    trades, pos, pending = [], None, None
    for i in range(len(df)):
        if pending is not None and pos is None:
            sgn = pending["sgn"]
            side = "BUY" if sgn > 0 else "SELL"
            entry = o[i] * (1 + sgn * SLIP)
            sl, tp = sanitize_sltp_levels(entry_price=entry, side=side, stop_loss=entry - sgn * 2 * pending["atr"],
                                          take_profit=entry + sgn * 4 * pending["atr"])
            if sl > 0 and tp > 0:
                pos = {"side": side, "sgn": sgn, "entry": entry, "sl": sl, "tp": tp, "risk": abs(entry - sl),
                       "peak": entry, "t_in": int(t[i]), "be": False}
            pending = None
        if pos is not None:
            sgn = pos["sgn"]
            hit_sl = (l[i] <= pos["sl"]) if sgn > 0 else (h[i] >= pos["sl"])
            hit_tp = (h[i] >= pos["tp"]) if sgn > 0 else (l[i] <= pos["tp"])
            exit_px = why = None
            if hit_sl:
                gap = (o[i] < pos["sl"]) if sgn > 0 else (o[i] > pos["sl"])
                exit_px = (o[i] if gap else pos["sl"]) * (1 - sgn * SLIP)
                why = "BE/TRAIL" if pos["be"] else "SL"
            elif hit_tp:
                exit_px, why = pos["tp"], "TP"
            if exit_px is not None:
                net = sgn * (exit_px - pos["entry"]) / pos["entry"] - 2 * FEE
                trades.append({"variant": key, "symbol": sym, "side": pos["side"], "t_in": pos["t_in"],
                               "t_out": int(t[i]), "ret": net, "R": net * pos["entry"] / pos["risk"], "exit": why,
                               "sl_pct": pos["risk"] / pos["entry"]})
                pos = None
            else:
                pos["peak"] = max(pos["peak"], h[i]) if sgn > 0 else min(pos["peak"], l[i])
                mfe = sgn * (pos["peak"] - pos["entry"])
                target = None
                if mfe >= e9.BE_R * pos["risk"]:
                    target = pos["entry"] * (1 + sgn * e9.BE_BUF)
                if mfe >= e9.TRAIL_AFTER_R * pos["risk"]:
                    trail = pos["peak"] - sgn * e9.TRAIL_R * pos["risk"]
                    target = trail if target is None or sgn * (trail - target) > 0 else target
                if target is not None:
                    target = min(target, c[i] * 0.998) if sgn > 0 else max(target, c[i] * 1.002)
                    if sgn * (target - pos["sl"]) > 0:
                        pos["sl"], pos["be"] = target, True
        if pos is None and pending is None and sg[i] != 0 and t[i] >= DEV0 - 1 and np.isfinite(a[i]):
            pending = {"sgn": float(sg[i]), "atr": float(a[i])}
    return trades


def summarize(tr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, g in tr.groupby("variant"):
        g = g.sort_values("t_in")
        wins, losses = g.ret[g.ret > 0].sum(), -g.ret[g.ret < 0].sum()
        half = len(g) // 2
        months = (g.t_in.max() - g.t_in.min()) / 2.6e9
        rows.append({"variant": key, "name": VARIANTS[key]["name"], "trades": len(g),
                     "trades_per_month": round(len(g) / max(months, 1), 1), "win_rate": round((g.ret > 0).mean(), 3),
                     "PF": round(wins / losses, 2) if losses else np.inf, "mean_R": round(g.R.mean(), 3),
                     "mean_ret_bps": round(g.ret.mean() * 1e4, 1),
                     "gross_bps": round((g.ret.mean() + 2 * FEE) * 1e4, 1),
                     "first_half_R": round(g.R.iloc[:half].mean(), 3), "second_half_R": round(g.R.iloc[half:].mean(), 3),
                     "symbols_positive": int((g.groupby("symbol").ret.sum() > 0).sum()),
                     "long_share": round((g.side == "BUY").mean(), 2),
                     "mean_R_long": round(g[g.side == "BUY"].R.mean(), 3),
                     "mean_R_short": round(g[g.side == "SELL"].R.mean(), 3),
                     "median_sl_pct": round(g.sl_pct.median() * 100, 2),
                     "exits": g.exit.value_counts().to_dict()})
    s = pd.DataFrame(rows)
    s["dev_rule_pass"] = ((s.trades >= 100) & (s.PF >= 1.2) & (s.mean_R >= 0.05) & (s.first_half_R > 0)
                          & (s.second_half_R > 0) & (s.symbols_positive >= 6))
    return s


def _job(args):
    return simulate(*args)


def main() -> None:
    from concurrent.futures import ProcessPoolExecutor
    holdout = sys.argv[sys.argv.index("--holdout") + 1] if "--holdout" in sys.argv else None
    keys = [holdout] if holdout else list(VARIANTS)
    for s in e9.SYMBOLS:
        for tf in ("15m", "1h"):
            e9.klines(s, tf)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(_job, [(s, k) for k in keys for s in e9.SYMBOLS]))
    tr = pd.DataFrame([x for r in res for x in r])
    tr = tr[(tr.t_in >= HOLD0)] if holdout else tr[(tr.t_in >= DEV0) & (tr.t_in < HOLD0)]
    tag = f"holdout_{holdout}" if holdout else "dev"
    tr.to_csv(OUT / f"E10_vol_breakout_{tag}_trades.csv", index=False)
    s = summarize(tr)
    if holdout:
        s["holdout_rule_pass"] = (s.mean_R > 0) & (s.PF >= 1.1)
    s.to_csv(OUT / f"E10_vol_breakout_{tag}_summary.csv", index=False)
    pd.set_option("display.width", 300)
    print(s.drop(columns="exits").to_string(index=False))
    print(s[["variant", "exits"]].to_string(index=False))


if __name__ == "__main__":
    main()
