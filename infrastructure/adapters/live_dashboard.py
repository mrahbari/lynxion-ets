"""Live dashboard following hexagonal architecture."""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
import json
import threading
import time
import os
from pathlib import Path
from typing import Dict, Any

from shared.logger import EnhancedLogger
from domain.ports.data_ports import DataProviderPort
from domain.ports.portfolio_ports import PortfolioManagementPort


class LiveDashboardAdapter:
    """Dashboard adapter following hexagonal architecture."""

    def __init__(self,
                 market_data_repo: DataProviderPort,
                 portfolio_service: PortfolioManagementPort,
                 best_params_file: str = "data/best_params_live.json",
                 trades_log_file: str = "data/live_trades.json",
                 equity_curve_file: str = "data/equity_curve.json"):
        self.market_data_repo = market_data_repo
        self.portfolio_service = portfolio_service
        self.best_params_file = Path(best_params_file)
        self.trades_log_file = Path(trades_log_file)
        self.equity_curve_file = Path(equity_curve_file)
        self.logger = EnhancedLogger("LiveDashboardAdapter")

        # Create directories if they don't exist
        self.best_params_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize Dash app
        self.app = dash.Dash(__name__)
        self.app.layout = self._create_layout()

        # Register callbacks
        self._register_callbacks()

    def _create_layout(self):
        """Create the dashboard layout."""
        return html.Div([
            html.H2("💹 Hedge-Fund Live Dashboard"),
            dcc.Interval(id='interval-component', interval=5000, n_intervals=0),
            html.Div(id='metrics-div'),
            dcc.Graph(id='equity-curve-graph'),
            dcc.Graph(id='trades-log-graph')
        ])

    def _register_callbacks(self):
        """Register dashboard callbacks."""
        @self.app.callback(
            [Output('metrics-div', 'children'),
             Output('equity-curve-graph', 'figure'),
             Output('trades-log-graph', 'figure')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            try:
                equity_data = self._load_json(self.equity_curve_file)
                trades_data = self._load_json(self.trades_log_file)

                # Equity Curve Graph
                eq_fig = go.Figure()
                for asset, curve in equity_data.items():
                    eq_fig.add_trace(go.Scatter(y=curve, mode='lines', name=asset))
                eq_fig.update_layout(title="Equity Curve", xaxis_title="Time", yaxis_title="Balance")

                # Trades Log Graph
                trades_fig = go.Figure()
                for asset, trades in trades_data.items():
                    for trade in trades:
                        color = "green" if trade.get("pnl", 0) > 0 else "red"
                        trades_fig.add_trace(go.Scatter(
                            x=[trade["timestamp"]],
                            y=[trade.get("entry", trade.get("exit", 0))],
                            mode='markers',
                            marker=dict(color=color, size=10),
                            name=f"{asset} {trade['side']}"
                        ))
                trades_fig.update_layout(title="Trade Log", xaxis_title="Time", yaxis_title="Price")

                # Metrics
                metrics_div = []
                for asset, trades in trades_data.items():
                    if trades:  # Check if trades exist
                        df = pd.DataFrame(trades)
                        df_closed = df[df["type"]=="CLOSE"]
                        pnl = df_closed["pnl"].sum() if not df_closed.empty else 0
                        win_rate = (df_closed["pnl"]>0).mean()*100 if not df_closed.empty else 0
                        metrics_div.append(html.P(f"{asset} | PnL: {pnl:.2f} | WinRate: {win_rate:.2f}%"))

                return metrics_div, eq_fig, trades_fig
            except Exception as e:
                self.logger.error(f"Error updating dashboard: {e}")
                return [], go.Figure(), go.Figure()

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON data from file."""
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # Create empty file if it doesn't exist
            self._create_empty_file(file_path)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {e}")
            return {}

    def _create_empty_file(self, file_path: Path):
        """Create an empty JSON file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump({}, f)
        except Exception as e:
            self.logger.error(f"Error creating {file_path}: {e}")

    def run_dashboard(self, debug: bool = False, port: int = 8050):
        """Run the dashboard server."""
        self.logger.info(f"Starting dashboard server on port {port}")
        self.app.run(debug=debug, port=port, host='0.0.0.0')

    def start_dashboard_thread(self):
        """Start dashboard in a separate thread."""
        thread = threading.Thread(target=self.run_dashboard)
        thread.daemon = True
        thread.start()
        return thread


# Helper functions for backward compatibility
def load_json(file):
    """Helper function for backward compatibility."""
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}


def run_dashboard():
    """Standalone dashboard runner."""
    from domain.ports.data_ports import DataProviderPort
    from domain.ports.portfolio_ports import PortfolioManagementPort

    # Create mock implementations for standalone usage
    class MockMarketDataRepository(DataProviderPort):
        def get_current_price(self, symbol):
            return 100.0  # Mock price

        def get_historical_data(self, symbol, period, timeframe='1m'):
            import pandas as pd
            import numpy as np
            dates = pd.date_range(start='2023-01-01', periods=10, freq='H')
            return pd.DataFrame({
                'timestamp': dates,
                'open': np.random.rand(10)*10+100,
                'high': np.random.rand(10)*10+100,
                'low': np.random.rand(10)*10+100,
                'close': np.random.rand(10)*10+100,
                'volume': np.random.rand(10)*1000
            })

        def subscribe_to_market_data(self, symbol, callback):
            return "subscription_id"

        def unsubscribe_from_market_data(self, subscription_id: str):
            pass

    class MockPortfolioService(PortfolioManagementPort):
        def calculate_allocation(self, total_capital: float, symbols):
            from domain.value_objects import Symbol, Percentage
            return {Symbol('BTC-USDT'): total_capital/len(symbols) if symbols else 0}

        def rebalance_portfolio(self, target_allocations):
            return []

        def get_portfolio_metrics(self):
            return {"sharpe_ratio": 1.0, "max_drawdown": -0.05, "total_return": 0.1}

    # Create dashboard adapter
    dashboard = LiveDashboardAdapter(
        market_data_repo=MockMarketDataRepository(),
        portfolio_service=MockPortfolioService()
    )

    # Run the dashboard
    dashboard.run_dashboard(debug=False, port=8050)


def start_dashboard_thread():
    """Start dashboard thread for backward compatibility."""
    thread = threading.Thread(target=run_dashboard)
    thread.daemon = True
    thread.start()
    return thread


if __name__ == "__main__":
    run_dashboard()