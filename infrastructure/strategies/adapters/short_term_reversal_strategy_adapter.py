"""Short-Term Statistical Reversal (STR) — RETIRED-slot replacement candidate C1.

Hypothesis: at short horizons in NON-trending (ranging) regimes, crypto returns mean-revert —
an over-extended 1-bar move (large return z-score vs its recent distribution) tends to partially
reverse. The strategy FADES extreme short-term moves while the market is ranging.

Distinct from mean_reversion (structural range bounds + RSI + failed-expansion) and vwap_reversal
(session-anchored VWAP band): STR is a pure statistical return-reversal with no levels/VWAP.

A-priori parameters (NO tuning / NO search): z-window 20 bars, entry band 2.0σ, ranging gate via a
flat sma20-vs-sma50 separation. Design timeframe 15m. Auditable: the signal is a single z-score test.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

import numpy as np

from domain.entities import Signal, SignalType
from domain.value_objects import Percentage
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class ShortTermReversalStrategyAdapter(BaseStrategyAdapter):
    """Fade extreme short-term return moves in a ranging regime (statistical reversal)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("ShortTermStatisticalReversal")
        c = config or {}
        # a-priori standard values; not tuned
        self.z_window = c.get("z_window", 20)
        self.entry_z = c.get("entry_z", 2.0)
        self.trend_gate = c.get("trend_gate", 0.004)   # |sma20-sma50|/price below this => ranging
        self.min_bars = self.z_window + 55

    def generate_signal(self, symbol):
        buf = getattr(self, "data_buffer", None)
        if not buf or len(buf) < self.min_bars:
            return None
        closes = np.array([b["close"] for b in buf], dtype=float)
        rets = np.diff(closes) / closes[:-1]
        window = rets[-self.z_window:]
        mu, sd = float(window.mean()), float(window.std())
        if sd <= 0:
            return None
        z = (rets[-1] - mu) / sd

        # ranging gate: small separation of sma20 vs sma50 => not strongly trending
        sma20 = float(closes[-20:].mean())
        sma50 = float(closes[-50:].mean())
        price = float(closes[-1])
        ranging = price > 0 and abs(sma20 - sma50) / price < self.trend_gate

        sig_type = SignalType.HOLD
        if ranging:
            if z >= self.entry_z:
                sig_type = SignalType.SELL          # fade the up-extension
            elif z <= -self.entry_z:
                sig_type = SignalType.BUY            # fade the down-extension

        conf = float(min(1.0, max(0.1, abs(z) / (2 * self.entry_z))))
        score = float(max(-1.0, min(1.0, -z / (2 * self.entry_z))))  # reversal direction
        return Signal(
            symbol=symbol,
            signal_type=sig_type,
            confidence=Percentage(Decimal(str(conf))),
            score=score,
            timestamp=datetime.now(),
            source_layer="ShortTermStatisticalReversal",
            metadata={"z": z, "ranging": ranging, "sma20": sma20, "sma50": sma50,
                      "regime_required": "ranging"},
        )
