"""Consolidated tracking adapter (E3.T5).

A single adapter behind the tracking ports
(:class:`domain.ports.tracking_ports.TradeTrackingPort`,
:class:`~domain.ports.tracking_ports.ResultsTrackingPort`, and
:class:`~domain.ports.tracking_ports.ShadowKPITrackingPort`) that presents the
three previously fragmented tracking subsystems as one tracking system.

Tracked-metric values and persistence formats are preserved **byte-for-byte** by
delegating to the existing canonical implementations:

* ``infrastructure.tracking.trade_tracker.TradeTracker`` — active-trade lifecycle
  + forensic closure logging,
* ``infrastructure.results_tracking.results_tracker.ResultsTracker`` — hyperopt /
  backtest result persistence (SQLite + JSON), and
* ``infrastructure.monitoring.shadow_kpi_monitor.ShadowKPIMonitor`` —
  shadow-deployment KPI tracking + alerting.

Those modules remain importable for existing consumers; physical removal of the
fragmented directories is deferred to E8. This adapter changes no formula,
threshold, schema, or file path — it only unifies access behind one port surface.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List

from domain.ports.tracking_ports import (
    TradeTrackingPort,
    ResultsTrackingPort,
    ShadowKPITrackingPort,
)


class ConsolidatedTrackingAdapter(TradeTrackingPort, ResultsTrackingPort, ShadowKPITrackingPort):
    """Single, container-managed tracking system.

    Delegates to the canonical trade / results / shadow-KPI trackers without
    altering any tracked value or persistence format. Underlying trackers may be
    injected (e.g. the container's configured ``ResultsTracker``); otherwise they
    are constructed lazily on first use with their own defaults, so importing this
    module has no side effects and each container holds its own instances.
    """

    def __init__(self, trade_tracker=None, results_tracker=None, shadow_kpi_monitor=None):
        self._trade_tracker = trade_tracker
        self._results_tracker = results_tracker
        self._shadow_kpi_monitor = shadow_kpi_monitor

    # -- lazy underlying trackers --------------------------------------------------

    def _trades(self):
        if self._trade_tracker is None:
            from infrastructure.tracking.trade_tracker import TradeTracker
            self._trade_tracker = TradeTracker()
        return self._trade_tracker

    def _results(self):
        if self._results_tracker is None:
            from infrastructure.results_tracking.results_tracker import ResultsTracker
            self._results_tracker = ResultsTracker()
        return self._results_tracker

    def _shadow(self):
        if self._shadow_kpi_monitor is None:
            from infrastructure.monitoring.shadow_kpi_monitor import ShadowKPIMonitor
            self._shadow_kpi_monitor = ShadowKPIMonitor()
        return self._shadow_kpi_monitor

    # -- TradeTrackingPort ---------------------------------------------------------

    def register_trade(self, trade_id: str, symbol: str, side: str, price: float,
                       quantity: float, sl: float, tp: float, timestamp: datetime,
                       setup_type: Optional[str] = None) -> None:
        if setup_type is not None:
            return self._trades().register_trade(
                trade_id, symbol, side, price, quantity, sl, tp, timestamp, setup_type
            )
        return self._trades().register_trade(
            trade_id, symbol, side, price, quantity, sl, tp, timestamp
        )

    def close_trade(self, trade_id: str, exit_price: float, exit_reason: str,
                    exit_timestamp: datetime = None) -> Optional[Dict]:
        return self._trades().close_trade(trade_id, exit_price, exit_reason, exit_timestamp)

    # -- ResultsTrackingPort -------------------------------------------------------

    def save_hyperopt_result(self, strategy_name: str, symbol: str,
                             parameters: Dict[str, Any], best_value: float,
                             trials_completed: int, optimization_objective: str = None,
                             execution_time: float = None, notes: str = None) -> int:
        return self._results().save_hyperopt_result(
            strategy_name, symbol, parameters, best_value, trials_completed,
            optimization_objective, execution_time, notes,
        )

    def save_backtest_result(self, strategy_name: str, symbol: str,
                             parameters: Dict[str, Any], total_return: float,
                             sharpe_ratio: float, max_drawdown: float, win_rate: float,
                             total_trades: int, profit_factor: float,
                             execution_time: float = None, notes: str = None) -> int:
        return self._results().save_backtest_result(
            strategy_name, symbol, parameters, total_return, sharpe_ratio,
            max_drawdown, win_rate, total_trades, profit_factor, execution_time, notes,
        )

    def get_hyperopt_results(self, strategy_name: str = None, symbol: str = None,
                             limit: int = None) -> List[Dict[str, Any]]:
        return self._results().get_hyperopt_results(strategy_name, symbol, limit)

    def get_backtest_results(self, strategy_name: str = None, symbol: str = None,
                             limit: int = None) -> List[Dict[str, Any]]:
        return self._results().get_backtest_results(strategy_name, symbol, limit)

    def get_best_parameters(self, strategy_name: str, symbol: str,
                            metric: str = "sharpe_ratio") -> Optional[Dict[str, Any]]:
        return self._results().get_best_parameters(strategy_name, symbol, metric)

    # -- ShadowKPITrackingPort -----------------------------------------------------

    def calculate_kpis(self, current_metrics: Dict[str, Any],
                       baseline_metrics: Dict[str, Any]) -> Dict[str, Any]:
        return self._shadow().calculate_kpis(current_metrics, baseline_metrics)

    def check_alerts(self, kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._shadow().check_alerts(kpis)

    def log_kpis(self, kpis: Dict[str, Any]) -> None:
        return self._shadow().log_kpis(kpis)

    def log_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        return self._shadow().log_alerts(alerts)

    def generate_dashboard_report(self) -> Dict[str, Any]:
        return self._shadow().generate_dashboard_report()
