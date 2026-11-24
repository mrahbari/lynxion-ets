"""
Infrastructure implementation of the VWAP Reversal Strategy following hexagonal architecture.
"""
from typing import Dict, Any, Optional, List
from domain.entities import Signal, SignalType, FusedSignal, ExecutionIntent
from domain.value_objects import Symbol
from datetime import datetime
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class VWAPReversalStrategyAdapter(BaseStrategyAdapter):
    """Session-anchored VWAP reversal strategy with mean-reversion regime filtering"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("VWAPReversal")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_vwap_reversal_config
        system_config = get_vwap_reversal_config()

        # Extract and merge config settings
        params = system_config.get('parameters', {})
        top_level = {k: v for k, v in system_config.items() if k != 'parameters'}
        self.config = {**top_level, **params}

        # Merge new global settings from bootstrap/settings
        try:
            from bootstrap.settings.loaders import load_settings
            global_settings = load_settings().strategy
            if global_settings:
                for field in ['atr_period', 'atr_sl_multiplier', 'min_stop_distance_percent', 'min_reward_risk_ratio', 'enable_dynamic_tp', 'reject_low_rr_setup']:
                    if hasattr(global_settings, field):
                        self.config[field] = getattr(global_settings, field)
        except Exception:
            pass

        # Apply constructor overrides
        if config:
            self.config.update(config)

        from infrastructure.market_structure.market_structure_engine import MarketStructureEngine
        from infrastructure.strategies.setup_engine import SetupEngine
        from infrastructure.strategies.decision_pipeline import DecisionPipeline

        self.market_structure_engine = MarketStructureEngine()
        self.setup_engine = SetupEngine()
        self.pipeline = DecisionPipeline()

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate signal using mean reversion setups."""
        sym_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
        if not self._passes_exit_cooldown_check(sym_str):
            return None

        if len(self.data_buffer) < 25:
            return None

        try:
            closes = [float(item['close']) for item in self.data_buffer]
            highs = [float(item.get('high', item['close'])) for item in self.data_buffer]
            lows = [float(item.get('low', item['close'])) for item in self.data_buffer]
            volumes = [float(item.get('volume', 0.0)) for item in self.data_buffer]

            # E16-U10 (2026-11-24): canonical session-VWAP 2-sigma re-entry on closed 15m bars (E21 VR1).
            from infrastructure.strategies.vwap_session import session_vwap_setup, closed_bars
            setup = session_vwap_setup(self.data_buffer, symbol)
            if not setup:
                return None
            done = closed_bars(self.data_buffer)
            struct = {"method": "session_vwap", "vwap": float(setup.take_profit_level)}

            latest_bar = done[-1]


            from infrastructure.strategies.decision_pipeline import calculate_dynamic_metrics
            dyn_conf_float, perf_score_float, risk_adj_score_float = calculate_dynamic_metrics(setup, struct, self.data_buffer)

            from domain.value_objects import Percentage
            from decimal import Decimal

            signal_type = SignalType.BUY if setup.direction == "BUY" else SignalType.SELL
            return Signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=Percentage(Decimal(str(dyn_conf_float))),
                score=1.0 if setup.direction == "BUY" else -1.0,
                timestamp=datetime.now(),
                source_layer="strategy",
                metadata={
                    "setup": setup,
                    "struct": struct,
                    "confidence": dyn_conf_float,
                    "fused_confidence": dyn_conf_float,
                    "performance_score": perf_score_float,
                    "risk_adjusted_score": risk_adj_score_float
                }
            )

        except Exception:
            return None

    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate fused signal using mean reversion confirmation and optimization."""
        sym_str = fused_signal.symbol.value if hasattr(fused_signal.symbol, 'value') else str(fused_signal.symbol)
        if not self._passes_exit_cooldown_check(sym_str):
            return None

        self.ensure_data_buffer(fused_signal.symbol)
        setup = fused_signal.metadata.get("setup") if fused_signal.metadata else None

        closes = [float(item['close']) for item in self.data_buffer]
        highs = [float(item.get('high', item['close'])) for item in self.data_buffer]
        lows = [float(item.get('low', item['close'])) for item in self.data_buffer]
        volumes = [float(item.get('volume', 0.0)) for item in self.data_buffer]

        from infrastructure.strategies.vwap_session import session_vwap_setup, closed_bars, SETUP_TYPE
        if not setup or getattr(setup, "setup_type", None) != SETUP_TYPE:
            setup = session_vwap_setup(self.data_buffer, fused_signal.symbol)
        if not setup:
            return None
        done = closed_bars(self.data_buffer)
        if not done:
            return None
        latest_bar = done[-1]
        closes = [float(x['close']) for x in done]

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
        """Verify the regime context is mean-reverting/ranging/stable."""
        from infrastructure.strategies.strategy_config import StrategyConfig
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        is_reverting = any(term in fused_signal.regime_context.lower() for term in ['mean', 'revert', 'ranging', 'stable'])
        return is_reverting