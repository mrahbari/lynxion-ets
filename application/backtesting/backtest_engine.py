import numpy as np
import pandas as pd
import time

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from infrastructure.strategies.adapters.router import StrategyRouter
from application.backtesting.report import BacktestReport


class BacktestEngine:
    def __init__(self, strategies, risk_config, initial_balance=10000, leverage=10):
        """
        strategies: dict -> {"CB": "CryptoBreakout", "MR": "MeanReversion", ...}
        """
        self.original_strategies = strategies  # Store original strategies for backtesting
        self.router = StrategyRouter()
        for name, strategy in strategies.items():
            self.router.register_strategy(name, strategy)

        self.risk = EnterpriseRiskManager(
            max_portfolio_exposure=risk_config.get('max_portfolio_exposure', 100000),
            max_position_exposure=risk_config.get('max_position_exposure', 50000),
            max_risk_per_trade=risk_config.get('max_risk_per_trade', 0.01),
            max_daily_loss_pct=risk_config.get('max_daily_loss_pct', 0.05),
            max_drawdown_pct=risk_config.get('max_drawdown_pct', 0.15)
        )

        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.leverage = leverage

        self.equity_curve = []
        self.trade_log = []
        self.position = None  # {"side": "long/short", "size":..., "entry":...}
        self.pnl = 0

    def run(self, asset_name, df):
        """
        df must include:
        timestamp, open, high, low, close, volume, features...
        """

        print(f"\n🚀 Running Backtest on {asset_name} ...")

        for i in range(len(df)):
            row = df.iloc[i]

            # 1) Strategy router → signal
            # For backtesting with hexagonal architecture, we need to adapt
            # Get signal from the first strategy directly for now
            signal = 0  # default
            if self.router.strategies:
                # Get first strategy function for backtesting
                first_strategy_name = next(iter(self.router.strategies))
                strategy_func = self.router.strategies[first_strategy_name]

                # Since backtesting strategies might be different objects that expect data rows,
                # we need to handle this differently. The proper approach would be to adapt
                # the strategies to work with hexagonal architecture, but for now
                # we'll call the strategy's get_signal method if it exists
                if hasattr(strategy_func, 'get_signal'):
                    # This handles classic strategy objects
                    signal = strategy_func.get_signal(row)
                elif callable(strategy_func):
                    # This handles the case where strategy is a function
                    # We might need to adapt the strategy to work with hexagonal architecture
                    # Create a mock signal based on the row data
                    from shared.types import Signal, SignalType
                    from datetime import datetime
                    # For now, use a simple approach: get signal from a classic strategy class if available
                    # The most practical approach is to get the first actual strategy object
                    # that has the get_signal method
                    for name, strat in self.original_strategies.items():
                        if hasattr(strat, 'get_signal'):
                            signal = strat.get_signal(row)
                            break

            # 2) Apply risk rules (position size)
            size = self.risk.calculate_position_size(
                entry_price=row["close"],
                stop_loss=row["close"] * 0.99,  # Placeholder stop loss
                portfolio_equity=self.balance
            )

            # 3) Trading Logic (Enter / Exit)
            self._process_signal(signal, size, row)

            # 4) Track Equity
            self.equity_curve.append(self.balance)

        result = BacktestReport(
            balance=self.balance,
            initial=self.initial_balance,
            trades=self.trade_log,
            equity_curve=self.equity_curve
        )

        print(f"🏁 Finished {asset_name}")
        return result

    # ------------------------------
    # INTERNAL TRADE PROCESSOR
    # ------------------------------
    def _process_signal(self, signal, size, row):

        price = row["close"]

        # If we get a "close" signal
        if signal == 0:
            if self.position:
                self._close_position(price, row)
            return

        # If long signal
        if signal == 1:
            if self.position and self.position["side"] == "long":
                return
            if self.position:
                self._close_position(price, row)
            self._open_position("long", size, price, row)

        # If short signal
        if signal == -1:
            if self.position and self.position["side"] == "short":
                return
            if self.position:
                self._close_position(price, row)
            self._open_position("short", size, price, row)

    # ---------------------------
    # OPEN / CLOSE
    # ---------------------------
    def _open_position(self, side, size, price, row):
        # 🛡️ SAFETY FIX: Inject Realistic Fees & Slippage
        fee_pct = 0.001        # 0.1% commission
        slippage_pct = 0.0005  # 0.05% slippage

        # Apply slippage to entry price
        if side == "long":
            executed_price = price * (1 + slippage_pct)
        else:
            executed_price = price * (1 - slippage_pct)

        # Deduct entry fee
        entry_fee = executed_price * size * fee_pct
        self.balance -= entry_fee

        self.position = {
            "side": side,
            "size": size,
            "entry": executed_price,
            "timestamp": row["timestamp"]
        }

        self.trade_log.append({
            "timestamp": row["timestamp"],
            "type": "OPEN",
            "side": side,
            "entry": executed_price,
            "size": size,
            "fee": entry_fee
        })

    def _close_position(self, price, row):
        # 🛡️ SAFETY FIX: Inject Realistic Fees & Slippage
        fee_pct = 0.001        # 0.1% commission
        slippage_pct = 0.0005  # 0.05% slippage

        entry = self.position["entry"]
        side = self.position["side"]
        size = self.position["size"]

        # Apply slippage to exit price
        if side == "long":
            executed_price = price * (1 - slippage_pct)
            gross_pnl = (executed_price - entry) * size
        else:
            executed_price = price * (1 + slippage_pct)
            gross_pnl = (entry - executed_price) * size

        # Deduct exit fee
        exit_fee = executed_price * size * fee_pct
        net_pnl = gross_pnl - exit_fee

        self.balance += gross_pnl - exit_fee
        self.trade_log.append({
            "timestamp": row["timestamp"],
            "type": "CLOSE",
            "side": side,
            "exit": executed_price,
            "pnl": net_pnl,
            "fee": exit_fee
        })

        self.position = None