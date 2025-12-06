import numpy as np
import pandas as pd

class BacktestReport:
    def __init__(self, balance, initial, trades, equity_curve):
        self.balance = balance
        self.initial = initial
        self.trades = trades
        self.equity_curve = equity_curve

    def summary(self):
        df = pd.DataFrame(self.trades)

        df_closed = df[df["type"]=="CLOSE"]

        win_rate = (df_closed["pnl"] > 0).mean() * 100 if len(df_closed)>0 else 0
        pnl = df_closed["pnl"].sum()
        ret = (self.balance - self.initial) / self.initial * 100

        eq = np.array(self.equity_curve)
        dd = np.min(eq - np.maximum.accumulate(eq))

        sharpe = (np.mean(np.diff(eq)) / np.std(np.diff(eq)) * np.sqrt(365)
                  if len(eq) > 10 else 0)

        return {
            "Final Balance": self.balance,
            "PnL": pnl,
            "Return %": ret,
            "Win Rate %": win_rate,
            "Max Drawdown": dd,
            "Sharpe": sharpe,
            "Total Trades": len(df_closed)
        }