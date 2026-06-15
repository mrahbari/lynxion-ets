"""Non-production trading-mode use cases (E2.T5.2).

Owns the orchestration for the live runner's NON-production CLI modes that
previously lived inline in ``run_trading_system.py``:

* ``config-test`` — import/instantiate a logger and report success.
* ``backtest``    — run a backtest through the injected backtest pipeline.
* ``optimize``    — run hyperopt optimization through injected optimizer ports.
* ``retune``      — run auto-retune through the injected optimizer factory.
* ``monitor``     — the simple monitoring loop.

All infrastructure is supplied through injected composition-root factories; this
module never imports the ``infrastructure`` package nor constructs adapters /
services directly, and contains no fallback construction. The orchestration
(date math, symbol formatting, sample-data generation, console output, loop
structure) is preserved byte-identically from the legacy runner.

Production + auto-detect modes are intentionally OUT OF SCOPE (E2.T5.3).

Flow: Runner -> CLI -> UseCase -> Port -> Infrastructure.
"""

import sys
from datetime import datetime, timedelta


class TradingModesUseCase:
    """Application use case for the five non-production trading-system modes.

    Heavy collaborators (backtest pipeline, hyperopt optimizer, auto-retune
    optimizer) are built by injected composition-root factories, so the use case
    holds no infrastructure imports and constructs nothing itself.
    """

    def __init__(self,
                 backtest_use_case_factory=None,
                 hyperopt_config_factory=None,
                 hyperopt_optimizer_factory=None,
                 auto_retune_optimizer_factory=None):
        self._backtest_use_case_factory = backtest_use_case_factory
        self._hyperopt_config_factory = hyperopt_config_factory
        self._hyperopt_optimizer_factory = hyperopt_optimizer_factory
        self._auto_retune_optimizer_factory = auto_retune_optimizer_factory

    # -- config-test ---------------------------------------------------------------

    def run_config_test(self) -> int:
        print("🔧 Testing configuration...")
        # Test that we can import and instantiate key components
        try:
            from shared.logger import EnhancedLogger

            logger = EnhancedLogger("ConfigTest")
            logger.info("Configuration test passed!")
            print("✅ Configuration test completed successfully")
            return 0
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
            return 1

    # -- backtest ------------------------------------------------------------------

    def run_backtest(self, strategy: str, symbol, days_back: int) -> int:
        print(f"📊 Running backtest for strategy: {strategy}, symbol: {symbol}")

        from domain.value_objects.money import Symbol

        # Set up dates for backtesting
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # Backtest pipeline (risk manager + adapters + service + use case) is built
        # by the composition root and injected here.
        backtest_use_case = self._backtest_use_case_factory(strategy)

        # Run backtest - convert symbol format from BTC/USDT to BTCUSDT
        raw_symbol = symbol if symbol else "BTC/USDT"
        formatted_symbol = raw_symbol.replace("/", "")  # Convert BTC/USDT to BTCUSDT
        symbol_obj = Symbol(formatted_symbol)
        results = backtest_use_case.execute(
            symbol=symbol_obj,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10000,
            strategy_name=strategy
        )

        print(f"✅ Backtest completed!")
        print(f"📈 Results: Total Return = {results.get('total_return', 0):.2%}, "
              f"Win Rate = {results.get('win_rate', 0):.2%}, "
              f"Total Trades = {results.get('total_trades', 0)}")
        return 0

    # -- optimize ------------------------------------------------------------------

    def run_optimize(self, strategy: str, symbol, max_evals: int) -> int:
        print(f"⚙️ Running optimization for strategy: {strategy}, symbol: {symbol}")

        import pandas as pd
        import numpy as np

        # Set up optimization (config + optimizer built by injected factories)
        config = self._hyperopt_config_factory(strategy)
        optimizer = self._hyperopt_optimizer_factory(config, strategy)

        # Generate sample data for optimization (in a real system, this would come from data provider)
        print("📊 Generating sample data for optimization...")
        timestamps = pd.date_range(start='2023-01-01', periods=500, freq='1h')
        prices = 30000 + np.cumsum(np.random.randn(500) * 100)  # Simulated BTC prices
        sample_data = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices + np.random.randn(500) * 5,
            'high': prices + abs(np.random.randn(500)) * 10,
            'low': prices - abs(np.random.randn(500)) * 10,
            'close': prices,
            'volume': np.abs(np.random.randn(500)) * 500,
            'volatility': np.abs(np.random.randn(500)) * 5
        })

        # Run optimization
        symbol = symbol if symbol else "BTCUSDT"
        results = optimizer.optimize_with_config(
            strategy_name=strategy,
            data=sample_data,
            symbol=symbol,
            custom_config={"max_evals": max_evals}
        )

        print(f"✅ Optimization completed!")
        print(f"📊 Best parameters: {results.get('best_params', {})}")
        print(
            f"🏆 Best score: {results.get('best_value', 0) if 'best_value' in results else results.get('best_loss', 'N/A')}")
        return 0

    # -- retune --------------------------------------------------------------------

    def run_retune(self, strategy: str, symbol, symbols) -> int:
        print(f"🔄 Running auto-retune for strategy: {strategy}")

        symbol_list = symbols.split(",") if symbols else [symbol if symbol else "BTC/USDT"]

        auto_retune = self._auto_retune_optimizer_factory(strategy, -5.0)

        # Run auto-retune for each symbol
        for sym in symbol_list:
            result = auto_retune.run_auto_retune(
                strategy_name=strategy,
                symbols=[sym],
                risk_config={"atr_multiplier": 1.5, "use_dynamic_position": True}
            )
            print(f"✅ Auto-retune completed for {sym}")

        print("✅ All auto-retune processes completed!")
        return 0

    # -- monitor -------------------------------------------------------------------

    def run_monitor(self) -> int:
        print("📊 Starting monitoring mode...")
        print("Note: In a full implementation, this would connect to live data sources and monitor performance")
        # For now, just simulate monitoring
        import time
        import random

        while True:
            try:
                print(f"📈 Monitoring system: Portfolio value = ${10000 + random.randint(-500, 500):.2f}")
                time.sleep(5)  # Update every 5 seconds
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                break
        return 0
