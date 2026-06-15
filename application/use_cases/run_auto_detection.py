"""Auto-detection trading use case (E2.T5.3).

Wraps the ``AutoDetectionOrchestrator`` via an injected composition-root factory.
The orchestrator (and the broker/data/execution wiring it depends on) is built by
the container; this use case constructs no infrastructure and contains no
fallback construction.

Behavior is preserved byte-for-byte from the legacy production ``--auto-detect``
CLI branch: the same intro/console output, the same symbol resolution, the same
risk config, the same ``run_auto_detection()`` call and KeyboardInterrupt handling.

Flow: Runner -> CLI -> UseCase -> Port -> Infrastructure.
"""


class RunAutoDetectionUseCase:
    """Drives the auto-detection orchestrator."""

    def __init__(self, orchestrator_factory=None):
        self._orchestrator_factory = orchestrator_factory

    def run(self, symbols_arg=None, symbol_arg=None, comprehensive_logging: bool = False) -> int:
        # Run in auto-detection mode
        print("🚀 Starting auto-detection mode...")
        if symbols_arg or symbol_arg:
            symbol_list = symbols_arg or [symbol_arg]
            print(
                f"📊 System will monitor markets and automatically detect opportunities for symbols: {symbol_list}")
        else:
            print("📊 System will automatically discover and monitor market opportunities across multiple symbols")

        # Determine symbols to monitor
        symbols = []
        if symbols_arg:
            symbols = symbols_arg.split(",")
        elif symbol_arg:
            symbols = [symbol_arg]
        # If no symbols provided in auto-detect mode, the orchestrator will auto-discover them

        # Create risk config
        risk_config = {
            "max_risk": 0.02,
            "atr_multiplier": 1.5,
            "use_dynamic_position": True
        }

        # Create and run auto-detection orchestrator
        auto_detection_orchestrator = self._orchestrator_factory(
            symbols if symbols else None,  # Pass None if no symbols specified
            risk_config,
            comprehensive_logging
        )

        try:
            auto_detection_orchestrator.run_auto_detection()
        except KeyboardInterrupt:
            print("\n🛑 Auto-detection mode stopped by user")
        return 0
