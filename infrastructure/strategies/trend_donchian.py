"""Donchian-20 breakout with EMA(50/200) trend filter (E16-U10 / E21 "TF1", adopted live 2026-11-24).

Canonical trend-following (Donchian / turtle breakout with a moving-average regime filter) replacing the
NGTREND_FOLLOW setup (price beyond the value area + fixed 0.2 % SMA gap; defect S-4). E21 on the E9
universe: DEV -0.027 R (old -0.028), HOLDOUT -0.010 R (old -0.055), 33 % fewer trades. No proven edge;
adopted as the correct definition with smaller holdout losses (operator decision 2026-11-24).
  * 1h CLOSED bars, the last 400 (EMA initialisation identical to the research replay).
  * BUY: close > highest high of the previous 20 bars AND EMA50 > EMA200; SELL mirror.
  * Stop 2 x ATR(14); target 6 x ATR (3 R; break-even / trailing by the position manager).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from infrastructure.strategies.vwap_session import _open_s

SETUP_TYPE = "DONCHIAN20_EMA_TREND"
BAR_SECONDS = 3600
WINDOW = 400
MIN_BARS = 210
HISTORY_PERIOD = "18d"            # >= 400 closed 1h bars


def closed_bars(bars: List[Dict[str, Any]], now_s: Optional[float] = None) -> List[Dict[str, Any]]:
    import time
    now_s = time.time() if now_s is None else now_s
    return [b for b in bars if _open_s(b) is not None and _open_s(b) + BAR_SECONDS <= now_s]


def donchian_trend_setup(bars: List[Dict[str, Any]], symbol, now_s: Optional[float] = None):
    from domain.entities.research import CandidateSetup
    from domain.value_objects import ExchangeTimestamp

    b = closed_bars(bars, now_s)[-WINDOW:]
    if len(b) < MIN_BARS:
        return None
    c = np.array([float(x["close"]) for x in b])
    h = np.array([float(x["high"]) for x in b])
    l = np.array([float(x["low"]) for x in b])
    s = pd.Series(c)
    e50 = s.ewm(span=50, adjust=False).mean().iloc[-1]
    e200 = s.ewm(span=200, adjust=False).mean().iloc[-1]
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    atr = float(tr[-14:].mean())
    px = float(c[-1])
    if px > h[-21:-1].max() and e50 > e200:
        side, sl, tp = "BUY", px - 2 * atr, px + 6 * atr
    elif px < l[-21:-1].min() and e50 < e200:
        side, sl, tp = "SELL", px + 2 * atr, px - 6 * atr
    else:
        return None
    return CandidateSetup(symbol=symbol, timestamp=ExchangeTimestamp(int((_open_s(b[-1]) + BAR_SECONDS) * 1000)),
                          setup_type=SETUP_TYPE, direction=side, trigger_price=Decimal(str(px)),
                          stop_loss_level=Decimal(str(sl)), take_profit_level=Decimal(str(tp)))
