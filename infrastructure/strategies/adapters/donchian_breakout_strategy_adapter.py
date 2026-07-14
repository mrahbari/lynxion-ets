"""Donchian Channel Breakout (DCB) — RETIRED-slot replacement candidate C2.

Hypothesis: a decisive break of the prior N-bar high/low channel (classic Donchian/turtle channel)
initiates a directional move that continues, filtered to expanding volatility. Distinct *mechanism*
from breakout (consolidation-compression + rejection geometry) and volatility_breakout (ATR-expansion
magnitude trigger): DCB is a pure N-bar channel break.

A-priori parameters (NO tuning / NO search): channel N=20, ATR-expansion filter (current ATR above its
rolling median). Design timeframe 1h. Auditable: signal is a single channel-break test + a volatility
gate.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

import numpy as np

from domain.entities import Signal, SignalType
from domain.value_objects import Percentage
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class DonchianBreakoutStrategyAdapter(BaseStrategyAdapter):
    """Break of the prior N-bar high/low channel in an expanding-volatility regime."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("DonchianChannelBreakout")
        c = config or {}
        self.channel = c.get("channel", 20)
        self.atr_window = c.get("atr_window", 14)
        self.atr_med_window = c.get("atr_med_window", 100)
        self.min_bars = self.atr_med_window + self.channel + 5

    def generate_signal(self, symbol):
        buf = getattr(self, "data_buffer", None)
        if not buf or len(buf) < self.min_bars:
            return None
        highs = np.array([b["high"] for b in buf], dtype=float)
        lows = np.array([b["low"] for b in buf], dtype=float)
        closes = np.array([b["close"] for b in buf], dtype=float)

        # prior N-bar channel (exclude the current bar)
        prior_high = float(highs[-self.channel - 1:-1].max())
        prior_low = float(lows[-self.channel - 1:-1].min())
        close = float(closes[-1])

        # volatility-expansion gate: true-range ATR above its rolling median
        tr = np.maximum(highs[1:] - lows[1:],
                        np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])))
        atr = float(tr[-self.atr_window:].mean())
        atr_med = float(np.median(tr[-self.atr_med_window:]))
        expanding = atr_med > 0 and atr > 1.1 * atr_med

        sig_type = SignalType.HOLD
        if expanding:
            if close > prior_high:
                sig_type = SignalType.BUY
            elif close < prior_low:
                sig_type = SignalType.SELL

        # confidence ~ break size relative to ATR
        if sig_type == SignalType.BUY:
            mag = (close - prior_high) / atr if atr > 0 else 0
        elif sig_type == SignalType.SELL:
            mag = (prior_low - close) / atr if atr > 0 else 0
        else:
            mag = 0
        conf = float(min(1.0, max(0.1, abs(mag))))
        score = float(max(-1.0, min(1.0, mag if sig_type == SignalType.BUY else -mag)))
        return Signal(
            symbol=symbol,
            signal_type=sig_type,
            confidence=Percentage(Decimal(str(conf))),
            score=score,
            timestamp=datetime.now(),
            source_layer="DonchianChannelBreakout",
            metadata={"prior_high": prior_high, "prior_low": prior_low, "atr": atr,
                      "atr_median": atr_med, "expanding": expanding, "regime_required": "breakout"},
        )

    def should_execute(self, fused_signal) -> bool:
        """Check if the Donchian breakout strategy should execute based on the fused signal"""
        from infrastructure.strategies.strategy_config import StrategyConfig
        
        # First check if strategy is enabled
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        # Get strategy-specific configuration
        min_confidence = getattr(self, "config", {}).get('min_confidence', 0.5)

        # Check if signal meets breakout criteria
        confidence = float(fused_signal.confidence.value)
        is_volatile = 'volatile' in fused_signal.regime_context.lower() or 'breakout' in fused_signal.regime_context.lower()

        # Log specific rejection reason
        if confidence < min_confidence:
            self.logger.info(f"Trade rejected: "
                           f"confidence={confidence:.2f} < "
                           f"DONCHIAN_BREAKOUT_MIN_CONFIDENCE_THRESHOLD={min_confidence:.2f} "
                           f"source=donchian_breakout_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False
        elif not is_volatile:
            self.logger.info(f"Trade rejected: "
                           f"regime_context='{fused_signal.regime_context}' does not indicate volatile/breakout market "
                           f"source=donchian_breakout_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False

        return True

