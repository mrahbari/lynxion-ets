"""Explicit candle duration separates bar-open identity from signal availability."""

from datetime import timedelta

import pandas as pd
import pytest

from infrastructure.backtest.execution_intent import OrderSide, create_execution_intent
from infrastructure.backtest.realistic_backtester import RealisticBacktester


def test_historical_signal_uses_closed_bar_availability_and_next_open():
    index = pd.date_range('2026-01-01', periods=62, freq='15min', tz='UTC')
    bars = pd.DataFrame({
        'open': [100.0] * 61 + [110.0],
        'high': [101.0] * 61 + [111.0],
        'low': [99.0] * 61 + [109.0],
        'close': [100.0] * 61 + [110.0],
        'volume': [1000.0] * 62,
    }, index=index)
    observed = []

    def strategy(row, _params):
        if row.name != index[60]:
            return None
        observed.append(row['timestamp'])
        assert row['_replay_available_at'] == row['timestamp']
        assert row['_replay_bar_open_at'] == row.name
        assert row['_replay_bar_duration_seconds'] == 900
        return create_execution_intent(
            side=OrderSide.BUY, size=1.0, price=float(row['close']),
            timestamp=row['timestamp'], symbol='BTCUSDT')

    backtester = RealisticBacktester(fee_rate=0, slippage_factor=0,
                                     spread_bps=0, latency_slippage_bps=0)
    result = backtester.run_backtest(
        bars, strategy, {'symbol': 'BTCUSDT', 'bar_duration_seconds': 900})
    entry = next(trade for trade in result['trades'] if trade.get('intent_id'))
    expected_close = index[60] + timedelta(minutes=15)
    assert observed == [expected_close]
    assert pd.Timestamp(entry['signal_timestamp']) == expected_close
    assert pd.Timestamp(entry['timestamp']) == index[61]
    assert entry['price'] == 110.0


def test_maker_only_pipeline_intent_cannot_be_silently_filled_as_market():
    """A maker bid below every future low cannot fill above its limit."""
    from types import SimpleNamespace
    from domain.value_objects import Symbol
    from infrastructure.strategies.setup_engine import SetupEngine
    from infrastructure.strategies.decision_pipeline import DecisionPipeline
    index = pd.date_range('2026-01-01', periods=62, freq='15min', tz='UTC')
    bars = pd.DataFrame({'open':[10.0]*61+[10.25], 'close':[10.0]*60+[10.2,10.25],
        'high':[11.0]*60+[11.2,10.3], 'low':[9.0]*60+[8.5,10.2],
        'volume':[1000.0]*62}, index=index)
    engine, pipeline = SetupEngine(), DecisionPipeline()
    observed = []
    def strategy(row, params):
        if row.name != index[60]: return None
        available = row['_replay_available_at']
        setup = next(s for s in engine.scan_for_setups(
            Symbol('ETH-USDT'), [10.0]*24+[10.2], [11.0]*24+[11.2],
            [9.0]*24+[8.5], 8,12,10, available_at=available) if s.setup_type=='NGLS_SWEEP')
        fused = SimpleNamespace(symbol=setup.symbol, timestamp=available,
            metadata={'confidence':0.7,'performance_score':1.1,'risk_adjusted_score':1.1})
        # Explicit synthetic microstructure values; no default observations used.
        latest = row.to_dict()
        latest.update(obi_ratio=0.2, cvd=1.0, best_bid=10.199, best_ask=10.201)
        intent = pipeline.process_execution_intent(setup,fused,latest,10.2,0.1,'synthetic')
        assert intent is not None
        assert setup.timestamp.to_datetime() == available == intent.timestamp
        assert intent.symbol == setup.symbol
        observed.append(intent)
        return intent
    backtester = RealisticBacktester(fee_rate=0,slippage_factor=0,spread_bps=0,latency_slippage_bps=0)
    with pytest.raises(ValueError, match='maker|limit|time.in.force'):
        backtester.run_backtest(bars,strategy,{'symbol':'ETH-USDT','bar_duration_seconds':900})
    assert len(observed)==1
    assert observed[0].risk_parameters['limit_price'] == 10.199
    assert observed[0].risk_parameters['time_in_force'] == 'POST_ONLY'
    assert not backtester.trades


def test_unsupported_order_fields_reject_before_risk_container_lookup(monkeypatch):
    import sys
    from types import SimpleNamespace
    calls=[]
    monkeypatch.setitem(sys.modules,'application.containers.container',
        SimpleNamespace(container=SimpleNamespace(resolve=lambda *args:calls.append(True))))
    backtester=RealisticBacktester()
    for risk in ({'limit_price':100}, {'time_in_force':'POST_ONLY'}, {'order_type':'LIMIT'}):
        with pytest.raises(ValueError,match='unsupported'):
            backtester._adapt_domain_execution_intent(SimpleNamespace(risk_parameters=risk),pd.Series({'close':100}))
    assert not calls


def test_overlapping_bar_cannot_fill_before_signal_is_available():
    index = pd.date_range('2026-01-01', periods=62, freq='10min', tz='UTC')
    bars = pd.DataFrame({
        'open': [100.0] * 62, 'high': [101.0] * 62,
        'low': [99.0] * 62, 'close': [100.0] * 62,
        'volume': [1000.0] * 62,
    }, index=index)

    def strategy(row, _params):
        if row.name != index[60]:
            return None
        return create_execution_intent(
            side=OrderSide.BUY, size=1.0, price=100.0,
            timestamp=row['timestamp'], symbol='BTCUSDT')

    backtester = RealisticBacktester(fee_rate=0, slippage_factor=0)
    with pytest.raises(ValueError, match='not available'):
        backtester.run_backtest(
            bars, strategy, {'symbol': 'BTCUSDT', 'bar_duration_seconds': 900})


def test_backdated_strategy_intent_is_rejected():
    index = pd.date_range('2026-01-01', periods=62, freq='15min', tz='UTC')
    bars = pd.DataFrame({
        'open': [100.0] * 62, 'high': [101.0] * 62,
        'low': [99.0] * 62, 'close': [100.0] * 62,
        'volume': [1000.0] * 62,
    }, index=index)

    def strategy(row, _params):
        if row.name != index[60]:
            return None
        return create_execution_intent(
            side=OrderSide.BUY, size=1.0, price=100.0,
            timestamp=row.name.to_pydatetime(), symbol='BTCUSDT')

    with pytest.raises(ValueError, match='signal availability'):
        RealisticBacktester().run_backtest(
            bars, strategy, {'symbol': 'BTCUSDT', 'bar_duration_seconds': 900})


@pytest.mark.parametrize('duration', [0, -1, float('nan'), '900'])
def test_invalid_bar_duration_is_rejected(duration):
    backtester = RealisticBacktester()
    with pytest.raises(ValueError, match='bar_duration_seconds'):
        backtester.run_backtest(pd.DataFrame(), lambda *_: None,
                                {'bar_duration_seconds': duration})
