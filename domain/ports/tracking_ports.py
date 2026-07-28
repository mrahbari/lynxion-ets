"""Tracking ports for the consolidated tracking system (E3.T5).

Tracking was fragmented across three directories (**P5**):

* ``infrastructure/tracking/trade_tracker.py`` — active-trade lifecycle and
  forensic closure logging.
* ``infrastructure/results_tracking/results_tracker.py`` — hyperopt / backtest
  result persistence (SQLite + JSON).
* ``infrastructure/monitoring/shadow_kpi_monitor.py`` — shadow-deployment KPI
  tracking and alerting.

These three concerns have distinct method surfaces, so — exactly as the risk
module separated portfolio risk from SL/TP (E3.T4) — they are exposed as three
focused ports rather than one flattened interface. A single consolidated
adapter (:class:`infrastructure.tracking.tracking_adapter.ConsolidatedTrackingAdapter`)
implements all three, preserving every tracked-metric value and persistence
format byte-for-byte.
"""
from abc import abstractmethod
from datetime import datetime
from typing import Protocol, Optional, Dict, Any, List


class TradeTrackingPort(Protocol):
    """Active-trade lifecycle tracking with forensic closure logging (E3.T5)."""

    @abstractmethod
    def register_trade(self, trade_id: str, symbol: str, side: str, price: float,
                       quantity: float, sl: float, tp: float, timestamp: datetime,
                       setup_type: Optional[str] = None) -> None:
        """Register a newly opened trade."""
        pass

    @abstractmethod
    def close_trade(self, trade_id: str, exit_price: float, exit_reason: str,
                    exit_timestamp: datetime = None) -> Optional[Dict]:
        """Close a trade, log the closure, and return its PnL/ROI summary."""
        pass


class ResultsTrackingPort(Protocol):
    """Hyperopt / backtest result persistence and retrieval (E3.T5)."""

    @abstractmethod
    def save_hyperopt_result(self, strategy_name: str, symbol: str,
                             parameters: Dict[str, Any], best_value: float,
                             trials_completed: int, optimization_objective: str = None,
                             execution_time: float = None, notes: str = None) -> int:
        """Persist a hyperopt optimization result; return its storage id."""
        pass

    @abstractmethod
    def save_backtest_result(self, strategy_name: str, symbol: str,
                             parameters: Dict[str, Any], total_return: float,
                             sharpe_ratio: float, max_drawdown: float, win_rate: float,
                             total_trades: int, profit_factor: float,
                             execution_time: float = None, notes: str = None) -> int:
        """Persist a backtest result; return its storage id."""
        pass

    @abstractmethod
    def get_hyperopt_results(self, strategy_name: str = None, symbol: str = None,
                             limit: int = None) -> List[Dict[str, Any]]:
        """Retrieve hyperopt results with optional filters."""
        pass

    @abstractmethod
    def get_backtest_results(self, strategy_name: str = None, symbol: str = None,
                             limit: int = None) -> List[Dict[str, Any]]:
        """Retrieve backtest results with optional filters."""
        pass

    @abstractmethod
    def get_best_parameters(self, strategy_name: str, symbol: str,
                            metric: str = "sharpe_ratio") -> Optional[Dict[str, Any]]:
        """Return the best stored parameters for a strategy/symbol by ``metric``."""
        pass


class ShadowKPITrackingPort(Protocol):
    """Shadow-deployment KPI tracking, alerting, and reporting (E3.T5)."""

    @abstractmethod
    def calculate_kpis(self, current_metrics: Dict[str, Any],
                       baseline_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute shadow-deployment KPIs from current vs baseline metrics."""
        pass

    @abstractmethod
    def check_alerts(self, kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return the alerts implied by KPI threshold breaches."""
        pass

    @abstractmethod
    def log_kpis(self, kpis: Dict[str, Any]) -> None:
        """Append KPIs to history and persist."""
        pass

    @abstractmethod
    def log_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Append alerts to history and persist."""
        pass

    @abstractmethod
    def generate_dashboard_report(self) -> Dict[str, Any]:
        """Build the shadow-deployment dashboard report."""
        pass
