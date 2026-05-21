"""
Engine service for processing raw market observations into interpreted signals.
Following the correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
from typing import List, Optional
from domain.entities.signal_entities import MarketObservation, InterpretedSignal
from domain.value_objects import Symbol, Percentage
from datetime import datetime
from decimal import Decimal


class EngineService:
    """Service to process raw market observations into interpreted signals"""
    
    def __init__(self):
        self.logger = None  # Will be set by the calling component if needed

    def process_observation(self, observation: MarketObservation) -> Optional[InterpretedSignal]:
        """Convert a raw market observation into an interpreted signal"""
        try:
            # Log the incoming observation
            symbol = observation.symbol.value if hasattr(observation.symbol, 'value') else str(observation.symbol)
            if self.logger:
                self.logger.info(f"Engine processing observation: {observation.observation_type} for {symbol}, "
                               f"value: {observation.observation_value:.3f}, "
                               f"confidence: {float(observation.confidence.value):.3f}")

            # Determine signal type based on observation type
            signal_type = self._determine_signal_type(observation)

            # Calculate direction and strength based on observation value and confidence
            direction = self._calculate_direction(observation)
            strength = self._calculate_strength(observation)

            # Create interpreted signal
            interpreted_signal = InterpretedSignal(
                symbol=observation.symbol,
                signal_type=signal_type,
                direction=direction,
                strength=strength,
                confidence=observation.confidence,
                timestamp=observation.timestamp,
                source_watcher=observation.metadata.get('watcher_name') if observation.metadata else None,
                metadata=observation.metadata or {}
            )

            if self.logger:
                self.logger.info(f"Engine processed observation: {observation.observation_type} -> {signal_type.value}, "
                               f"direction: {direction:.3f}, strength: {strength:.3f}, "
                               f"confidence: {float(interpreted_signal.confidence.value):.3f}")

            return interpreted_signal

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing observation in engine: {e}")
            return None

    def _determine_signal_type(self, observation: MarketObservation):
        """Determine signal type based on observation type"""
        from domain.entities.signal_entities import SignalType

        obs_type = observation.observation_type.lower()

        # Handle market pulse observations (e.g., market_pulse_positive, market_pulse_negative)
        if 'market_pulse' in obs_type:
            if 'positive' in obs_type or observation.observation_value > 0.01:  # Lowered threshold from 0.1 to 0.01
                return SignalType.BUY
            elif 'negative' in obs_type or observation.observation_value < -0.01:  # Lowered threshold from -0.1 to -0.01
                return SignalType.SELL
            else:
                return SignalType.NEUTRAL

        # Handle trend observations (e.g., trend_neutral, trend_bullish, trend_bearish)
        elif 'trend' in obs_type:
            if 'bullish' in obs_type or 'positive' in obs_type or observation.observation_value > 0.01:  # Lowered threshold from 0.1 to 0.01
                return SignalType.BUY
            elif 'bearish' in obs_type or 'negative' in obs_type or observation.observation_value < -0.01:  # Lowered threshold from -0.1 to -0.01
                return SignalType.SELL
            else:
                return SignalType.NEUTRAL

        # Handle momentum observations
        elif 'momentum' in obs_type:
            if observation.observation_value > 0.01:  # Lowered threshold from 0.1 to 0.01
                return SignalType.BUY
            elif observation.observation_value < -0.01:  # Lowered threshold from -0.1 to -0.01
                return SignalType.SELL
            else:
                return SignalType.NEUTRAL

        # Handle volatility observations (e.g., volatility_normal, volatility_high, volatility_low)
        elif 'volatility' in obs_type:
            if 'high' in obs_type or 'expansion' in obs_type or observation.observation_value > 0.7:  # High volatility or expansion
                return SignalType.BUY  # Assuming breakout opportunity
            elif 'low' in obs_type or 'compression' in obs_type or 'contraction' in obs_type or observation.observation_value < 0.3:  # Low volatility
                return SignalType.HOLD  # Wait for higher volatility
            else:
                return SignalType.NEUTRAL  # Normal volatility

        # Handle liquidity observations
        elif 'liquidity' in obs_type:
            if observation.observation_value > 0.7:  # High liquidity
                return SignalType.NEUTRAL  # Good for execution but not directional
            else:
                return SignalType.HOLD  # Low liquidity might be risky

        # Handle anomaly observations
        elif 'anomaly' in obs_type:
            if 'positive' in obs_type or observation.observation_value > 0.01:  # Lowered threshold from 0.1 to 0.01
                return SignalType.SELL  # Positive anomaly might revert down
            elif 'negative' in obs_type or observation.observation_value < -0.01:  # Lowered threshold from -0.1 to -0.01
                return SignalType.BUY   # Negative anomaly might revert up
            else:
                return SignalType.NEUTRAL

        # Handle single candle observations (our new observation type)
        elif 'single_candle' in obs_type:
            # For single candle observations, we can't determine direction from just price
            # So we'll return NEUTRAL to indicate we need more data
            return SignalType.NEUTRAL

        # Default to neutral for unknown observation types
        else:
            return SignalType.NEUTRAL

    def _calculate_direction(self, observation: MarketObservation) -> float:
        """Calculate direction based on observation value"""
        # Normalize observation value to range [-1, 1] based on its nature
        obs_value = observation.observation_value

        # For single candle observations, we can't determine direction from absolute price
        # So we'll return 0.0 (neutral) for single candle observations
        if 'single_candle' in observation.observation_type.lower():
            return 0.0

        # For other observation types, normalize to [-1, 1] range
        # This is a simple approach - in a real system, this would be more sophisticated
        # based on the specific observation type and its meaning
        normalized_value = max(-1.0, min(1.0, float(obs_value)))
        return normalized_value

    def _calculate_strength(self, observation: MarketObservation) -> float:
        """Calculate strength based on observation confidence and value"""
        # Strength is based on both the observation value and confidence
        base_strength = float(observation.confidence.value)
        value_factor = min(abs(observation.observation_value), 1.0)  # Cap at 1.0
        
        # Combine confidence and value to determine strength
        strength = base_strength * (0.5 + 0.5 * value_factor)  # Ensure at least 50% of confidence is preserved
        
        return min(strength, 1.0)  # Cap at 1.0


# Global engine service instance
engine_service = EngineService()