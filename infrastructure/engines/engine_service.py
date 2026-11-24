"""
Engine service for processing raw market observations into interpreted signals.
Following the correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
from typing import List, Optional
from domain.entities import MarketObservation, InterpretedSignal
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

            source_watcher = (observation.metadata.get('watcher_name') if observation.metadata else None) \
                or self._guess_watcher(observation)
            role = self.role_of(observation, source_watcher)

            # Create interpreted signal
            interpreted_signal = InterpretedSignal(
                symbol=observation.symbol,
                signal_type=signal_type,
                direction=direction,
                strength=strength,
                confidence=observation.confidence,
                timestamp=observation.timestamp,
                source_watcher=source_watcher,
                metadata={**(observation.metadata or {}), 'observation_type': observation.observation_type,
                          'watcher_name': source_watcher, 'engine_role': role}
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

    @staticmethod
    def _guess_watcher(observation: MarketObservation) -> Optional[str]:
        """Fallback when metadata lacks the watcher name (order matters: 'market_pulse' before 'trend')."""
        o = str(observation.observation_type or '').lower()
        for keys, name in ((('pulse', 'momentum'), 'MarketPulseWatcher'), (('trend',), 'TrendMTFWatcher'),
                           (('volatility',), 'VolatilityWatcher'), (('anomaly',), 'AnomalyMLWatcher'),
                           (('order_flow',), 'OrderFlowWSWatcher'), (('liquidity',), 'LiquidityWatcher'),
                           (('funding',), 'FundingRateWatcher'), (('tick',), 'TickWatcherAdapter'),
                           (('screening', 'cmc'), 'CMCScreener'),
                           (('candle', 'pattern', 'doji', 'engulfing', 'hammer'), 'HistoricalCandleWatcherAdapter')):
            if any(k in o for k in keys):
                return name
        return None

    # E16-U7 (2026-11-24): role-aware translation from the watcher contract. Only DIRECTION-role
    # watchers get a side (from their label, the same rule Fusion uses); regime / positioning /
    # execution observations are NEUTRAL with direction 0 (they were HOLD / "bullish" / contrarian
    # before). The anomaly-reversion and funding-contrarian hypotheses were removed from this layer:
    # anomaly reversion is not supported by data (E18 probe), funding contrarian is untested (E16-U4).
    @staticmethod
    def role_of(observation: MarketObservation, watcher: Optional[str] = None) -> str:
        from infrastructure.fusion.symbol_state_fusion import CLASS_TO_WATCHER, FALLBACK_ROLE
        meta = observation.metadata or {}
        contract = meta.get('contract') if isinstance(meta.get('contract'), dict) else {}
        if contract.get('role'):
            return str(contract['role'])
        key = CLASS_TO_WATCHER.get(watcher or '', watcher or '')
        return FALLBACK_ROLE.get(key, 'direction')

    def _side(self, observation: MarketObservation) -> int:
        from infrastructure.fusion.symbol_state_fusion import _side
        if 'single_candle' in str(observation.observation_type).lower():
            return 0
        meta = observation.metadata or {}
        if self.role_of(observation, meta.get('watcher_name') or self._guess_watcher(observation)) != 'direction':
            return 0
        return _side(str(observation.observation_type))

    def _determine_signal_type(self, observation: MarketObservation):
        """BUY / SELL for a directional observation with a side, otherwise NEUTRAL."""
        from domain.entities import SignalType
        side = self._side(observation)
        return SignalType.BUY if side > 0 else SignalType.SELL if side < 0 else SignalType.NEUTRAL

    def _calculate_direction(self, observation: MarketObservation) -> float:
        """Side of a directional observation (-1 / 0 / +1); magnitude lives in strength/confidence."""
        return float(self._side(observation))

    def _calculate_strength(self, observation: MarketObservation) -> float:
        """Calculate strength based on observation confidence and value"""
        # Strength is based on both the observation value and confidence
        base_strength = float(observation.confidence.value)
        value_factor = min(abs(observation.observation_value), 1.0)  # Cap at 1.0
        
        # Combine confidence and value to determine strength
        strength = base_strength * (0.5 + 0.5 * value_factor)  # Ensure at least 50% of confidence is preserved
        
        return min(strength, 1.0)  # Cap at 1.0


# Module-level singleton retired (E2.T6). The canonical instance is now created
# in bootstrap/container.py (container-scoped). This lazy accessor preserves
# backward compatibility for ``from ... import engine_service`` without
# instantiating at import time. New code should resolve from the container.
_engine_service_singleton = None


def __getattr__(name):
    global _engine_service_singleton
    if name == "engine_service":
        if _engine_service_singleton is None:
            _engine_service_singleton = EngineService()
        return _engine_service_singleton
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")