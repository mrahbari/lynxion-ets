"""E34 — EMA-gap mean reversion (operator link: github.com/Xtley001/Mean-Reversion-Gap-Strategy-Trading-Bot) (2026-11-24).

The repo is an MT5 bot (M5/M15/M30, gold, FX, indices, BTCUSD, ETHUSD) with no backtest or results. Its rules,
ported as written (values from config.py; crypto RSI bands 75/25), on the E9 engine / universe / windows / costs
(10 liquid USDT-M perps; DEV 2025-11-01..2026-06-30; HOLDOUT 2026-07-01..10-31 read once; next-bar-open entry
— the repo's 2-pip limit is approximated by the open; SL before TP on High/Low; 5 bp fee + 2 bp slippage per
side; live SL/TP sanitiser; break-even 1.5 R and trail after 2 R in place of the repo's $50-step trail).
Pre-registered (committed before any run). 15m closed bars (middle of the repo's timeframes).
  gap = 0.6 % of EMA(360).
  LONG : ATR(10) < ATR(20), close < EMA360 - gap, close > EMA(20), RSI(20) falling, RSI(20) < 75.
  SHORT: ATR(10) < ATR(20), close > EMA360 + gap, close < EMA(20), RSI(20) rising,  RSI(20) > 25.
  Stop = 1.5 x ATR(10); target = 5 x the stop distance. ATR and RSI use simple rolling means (as in the repo).
  At most one signal per symbol every 5 bars (repo MIN_BARS_BETWEEN_TRADES).
  EDGE: mean net R >= +0.05 with n >= 100 on DEV and > 0 on HOLDOUT.
  Decision: EDGE -> candidate replacement for MeanReversion (shadow first). Otherwise record.
Usage: python research/v2/experiments/e34_ema_gap_reversion.py
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


def sma_atr(h, l, c, n):
    tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
    return float(tr[-n:].mean())


def rsi_simple(c, n=20):
    d = np.diff(c)
    up, dn = np.maximum(d, 0)[-n:].mean(), np.maximum(-d, 0)[-n:].mean()
    return 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)


class EmaGap(_Base):
    def __init__(self, _cfg=None):
        super().__init__()
        self.cool = 0

    def generate_signal(self, _s):
        self.cool = max(0, self.cool - 1)
        if len(self.buf) < 400 or self.cool:
            return None
        c, h, l = self._arr("close"), self._arr("high"), self._arr("low")
        s = pd.Series(c)
        e360, e20 = s.ewm(span=360, adjust=False).mean().iloc[-1], s.ewm(span=20, adjust=False).mean().iloc[-1]
        a10, a20 = sma_atr(h, l, c, 10), sma_atr(h, l, c, 20)
        r1, r0 = rsi_simple(c[:-1]), rsi_simple(c)
        gap, px = e360 * 0.006, c[-1]
        if a10 < a20 and px < e360 - gap and px > e20 and r1 > r0 and r0 < 75:
            sl = px - 1.5 * a10
            self.cool = 5
            return _sig("BUY", sl, px + 5 * (px - sl))
        if a10 < a20 and px > e360 + gap and px < e20 and r1 < r0 and r0 > 25:
            sl = px + 1.5 * a10
            self.cool = 5
            return _sig("SELL", sl, px - 5 * (sl - px))
        return None


def main():
    e9.STRATEGIES["EMA_GAP"] = ("e34_ema_gap_reversion", "EmaGap", "15m")
    tr = pd.DataFrame([t for s in e9.SYMBOLS for t in e9.run(("EMA_GAP", s))])
    tr.to_csv(e9.OUT / "E34_ema_gap_trades.csv", index=False)
    s = e9.summarize(tr)
    s.to_csv(e9.OUT / "E34_ema_gap_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(s[["strategy", "window", "trades", "win_rate", "PF", "mean_R", "mean_ret_bps", "first_half_R",
             "second_half_R", "symbols_positive", "long_share", "mean_R_long", "mean_R_short", "median_sl_pct"]].to_string(index=False))
    d, h = s[s.window == "dev"].iloc[0], s[s.window == "holdout"].iloc[0]
    print("EMA_GAP", "EDGE" if (d.trades >= 100 and d.mean_R >= 0.05 and h.mean_R > 0) else "NO EDGE")


if __name__ == "__main__":
    main()
