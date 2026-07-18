"""Unit tests validating the short position tracking fixes, SL/TP exits, and long/short execution parity."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from infrastructure.backtest.realistic_backtester import RealisticBacktester
from infrastructure.backtest.execution_intent import create_execution_intent, OrderSide

def _generate_mock_data(start_price=100.0, trend="up", num_candles=10):
    """Generate mock candle data for tests."""
    timestamps = [datetime(2023, 11, 1) + timedelta(minutes=i) for i in range(num_candles)]
    data = []
    current_price = start_price
    
    for i in range(num_candles):
        if trend == "up":
            close = current_price + 1.0
            high = close + 0.5
            low = current_price - 0.5
            open_val = current_price
        elif trend == "down":
            close = current_price - 1.0
            high = current_price + 0.5
            low = close - 0.5
            open_val = current_price
        else:  # Flat
            close = current_price
            high = current_price + 0.5
            low = current_price - 0.5
            open_val = current_price
            
        data.append({
            "open": open_val,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1000.0
        })
        current_price = close
        
    df = pd.DataFrame(data, index=timestamps)
    df.index.name = "timestamp"
    return df

@pytest.mark.unit
def test_short_position_sl_hit():
    """Verify that a short position correctly hits its stop-loss."""
    df = _generate_mock_data(start_price=100.0, trend="up", num_candles=10)
    
    # Disable spread and slippage to isolate math
    bt = RealisticBacktester(initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0, spread_bps=0.0, max_fill_ratio=1.0)
    
    def short_strategy(row, params):
        ts = row.name.to_pydatetime()
        if ts == datetime(2023, 11, 1, 0, 1):
            return create_execution_intent(
                side=OrderSide.SELL,
                size=1.0,
                price=101.0,
                timestamp=ts,
                stop_loss=103.0,
                take_profit=95.0,
                strategy_name="rsi_strategy",
                symbol="BTCUSDT"
            )
        return None
        
    metrics = bt.run_backtest(df, short_strategy, strategy_params={"symbol": "BTCUSDT"}, strategy_name="rsi_strategy")
    
    trades = metrics["trades"]
    assert len(trades) == 2
    
    entry_trade = trades[0]
    exit_trade = trades[1]
    
    assert entry_trade["side"] == "sell"
    assert exit_trade["side"] == "buy"
    assert exit_trade["exit_type"] == "SL"
    assert exit_trade["price"] == 103.0
    
    # Expected exit PnL calculation: (entry_price - exit_price) * size - fees
    # entry_price = 101.0, exit_price = 103.0, size = 1.0
    # gross_pnl = (101.0 - 103.0) * 1.0 = -2.0
    # exit_fees = 103.0 * 1.0 * 0.001 = 0.103
    # net_pnl = gross_pnl - exit_fees = -2.0 - 0.103 = -2.103
    assert abs(exit_trade["pnl"] - (-2.103)) < 1e-6
    
    assert len(bt.active_positions) == 0
    assert bt.position == 0

@pytest.mark.unit
def test_short_position_tp_hit():
    """Verify that a short position correctly hits its take-profit."""
    df = _generate_mock_data(start_price=100.0, trend="down", num_candles=10)
    
    # Disable spread and slippage to isolate math
    bt = RealisticBacktester(initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0, spread_bps=0.0, max_fill_ratio=1.0)
    
    def short_strategy(row, params):
        ts = row.name.to_pydatetime()
        if ts == datetime(2023, 11, 1, 0, 1):
            return create_execution_intent(
                side=OrderSide.SELL,
                size=1.0,
                price=99.0,
                timestamp=ts,
                stop_loss=105.0,
                take_profit=97.0,
                strategy_name="rsi_strategy",
                symbol="BTCUSDT"
            )
        return None
        
    metrics = bt.run_backtest(df, short_strategy, strategy_params={"symbol": "BTCUSDT"}, strategy_name="rsi_strategy")
    
    trades = metrics["trades"]
    assert len(trades) == 2
    
    entry_trade = trades[0]
    exit_trade = trades[1]
    
    assert entry_trade["side"] == "sell"
    assert exit_trade["side"] == "buy"
    assert exit_trade["exit_type"] == "TP"
    assert exit_trade["price"] == 97.0
    
    # Expected exit PnL calculation: (entry_price - exit_price) * size - fees
    # entry_price = 99.0, exit_price = 97.0, size = 1.0
    # gross_pnl = (99.0 - 97.0) * 1.0 = +2.0
    # exit_fees = 97.0 * 1.0 * 0.001 = 0.097
    # net_pnl = gross_pnl - exit_fees = 2.0 - 0.097 = 1.903
    assert abs(exit_trade["pnl"] - 1.903) < 1e-6
    
    assert len(bt.active_positions) == 0
    assert bt.position == 0

@pytest.mark.unit
def test_long_short_parity_reversals():
    """Verify long/short execution parity and position reversals."""
    df = _generate_mock_data(start_price=100.0, trend="flat", num_candles=5)
    
    bt = RealisticBacktester(initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0, spread_bps=0.0, max_fill_ratio=1.0)
    
    def reversal_strategy(row, params):
        ts = row.name.to_pydatetime()
        if ts == datetime(2023, 11, 1, 0, 1):
            return create_execution_intent(side=OrderSide.BUY, size=1.0, price=100.0, timestamp=ts, stop_loss=98.0, take_profit=104.0, strategy_name="rsi_strategy", symbol="BTCUSDT")
        elif ts == datetime(2023, 11, 1, 0, 2):
            return create_execution_intent(side=OrderSide.SELL, size=2.0, price=100.0, timestamp=ts, stop_loss=102.0, take_profit=96.0, strategy_name="rsi_strategy", symbol="BTCUSDT")
        elif ts == datetime(2023, 11, 1, 0, 3):
            return create_execution_intent(side=OrderSide.BUY, size=2.0, price=100.0, timestamp=ts, stop_loss=98.0, take_profit=104.0, strategy_name="rsi_strategy", symbol="BTCUSDT")
        return None
        
    metrics = bt.run_backtest(df, reversal_strategy, strategy_params={"symbol": "BTCUSDT"}, strategy_name="rsi_strategy")
    
    trades = metrics["trades"]
    # Reversal intents:
    # 1. Buy 1.0 (long entry)
    # 2. Sell 2.0 (reversal: closes long 1.0, opens short 1.0)
    # 3. Buy 2.0 (reversal: closes short 1.0, opens long 1.0)
    # 4. Force Close (closes long 1.0)
    # Total recorded trade records = 4
    assert len(trades) == 4
    
    assert trades[0]["side"] == "buy"
    assert trades[1]["side"] == "sell"  # Reversal to short
    assert trades[2]["side"] == "buy"   # Reversal to long
    assert trades[3]["side"] == "sell"  # Force close

@pytest.mark.unit
def test_deterministic_reproducibility():
    """Verify that backtest runs are 100% deterministic and reproducible."""
    df = _generate_mock_data(start_price=100.0, trend="up", num_candles=20)
    
    def rsi_like_strategy(row, params):
        ts = row.name.to_pydatetime()
        val = ts.minute % 4
        if val == 1:
            return create_execution_intent(side=OrderSide.BUY, size=0.1, price=row["close"], timestamp=ts, stop_loss=row["close"]*0.99, take_profit=row["close"]*1.02, strategy_name="rsi_strategy", symbol="BTCUSDT")
        elif val == 3:
            return create_execution_intent(side=OrderSide.SELL, size=0.1, price=row["close"], timestamp=ts, stop_loss=row["close"]*1.01, take_profit=row["close"]*0.98, strategy_name="rsi_strategy", symbol="BTCUSDT")
        return None
        
    bt1 = RealisticBacktester(initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005)
    metrics1 = bt1.run_backtest(df, rsi_like_strategy, strategy_params={"symbol": "BTCUSDT"}, strategy_name="rsi_strategy")
    
    bt2 = RealisticBacktester(initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005)
    metrics2 = bt2.run_backtest(df, rsi_like_strategy, strategy_params={"symbol": "BTCUSDT"}, strategy_name="rsi_strategy")
    
    keys = ["total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown", "win_rate", "profit_factor", "total_trades"]
    for k in keys:
        assert metrics1[k] == metrics2[k]
        
    assert len(metrics1["trades"]) == len(metrics2["trades"])
    for t1, t2 in zip(metrics1["trades"], metrics2["trades"]):
        assert t1["side"] == t2["side"]
        assert t1["price"] == t2["price"]
        assert t1["size"] == t2["size"]
        assert t1["pnl"] == t2["pnl"]
