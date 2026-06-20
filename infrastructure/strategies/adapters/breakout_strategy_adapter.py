"""
Infrastructure implementation of the Breakout Strategy following hexagonal architecture.
"""
from typing import List, Optional, Dict, Any
from domain.entities import Signal, SignalType
from domain.entities import FusedSignal, ExecutionIntent, OrderSide
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter
from infrastructure.strategies.strategy_config import StrategyConfig
from infrastructure.logging.forensic_logger import forensic_logger


class BreakoutStrategyAdapter(BaseStrategyAdapter):
    """Infrastructure implementation of structure-based breakout strategy with clear market hypothesis"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Breakout")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_breakout_config
        system_config = get_breakout_config()

        # Merge with any passed config, prioritizing passed config
        self.config = {**system_config.get('parameters', {}), **(config or {})}

        # Use configuration values or defaults
        self.lookback_period = self.config.get("lookback_period", 20)
        self.consolidation_period = self.config.get("consolidation_period", 10)
        # Confirmation margin a close must clear beyond the prior range to count as a
        # breakout. The old default 0.02 (2%) is impossible for a single bar on the
        # configured 1m timeframe (~0.05%/bar) -> the strategy emitted 0 signals.
        # 0.001 (0.1%) is a realistic per-bar confirmation margin that preserves the
        # "price breaks the consolidation range" hypothesis (signal-starvation fix).
        self.breakout_threshold = self.config.get("breakout_threshold", 0.001)
        self.atr_period = self.config.get("atr_period", 14)

        # Range tracking for preventing re-entry until new structure forms
        self.range_start_time = None
        self.range_high = None
        self.range_low = None
        self.last_breakout_direction = None  # None, 'bullish', 'bearish'
        self.range_broken = False
        self.entry_allowed = True

        # Time window for range validity (in number of bars)
        self.range_validity_bars = self.config.get("range_validity_bars", 50)

    def _define_range(self, highs: List[float], lows: List[float], closes: List[float]) -> Dict[str, Any]:
        """Explicitly define what constitutes a range (time + price compression)"""
        if len(highs) < self.consolidation_period or len(lows) < self.consolidation_period:
            return {"is_defined": False, "range_high": None, "range_low": None, "compression_ratio": 0}

        # Calculate recent price range vs historical range for compression.
        # EXCLUDE the current (potential breakout) bar: the range must be the PRIOR
        # consolidation so current price can actually break it. Including the current
        # bar made range_high = max(highs incl. current high) >= current close, so a
        # breakout (current_price > range_high) was structurally impossible — the
        # strategy emitted 0 signals (signal starvation). Fidelity fix, not a tune.
        recent_highs = highs[-self.consolidation_period - 1:-1]
        recent_lows = lows[-self.consolidation_period - 1:-1]
        recent_range = max(recent_highs) - min(recent_lows) if recent_highs and recent_lows else 0

        historical_highs = highs[-self.lookback_period - 1:-1]
        historical_lows = lows[-self.lookback_period - 1:-1]
        historical_range = max(historical_highs) - min(historical_lows) if historical_highs and historical_lows else 0

        # Calculate compression ratio (how much tighter the recent range is compared to historical)
        compression_ratio = historical_range / recent_range if recent_range > 0 else float('inf')

        # Define range boundaries
        range_high = max(recent_highs) if recent_highs else None
        range_low = min(recent_lows) if recent_lows else None

        # Check if market is eligible for breakout trading
        is_eligible = (
            compression_ratio > 1.5 and  # At least 50% more compressed than historical
            recent_range > 0 and  # There is actual price movement
            range_high is not None and
            range_low is not None
        )

        return {
            "is_defined": is_eligible,
            "range_high": range_high,
            "range_low": range_low,
            "compression_ratio": compression_ratio,
            "recent_range": recent_range,
            "historical_range": historical_range
        }

    def _validate_breakout(self, current_price: float, range_high: float, range_low: float,
                          highs: List[float], lows: List[float], closes: List[float]) -> Dict[str, Any]:
        """Validate breakout with proper confirmation"""
        if range_high is None or range_low is None:
            return {"is_valid": False, "direction": None, "confirmed": False, "invalid_reason": "Range not defined"}

        # Check for potential breakouts
        potential_bullish_breakout = current_price > range_high * (1 + self.breakout_threshold)
        potential_bearish_breakout = current_price < range_low * (1 - self.breakout_threshold)

        # Check for invalid breakouts (wick-only breaks or immediate rejection)
        recent_bars = min(3, len(highs), len(lows))
        if recent_bars < 2:
            return {"is_valid": False, "direction": None, "confirmed": False, "invalid_reason": "Insufficient recent bars"}

        recent_highs = highs[-recent_bars:]
        recent_lows = lows[-recent_bars:]
        recent_closes = closes[-recent_bars:]

        # Check for immediate rejection (price moved beyond level but closed back inside)
        bullish_rejection = (
            potential_bullish_breakout and
            current_price < range_high and  # Closed back inside
            any(high > range_high for high in recent_highs[:-1])  # Had a wick above
        )

        bearish_rejection = (
            potential_bearish_breakout and
            current_price > range_low and  # Closed back inside
            any(low < range_low for low in recent_lows[:-1])  # Had a wick below
        )

        # Check for wick-only breaks (price went beyond level but didn't close beyond)
        wick_only_bullish = (
            any(high > range_high * (1 + self.breakout_threshold) for high in recent_highs) and
            current_price <= range_high  # But closed back inside
        )

        wick_only_bearish = (
            any(low < range_low * (1 - self.breakout_threshold) for low in recent_lows) and
            current_price >= range_low  # But closed back inside
        )

        # Determine if breakout is confirmed (not just a wick)
        is_confirmed_bullish = potential_bullish_breakout and not bullish_rejection and not wick_only_bullish
        is_confirmed_bearish = potential_bearish_breakout and not bearish_rejection and not wick_only_bearish

        # Validate breakout based on confirmation
        if is_confirmed_bullish:
            return {
                "is_valid": True,
                "direction": "bullish",
                "confirmed": True,
                "invalid_reason": None,
                "pullback_detected": current_price < recent_closes[-2] if len(recent_closes) > 1 else False
            }
        elif is_confirmed_bearish:
            return {
                "is_valid": True,
                "direction": "bearish",
                "confirmed": True,
                "invalid_reason": None,
                "pullback_detected": current_price > recent_closes[-2] if len(recent_closes) > 1 else False
            }
        elif bullish_rejection or wick_only_bullish:
            return {
                "is_valid": False,
                "direction": "bullish",
                "confirmed": False,
                "invalid_reason": "bullish_rejection" if bullish_rejection else "wick_only_bullish",
                "pullback_detected": False
            }
        elif bearish_rejection or wick_only_bearish:
            return {
                "is_valid": False,
                "direction": "bearish",
                "confirmed": False,
                "invalid_reason": "bearish_rejection" if bearish_rejection else "wick_only_bearish",
                "pullback_detected": False
            }
        else:
            return {
                "is_valid": False,
                "direction": None,
                "confirmed": False,
                "invalid_reason": "no_breakout_detected",
                "pullback_detected": False
            }

    def _check_new_structure_needed(self) -> bool:
        """Check if a new structure is needed before allowing re-entry"""
        # Allow re-entry if no previous breakout or if enough bars have passed since last breakout
        if self.last_breakout_direction is None:
            return True

        # In a real implementation, we'd track bar indices, but for now we'll use a simple approach
        # This would be enhanced with actual bar counting in a live system
        return True  # Simplified for this implementation

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal using structure-based breakout logic with clear market hypothesis"""
        if len(self.data_buffer) < max(self.lookback_period, self.consolidation_period, 15):
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {max(self.lookback_period, self.consolidation_period, 15)}")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]

            if len(closes) < max(self.lookback_period, self.consolidation_period, 15):
                self.logger.debug(f"Not enough prices for {self.name}: {len(closes)}")
                return None

            current_price = closes[-1]

            # STEP 1: Define / LATCH the consolidation range (Setup phase).
            # The range must PERSIST so a LATER bar can break it. Recomputing the range
            # every bar created a catch-22 — a real break expands the window and
            # collapses is_defined → 0 breakouts ever. Latch a defined range and test
            # breaks against the STORED range on subsequent bars. The adapter's
            # range_high/range_low/range_broken fields were designed for this but were
            # never wired (dead state). Hypothesis-preserving fix.
            range_info = self._define_range(highs, lows, closes)
            if not hasattr(self, "_latch_age"):
                self._latch_age = 0

            if self.range_high is None:
                # No active range: establish (latch) one if eligible, then WAIT for a break.
                if range_info["is_defined"]:
                    self.range_high = range_info["range_high"]
                    self.range_low = range_info["range_low"]
                    self._latch_compression = range_info["compression_ratio"]
                    self._latch_age = 0
                return None
            # Active latched range: expire it after range_validity_bars, else test the
            # STORED boundaries for a break on this (later) bar.
            self._latch_age += 1
            if self._latch_age > self.range_validity_bars:
                self.range_high = None
                self.range_low = None
                return None
            _span = (self.range_high - self.range_low) if (self.range_high is not None
                     and self.range_low is not None) else 0
            range_info = {"is_defined": True, "range_high": self.range_high,
                          "range_low": self.range_low,
                          "compression_ratio": getattr(self, "_latch_compression", 2.0),
                          "recent_range": _span, "historical_range": _span}

            # STEP 2: use the latched range boundaries
            range_high = range_info["range_high"]
            range_low = range_info["range_low"]

            # Check if we need a new structure before allowing re-entry
            if not self._check_new_structure_needed():
                self.logger.debug(f"New structure needed for {self.name}, skipping breakout analysis")
                return None

            # STEP 3: Validate breakout (Trigger phase)
            breakout_validation = self._validate_breakout(current_price, range_high, range_low, highs, lows, closes)

            if not breakout_validation["is_valid"]:
                # Log invalid breakouts for monitoring
                if breakout_validation["invalid_reason"] in ["bullish_rejection", "bearish_rejection", "wick_only_bullish", "wick_only_bearish"]:
                    self.logger.debug(f"Invalid breakout detected for {self.name}: {breakout_validation['invalid_reason']}")
                return None

            # STEP 4: Determine entry based on pullback or acceptance (Entry phase)
            # Entry should occur on first pullback or acceptance, not on the breakout bar itself
            breakout_direction = breakout_validation["direction"]
            pullback_detected = breakout_validation["pullback_detected"]

            # Calculate momentum to confirm breakout direction
            momentum_period = min(5, len(closes) - 1)
            if momentum_period > 0:
                calculated_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                calculated_momentum = 0

            # Determine signal based on validated breakout with proper entry timing
            final_signal_type = SignalType.HOLD
            final_confidence_factor = self.config.get("default_confidence_factor", 0.3)
            final_score = 0.0

            if breakout_direction == "bullish":
                # For bullish breakouts, we want to enter on pullback to the breakout level or after confirmation
                # Only enter if there's momentum confirmation and proper pullback/acceptance
                if calculated_momentum > 0 and (pullback_detected or current_price > range_high):
                    final_signal_type = SignalType.BUY
                    # Confidence based on compression ratio and momentum
                    strength = (current_price - range_high) / range_high if range_high > 0 else 0
                    final_confidence_factor = min(1.0, (range_info["compression_ratio"] / 10 + abs(calculated_momentum)) / 2)
                    final_score = min(1.0, strength * 10)

                    # Update breakout tracking
                    self.last_breakout_direction = "bullish"
                    self.range_broken = True
                    self.entry_allowed = False  # Prevent re-entry until new structure
            elif breakout_direction == "bearish":
                # For bearish breakouts, we want to enter on pullback to the breakout level or after confirmation
                if calculated_momentum < 0 and (pullback_detected or current_price < range_low):
                    final_signal_type = SignalType.SELL
                    strength = (range_low - current_price) / range_low if range_low > 0 else 0
                    final_confidence_factor = min(1.0, (range_info["compression_ratio"] / 10 + abs(calculated_momentum)) / 2)
                    final_score = max(-1.0, -strength * 10)

                    # Update breakout tracking
                    self.last_breakout_direction = "bearish"
                    self.range_broken = True
                    self.entry_allowed = False  # Prevent re-entry until new structure

            # A confirmed breakout consumes the latched range: clear it so a NEW
            # consolidation must form before the next breakout.
            if final_signal_type != SignalType.HOLD:
                self.range_high = None
                self.range_low = None

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                timestamp=datetime.now(),
                source_layer="StructureBasedBreakout",
                metadata={
                    "range_high": range_high,
                    "range_low": range_low,
                    "current_price": current_price,
                    "breakout_direction": breakout_direction,
                    "compression_ratio": range_info["compression_ratio"],
                    "momentum": calculated_momentum,
                    "recent_range": range_info["recent_range"],
                    "historical_range": range_info["historical_range"],
                    "pullback_detected": pullback_detected,
                    "invalid_breakout_reason": breakout_validation["invalid_reason"],
                    "setup_phase_details": {
                        "range_defined": range_info["is_defined"],
                        "eligibility_criteria_met": True
                    },
                    "trigger_phase_details": {
                        "breakout_validated": breakout_validation["is_valid"],
                        "confirmation_present": breakout_validation["confirmed"]
                    },
                    "entry_phase_details": {
                        "pullback_or_acceptance_present": pullback_detected or (breakout_direction == "bullish" and current_price > range_high) or (breakout_direction == "bearish" and current_price < range_low)
                    }
                }
            )

            # Log signal if generated
            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")
                self.logger.info(f"Range: {range_low:.5f} - {range_high:.5f}, Compression Ratio: {range_info['compression_ratio']:.2f}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None

    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate a fused signal and return execution intent if strategy accepts it.

        This method overrides the base implementation to explicitly control ExecutionIntent
        creation from the strategy level.
        """
        # Check if strategy is enabled before processing
        if not StrategyConfig.get_strategy_enabled(self.name):
            self.logger.debug(f"Strategy {self.name} is disabled, skipping signal evaluation")
            return None

        # Increment bar counter for this symbol to track timing between entries
        symbol = fused_signal.symbol.value
        self.increment_bar_counter(symbol)

        # Check intent discipline rules before proceeding
        should_emit, reason = self._should_emit_intent(fused_signal)
        if not should_emit:
            self.logger.info(f"Strategy {self.name} blocked intent emission for {symbol}: {reason}")
            return None

        # Use the fused signal to determine if we should execute
        # Check signal confidence against strategy threshold
        min_confidence = self.config.get('min_confidence', 0.5)
        confidence = float(fused_signal.confidence.value)

        if confidence < min_confidence:
            self.logger.info(f"Trade rejected: "
                           f"confidence={confidence:.2f} < "
                           f"STRATEGY_MIN_CONFIDENCE_THRESHOLD={min_confidence:.2f} "
                           f"source=crypto_breakout_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return None

        # Determine if we should execute based on the fused signal characteristics
        # For breakout strategy, we need to check if the market conditions align with breakout patterns

        # Determine the side based on fused signal direction and bias
        from domain.entities import OrderSide

        # Check for consistency between direction and dominant bias
        direction_side = None
        if fused_signal.direction > 0.1:  # Threshold to avoid neutral signals
            direction_side = OrderSide.BUY
        elif fused_signal.direction < -0.1:
            direction_side = OrderSide.SELL
        else:
            direction_side = None  # Neutral based on direction

        # Get bias side
        bias_side = None
        if fused_signal.dominant_bias.value in ['BUY', 'LONG']:
            bias_side = OrderSide.BUY
        elif fused_signal.dominant_bias.value in ['SELL', 'SHORT']:
            bias_side = OrderSide.SELL
        else:
            bias_side = OrderSide.BUY if fused_signal.direction >= 0 else OrderSide.SELL  # Default to direction

        # Determine final side based on alignment
        final_side = None
        if direction_side is not None and direction_side == bias_side:
            final_side = direction_side
        elif direction_side is not None:
            # If we have direction but bias differs, use direction but with reduced confidence
            final_side = direction_side
        elif bias_side is not None:
            # If we only have bias, use that
            final_side = bias_side
        else:
            # Both are neutral, don't execute
            return None

        # Calculate risk parameters based on market conditions
        risk_parameters = self._calculate_comprehensive_risk_parameters(fused_signal)

        # Create execution intent with the determined side
        execution_intent = ExecutionIntent(
            symbol=fused_signal.symbol,
            strategy_name=self.get_strategy_name(),
            side=final_side,
            intent_confidence=Percentage(min(Decimal('1.0'),
                                          max(Decimal('0.0'),
                                              fused_signal.confidence.value * Decimal('0.8')))),  # Slightly reduce confidence
            risk_parameters=risk_parameters,
            timestamp=getattr(fused_signal, 'timestamp', None) or datetime.now(),  # E-P5.2: simulated time
            fused_signal=fused_signal,
            metadata={
                'strategy_reasoning': f'Signal aligned with {self.get_strategy_name()} strategy criteria',
                'dominant_bias': fused_signal.dominant_bias.value,
                'regime_context': fused_signal.regime_context,
                'breakout_specific_logic': 'Explicit ExecutionIntent creation from crypto_breakout strategy'
            }
        )

        # Record the intent emission for discipline tracking
        self.record_intent_emission(fused_signal, execution_intent)

        # Generate trade ID for this execution
        trade_id = forensic_logger._generate_trade_id(fused_signal.symbol.value, getattr(fused_signal, 'exchange', 'BINANCE'))

        self.logger.info(f"Strategy {self.name} accepted fused signal for {fused_signal.symbol.value} "
                        f"with intent confidence {float(execution_intent.intent_confidence.value):.2%}")

        # Prepare detailed strategy decision information for forensic logging
        decision_reasons = {
            'fused_signal_direction': fused_signal.direction,
            'fused_signal_dominant_bias': fused_signal.dominant_bias.value if hasattr(fused_signal.dominant_bias, 'value') else str(fused_signal.dominant_bias),
            'fused_signal_regime_context': fused_signal.regime_context,
            'fused_signal_confidence': float(fused_signal.confidence.value),
            'filters_passed': True,  # Would be determined by actual filter checks
            'risk_profile_requested': risk_parameters,
            'selected_strategy': self.get_strategy_name()
        }

        # Identify which fusion outputs were used
        fusion_outputs_used = {
            'regime_context': fused_signal.regime_context,
            'dominant_bias': fused_signal.dominant_bias.value if hasattr(fused_signal.dominant_bias, 'value') else str(fused_signal.dominant_bias),
            'direction': fused_signal.direction,
            'confidence': float(fused_signal.confidence.value),
            'dominance_score': fused_signal.dominance_score
        }

        # Log the strategy decision to forensic log with enhanced details
        forensic_logger.log_strategy_decision(
            strategy=self.name,
            symbol=fused_signal.symbol.value,
            exchange=getattr(fused_signal, 'exchange', 'BINANCE'),
            decision=final_side.name if hasattr(final_side, 'name') else str(final_side),
            confidence=float(execution_intent.intent_confidence.value),
            trade_id=trade_id,
            decision_reasons=decision_reasons,
            fusion_outputs_used=fusion_outputs_used,
            timestamp=execution_intent.timestamp
        )

        # Add trade_id to execution intent metadata
        execution_intent.metadata['trade_id'] = trade_id

        return execution_intent

    def _calculate_comprehensive_risk_parameters(self, fused_signal: FusedSignal) -> Dict[str, Any]:
        """Calculate comprehensive risk parameters based on fused signal and market conditions."""
        # Base risk parameters
        base_risk_params = {
            'max_position_size': self.config.get('max_position_size', 0.05),
            'stop_loss_pct': self.config.get('risk_per_trade', 0.02),  # Use risk per trade as stop loss pct
            'take_profit_pct': self.config.get('risk_per_trade', 0.02) * self.config.get('take_profit_multiplier', 2.0),
            'stop_loss_price': None,  # Will be calculated based on entry price
            'take_profit_price': None,  # Will be calculated based on entry price
            'risk_per_trade': self.config.get('risk_per_trade', 0.02),
            'max_position_exposure': self.config.get('max_position_size', 0.05) * 10000,  # Assuming $10k account
            'position_quantity': 0.0,  # Will be calculated based on account size and risk
        }

        # Adjust risk parameters based on market conditions from fused signal
        regime_context = fused_signal.regime_context.lower()

        # Adjust for different market regimes
        if 'volatile' in regime_context:
            # Reduce position size in volatile markets
            base_risk_params['max_position_size'] *= 0.7
            base_risk_params['stop_loss_pct'] *= 1.2  # Wider stops in volatile markets
        elif 'trend' in regime_context:
            # Slightly increase position size in trending markets
            base_risk_params['max_position_size'] *= 1.1
            base_risk_params['take_profit_pct'] *= 1.1  # Extend targets in trending markets

        # Adjust based on confidence level
        confidence_factor = min(1.5, max(0.5, float(fused_signal.confidence.value) * 2))
        base_risk_params['max_position_size'] *= confidence_factor
        base_risk_params['position_quantity'] = base_risk_params['max_position_size'] * 0.1  # Simplified calc

        # Add risk adjustment factors
        base_risk_params['risk_adjustment_factors'] = {
            'volatility_factor': 1.0,
            'correlation_factor': 1.0,
            'regime_factor': 1.0,
            'market_condition_factor': confidence_factor,
            'position_size_multiplier': confidence_factor,
            'stop_loss_multiplier': self.config.get('stop_loss_multiplier', 1.5),
            'take_profit_multiplier': self.config.get('take_profit_multiplier', 2.0)
        }

        return base_risk_params