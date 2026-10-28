"""Historical indicator preparation must not leak future rows or lose time alignment."""

import pandas as pd

from application.use_cases.run_backtest import calculate_indicators_with_shifting, fill_indicator_gaps_causally


def _bars(count):
    index = pd.date_range('2026-01-01', periods=count, freq='15min', tz='UTC')
    close = [100.0 + i * 0.2 for i in range(count)]
    return pd.DataFrame({
        'open': close, 'high': [x + 1 for x in close],
        'low': [x - 1 for x in close], 'close': close,
        'volume': [1000.0] * count,
    }, index=index)


def test_leading_gap_does_not_use_future_indicator():
    index = pd.date_range('2026-01-01', periods=3, freq='15min', tz='UTC')
    frame = pd.DataFrame({'sma_20': [float('nan'), float('nan'), 123.0]}, index=index)
    filled = fill_indicator_gaps_causally(frame)
    assert filled['sma_20'].tolist() == [0.0, 0.0, 123.0]
    assert fill_indicator_gaps_causally(frame.iloc[:2]).equals(filled.iloc[:2])


def test_adx_is_available_and_prefix_invariant_on_datetime_index():
    short = calculate_indicators_with_shifting(_bars(80))
    long = calculate_indicators_with_shifting(_bars(100))
    assert long['adx'].iloc[-1] > 0
    pd.testing.assert_series_equal(short['adx'], long['adx'].iloc[:80])


def test_setup_timestamp_uses_explicit_closed_bar_availability():
    from datetime import datetime, timezone
    from infrastructure.strategies.setup_engine import SetupEngine
    from domain.value_objects import Symbol
    available = datetime(2023, 1, 1, 0, 15, tzinfo=timezone.utc)
    setups = SetupEngine().scan_for_setups(
        symbol=Symbol('BTC-USDT'), prices=[10.0]*20+[10.2],
        highs=[11.0]*20+[11.2], lows=[9.0]*20+[8.5],
        val=8.0, vah=12.0, poc=10.0, available_at=available)
    assert setups
    assert all(s.timestamp.millis == int(available.timestamp()*1000) for s in setups)


def test_setup_rejects_ambiguous_replay_clock():
    import pytest
    from datetime import datetime
    from infrastructure.strategies.setup_engine import SetupEngine
    from domain.value_objects import Symbol
    for value in (datetime(2023, 1, 1), '2023-01-01', 1672531200):
        with pytest.raises(ValueError, match='timezone-aware'):
            SetupEngine().scan_for_setups(Symbol('BTC-USDT'), [], [], [], 8, 12, 10, available_at=value)


def test_legacy_setup_call_keeps_live_clock():
    from datetime import datetime, timezone
    from infrastructure.strategies.setup_engine import SetupEngine
    from domain.value_objects import Symbol
    before = int(datetime.now(timezone.utc).timestamp()*1000)
    setups = SetupEngine().scan_for_setups(
        Symbol('BTC-USDT'), [10.0]*20+[10.2], [11.0]*20+[11.2],
        [9.0]*20+[8.5], 8, 12, 10)
    after = int(datetime.now(timezone.utc).timestamp()*1000)
    assert setups
    assert all(before <= s.timestamp.millis <= after for s in setups)


def test_same_price_cannot_override_stale_setup_timestamp():
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    from datetime import datetime, timezone, timedelta
    tree = ast.parse(Path('infrastructure/strategies/strategy_adapters.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BaseStrategyAdapter')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_is_setup_fresh')
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<actual-freshness>', 'exec'), namespace)
    check = namespace['_is_setup_fresh']
    now = datetime(2023, 1, 1, tzinfo=timezone.utc)
    for delta in (-900, 900):
        setup = SimpleNamespace(trigger_price=100, timestamp=now+timedelta(seconds=delta))
        assert not check(None, setup, {'close':100, 'timestamp':now})
    assert check(None, SimpleNamespace(trigger_price=100, timestamp=now), {'close':100,'timestamp':now})
    assert check(None, SimpleNamespace(trigger_price=100, timestamp=now), {'close':100})
    assert check(None, SimpleNamespace(trigger_price=99, timestamp=now), {'close':100,'timestamp':now})


def test_freshness_compares_absolute_utc_instants():
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    from datetime import datetime, timezone, timedelta
    tree = ast.parse(Path('infrastructure/strategies/strategy_adapters.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BaseStrategyAdapter')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_is_setup_fresh')
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<actual-freshness>', 'exec'), namespace)
    check = namespace['_is_setup_fresh']
    instant = datetime(2023, 1, 1, tzinfo=timezone.utc)
    offset = timezone(timedelta(hours=2))
    setup = SimpleNamespace(trigger_price=100, timestamp=instant)
    assert check(None, setup, {'close':100, 'timestamp':instant.astimezone(offset)})
    assert not check(None, setup, {'close':100, 'timestamp':instant.replace(tzinfo=offset)})
    assert check(None, setup, {'close':100, 'timestamp':instant.timestamp()})
    assert check(None, setup, {'close':100, 'timestamp':int(instant.timestamp()*1000)})
    for ambiguous in (instant.replace(tzinfo=None), float('nan'), float('inf'), True):
        assert not check(None, setup, {'close':100, 'timestamp':ambiguous})


def test_replay_clock_rejects_missing_naive_future_and_nonmonotonic_markers():
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    from datetime import datetime, timezone, timedelta
    import pytest
    tree = ast.parse(Path('infrastructure/strategies/strategy_adapters.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BaseStrategyAdapter')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_replay_clock')
    ns = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<actual-clock>', 'exec'), ns)
    clock = ns['_replay_clock']
    opened = datetime(2023,1,1,tzinfo=timezone.utc)
    available = opened+timedelta(minutes=15)
    valid = {'_replay_available_at':available, '_replay_bar_open_at':opened,
             '_replay_bar_duration_seconds':900, 'timestamp':available}
    assert clock(SimpleNamespace(data_buffer=[valid])) == available
    assert clock(SimpleNamespace(data_buffer=[{'timestamp':opened}])) is None
    for change in ({'_replay_available_at':None}, {'_replay_available_at':available.replace(tzinfo=None)},
                   {'_replay_available_at':available+timedelta(seconds=1)}, {'timestamp':opened}):
        with pytest.raises(ValueError):
            clock(SimpleNamespace(data_buffer=[dict(valid, **change)]))
    for previous in (available, available+timedelta(minutes=15)):
        with pytest.raises(ValueError):
            clock(SimpleNamespace(data_buffer=[{'_replay_available_at':previous}, valid]))


def test_three_strategy_signal_paths_share_replay_setup_clock(monkeypatch):
    import ast, __future__, types, sys
    from pathlib import Path
    from datetime import datetime, timezone, timedelta
    from types import SimpleNamespace
    from domain.value_objects import Symbol
    monkeypatch.setitem(sys.modules, 'infrastructure.strategies.decision_pipeline',
        SimpleNamespace(calculate_dynamic_metrics=lambda *args: (0.7, 1.0, 1.0)))
    clock = datetime(2023,1,1,0,15,tzinfo=timezone.utc)
    for name, family in [('trend_follow','NGTREND_FOLLOW'), ('breakout','NGBREAKOUT'), ('liquidity','NGLS_SWEEP')]:
        tree = ast.parse(Path('infrastructure/strategies/adapters/'+name+'_strategy_adapter.py').read_text())
        cls = next(n for n in tree.body if isinstance(n,ast.ClassDef))
        method = next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='generate_signal')
        captured = []
        def scan(**kwargs):
            captured.append(kwargs.get('available_at'))
            return [SimpleNamespace(setup_type=family, direction='BUY')]
        strategy = SimpleNamespace(data_buffer=[{'close':10,'high':11,'low':9,'volume':1}]*25,
            _passes_exit_cooldown_check=lambda *args:True,
            market_structure_engine=SimpleNamespace(calculate_market_structure=lambda *args:{'val':8,'vah':12,'poc':10}),
            setup_engine=SimpleNamespace(scan_for_setups=scan), _is_setup_fresh=lambda *args:True,
            _replay_clock=lambda:clock)
        ns = {'Signal':lambda **kwargs:SimpleNamespace(**kwargs), 'SignalType':SimpleNamespace(BUY='BUY',SELL='SELL'),
              'datetime':datetime}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<actual-signal>', 'exec', flags=__future__.annotations.compiler_flag), ns)
        signal = ns['generate_signal'](strategy,Symbol('ETH-USDT'))
        assert signal is not None, name
        assert captured == [clock], name
        assert signal.timestamp == clock, name


def test_replay_intent_rejects_wrong_fusion_clock_before_confirmation():
    from infrastructure.strategies.decision_pipeline import DecisionPipeline
    from types import SimpleNamespace
    from datetime import datetime, timezone, timedelta
    from domain.value_objects import ExchangeTimestamp, Symbol
    import pytest
    clock = datetime(2023,1,1,0,15,tzinfo=timezone.utc)
    calls = []
    confirmation = SimpleNamespace(confirm_execution=lambda *args:calls.append(True))
    pipeline = DecisionPipeline(confirmation, SimpleNamespace())
    setup = SimpleNamespace(direction='BUY',timestamp=ExchangeTimestamp(int(clock.timestamp()*1000)))
    bar = {'timestamp':clock, '_replay_available_at':clock,
           '_replay_bar_open_at':clock-timedelta(minutes=15), '_replay_bar_duration_seconds':900}
    for wrong in (None, clock.replace(tzinfo=None), clock-timedelta(seconds=1), clock+timedelta(seconds=1)):
        fused = SimpleNamespace(symbol=Symbol('ETH-USDT'), timestamp=wrong)
        with pytest.raises(ValueError, match='replay'):
            pipeline.process_execution_intent(setup,fused,bar,100,1,'synthetic')
    assert not calls


def test_replay_intent_preserves_causal_clock_and_legacy_fallback():
    from infrastructure.strategies.decision_pipeline import DecisionPipeline
    from types import SimpleNamespace
    from datetime import datetime, timezone, timedelta
    from decimal import Decimal
    from domain.value_objects import ExchangeTimestamp, Symbol
    clock = datetime(2023,1,1,0,15,tzinfo=timezone.utc)
    setup = SimpleNamespace(direction='BUY', timestamp=ExchangeTimestamp(int(clock.timestamp()*1000)),
        trigger_price=Decimal('100'), stop_loss_level=Decimal('98'), take_profit_level=Decimal('103'), setup_type='SYNTHETIC')
    pipeline = DecisionPipeline(SimpleNamespace(confirm_execution=lambda *args:True),
        SimpleNamespace(optimize_order=lambda **kwargs:{'price':100,'time_in_force':'POST_ONLY'}))
    bar = {'timestamp':clock, '_replay_available_at':clock,
           '_replay_bar_open_at':clock-timedelta(minutes=15), '_replay_bar_duration_seconds':900}
    metadata = {'confidence':0.7,'performance_score':1.1,'risk_adjusted_score':1.1}
    fused = SimpleNamespace(symbol=Symbol('ETH-USDT'),timestamp=clock,metadata=metadata)
    intent = pipeline.process_execution_intent(setup,fused,bar,100,1,'synthetic')
    assert intent.timestamp == clock
    assert intent.symbol == fused.symbol
    assert intent.fused_signal is fused
    fused.timestamp = None
    before = datetime.now()
    legacy = pipeline.process_execution_intent(setup,fused,{},100,1,'synthetic')
    assert before <= legacy.timestamp <= datetime.now()
