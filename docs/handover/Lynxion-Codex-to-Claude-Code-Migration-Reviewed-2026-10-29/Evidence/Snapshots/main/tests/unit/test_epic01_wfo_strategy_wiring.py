import pandas as pd
import pytest

from infrastructure.backtest.adapters.walk_forward import WalkForwardAnalyzer


def test_oos_replay_uses_supplied_strategy_and_backtester():
    calls = []
    data = pd.DataFrame({"close": [100, 101]})
    params = {"window": 2}

    def strategy(row, strategy_params):
        return 1

    class FakeBacktester:
        def run_backtest(self, **kwargs):
            calls.append(kwargs)
            return {"total_trades": 1, "sharpe_ratio": 2}

    result = WalkForwardAnalyzer({})._test_on_out_of_sample(
        data, FakeBacktester, params, strategy
    )
    assert result == {"total_trades": 1, "sharpe_ratio": 2}
    assert len(calls) == 1
    assert calls[0]["data"] is data
    assert calls[0]["strategy_function"] is strategy
    assert calls[0]["strategy_params"] is params


def test_oos_replay_fails_closed_without_strategy():
    with pytest.raises(ValueError, match="strategy_function"):
        WalkForwardAnalyzer({})._test_on_out_of_sample(
            pd.DataFrame({"close": [100]}), None, {}
        )


def test_oos_replay_does_not_fabricate_neutral_metrics_on_error():
    class FailingBacktester:
        def run_backtest(self, **kwargs):
            raise RuntimeError("synthetic replay failure")

    with pytest.raises(RuntimeError, match="synthetic replay failure"):
        WalkForwardAnalyzer({})._test_on_out_of_sample(
            pd.DataFrame({"close": [100]}), FailingBacktester, {}, lambda row, params: 0
        )


def test_optimizer_symbol_context_does_not_retry_callback_typeerror():
    analyzer = WalkForwardAnalyzer({'train_size': 40, 'test_size': 10, 'step': 10})
    data = pd.DataFrame({'close': range(51)},
                        index=pd.date_range('2026-01-01', periods=51, freq='h', tz='UTC'))
    calls = []
    def optimizer(train, *, symbol):
        calls.append(symbol)
        raise TypeError('synthetic internal callback error')
    with pytest.raises(TypeError, match='synthetic internal callback error'):
        analyzer.run_walk_forward_analysis(
            {'ETHUSDT': data}, optimizer, strategy_function=lambda row, params: 0,
            optimizer_with_symbol=True)
    assert calls == ['ETHUSDT']
