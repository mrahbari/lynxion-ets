"""E21 — canonical, cost-aware rebuild of the two LIVE setups (roadmap E16-U10).

Baseline (E9, same engine, net of costs): trend_following DEV -0.028 R / HOLDOUT -0.055 R (1h);
vwap_reversal DEV -0.124 R / HOLDOUT -0.123 R (5m, ~1,000 trades/month). Both lose after costs.

Pre-registered (2026-11-24, committed before any run). Same E9 engine and universe (10 liquid
USDT-M perps, DEV 2025-11-01..2026-06-30, HOLDOUT 2026-07-01..10-31, next-bar-open entry, SL first on
High/Low, 5 bp fee/side, 2 bp slippage, BE at 1.5 R, trail after 2 R). Signals use CLOSED bars only.
  TF1 trend_canonical (1h): Donchian breakout — close > highest high of the previous 20 bars and
      EMA(50) > EMA(200) -> BUY (mirror SELL). Stop 2 x ATR(14), target 6 x ATR (3 R) with BE/trail.
  TF2 trend_canonical_4h (4h bars resampled from 1h): same rule on 4h (fewer, larger moves = lower
      cost per R).
  VR1 vwap_canonical (15m): UTC-session VWAP with volume-weighted sigma; BUY when the previous close
      was below VWAP - 2 sigma and this close is back above it (re-entry), SELL mirror at +2 sigma.
      Target VWAP; stop = extreme of the last 3 bars -/+ 0.5 ATR(14). Cost filter: target distance
      >= 0.4 % of price and >= 1.0 x stop distance; no entries in the first 2 hours of the session.
PASS (per design): mean net R >= +0.05 with n >= 100 on DEV AND mean net R > 0 on HOLDOUT.
Decision: a passing design replaces the live setup of its strategy (TF* -> TrendFollow, VR1 ->
VWAPReversal); if both TF designs pass, the larger DEV R. A family with no passing design: the live
strategy is retired from the allowlist only if its baseline is also negative on HOLDOUT (it is, for
both) -> recorded, not silently kept.

Usage: python research/v2/experiments/e21_canonical_setups.py
"""
from __future__ import annotations

import sys
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402


def _sig(side, sl, tp):
    return SimpleNamespace(signal_type=SimpleNamespace(name=side),
                           metadata={"setup": SimpleNamespace(stop_loss_level=Decimal(str(sl)),
                                                              take_profit_level=Decimal(str(tp)))})


class _Base:
    def __init__(self, _cfg=None):
        self.buf = deque(maxlen=400)

    def update_with_market_data(self, bar):
        self.buf.append(bar)

    def _arr(self, k):
        return np.array([b[k] for b in self.buf], dtype=float)

    @staticmethod
    def _atr(h, l, c, n=14):
        tr = np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))
        return float(tr[-n:].mean())


class TrendCanonical(_Base):
    HOURS = 1

    def __init__(self, _cfg=None):
        super().__init__()
        self.agg, self.acc = deque(maxlen=400), None

    def update_with_market_data(self, bar):
        if self.HOURS == 1:
            self.agg.append(bar)
            self._new = True
            return
        ts = bar["timestamp"]
        start = ts.hour % self.HOURS == 0
        if start or self.acc is None:
            self.acc = dict(bar, n=1)
        else:
            self.acc.update(high=max(self.acc["high"], bar["high"]), low=min(self.acc["low"], bar["low"]),
                            close=bar["close"], n=self.acc["n"] + 1)
        self._new = self.acc["n"] == self.HOURS
        if self._new:
            self.agg.append(dict(self.acc))

    def generate_signal(self, _s):
        if not getattr(self, "_new", False) or len(self.agg) < 210:
            return None
        self._new = False
        c = np.array([b["close"] for b in self.agg]); h = np.array([b["high"] for b in self.agg])
        l = np.array([b["low"] for b in self.agg])
        s = pd.Series(c)
        e50, e200 = s.ewm(span=50, adjust=False).mean().iloc[-1], s.ewm(span=200, adjust=False).mean().iloc[-1]
        atr = self._atr(h, l, c)
        if c[-1] > h[-21:-1].max() and e50 > e200:
            return _sig("BUY", c[-1] - 2 * atr, c[-1] + 6 * atr)
        if c[-1] < l[-21:-1].min() and e50 < e200:
            return _sig("SELL", c[-1] + 2 * atr, c[-1] - 6 * atr)
        return None


class Trend4h(TrendCanonical):
    HOURS = 4


class VWAPCanonical(_Base):
    def __init__(self, _cfg=None):
        super().__init__()
        self.day, self.pv, self.v, self.pv2, self.prev_dev = None, 0.0, 0.0, 0.0, None

    def update_with_market_data(self, bar):
        super().update_with_market_data(bar)
        ts = bar["timestamp"]
        if ts.date() != self.day:
            self.day, self.pv, self.v, self.pv2, self.prev_dev = ts.date(), 0.0, 0.0, 0.0, None
        tp = (bar["high"] + bar["low"] + bar["close"]) / 3
        self.pv += tp * bar["volume"]; self.v += bar["volume"]; self.pv2 += tp * tp * bar["volume"]
        self.hour = ts.hour + ts.minute / 60 + 0.25          # session hours elapsed at bar close

    def generate_signal(self, _s):
        if self.v <= 0 or len(self.buf) < 20:
            return None
        vwap = self.pv / self.v
        sd = np.sqrt(max(self.pv2 / self.v - vwap * vwap, 0.0))
        c, h, l = self._arr("close"), self._arr("high"), self._arr("low")
        dev = (c[-1] - vwap) / sd if sd > 0 else 0.0
        prev, self.prev_dev = self.prev_dev, dev
        if prev is None or self.hour < 2 or sd <= 0:
            return None
        atr, px = self._atr(h, l, c), c[-1]
        if prev < -2 and dev >= -2:
            sl = l[-3:].min() - 0.5 * atr
            if vwap - px >= max(0.004 * px, px - sl):
                return _sig("BUY", sl, vwap)
        if prev > 2 and dev <= 2:
            sl = h[-3:].max() + 0.5 * atr
            if px - vwap >= max(0.004 * px, sl - px):
                return _sig("SELL", sl, vwap)
        return None


DESIGNS = {"TF1_trend_canonical": ("TrendCanonical", "1h"), "TF2_trend_canonical_4h": ("Trend4h", "1h"),
           "VR1_vwap_canonical": ("VWAPCanonical", "15m")}


def main() -> None:
    for name, (cls, tf) in DESIGNS.items():
        e9.STRATEGIES[name] = ("e21_canonical_setups", cls, tf)
    trades = []
    for name in DESIGNS:
        for sym in e9.SYMBOLS:
            trades += e9.run((name, sym))
    tr = pd.DataFrame(trades)
    tr.to_csv(e9.OUT / "E21_canonical_setups_trades.csv", index=False)
    s = e9.summarize(tr)
    s.to_csv(e9.OUT / "E21_canonical_setups_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(s[["strategy", "window", "trades", "trades_per_month", "win_rate", "PF", "mean_R", "mean_ret_bps",
             "first_half_R", "second_half_R", "symbols_positive", "median_sl_pct"]].to_string(index=False))
    for name in DESIGNS:
        d = s[(s.strategy == name) & (s.window == "dev")]
        hd = s[(s.strategy == name) & (s.window == "holdout")]
        ok = (len(d) and d.trades.iloc[0] >= 100 and d.mean_R.iloc[0] >= 0.05 and len(hd) and hd.mean_R.iloc[0] > 0)
        print(name, "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
