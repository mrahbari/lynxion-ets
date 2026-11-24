"""E25 — canonical rebuild of the three remaining non-standard setups (Strategy layer, 2026-11-24).

Same E9 engine / universe / costs as E21 (10 liquid USDT-M perps; DEV 2025-11..2026-06, HOLDOUT 2026-07..10;
next-bar-open entry; SL before TP on High/Low; 5 bp fee + 2 bp slippage per side; BE at 1.5 R, trail after 2 R).
Closed bars only. ONE textbook variant per strategy, values from the canonical references, no search.

Pre-registered (2026-11-24, committed before any run):
  MR1 MeanReversion (1h) — Connors RSI(2): LONG if close > SMA200 and RSI(2) < 10; SHORT if close < SMA200 and
      RSI(2) > 90. Target = SMA(5) at the signal bar (must be >= 0.5 ATR away in the trade direction, else
      skip); stop 2.5 x ATR(14).
  BO1 Breakout (15m) — TTM squeeze release: squeeze = Bollinger(20, 2) inside Keltner(20, EMA20 +/- 1.5 ATR);
      fire on the first bar after >= 6 squeeze bars where the squeeze is off; LONG if close > EMA20 and
      momentum (close - midpoint of 20-bar high/low and EMA20) > 0, SHORT mirror. Stop 1.5 x ATR, target 3 x ATR.
  LQ1 Liquidity (15m) — swing-pivot sweep + structure shift: confirmed pivot low (2 bars each side) within the
      last 50 bars; this bar trades below it and closes back above it AND above the previous bar's high
      -> LONG; mirror for SHORT at a pivot high. Stop = sweep extreme -/+ 0.25 ATR; target 2 R.
Baselines (E9, live definitions): mean_reversion -0.087 / -0.014 R, breakout -0.137 / -0.124 R,
liquidity -0.092 / -0.120 R (DEV / HOLDOUT).
PASS (edge): mean net R >= +0.05 with n >= 100 on DEV and > 0 on HOLDOUT.
ADOPT (correct definition, operator rule of 2026-11-24): net R better than its baseline on DEV AND on
HOLDOUT -> replaces the live definition (labelled "no proven edge" unless PASS). Otherwise keep the current one.
Usage: python research/v2/experiments/e25_canonical_rest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402
from e21_canonical_setups import _Base, _sig  # noqa: E402

BASE = {"MR1": (-0.087, -0.014), "BO1": (-0.137, -0.124), "LQ1": (-0.092, -0.120)}


def _atr(h, l, c, n=14):
    tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    return float(tr[-n:].mean())


def rsi2(c):
    d = np.diff(c[-3:])
    up = pd.Series(np.maximum(np.diff(c), 0)).ewm(alpha=1 / 2, adjust=False).mean().iloc[-1]
    dn = pd.Series(np.maximum(-np.diff(c), 0)).ewm(alpha=1 / 2, adjust=False).mean().iloc[-1]
    return 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)


class MR1(_Base):
    def generate_signal(self, _s):
        if len(self.buf) < 210:
            return None
        c, h, l = self._arr("close"), self._arr("high"), self._arr("low")
        sma200, sma5, atr, px = c[-200:].mean(), c[-5:].mean(), _atr(h, l, c), c[-1]
        r = rsi2(c[-60:])
        if px > sma200 and r < 10 and sma5 - px >= 0.5 * atr:
            return _sig("BUY", px - 2.5 * atr, sma5)
        if px < sma200 and r > 90 and px - sma5 >= 0.5 * atr:
            return _sig("SELL", px + 2.5 * atr, sma5)
        return None


class BO1(_Base):
    def __init__(self, _cfg=None):
        super().__init__()
        self.sq = []

    def generate_signal(self, _s):
        if len(self.buf) < 40:
            return None
        c, h, l = self._arr("close"), self._arr("high"), self._arr("low")
        s = pd.Series(c)
        ema = s.ewm(span=20, adjust=False).mean().iloc[-1]
        sd = c[-20:].std(ddof=0)
        atr = _atr(h, l, c, 20)
        sma = c[-20:].mean()
        squeeze = (sma + 2 * sd < ema + 1.5 * atr) and (sma - 2 * sd > ema - 1.5 * atr)
        self.sq.append(squeeze)
        self.sq = self.sq[-50:]
        if squeeze or len(self.sq) < 8 or not all(self.sq[-7:-1]):
            return None
        mom = c[-1] - ((h[-20:].max() + l[-20:].min()) / 2 + ema) / 2
        a14, px = _atr(h, l, c), c[-1]
        if px > ema and mom > 0:
            return _sig("BUY", px - 1.5 * a14, px + 3 * a14)
        if px < ema and mom < 0:
            return _sig("SELL", px + 1.5 * a14, px - 3 * a14)
        return None


class LQ1(_Base):
    def generate_signal(self, _s):
        if len(self.buf) < 60:
            return None
        c, h, l = self._arr("close"), self._arr("high"), self._arr("low")
        atr, n = _atr(h, l, c), len(c)
        piv_lo = [l[i] for i in range(n - 52, n - 3) if l[i] == min(l[i - 2:i + 3])]
        piv_hi = [h[i] for i in range(n - 52, n - 3) if h[i] == max(h[i - 2:i + 3])]
        px = c[-1]
        lo = [p for p in piv_lo if l[-1] < p < px]
        if lo and px > h[-2]:
            sl = l[-1] - 0.25 * atr
            return _sig("BUY", sl, px + 2 * (px - sl))
        hi = [p for p in piv_hi if h[-1] > p > px]
        if hi and px < l[-2]:
            sl = h[-1] + 0.25 * atr
            return _sig("SELL", sl, px - 2 * (sl - px))
        return None


DESIGNS = {"MR1": ("MR1", "1h"), "BO1": ("BO1", "15m"), "LQ1": ("LQ1", "15m")}


def main():
    for name, (cls, tf) in DESIGNS.items():
        e9.STRATEGIES[name] = ("e25_canonical_rest", cls, tf)
    tr = pd.DataFrame([t for name in DESIGNS for s in e9.SYMBOLS for t in e9.run((name, s))])
    tr.to_csv(e9.OUT / "E25_canonical_rest_trades.csv", index=False)
    s = e9.summarize(tr)
    s.to_csv(e9.OUT / "E25_canonical_rest_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(s[["strategy", "window", "trades", "trades_per_month", "win_rate", "PF", "mean_R", "mean_ret_bps",
             "first_half_R", "second_half_R", "symbols_positive", "median_sl_pct"]].to_string(index=False))
    for name in DESIGNS:
        d = s[(s.strategy == name) & (s.window == "dev")].iloc[0]
        h = s[(s.strategy == name) & (s.window == "holdout")].iloc[0]
        edge = d.trades >= 100 and d.mean_R >= 0.05 and h.mean_R > 0
        adopt = d.mean_R > BASE[name][0] and h.mean_R > BASE[name][1]
        print(name, "PASS" if edge else "FAIL", "| ADOPT" if adopt else "| KEEP CURRENT")


if __name__ == "__main__":
    main()
