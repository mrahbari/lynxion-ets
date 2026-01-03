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
                               f"strength: {strength:.2f}, confidence: {float(interpreted_signal.confidence.value):.2%}")
            
            return interpreted_signal
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing observation in engine: {e}")
            return None

    def _determine_signal_type(self, observation: MarketObservation):
        """Determine signal type based on observation type"""
        from domain.entities.signal_entities import SignalType
        
        obs_type = observation.observation_type.lower()
        
        if 'momentum' in obs_type or 'trend' in obs_type:
            # For positive momentum/trend observations
            if observation.observation_value > 0:
                return SignalType.BUY
            else:
                return SignalType.SELL
        elif 'volatility' in obs_type:
            # High volatility could indicate breakout opportunities
            if observation.observation_value > 0.5:  # threshold for high volatility
                return SignalType.BUY  # Assuming breakout to the upside
            else:
                return SignalType.NEUTRAL
        elif 'liquidity' in obs_type:
            # High liquidity could indicate good entry/exit opportunities
            if observation.observation_value > 0.7:  # threshold for high liquidity
                return SignalType.NEUTRAL  # High liquidity is generally neutral but good for execution
            else:
                return SignalType.HOLD  # Low liquidity might be risky
        elif 'anomaly' in obs_type:
            # Anomalies might indicate mean reversion opportunities
            if observation.observation_value > 0:
                return SignalType.SELL  # If value is high, might revert down
            else:
                return SignalType.BUY   # If value is low, might revert up
        else:
            # Default to neutral for unknown observation types
            return SignalType.NEUTRAL

    def _calculate_direction(self, observation: MarketObservation) -> float:
        """Calculate direction based on observation value"""
        # Normalize observation value to range [-1, 1] based on its nature
        # For now, we'll use a simple approach
        obs_value = observation.observation_value
        
        # Clamp to reasonable range and normalize
        if obs_value > 1.0:
            return 1.0
        elif obs_value < -1.0:
            return -1.0
        else:
            return float(obs_value)

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