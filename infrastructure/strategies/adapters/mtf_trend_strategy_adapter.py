"""
Infrastructure implementation of the MTF Trend Strategy following hexagonal architecture.
"""
from typing import Dict, Any, Optional, List
from domain.entities import Signal, SignalType, FusedSignal, ExecutionIntent
from domain.value_objects import Symbol
from datetime import datetime
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class MTFTrendStrategyAdapter(BaseStrategyAdapter):
    """Multi-timeframe trend strategy"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("MTFTrend")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_mtf_trend_config
        system_config = get_mtf_trend_config()

        # Extract and merge config settings
        params = system_config.get('parameters', {})
        top_level = {k: v for k, v in system_config.items() if k != 'parameters'}
        self.config = {**top_level, **params, **(config or {})}

        from infrastructure.market_structure.market_structure_engine import MarketStructureEngine
        from infrastructure.strategies.setup_engine import SetupEngine
        from infrastructure.strategies.decision_pipeline import DecisionPipeline

        self.market_structure_engine = MarketStructureEngine()
        self.setup_engine = SetupEngine()
        self.pipeline = DecisionPipeline()

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate signal using trend following setups."""
        if len(self.data_buffer) < 25:
            return None

        try:
            closes = [float(item['close']) for item in self.data_buffer]
            highs = [float(item.get('high', item['close'])) for item in self.data_buffer]
            lows = [float(item.get('low', item['close'])) for item in self.data_buffer]
            volumes = [float(item.get('volume', 0.0)) for item in self.data_buffer]

            struct = self.market_structure_engine.calculate_market_structure(closes, highs, lows, volumes)
            setups = self.setup_engine.scan_for_setups(
                symbol=symbol,
                prices=closes,
                highs=highs,
                lows=lows,
                val=struct["val"],
                vah=struct["vah"],
                poc=struct["poc"]
            )

            # Filter setups to only match NGTREND_FOLLOW setups
            setup = next((s for s in setups if s.setup_type == "NGTREND_FOLLOW"), None)
            if not setup:
                return None

            latest_bar = self.data_buffer[-1] if self.data_buffer else {}
            if not self._is_setup_fresh(setup, latest_bar):
                return None


            from domain.value_objects import Percentage
            from decimal import Decimal

            signal_type = SignalType.BUY if setup.direction == "BUY" else SignalType.SELL
            return Signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=Percentage(Decimal("0.8")),
                score=1.0 if setup.direction == "BUY" else -1.0,
                timestamp=datetime.now(),
                source_layer="strategy",
                metadata={
                    "setup": setup,
                    "struct": struct
                }
            )

        except Exception:
            return None

    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate fused signal using trend following confirmation and optimization."""
        self.ensure_data_buffer(fused_signal.symbol)
        setup = fused_signal.metadata.get("setup") if fused_signal.metadata else None

        if not self.data_buffer and not setup:
            return None

        if not self.data_buffer and setup:
            trigger_price = float(setup.trigger_price)
            closes = [trigger_price]
            highs = [trigger_price]
            lows = [trigger_price]
            volumes = [0.0]
        else:
            closes = [float(item['close']) for item in self.data_buffer]
            highs = [float(item.get('high', item['close'])) for item in self.data_buffer]
            lows = [float(item.get('low', item['close'])) for item in self.data_buffer]
            volumes = [float(item.get('volume', 0.0)) for item in self.data_buffer]

        if not setup:
            struct = self.market_structure_engine.calculate_market_structure(closes, highs, lows, volumes)
            setups = self.setup_engine.scan_for_setups(
                symbol=fused_signal.symbol,
                prices=closes,
                highs=highs,
                lows=lows,
                val=struct["val"],
                vah=struct["vah"],
                poc=struct["poc"]
            )
            setup = next((s for s in setups if s.setup_type == "NGTREND_FOLLOW"), None)

        if not setup:
            return None

        latest_bar = self.data_buffer[-1] if self.data_buffer else {}
        if not self._is_setup_fresh(setup, latest_bar):
            return None

        current_price = closes[-1]
        max_position_size = float(self.config.get("max_position_size", 0.05))

        return self.pipeline.process_execution_intent(
            setup=setup,
            fused_signal=fused_signal,
            latest_bar=latest_bar,
            current_price=current_price,
            max_position_size=max_position_size,
            strategy_name=self.name
        )

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Verify the regime context is trending."""
        from infrastructure.strategies.strategy_config import StrategyConfig
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        is_trending = 'trend' in fused_signal.regime_context.lower()
        has_direction = abs(fused_signal.direction) > 0.1
        return is_trending and has_direction