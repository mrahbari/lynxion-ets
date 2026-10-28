"""Live (production) trading use case (E2.T5.3).

Wraps the ``ProductionTradingOrchestrator`` lifecycle (build -> initialize ->
run) using an injected composition-root factory. The orchestrator (and the
broker/data/execution/dashboard wiring it depends on) is built by the container;
this use case constructs no infrastructure and contains no fallback construction.

Behavior is preserved byte-for-byte from the legacy ``run_production_orchestrator``
+ the production CLI branch: the same sample data fetcher, the same risk config,
the same console output, the same ``initialize_system()`` then
``run_production_trading(...)`` sequence.

Flow: Runner -> CLI -> UseCase -> Port -> Infrastructure.
"""


class RunLiveTradingUseCase:
    """Drives the production trading orchestrator's lifecycle."""

    def __init__(self, orchestrator_factory=None):
        self._orchestrator_factory = orchestrator_factory

    def run(self, strategy_name: str = "crypto_breakout", symbol=None) -> int:
        # Run in original production mode with manual strategy selection
        def sample_data_fetcher():
            """Sample data fetcher for testing."""
            import pandas as pd
            import numpy as np
            timestamps = pd.date_range(start='2023-01-01', periods=100, freq='1min')
            prices = 2000 + np.cumsum(np.random.randn(100) * 0.1)
            df = pd.DataFrame({
                'timestamp': timestamps,
                'open': prices + np.random.randn(100) * 0.05,
                'high': prices + abs(np.random.randn(100)) * 0.1,
                'low': prices - abs(np.random.randn(100)) * 0.1,
                'close': prices,
                'volume': np.abs(np.random.randn(100)) * 100,
                'volatility': np.abs(np.random.randn(100)) * 0.1
            })
            # Return data for the specified symbol if provided
            symbol_key = symbol if symbol else "BTCUSD"
            return {symbol_key: df}

        risk_config = {
            "max_risk": 0.02,
            "atr_multiplier": 1.5,
            "use_dynamic_position": True
        }

        print("📊 Running production orchestrator with sample data...")

        orchestrator = self._orchestrator_factory()
        orchestrator.initialize_system()
        orchestrator.run_production_trading(
            data_fetcher=sample_data_fetcher,
            strategy_name=strategy_name,
            risk_config=risk_config
        )
        return 0
