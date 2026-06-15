"""
Infrastructure implementation of the VWAP Reversal Strategy following hexagonal architecture.
"""
from typing import Dict, Any, Optional, List
from domain.entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime, time, timedelta
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class VWAPReversalStrategyAdapter(BaseStrategyAdapter):
    """Session-anchored VWAP reversal strategy with mean-reversion regime filtering"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("VWAPReversal")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_vwap_reversal_config
        system_config = get_vwap_reversal_config()

        # Merge with any passed config, prioritizing passed config
        self.config = {**system_config.get('parameters', {}), **(config or {})}

        self.lookback = self.config.get("lookback", 200)
        self.std_mult = self.config.get("std_mult", 2.0)
        self.session_reset_hour = self.config.get("session_reset_hour", 0)  # Hour to reset VWAP (0 = midnight UTC)
        self.deviation_threshold = self.config.get("deviation_threshold", 0.02)  # Legacy fixed band (now a fallback only)
        self.min_deviation_floor = self.config.get("min_deviation_floor", 0.001)  # Absolute floor for the sigma band
        self.trend_exhaustion_threshold = self.config.get("trend_exhaustion_threshold", 0.005)  # Threshold for trend exhaustion
        self.rejection_confirmation_bars = self.config.get("rejection_confirmation_bars", 2)  # Bars to confirm rejection

        # Session VWAP tracking
        self.session_vwap = None
        self.session_start_bar = 0
        self.last_session_hour = None
        self.last_session_anchor = None  # Real-time session anchor (UTC day for reset_hour=0)

        # Trend tracking
        self.trend_direction = None  # None, 'bullish', 'bearish'
        self.vwap_broken = False  # Track if VWAP has been broken recently

    def _should_reset_session(self, current_bar_index: int) -> bool:
        """Determine if we should reset the session VWAP based on time"""
        # Prefer the bar's REAL timestamp when available so the session is anchored to
        # an actual trading day (the design intent — see session_reset_hour, default
        # midnight UTC). The old `current_bar_index % 24` placeholder made a "session"
        # only 24 bars (24 minutes on 1m), so the session VWAP hugged price and the
        # deviation gate could never be reached -> the strategy never fired. (Type-C
        # implementation defect: simulated time, not real time.)
        ts = None
        if self.data_buffer:
            ts = self.data_buffer[-1].get('timestamp')
        if isinstance(ts, (int, float)):
            ts = datetime.utcfromtimestamp(ts)
        if isinstance(ts, datetime):
            # Anchor day = most recent calendar day whose session_reset_hour has passed.
            anchor = ts.date() if ts.hour >= self.session_reset_hour else (ts - timedelta(days=1)).date()
            should_reset = self.last_session_anchor is not None and anchor != self.last_session_anchor
            self.last_session_anchor = anchor
            return should_reset

        # Fallback (no real timestamp available): legacy simulated-hour progression.
        current_hour = (current_bar_index % 24)  # Simulate hour progression

        # Reset if we've crossed the session boundary
        should_reset = False
        if self.last_session_hour is not None:
            # Check if we crossed the reset hour (e.g., from 23 to 0 for midnight reset)
            if self.session_reset_hour == 0:
                # Special case for midnight reset
                if self.last_session_hour == 23 and current_hour == 0:
                    should_reset = True
            elif self.last_session_hour < self.session_reset_hour <= current_hour:
                should_reset = True
            elif current_hour < self.last_session_hour and current_hour < self.session_reset_hour:
                # Handle case where we wrap around midnight
                should_reset = True

        self.last_session_hour = current_hour
        return should_reset

    def _compute_session_vwap(self, closes: List[float], volumes: List[float], start_idx: int) -> float:
        """Compute VWAP for the current session"""
        if not volumes or sum(volumes[start_idx:]) <= 0:
            # Fallback to simple average if no volume data
            return sum(closes[start_idx:]) / len(closes[start_idx:]) if closes[start_idx:] else np.mean(closes[-20:])

        session_closes = closes[start_idx:]
        session_volumes = volumes[start_idx:]

        if len(session_closes) != len(session_volumes):
            # Adjust to match lengths
            min_len = min(len(session_closes), len(session_volumes))
            session_closes = session_closes[:min_len]
            session_volumes = session_volumes[:min_len]

        if not session_closes or not session_volumes:
            return np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes) if closes else 0

        total_pv = sum(c * v for c, v in zip(session_closes, session_volumes))
        total_v = sum(session_volumes)

        return total_pv / total_v if total_v > 0 else np.mean(session_closes)

    def _assess_trend_exhaustion(self, closes: List[float], current_price: float, vwap: float) -> bool:
        """Assess if the higher-timeframe trend is flat or exhausted"""
        if len(closes) < 50:
            return True  # Default to allowing if not enough data

        # Calculate recent trend using linear regression
        lookback = min(50, len(closes))
        recent_prices = closes[-lookback:]

        x = np.arange(len(recent_prices))
        slope, _ = np.polyfit(x, recent_prices, 1) if len(recent_prices) > 1 else (0, 0)
        # Normalize slope to a FRACTIONAL per-bar change. np.polyfit returns slope in
        # absolute price units ($/bar — ~$5 for BTC), but trend_exhaustion_threshold
        # (0.005) is a small fractional constant, so abs(slope) <= threshold (the
        # flat-trend clause) was unreachable -> mean-reversion regime fired ~0.07% of
        # bars and the strategy never traded. Scale-invariant unit-bug fix (type C).
        slope = (slope / current_price) if current_price else slope

        # Determine trend direction
        current_trend_direction = None
        if abs(slope) > self.trend_exhaustion_threshold:
            current_trend_direction = 'bullish' if slope > 0 else 'bearish'

        # Update internal trend tracking
        self.trend_direction = current_trend_direction

        # Check if trend is exhausted (flat) or if we're at the end of a trend
        is_trend_exhausted = (
            abs(slope) <= self.trend_exhaustion_threshold or  # Flat trend
            (slope > 0 and current_price > max(recent_prices[-5:])) or  # Bullish trend ending (price at highs)
            (slope < 0 and current_price < min(recent_prices[-5:]))     # Bearish trend ending (price at lows)
        )

        return is_trend_exhausted

    def _detect_vwap_break(self, closes: List[float], vwap: float) -> bool:
        """Detect if VWAP has been broken recently"""
        if len(closes) < 2:
            return self.vwap_broken

        # Check if VWAP was broken in recent bars (last 5 bars)
        recent_closes = closes[-5:]
        vwap_crossings = sum(1 for i in range(1, len(recent_closes))
                             if (recent_closes[i-1] <= vwap and recent_closes[i] > vwap) or
                                (recent_closes[i-1] >= vwap and recent_closes[i] < vwap))

        # If there were recent crossings, consider VWAP broken
        return vwap_crossings > 0

    def _check_rejection_pattern(self, highs: List[float], lows: List[float], closes: List[float],
                                 vwap: float) -> Dict[str, bool]:
        """Check for rejection patterns near VWAP"""
        if len(highs) < 3 or len(lows) < 3:
            return {"bullish_rejection": False, "bearish_rejection": False, "failure_swings": False}

        # Get the last few bars
        recent_highs = highs[-3:]
        recent_lows = lows[-3:]
        recent_closes = closes[-3:]

        # Check for bullish rejection (price rejected from below VWAP)
        bullish_rejection = (
            recent_lows[-1] < vwap and  # Latest bar touched below VWAP
            recent_closes[-1] > vwap  # But closed above VWAP
        )

        # Check for bearish rejection (price rejected from above VWAP)
        bearish_rejection = (
            recent_highs[-1] > vwap and  # Latest bar touched above VWAP
            recent_closes[-1] < vwap  # But closed below VWAP
        )

        # Check for failure swings (indicating trend exhaustion)
        failure_swings = False
        if len(recent_highs) >= 3:
            # Bearish failure swing: higher high but lower low/high
            bearish_fs = (recent_highs[-2] > recent_highs[-3] and
                         recent_lows[-1] < recent_lows[-2])
            # Bullish failure swing: lower low but higher high/close
            bullish_fs = (recent_lows[-2] < recent_lows[-3] and
                         recent_highs[-1] > recent_highs[-2])
            failure_swings = bearish_fs or bullish_fs

        return {
            "bullish_rejection": bullish_rejection,
            "bearish_rejection": bearish_rejection,
            "failure_swings": failure_swings
        }

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate signal using session-anchored VWAP reversal analysis with mean-reversion regime filtering"""
        if len(self.data_buffer) < 50:  # Need sufficient data for VWAP calculation
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least 50")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]
            volumes = [item.get('volume', 1.0) for item in self.data_buffer if 'close' in item]  # Default volume to 1.0 if not available

            if len(closes) < 50:
                self.logger.debug(f"Not enough data for {self.name}: closes={len(closes)}")
                return None

            current_price = closes[-1]
            current_bar_index = len(closes) - 1

            # Check if we should reset the session VWAP
            if self._should_reset_session(current_bar_index):
                self.session_start_bar = current_bar_index
                self.session_vwap = None
                self.vwap_broken = False  # Reset VWAP break status on new session

            # Compute or update session VWAP
            if self.session_vwap is None:
                self.session_vwap = self._compute_session_vwap(closes, volumes, self.session_start_bar)
            else:
                # Update VWAP incrementally with new data
                if len(volumes) > self.session_start_bar:
                    self.session_vwap = self._compute_session_vwap(closes, volumes, self.session_start_bar)

            # Assess if the market is in a mean-reversion regime
            is_mean_reversion_regime = self._assess_trend_exhaustion(closes, current_price, self.session_vwap)

            # Check if VWAP has been broken recently
            self.vwap_broken = self._detect_vwap_break(closes, self.session_vwap)

            # Calculate deviation from VWAP
            price_deviation = (current_price - self.session_vwap) / self.session_vwap if self.session_vwap != 0 else 0

            # Significant-deviation band. The strategy carries std_mult (=2.0) and
            # lookback (=200) for the canonical VWAP +/- std_mult*sigma reversion band,
            # but the gate used a fixed deviation_threshold (0.02 = 2%) that is
            # structurally unreachable: the max observed deviation from a daily session
            # VWAP on 1m crypto is ~1.1% (2-sigma ~0.21%). Wire the intended sigma band
            # (self-calibrating across assets/timeframes); keep an absolute floor so a
            # collapsed-volatility session can't trigger on noise. Type-B fidelity fix.
            _recent = np.array(closes[-self.lookback:]) if len(closes) >= self.lookback else np.array(closes)
            _dispersion = float(np.std(_recent / self.session_vwap - 1.0)) if self.session_vwap else 0.0
            sig_threshold = max(self.min_deviation_floor, self.std_mult * _dispersion)

            # Check for rejection patterns near VWAP
            rejection_patterns = self._check_rejection_pattern(highs, lows, closes, self.session_vwap)

            # Determine signal based on mean-reversion criteria
            final_signal_type = SignalType.HOLD
            final_confidence_factor = self.config.get("default_confidence_factor", 0.3)
            final_score = 0.0

            # Only allow trades if:
            # 1. Market is in mean-reversion regime
            # 2. VWAP hasn't been broken recently (indicating intact level)
            # 3. Price is significantly deviated from VWAP
            # 4. There's evidence of rejection/failure near VWAP
            if is_mean_reversion_regime and not self.vwap_broken and abs(price_deviation) >= sig_threshold:

                # Bullish setup: price significantly below VWAP with rejection
                if (price_deviation < -sig_threshold and
                    (rejection_patterns['bullish_rejection'] or rejection_patterns['failure_swings'])):

                    final_signal_type = SignalType.BUY
                    # Confidence based on deviation magnitude and rejection confirmation
                    strength = abs(price_deviation)
                    rejection_confirmed = 1.0 if rejection_patterns['bullish_rejection'] else 0.5
                    final_confidence_factor = min(1.0, 0.5 + strength + rejection_confirmed * 0.3)
                    final_score = min(1.0, strength * 5)

                # Bearish setup: price significantly above VWAP with rejection
                elif (price_deviation > sig_threshold and
                      (rejection_patterns['bearish_rejection'] or rejection_patterns['failure_swings'])):

                    final_signal_type = SignalType.SELL
                    # Confidence based on deviation magnitude and rejection confirmation
                    strength = abs(price_deviation)
                    rejection_confirmed = 1.0 if rejection_patterns['bearish_rejection'] else 0.5
                    final_confidence_factor = min(1.0, 0.5 + strength + rejection_confirmed * 0.3)
                    final_score = max(-1.0, -strength * 5)

            # Block trades during strong trend continuation
            if self.trend_direction and abs(price_deviation) < sig_threshold * 0.5:
                # If we're in a strong trend and not significantly deviated, don't trade
                final_signal_type = SignalType.HOLD
                final_confidence_factor = 0.1  # Very low confidence based on config

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                timestamp=datetime.now(),
                source_layer="SessionAnchoredVWAPReversal",
                metadata={
                    "current_price": current_price,
                    "session_vwap": self.session_vwap,
                    "price_deviation": price_deviation,
                    "deviation_threshold": self.deviation_threshold,
                    "is_mean_reversion_regime": is_mean_reversion_regime,
                    "vwap_broken_recently": self.vwap_broken,
                    "trend_direction": self.trend_direction,
                    "rejection_patterns": rejection_patterns,
                    "session_start_bar": self.session_start_bar,
                    "current_bar_index": current_bar_index,
                    "trend_exhaustion_assessed": True,
                    "rejection_confirmation_used": True
                }
            )

            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")
                self.logger.info(f"VWAP: {self.session_vwap:.5f}, Deviation: {price_deviation:.3f}, Regime: {'Mean-Reversion' if is_mean_reversion_regime else 'Trend'}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
        """Request position size - this should be handled by the risk manager"""
        # According to the risk governance rules, the Strategy module should only
        # request risk parameters but not calculate them. The actual calculation
        # must be done by the Risk module.

        # Return a default value that will be overridden by the risk manager
        # This is just a placeholder to maintain interface compatibility
        return 0.0

    def get_strategy_name(self) -> str:
        """Get the name of the strategy"""
        return self.name