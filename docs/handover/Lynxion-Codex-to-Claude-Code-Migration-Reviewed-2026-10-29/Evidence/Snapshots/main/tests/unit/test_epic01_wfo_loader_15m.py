"""WFO must load an explicit candle frame without writing into its source."""

import pandas as pd
import pytest

from application.walk_forward.wfo_orchestrator import WFOOrchestrator
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter


def test_wfo_requests_explicit_frame_and_retains_datetime_index(tmp_path):
    orchestrator = WFOOrchestrator({
        'data_path': str(tmp_path), 'results_dir': str(tmp_path / 'results'),
        'timeframe': '15m',
    })
    index = pd.date_range('2026-01-01', periods=2, freq='15min', tz='UTC')
    expected = pd.DataFrame({'close': [1.0, 2.0]}, index=index)

    class FakeLoader:
        def load_symbol_data(self, symbol, timeframe):
            assert (symbol, timeframe) == ('BTCUSDT', '15m')
            return expected

        def load(self, *args, **kwargs):
            raise AssertionError('WFO used the default daily/RangeIndex path')

    orchestrator.data_loader = FakeLoader()
    result = orchestrator._load_data(['BTCUSDT'])
    pd.testing.assert_frame_equal(result['BTCUSDT'], expected)


def test_wfo_refuses_implicit_daily_timeframe(tmp_path):
    orchestrator = WFOOrchestrator({
        'data_path': str(tmp_path), 'results_dir': str(tmp_path / 'results')})
    with pytest.raises(ValueError, match='explicit historical timeframe'):
        orchestrator._load_data(['BTCUSDT'])


@pytest.mark.parametrize('failure', ['empty', 'exception'])
def test_wfo_cannot_silently_drop_a_requested_asset(tmp_path, failure):
    orchestrator = WFOOrchestrator({
        'data_path': str(tmp_path), 'results_dir': str(tmp_path / 'results'),
        'timeframe': '15m',
    })
    expected = pd.DataFrame({'close': [1.0, 2.0]},
                            index=pd.date_range('2026-01-01', periods=2, freq='15min', tz='UTC'))

    class FakeLoader:
        def load_symbol_data(self, symbol, timeframe):
            if symbol == 'ETHUSDT':
                if failure == 'exception':
                    raise ValueError('synthetic missing input')
                return pd.DataFrame()
            return expected

    orchestrator.data_loader = FakeLoader()
    with pytest.raises(ValueError, match='requested WFO assets.*ETHUSDT'):
        orchestrator._load_data(['BTCUSDT', 'ETHUSDT'])


def test_wfo_retains_all_successfully_requested_assets(tmp_path):
    orchestrator = WFOOrchestrator({
        'data_path': str(tmp_path), 'results_dir': str(tmp_path / 'results'),
        'timeframe': '15m',
    })
    frames = {s: pd.DataFrame({'close': [i, i + 1]},
              index=pd.date_range('2026-01-01', periods=2, freq='15min', tz='UTC'))
              for i, s in enumerate(('BTCUSDT', 'ETHUSDT'), 1)}

    class FakeLoader:
        def load_symbol_data(self, symbol, timeframe):
            return frames[symbol]

    orchestrator.data_loader = FakeLoader()
    actual = orchestrator._load_data(list(frames))
    assert set(actual) == set(frames)
    for symbol in frames:
        pd.testing.assert_frame_equal(actual[symbol], frames[symbol])


def test_15m_coverage_and_provenance_output_are_separate(tmp_path):
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    times = pd.date_range('2026-01-01', periods=96, freq='15min', tz='UTC')
    pd.DataFrame({
        'timestamp': times.astype('int64') // 10**9,
        'open': [100.0] * 96, 'high': [101.0] * 96,
        'low': [99.0] * 96, 'close': [100.0] * 96,
        'volume': [10.0] * 96,
    }).to_csv(source_dir / 'BTCUSDT.csv', index=False)

    loader = CSVHistoryLoaderAdapter(
        base_path=str(source_dir), provenance_dir=tmp_path / 'results' / 'provenance')
    loaded = loader.load_symbol_data('BTCUSDT', '15m')
    assert len(loaded) == 96
    assert isinstance(loaded.index, pd.DatetimeIndex)
    assert not (source_dir / 'provenance').exists()
    assert (tmp_path / 'results' / 'provenance' / 'BTC-USDT_15m_provenance.json').exists()
