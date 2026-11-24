"""Session-VWAP 2-sigma re-entry setup (E16-U10 / E21 "VR1", adopted live 2026-11-24).

Canonical definition (replaces the rolling-VWAP NGMR_REVERSION setup for VWAPReversal; E21: DEV -0.017 R
vs -0.124 R, HOLDOUT -0.062 R vs -0.123 R; still no proven edge — adopted as the correct definition with
smaller losses, operator decision 2026-11-24):
  * 15m CLOSED bars only; VWAP and volume-weighted sigma of the typical price (H+L+C)/3 anchored at 00:00 UTC.
  * BUY when the previous closed bar was below VWAP - 2 sigma and the last closed bar is back at/above it;
    SELL mirror at +2 sigma. Previous bar must belong to the same session.
  * Target = VWAP; stop = extreme of the last 3 closed bars -/+ 0.5 x ATR(14).
  * Cost filter: target distance >= 0.4 % of price and >= 1.0 x stop distance.
  * No entries in the first 2 hours of the session (VWAP not yet meaningful).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

SETUP_TYPE = "VWAP_SESSION_2SIGMA"
BAR_SECONDS = 900
SIGMA = 2.0
MIN_SESSION_HOURS = 2.0
MIN_TARGET_PCT = 0.004


def _open_s(bar: Dict[str, Any]) -> Optional[float]:
    ts = bar.get("timestamp")
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return (ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)).timestamp()
    if hasattr(ts, "timestamp") and not isinstance(ts, (int, float)):
        return float(ts.timestamp())
    ts = float(ts)
    return ts / 1000.0 if ts > 1e11 else ts


def closed_bars(bars: List[Dict[str, Any]], now_s: Optional[float] = None) -> List[Dict[str, Any]]:
    now_s = time.time() if now_s is None else now_s
    return [b for b in bars if (_open_s(b) is not None and _open_s(b) + BAR_SECONDS <= now_s)]


def session_vwap_setup(bars: List[Dict[str, Any]], symbol, now_s: Optional[float] = None):
    """CandidateSetup for the last CLOSED 15m bar, or None."""
    from domain.entities.research import CandidateSetup
    from domain.value_objects import ExchangeTimestamp

    b = closed_bars(bars, now_s)
    if len(b) < 20:
        return None
    t = np.array([_open_s(x) for x in b])
    h = np.array([float(x["high"]) for x in b])
    l = np.array([float(x["low"]) for x in b])
    c = np.array([float(x["close"]) for x in b])
    v = np.array([float(x.get("volume", 0.0) or 0.0) for x in b])
    day = (t // 86400).astype(int)
    sess = day == day[-1]
    if sess.sum() < 2:
        return None                                   # previous bar is from another session
    tp = (h + l + c) / 3.0

    def dev_at(k: int) -> Optional[tuple]:
        m = sess & (np.arange(len(b)) <= k)
        vol = v[m].sum()
        if vol <= 0:
            return None
        vwap = (tp[m] * v[m]).sum() / vol
        sd = float(np.sqrt(max((tp[m] ** 2 * v[m]).sum() / vol - vwap ** 2, 0.0)))
        return (vwap, sd, (c[k] - vwap) / sd if sd > 0 else None)

    last, prev = dev_at(len(b) - 1), dev_at(len(b) - 2)
    if last is None or prev is None or last[2] is None or prev[2] is None:
        return None
    hours = (t[-1] % 86400) / 3600.0 + BAR_SECONDS / 3600.0     # session hours elapsed at bar close
    if hours < MIN_SESSION_HOURS:
        return None
    vwap, _, dev = last
    pdev = prev[2]
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    atr = float(tr[-14:].mean())
    px = float(c[-1])
    side = sl = None
    if pdev < -SIGMA <= dev:
        cand = float(l[-3:].min()) - 0.5 * atr
        if vwap - px >= max(MIN_TARGET_PCT * px, px - cand):
            side, sl = "BUY", cand
    elif pdev > SIGMA >= dev:
        cand = float(h[-3:].max()) + 0.5 * atr
        if px - vwap >= max(MIN_TARGET_PCT * px, cand - px):
            side, sl = "SELL", cand
    if side is None:
        return None
    return CandidateSetup(
        symbol=symbol, timestamp=ExchangeTimestamp(int((t[-1] + BAR_SECONDS) * 1000)), setup_type=SETUP_TYPE,
        direction=side, trigger_price=Decimal(str(px)), stop_loss_level=Decimal(str(sl)),
        take_profit_level=Decimal(str(vwap)))
