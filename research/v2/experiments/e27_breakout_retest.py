"""E27 — Breakout-Retest (operator idea, 2026-11-24): do not buy the break, buy the confirmed retest.

Why: raw breakouts lose in every test here (E9 breakout -0.137 / -0.124 R, E25 TTM, Codex C-35): entering at
the break buys the worst price with the highest fakeout risk. The operator's chart method (Lynxion MTF
Confluence: HTF alignment, wait for the zone, "touch alone is not entry", rejection + close confirmation,
room to the next obstacle) applied to breakouts = wait for the broken level to be retested and held.

Pre-registered (2026-11-24, committed before any run). One variant, textbook values, no search.
Engine / universe / windows / costs = E9 (10 liquid perps; DEV 2025-11-01..2026-06-30; HOLDOUT
2026-07-01..10-31 read once; next-bar-open entry; SL before TP on High/Low; 5 bp fee + 2 bp slippage per side;
break-even at 1.5 R, trail after 2 R). 1h closed bars.
  HTF trend: 4h bars built from closed 1h bars; EMA21 vs EMA55 of 4h closes (the indicator's EMA pair).
  Breakout: close > highest high of the previous 20 bars with HTF up -> pending LONG at level L = that high
            (SHORT mirror with HTF down, L = lowest low). A newer breakout replaces the pending one.
  Invalidation: a close beyond L by more than 0.3 ATR(14) on the wrong side, or 10 bars without a retest.
  Retest entry (bar after the breakout bar, within 10 bars): low <= L + 0.3 ATR (touch of the level zone)
            AND close > L (level held) AND close > open (rejection candle) -> LONG at the next open.
  Stop = min(retest low, L) - 0.25 ATR; target = entry + 2 R. SHORT mirror.
  Baseline = current Breakout definition (E9: -0.137 / -0.124 R).
  EDGE: mean net R >= +0.05 with n >= 100 on DEV and > 0 on HOLDOUT.
  ADOPT: better than the baseline on DEV and on HOLDOUT -> becomes the Breakout setup (labelled "no proven
  edge" unless EDGE).
Usage: python research/v2/experiments/e27_breakout_retest.py
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

BASE = (-0.137, -0.124)


class BreakoutRetest(_Base):
    def __init__(self, _cfg=None):
        super().__init__()
        self.h4, self.acc, self.pending = [], None, None

    def update_with_market_data(self, bar):
        super().update_with_market_data(bar)
        ts = bar["timestamp"]
        if ts.hour % 4 == 0 or self.acc is None:
            self.acc = {"close": bar["close"], "n": 1}
        else:
            self.acc = {"close": bar["close"], "n": self.acc["n"] + 1}
        if ts.hour % 4 == 3 and self.acc["n"] == 4:        # 4h bar closed
            self.h4.append(self.acc["close"])
            self.h4 = self.h4[-300:]

    def _htf(self):
        if len(self.h4) < 60:
            return 0
        s = pd.Series(self.h4)
        e21, e55 = s.ewm(span=21, adjust=False).mean().iloc[-1], s.ewm(span=55, adjust=False).mean().iloc[-1]
        return 1 if e21 > e55 else -1 if e21 < e55 else 0

    def generate_signal(self, _s):
        if len(self.buf) < 30:
            return None
        o, h, l, c = self._arr("open"), self._arr("high"), self._arr("low"), self._arr("close")
        atr = self._atr(h, l, c)
        i = len(c) - 1
        # 1) manage the pending breakout (retest / invalidation) on this closed bar
        if self.pending is not None:
            p = self.pending
            p["age"] += 1
            L, sgn = p["L"], p["sgn"]
            if p["age"] > 10 or sgn * (c[i] - L) < -0.3 * atr:
                self.pending = None
            else:
                touched = (l[i] <= L + 0.3 * atr) if sgn > 0 else (h[i] >= L - 0.3 * atr)
                held = (c[i] > L) if sgn > 0 else (c[i] < L)
                reject = (c[i] > o[i]) if sgn > 0 else (c[i] < o[i])
                if touched and held and reject:
                    self.pending = None
                    px = c[i]
                    if sgn > 0:
                        sl = min(l[i], L) - 0.25 * atr
                        return _sig("BUY", sl, px + 2 * (px - sl))
                    sl = max(h[i], L) + 0.25 * atr
                    return _sig("SELL", sl, px - 2 * (sl - px))
        # 2) new breakout on this closed bar (replaces any pending one)
        trend = self._htf()
        hi20, lo20 = h[i - 20:i].max(), l[i - 20:i].min()
        if trend > 0 and c[i] > hi20:
            self.pending = {"sgn": 1, "L": hi20, "age": 0}
        elif trend < 0 and c[i] < lo20:
            self.pending = {"sgn": -1, "L": lo20, "age": 0}
        return None


def main():
    e9.STRATEGIES["BRK_RETEST"] = ("e27_breakout_retest", "BreakoutRetest", "1h")
    tr = pd.DataFrame([t for s in e9.SYMBOLS for t in e9.run(("BRK_RETEST", s))])
    tr.to_csv(e9.OUT / "E27_breakout_retest_trades.csv", index=False)
    s = e9.summarize(tr)
    s.to_csv(e9.OUT / "E27_breakout_retest_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(s[["strategy", "window", "trades", "trades_per_month", "win_rate", "PF", "mean_R", "mean_ret_bps",
             "first_half_R", "second_half_R", "symbols_positive", "long_share", "mean_R_long", "mean_R_short",
             "median_sl_pct"]].to_string(index=False))
    d = s[s.window == "dev"].iloc[0]
    h = s[s.window == "holdout"].iloc[0]
    edge = d.trades >= 100 and d.mean_R >= 0.05 and h.mean_R > 0
    adopt = d.mean_R > BASE[0] and h.mean_R > BASE[1]
    print("BRK_RETEST", "EDGE" if edge else "NO EDGE", "|", "ADOPT" if adopt else "KEEP CURRENT")


if __name__ == "__main__":
    main()
