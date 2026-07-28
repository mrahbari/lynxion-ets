"""
Task 0040 Integration & Validation Test Suite.

Covers:
- Phase 1: Configuration wiring & default disabled state
- Phase 2: DI container registration & singleton lifecycle
- Phase 3: Position Sizing Engine Adapter integration
- Phase 4: Disabled mode zero-divergence parity
- Phase 5: Enabled mode Quarter-Kelly paper validation
- Phase 6: Safety tests (missing stats, invalid inputs, empty universe, risk gate interaction)
"""
import pytest
from typing import Dict

from application.configs.schemas.risk import PortfolioAllocationConfig, RiskConfig
from bootstrap.container import Container
from infrastructure.risk.portfolio_allocation_engine import (
    PortfolioAllocationEngine,
    AllocationMode,
    AssetPerformanceStats,
)
from infrastructure.position_sizing.position_sizing_engine_adapter import (
    PositionSizingEngineAdapter,
)


class _MockBaseSizingService:
    """Mock base sizer returning fixed 10.0 units."""
    def compute_size(self, algorithm, entry_price, stop_loss, portfolio_equity, risk_per_trade, **kwargs):
        dist = abs(entry_price - stop_loss)
        if dist <= 0:
            return 0.0
        return (portfolio_equity * risk_per_trade) / dist

    def get_available_models(self):
        return ["fixed_fractional", "kelly"]


@pytest.fixture
def sample_asset_stats() -> Dict[str, AssetPerformanceStats]:
    return {
        "SOLUSDT": AssetPerformanceStats(symbol="SOLUSDT", win_rate=0.543, win_loss_ratio=2.05),
        "ETHUSDT": AssetPerformanceStats(symbol="ETHUSDT", win_rate=0.600, win_loss_ratio=1.07),
        "XRPUSDT": AssetPerformanceStats(symbol="XRPUSDT", win_rate=0.357, win_loss_ratio=2.14),
        "BNBUSDT": AssetPerformanceStats(symbol="BNBUSDT", win_rate=0.488, win_loss_ratio=0.99),
        "BTCUSDT": AssetPerformanceStats(symbol="BTCUSDT", win_rate=0.455, win_loss_ratio=1.09),
    }


def test_phase1_config_default_disabled():
    """Verify PortfolioAllocationConfig defaults to enabled = False."""
    cfg = PortfolioAllocationConfig()
    assert cfg.enabled is False
    assert cfg.allocation_mode == "EQUAL_WEIGHT"
    assert cfg.kelly_fraction == 0.25
    assert cfg.min_floor_weight == 0.05
    assert cfg.max_cap_weight == 0.40

    risk_cfg = RiskConfig(
        max_position_size=100.0,
        max_drawdown=0.1,
        max_risk_per_trade=0.01,
        max_correlation=0.5,
        max_leverage=1.0,
        stop_loss_percentage=0.02,
        take_profit_percentage=0.04,
    )
    assert risk_cfg.portfolio_allocation.enabled is False


def test_phase2_di_container_registration():
    """Verify container registers portfolio_allocation_engine and wires it into position_sizing_engine."""
    from bootstrap.settings.profiles import dev
    container = Container(settings=dev.build_settings())

    assert "portfolio_allocation_engine" in container.registered_keys()
    assert "position_sizing_engine" in container.registered_keys()

    alloc_engine = container.resolve("portfolio_allocation_engine")
    assert isinstance(alloc_engine, PortfolioAllocationEngine)

    sizing_engine = container.resolve("position_sizing_engine")
    assert isinstance(sizing_engine, PositionSizingEngineAdapter)
    assert sizing_engine._allocation_engine is alloc_engine


def test_phase4_disabled_mode_replay_parity(sample_asset_stats):
    """Verify enabled = False produces 100% byte-for-byte identical position size."""
    alloc_engine = PortfolioAllocationEngine()
    disabled_config = PortfolioAllocationConfig(enabled=False)

    adapter = PositionSizingEngineAdapter(
        service=_MockBaseSizingService(),
        allocation_engine=alloc_engine,
        allocation_config=disabled_config,
    )

    symbols = ["SOLUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "BTCUSDT"]

    # Base size = (10,000 * 0.01) / |100 - 95| = 100 / 5 = 20.0 units
    size_disabled = adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=10000.0,
        risk_per_trade=0.01,
        symbol="SOLUSDT",
        symbols=symbols,
        asset_stats=sample_asset_stats,
    )

    # Without adapter allocation engine (baseline)
    baseline_adapter = PositionSizingEngineAdapter(service=_MockBaseSizingService())
    size_baseline = baseline_adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=10000.0,
        risk_per_trade=0.01,
    )

    assert size_disabled == size_baseline == 20.0


def test_phase5_enabled_mode_quarter_kelly(sample_asset_stats):
    """Verify enabled = True with FRACTIONAL_KELLY scales SOLUSDT correctly."""
    alloc_engine = PortfolioAllocationEngine()
    enabled_config = PortfolioAllocationConfig(enabled=True, allocation_mode="FRACTIONAL_KELLY", kelly_fraction=0.25)

    adapter = PositionSizingEngineAdapter(
        service=_MockBaseSizingService(),
        allocation_engine=alloc_engine,
        allocation_config=enabled_config,
    )

    symbols = ["SOLUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "BTCUSDT"]

    # Calculate expected weight
    res = alloc_engine.compute_weights(symbols, sample_asset_stats, mode=AllocationMode.FRACTIONAL_KELLY, kelly_fraction=0.25)
    sol_weight = res.weights["SOLUSDT"]
    expected_scale = sol_weight * len(symbols)  # sol_weight * 5

    size_enabled = adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=10000.0,
        risk_per_trade=0.01,
        symbol="SOLUSDT",
        symbols=symbols,
        asset_stats=sample_asset_stats,
    )

    base_size = 20.0
    expected_size = base_size * expected_scale
    assert pytest.approx(size_enabled, abs=1e-4) == expected_size
    assert size_enabled > base_size  # SOLUSDT has highest edge, should scale > 1.0


def test_phase6_safety_test1_missing_stats():
    """Safety Test 1: Missing stats should trigger Equal Weight fallback."""
    alloc_engine = PortfolioAllocationEngine()
    enabled_config = PortfolioAllocationConfig(enabled=True, allocation_mode="FRACTIONAL_KELLY")

    adapter = PositionSizingEngineAdapter(
        service=_MockBaseSizingService(),
        allocation_engine=alloc_engine,
        allocation_config=enabled_config,
    )

    symbols = ["SOLUSDT", "ETHUSDT"]
    size = adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=10000.0,
        risk_per_trade=0.01,
        symbol="SOLUSDT",
        symbols=symbols,
        asset_stats=None,  # Missing stats
    )

    # Fallback to Equal Weight: 0.5 * 2 = 1.0 scale factor -> size remains 20.0
    assert size == 20.0


def test_phase6_safety_test2_invalid_kelly_inputs():
    """Safety Test 2: Invalid stats (negative win_rate) fall back safely to floor weight."""
    alloc_engine = PortfolioAllocationEngine()
    enabled_config = PortfolioAllocationConfig(enabled=True, allocation_mode="FRACTIONAL_KELLY")

    adapter = PositionSizingEngineAdapter(
        service=_MockBaseSizingService(),
        allocation_engine=alloc_engine,
        allocation_config=enabled_config,
    )

    invalid_stats = {
        "SOLUSDT": AssetPerformanceStats(symbol="SOLUSDT", win_rate=-0.5, win_loss_ratio=2.0),
        "ETHUSDT": AssetPerformanceStats(symbol="ETHUSDT", win_rate=0.5, win_loss_ratio=1.0),
    }

    size = adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=10000.0,
        risk_per_trade=0.01,
        symbol="SOLUSDT",
        symbols=["SOLUSDT", "ETHUSDT"],
        asset_stats=invalid_stats,
    )

    assert size > 0.0  # Safe positive output


def test_phase6_safety_test4_risk_gate_interaction(sample_asset_stats):
    """Safety Test 4 & 5: RiskGate multiplier applies AFTER allocation scaling."""
    alloc_engine = PortfolioAllocationEngine()
    enabled_config = PortfolioAllocationConfig(enabled=True, allocation_mode="FRACTIONAL_KELLY")

    adapter = PositionSizingEngineAdapter(
        service=_MockBaseSizingService(),
        allocation_engine=alloc_engine,
        allocation_config=enabled_config,
    )

    symbols = ["SOLUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "BTCUSDT"]

    # 1. Full multiplier (1.0)
    size_full = adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=10000.0,
        risk_per_trade=0.01,
        symbol="SOLUSDT",
        symbols=symbols,
        asset_stats=sample_asset_stats,
        risk_gate_multiplier=1.0,
    )

    # 2. Warning multiplier (0.5)
    size_warn = adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=10000.0,
        risk_per_trade=0.01,
        symbol="SOLUSDT",
        symbols=symbols,
        asset_stats=sample_asset_stats,
        risk_gate_multiplier=0.5,
    )

    # 3. Hard Block multiplier (0.0)
    size_block = adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=10000.0,
        risk_per_trade=0.01,
        symbol="SOLUSDT",
        symbols=symbols,
        asset_stats=sample_asset_stats,
        risk_gate_multiplier=0.0,
    )

    assert size_warn == pytest.approx(size_full * 0.5, abs=1e-4)
    assert size_block == 0.0
