"""
Infrastructure implementation of the Liquidity Strategy following hexagonal architecture.
"""
from typing import Dict, Any, Optional, List
from domain.entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime, time
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class LiquidityStrategyAdapter(BaseStrategyAdapter):
    """
    True stop-sweep reaction model that identifies actual liquidity sweeps
    with proper confirmation and session awareness
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Liquidity")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_liquidity_config
        system_config = get_liquidity_config()

        # Merge with any passed config, prioritizing passed config
        self.config = {**system_config.get('parameters', {}), **(config or {})}

        self.lookback_period = self.config.get("lookback_period", 50)
        self.swing_threshold = self.config.get("swing_threshold", 0.005)  # 0.5% threshold for swing detection
        self.sweep_confirmation_bars = self.config.get("sweep_confirmation_bars", 2)  # Bars to confirm sweep
        self.session_timeout_bars = self.config.get("session_timeout_bars", 100)  # Bars before invalidating unused sweeps

        # Session times (in UTC) - typical forex sessions
        self.asia_session_start = time(23, 0)  # 11 PM UTC (Tokyo opens)
        self.london_session_start = time(6, 0)  # 6 AM UTC (London opens)
        self.ny_session_start = time(13, 0)    # 1 PM UTC (NY opens)

        # Track liquidity levels and their status
        self.liquidity_levels = []  # List of dictionaries containing level info
        self.last_sweep_time = None
        self.current_session = None

    def _detect_swing_points(self, highs: List[float], lows: List[float]) -> Dict[str, List[Dict]]:
        """Detect swing highs and lows that represent potential liquidity levels"""
        swing_highs = []
        swing_lows = []

        # Look for swing points using higher high/lower low methodology
        for i in range(5, len(highs) - 5):  # Need 5 bars on each side to detect swings
            # Check for swing high (higher high with lower highs on both sides)
            is_swing_high = (
                highs[i] > max(highs[i-5:i]) and  # Higher than 5 previous bars
                highs[i] >= max(highs[i+1:i+6]) and  # Higher than or equal to next 5 bars
                highs[i] > highs[i-1] and  # Strictly higher than previous
                highs[i] >= highs[i+1]     # Higher than or equal to next
            )

            # Check for swing low (lower low with higher lows on both sides)
            is_swing_low = (
                lows[i] < min(lows[i-5:i]) and  # Lower than 5 previous bars
                lows[i] <= min(lows[i+1:i+6]) and  # Lower than or equal to next 5 bars
                lows[i] < lows[i-1] and  # Strictly lower than previous
                lows[i] <= lows[i+1]     # Lower than or equal to next
            )

            if is_swing_high:
                swing_highs.append({
                    'index': i,
                    'level': highs[i],
                    'type': 'high',  # REQUIRED by _detect_sweeps; without it the level
                                     # defaulted to 'high' for BOTH highs and lows, so swing
                                     # lows were never swept -> 0 BUY signals (SELL-only bug).
                    'timestamp': i,  # Using index as proxy for time
                    'active': True,
                    'swept': False,
                    'confirmed': False
                })

            if is_swing_low:
                swing_lows.append({
                    'index': i,
                    'level': lows[i],
                    'type': 'low',  # see note above — restores swing-low sweeps -> BUY signals
                    'timestamp': i,  # Using index as proxy for time
                    'active': True,
                    'swept': False,
                    'confirmed': False
                })

        return {
            'swing_highs': swing_highs,
            'swing_lows': swing_lows
        }

    def _update_liquidity_levels(self, swing_points: Dict[str, List[Dict]], current_index: int):
        """Update liquidity levels based on new swing points and time expiration"""
        # Add new swing points to our tracking
        for swing_high in swing_points['swing_highs']:
            # Check if this swing high is significantly different from existing ones
            is_new_level = True
            for existing_level in self.liquidity_levels:
                if abs(swing_high['level'] - existing_level['level']) / existing_level['level'] < 0.002:  # 0.2% tolerance
                    is_new_level = False
                    break

            if is_new_level:
                self.liquidity_levels.append(swing_high)

        for swing_low in swing_points['swing_lows']:
            # Check if this swing low is significantly different from existing ones
            is_new_level = True
            for existing_level in self.liquidity_levels:
                if abs(swing_low['level'] - existing_level['level']) / existing_level['level'] < 0.002:  # 0.2% tolerance
                    is_new_level = False
                    break

            if is_new_level:
                self.liquidity_levels.append(swing_low)

        # Remove expired levels (older than session timeout)
        active_levels = []
        for level in self.liquidity_levels:
            if (current_index - level['index']) < self.session_timeout_bars:
                active_levels.append(level)

        self.liquidity_levels = active_levels

    def _detect_sweeps(self, highs: List[float], lows: List[float], closes: List[float]) -> List[Dict]:
        """Detect actual sweeps of liquidity levels"""
        sweeps = []

        current_price = closes[-1]

        for level_info in self.liquidity_levels:
            if not level_info['active'] or level_info['swept']:
                continue

            level = level_info['level']

            # Check if the level was swept (price moved beyond it)
            if level_info.get('type', 'high') == 'high':  # Swing high (resistance)
                was_swept = highs[-1] > level
                if was_swept:
                    # Check if price closed back inside the range (confirmation)
                    close_back_inside = closes[-1] <= level

                    sweeps.append({
                        'level_info': level_info,
                        'swept': True,
                        'confirmed': close_back_inside,  # True if price closed back inside
                        'direction': 'bearish',  # After sweeping a high, expect bearish reaction
                        'sweep_bar': len(closes) - 1,
                        'close_back_inside': close_back_inside
                    })
            else:  # Swing low (support)
                was_swept = lows[-1] < level
                if was_swept:
                    # Check if price closed back inside the range (confirmation)
                    close_back_inside = closes[-1] >= level

                    sweeps.append({
                        'level_info': level_info,
                        'swept': True,
                        'confirmed': close_back_inside,  # True if price closed back inside
                        'direction': 'bullish',  # After sweeping a low, expect bullish reaction
                        'sweep_bar': len(closes) - 1,
                        'close_back_inside': close_back_inside
                    })

        return sweeps

    def _get_current_session(self) -> str:
        """Determine the current trading session based on time"""
        # For simulation purposes, we'll use the bar index to simulate time
        # In a real system, this would use actual timestamps
        current_hour = (len(self.data_buffer) % 24)  # Simulate hour progression

        if 22 <= current_hour or current_hour < 6:  # Asia session (10 PM - 6 AM UTC)
            return 'asia'
        elif 6 <= current_hour < 13:  # London session (6 AM - 1 PM UTC)
            return 'london'
        elif 13 <= current_hour < 22:  # NY session (1 PM - 10 PM UTC)
            return 'ny'
        else:
            return 'inactive'

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate signal based on true liquidity sweep analysis with confirmation"""
        if len(self.data_buffer) < self.lookback_period:
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {self.lookback_period}")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]

            if len(closes) < self.lookback_period:
                return None

            current_price = closes[-1]
            current_index = len(closes) - 1

            # Determine current session
            self.current_session = self._get_current_session()

            # Detect swing points (potential liquidity levels)
            swing_points = self._detect_swing_points(highs, lows)

            # Update our liquidity level tracking
            self._update_liquidity_levels(swing_points, current_index)

            # Detect if any liquidity levels were swept
            sweeps = self._detect_sweeps(highs, lows, closes)

            # Process sweeps to find confirmed ones that happened in recent bars
            confirmed_sweeps = [
                sweep for sweep in sweeps
                if sweep['confirmed'] and
                sweep['close_back_inside'] and
                (current_index - sweep['sweep_bar']) <= self.sweep_confirmation_bars
            ]

            # Determine signal based on confirmed sweeps
            final_signal_type = SignalType.HOLD
            final_confidence_factor = self.config.get("default_confidence_factor", 0.3)
            final_score = 0.0

            if confirmed_sweeps:
                # Use the most recent confirmed sweep
                latest_sweep = confirmed_sweeps[-1]

                # Entry occurs AFTER sweep confirmation, not on the sweep candle
                sweep_direction = latest_sweep['direction']

                if sweep_direction == 'bullish':
                    final_signal_type = SignalType.BUY
                    # Confidence based on how deep the sweep went and how strong the rejection was
                    level = latest_sweep['level_info']['level']
                    sweep_depth = (level - lows[-1]) / level  # How far below the level price went
                    rejection_strength = (closes[-1] - lows[-1]) / (highs[-1] - lows[-1]) if highs[-1] != lows[-1] else 0.5
                    final_confidence_factor = min(1.0, 0.5 + sweep_depth + rejection_strength)
                    final_score = min(1.0, sweep_depth * 10)
                elif sweep_direction == 'bearish':
                    final_signal_type = SignalType.SELL
                    # Confidence based on how high above the level price went and how strong the rejection was
                    level = latest_sweep['level_info']['level']
                    sweep_depth = (highs[-1] - level) / level  # How far above the level price went
                    rejection_strength = (highs[-1] - closes[-1]) / (highs[-1] - lows[-1]) if highs[-1] != lows[-1] else 0.5
                    final_confidence_factor = min(1.0, 0.5 + sweep_depth + rejection_strength)
                    final_score = max(-1.0, -sweep_depth * 10)

                # Mark this level as swept to avoid duplicate signals
                latest_sweep['level_info']['swept'] = True
                latest_sweep['level_info']['active'] = False

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                timestamp=datetime.now(),
                source_layer="TrueLiquiditySweep",
                metadata={
                    "current_price": current_price,
                    "current_session": self.current_session,
                    "total_liquidity_levels": len(self.liquidity_levels),
                    "active_levels": len([level for level in self.liquidity_levels if level['active']]),
                    "confirmed_sweeps": len(confirmed_sweeps),
                    "latest_sweep_details": confirmed_sweeps[-1]['level_info'] if confirmed_sweeps else None,
                    "session_awareness_applied": True,
                    "sweep_detection_method": "swing_high_low_sweep_with_close_confirmation",
                    "sweep_confirmation_bars": self.sweep_confirmation_bars,
                    "session_timeout_bars": self.session_timeout_bars
                }
            )

            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")
                if confirmed_sweeps:
                    level = confirmed_sweeps[-1]['level_info']['level']
                    self.logger.info(f"Liquidity sweep confirmed at level: {level}, direction: {confirmed_sweeps[-1]['direction']}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None