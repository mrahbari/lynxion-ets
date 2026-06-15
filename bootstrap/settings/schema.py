"""Typed, frozen, validated aggregate settings schema.

``Settings`` mirrors the current configuration domains exactly by composing the
existing per-domain pydantic schemas. Field names, defaults, types and
validators are therefore preserved by construction (E1.T1 constraint).

The aggregate is frozen (immutable) so settings cannot be mutated after build.
Reusing the existing ``application.configs.schemas`` here is a deliberate,
temporary coupling for the additive extraction step; later E1 tasks relocate
the source of truth and break the Settings <-> Configs cycle.
"""

from pydantic import BaseModel, ConfigDict

from application.configs.schemas.broker import BrokerConfig
from application.configs.schemas.risk import RiskConfig
from application.configs.schemas.strategy import StrategyConfig
from application.configs.schemas.execution import ExecutionConfig
from application.configs.schemas.safety import SafetyConfig
from application.configs.schemas.data import DataConfig
from application.configs.schemas.optimization import OptimizationConfig
from application.configs.schemas.wfo import WFOConfig
from application.configs.schemas.monitoring import MonitoringConfig
from application.configs.schemas.analytics import AnalyticsConfig
from application.configs.schemas.infrastructure import InfrastructureConfig
from application.configs.schemas.position_sizing import PositionSizingConfig
from application.configs.schemas.watcher import WatcherConfig
from application.configs.schemas.portfolio import PortfolioConfig
from application.configs.schemas.backtest import BacktestConfig
from application.configs.schemas.fusion import FusionConfig

# Canonical ordering of configuration domains (matches ``Configs``).
DOMAINS = (
    "broker", "risk", "strategy", "execution", "safety", "data",
    "optimization", "wfo", "monitoring", "analytics", "infrastructure",
    "position_sizing", "watcher", "portfolio", "backtest", "fusion",
)


class Settings(BaseModel):
    """Immutable aggregate of every configuration domain."""

    model_config = ConfigDict(frozen=True)

    broker: BrokerConfig
    risk: RiskConfig
    strategy: StrategyConfig
    execution: ExecutionConfig
    safety: SafetyConfig
    data: DataConfig
    optimization: OptimizationConfig
    wfo: WFOConfig
    monitoring: MonitoringConfig
    analytics: AnalyticsConfig
    infrastructure: InfrastructureConfig
    position_sizing: PositionSizingConfig
    watcher: WatcherConfig
    portfolio: PortfolioConfig
    backtest: BacktestConfig
    fusion: FusionConfig
