"""
Infrastructure implementation of the Mean Reversion Strategy following hexagonal architecture.
"""
from typing import List, Optional, Dict, Any
from domain.entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class MeanReversionStrategyAdapter(BaseStrategyAdapter):
    """Range-bound mean reversion strategy with volatility and momentum filtering"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("MeanReversion")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_mean_reversion_config
        system_config = get_mean_reversion_config()

        # NOTE: system_config contains execution settings (like min_confidence, max_position_size)
        # at the top level, and mathematical model params inside the nested 'parameters' dict.
        # We must extract and merge both so that key settings are correctly loaded into self.config
        # and do not fall back to obsolete system defaults.
        params = system_config.get('parameters', {})
        top_level = {k: v for k, v in system_config.items() if k != 'parameters'}
        self.config = {**top_level, **params, **(config or {})}

        # Use configuration values or defaults
        self.lookback_period = self.config.get("lookback_period", 20)
        self.std_dev_threshold = self.config.get("std_dev_threshold", 1.5)
        self.rsi_oversold = self.config.get("rsi_oversold", 30)
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
        self.bb_period = self.config.get("bb_period", 20)
        self.bb_std_dev = self.config.get("bb_std_dev", 2.0)

        # Range and momentum detection parameters
        self.volatility_expansion_window = self.config.get("volatility_expansion_window", 20)
        self.momentum_window = self.config.get("momentum_window", 10)
        self.range_definition_window = self.config.get("range_definition_window", 50)
        # Number of prior failed range-break attempts required before entry. The core
        # hypothesis is "revert from a range extreme with rejection + oversold RSI";
        # demanding 3 prior failed breaks is an arbitrary engineering constant (type-B
        # miscalibration) that, conjoined with rejection AND RSI, never co-occurs on 1m
        # (suppressed the hypothesis). 1 keeps the "range is holding" confirmation
        # without the arbitrary strictness. Not optimization — fidelity restoration.
        self.failed_expansion_threshold = self.config.get("failed_expansion_threshold", 1)
        self.momentum_threshold = self.config.get("momentum_threshold", 0.005)  # Threshold for considering momentum high

    def _is_volatility_expanding(self, closes: List[float]) -> bool:
        """Check if volatility is expanding (blocking condition)"""
        if len(closes) < self.volatility_expansion_window * 2:
            return False

        # Compare recent volatility to historical volatility
        recent_prices = closes[-self.volatility_expansion_window:]
        older_prices = closes[-self.volatility_expansion_window*2:-self.volatility_expansion_window]

        recent_volatility = np.std(np.diff(recent_prices)) if len(recent_prices) > 1 else 0
        older_volatility = np.std(np.diff(older_prices)) if len(older_prices) > 1 else 0

        # If recent volatility is significantly higher than older volatility, it's expanding
        return recent_volatility > older_volatility * 1.2 and recent_volatility > 0

    def _is_directional_momentum_increasing(self, closes: List[float]) -> bool:
        """Check if directional momentum is increasing (blocking condition)"""
        if len(closes) < self.momentum_window + 5:  # Need extra bars for trend assessment
            return False

        # Calculate momentum using rate of change
        recent_prices = closes[-self.momentum_window:]
        momentum_values = [(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                          for i in range(1, len(recent_prices)) if recent_prices[i-1] != 0]

        if not momentum_values:
            return False

        # Calculate trend of momentum (is momentum itself trending?)
        if len(momentum_values) < 5:
            return False

        # Use linear regression to see if momentum is trending upward (in absolute terms)
        x = np.arange(len(momentum_values))
        slope, _ = np.polyfit(x, [abs(m) for m in momentum_values], 1) if len(momentum_values) > 1 else (0, 0)

        # Also check if average momentum magnitude is above threshold
        avg_momentum_magnitude = np.mean([abs(m) for m in momentum_values])

        # Return True if momentum trend is increasing AND magnitude is high
        return slope > 0.001 and avg_momentum_magnitude > self.momentum_threshold

    def _define_range_boundaries(self, highs: List[float], lows: List[float]) -> Dict[str, float]:
        """Define range boundaries based on swing highs and lows"""
        # EXCLUDE the most recent bars (the ones tested for rejection/failed-expansion)
        # so the range is the PRIOR consolidation. Computing bounds over a window that
        # INCLUDED those bars made upper_bound = max(highs incl. them) >= every tested
        # bar's high, so `current_high > upper_bound` (rejection) and failed-expansion
        # were structurally impossible — both helpers returned 0/False on every bar
        # (implementation bug, NOT the hypothesis). Excluding the test window restores
        # the intended "price probes the established range and is rejected" behavior.
        exclude = 20  # covers the current bar (rejection) + failed-expansion lookback
        win = self.range_definition_window
        if len(highs) < win + exclude or len(lows) < win + exclude:
            return {"upper_bound": None, "lower_bound": None, "middle": None}

        recent_highs = highs[-(win + exclude):-exclude]
        recent_lows = lows[-(win + exclude):-exclude]

        # Find highest high and lowest low in the range
        upper_bound = max(recent_highs) if recent_highs else None
        lower_bound = min(recent_lows) if recent_lows else None
        middle = (upper_bound + lower_bound) / 2 if upper_bound and lower_bound else None

        return {
            "upper_bound": upper_bound,
            "lower_bound": lower_bound,
            "middle": middle
        }

    def _count_failed_expansion_attempts(self, highs: List[float], lows: List[float],
                                       range_bounds: Dict[str, float]) -> int:
        """Count how many times price attempted to expand beyond range but failed"""
        if not range_bounds['upper_bound'] or not range_bounds['lower_bound']:
            return 0

        failed_attempts = 0
        lookback = min(20, len(highs))  # Look at recent attempts

        for i in range(1, lookback):
            prev_high = highs[-i-1] if i+1 <= len(highs) else highs[0]
            curr_high = highs[-i] if i <= len(highs) else highs[-1]
            prev_low = lows[-i-1] if i+1 <= len(lows) else lows[0]
            curr_low = lows[-i] if i <= len(lows) else lows[-1]

            # Check if there was an attempt to break out that failed
            # High tried to go above upper bound but came back down
            if prev_high <= range_bounds['upper_bound'] and curr_high > range_bounds['upper_bound']:
                # If next bar's high is back below the bound, it's a failed attempt
                next_high = highs[-i+1] if i > 1 and i-1 <= len(highs) else curr_high
                if next_high <= range_bounds['upper_bound']:
                    failed_attempts += 1

            # Low tried to go below lower bound but came back up
            if prev_low >= range_bounds['lower_bound'] and curr_low < range_bounds['lower_bound']:
                # If next bar's low is back above the bound, it's a failed attempt
                next_low = lows[-i+1] if i > 1 and i-1 <= len(lows) else curr_low
                if next_low >= range_bounds['lower_bound']:
                    failed_attempts += 1

        return failed_attempts

    def _check_rejection_confirmation(self, highs: List[float], lows: List[float],
                                    closes: List[float], range_bounds: Dict[str, float]) -> Dict[str, bool]:
        """Check for rejection confirmation near range extremes"""
        if not range_bounds['upper_bound'] or not range_bounds['lower_bound']:
            return {"near_upper_rejection": False, "near_lower_rejection": False}

        current_high = highs[-1] if highs else 0
        current_low = lows[-1] if lows else 0
        current_close = closes[-1] if closes else 0

        # Define thresholds for being "near" range bounds
        range_size = range_bounds['upper_bound'] - range_bounds['lower_bound']
        threshold = range_size * 0.05  # 5% of range size as threshold

        # Check for rejection near upper bound (price approached or went above but closed below)
        upper_rejection = (
            current_high >= range_bounds['upper_bound'] - threshold and
            current_close < range_bounds['upper_bound']
        )

        # Check for rejection near lower bound (price approached or went below but closed above)
        lower_rejection = (
            current_low <= range_bounds['lower_bound'] + threshold and
            current_close > range_bounds['lower_bound']
        )

        return {
            "near_upper_rejection": upper_rejection,
            "near_lower_rejection": lower_rejection
        }

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal using range-bound mean reversion logic with volatility and momentum filtering"""
        if len(self.data_buffer) < max(self.lookback_period, 15, self.range_definition_window):
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {max(self.lookback_period, 15, self.range_definition_window)}")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]

            if len(closes) < max(self.lookback_period, 15, self.range_definition_window):
                self.logger.debug(f"Not enough close prices for {self.name}: {len(closes)}")
                return None

            current_price = closes[-1]

            # BLOCK 1: Check if volatility is expanding (block trades if true)
            if self._is_volatility_expanding(closes):
                self.logger.debug(f"Volatility expanding for {self.name}, blocking trade")
                return None

            # BLOCK 2: Check if directional momentum is increasing (block trades if true)
            if self._is_directional_momentum_increasing(closes):
                self.logger.debug(f"Directional momentum increasing for {self.name}, blocking trade")
                return None

            # DEFINE RANGE: Define range boundaries
            range_bounds = self._define_range_boundaries(highs, lows)
            if not range_bounds['upper_bound'] or not range_bounds['lower_bound']:
                self.logger.debug(f"Could not define range for {self.name}")
                return None

            # COUNT FAILED EXPANSIONS: Count failed attempts to break the range
            failed_expansions = self._count_failed_expansion_attempts(highs, lows, range_bounds)

            # CHECK REJECTION: Check for rejection confirmation near range extremes
            rejection_confirmation = self._check_rejection_confirmation(highs, lows, closes, range_bounds)

            # Calculate RSI for traditional overbought/oversold signals
            calculated_rsi = self.calculate_rsi(closes, 14)

            # Determine signal based on range-bound criteria with rejection confirmation
            final_signal_type = SignalType.HOLD
            final_confidence_factor = self.config.get("default_confidence_factor", 0.2)
            final_score = 0.0

            # Only allow trades if:
            # 1. We're in a range-bound market (not expanding volatility or momentum)
            # 2. There have been multiple failed expansion attempts
            # 3. There's rejection confirmation near range extremes
            # 4. Traditional indicators align (RSI is oversold/overbought)

            if (failed_expansions >= self.failed_expansion_threshold and
                calculated_rsi is not None):

                # Bullish setup: near lower bound with rejection + oversold RSI
                if (rejection_confirmation['near_lower_rejection'] and
                    calculated_rsi < self.rsi_oversold):

                    final_signal_type = SignalType.BUY
                    # Confidence based on number of failed expansions and RSI extremeness
                    expansion_confidence = min(1.0, failed_expansions / 10.0)
                    rsi_confidence = min(1.0, (self.rsi_oversold - calculated_rsi) / self.rsi_oversold)
                    final_confidence_factor = (expansion_confidence + rsi_confidence) / 2
                    final_score = min(1.0, (range_bounds['middle'] - current_price) / (range_bounds['middle'] - range_bounds['lower_bound']) if range_bounds['middle'] and range_bounds['lower_bound'] and (range_bounds['middle'] - range_bounds['lower_bound']) != 0 else 0.5)

                # Bearish setup: near upper bound with rejection + overbought RSI
                elif (rejection_confirmation['near_upper_rejection'] and
                      calculated_rsi > self.rsi_overbought):

                    final_signal_type = SignalType.SELL
                    # Confidence based on number of failed expansions and RSI extremeness
                    expansion_confidence = min(1.0, failed_expansions / 10.0)
                    rsi_confidence = min(1.0, (calculated_rsi - self.rsi_overbought) / (100 - self.rsi_overbought))
                    final_confidence_factor = (expansion_confidence + rsi_confidence) / 2
                    final_score = max(-1.0, (current_price - range_bounds['middle']) / (range_bounds['upper_bound'] - range_bounds['middle']) if range_bounds['middle'] and range_bounds['upper_bound'] and (range_bounds['upper_bound'] - range_bounds['middle']) != 0 else 0.5)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                timestamp=datetime.now(),
                source_layer="RangeBoundMeanReversion",
                metadata={
                    "current_price": current_price,
                    "range_upper_bound": range_bounds['upper_bound'],
                    "range_lower_bound": range_bounds['lower_bound'],
                    "range_middle": range_bounds['middle'],
                    "failed_expansion_attempts": failed_expansions,
                    "rejection_confirmation": rejection_confirmation,
                    "rsi": calculated_rsi,
                    "volatility_expanding": self._is_volatility_expanding(closes),
                    "momentum_increasing": self._is_directional_momentum_increasing(closes),
                    "range_definition_window": self.range_definition_window,
                    "failed_expansion_threshold": self.failed_expansion_threshold,
                    "volatility_expansion_checked": True,
                    "momentum_increasing_checked": True,
                    "rejection_confirmation_used": True
                }
            )

            # Log signal if generated
            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")
                self.logger.info(f"Range: {range_bounds['lower_bound']:.5f} - {range_bounds['upper_bound']:.5f}, Failed expansions: {failed_expansions}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None

    def should_execute(self, fused_signal) -> bool:
        """Check if the mean reversion strategy should execute based on the fused signal"""
        from infrastructure.strategies.strategy_config import StrategyConfig
        
        # First check if strategy is enabled
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        # Get strategy-specific configuration
        min_confidence = self.config.get('min_confidence', 0.5)

        # Check if signal meets mean reversion criteria
        confidence = float(fused_signal.confidence.value)
        is_reverting = any(term in fused_signal.regime_context.lower() for term in ['mean', 'revert', 'ranging', 'stable'])

        # Log specific rejection reason
        if confidence < min_confidence:
            self.logger.info(f"Trade rejected: "
                           f"confidence={confidence:.2f} < "
                           f"MEAN_REVERSION_MIN_CONFIDENCE_THRESHOLD={min_confidence:.2f} "
                           f"source=mean_reversion_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False
        elif not is_reverting:
            self.logger.info(f"Trade rejected: "
                           f"regime_context='{fused_signal.regime_context}' does not indicate mean-reverting/ranging market "
                           f"source=mean_reversion_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False

        return True