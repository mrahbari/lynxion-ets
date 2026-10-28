"""Wiring and state-isolation fixtures; backtest/optimizer calls are synthetic fakes."""

import pytest
import numpy as np
import pandas as pd
from types import SimpleNamespace
from infrastructure.optimization import hyperopt_objective as objective_module

from application.walk_forward import hyperopt_adapter as module
from infrastructure.optimization.hyperopt_objective import HyperoptObjective


def test_unsupported_maker_domain_intent_is_failed_trial_not_zero_performance():
    from hyperopt import STATUS_FAIL
    index = pd.date_range('2026-01-01',periods=62,freq='15min',tz='UTC')
    bars = pd.DataFrame({'open':[100.0]*62,'close':[100.0]*62,
        'high':[101.0]*62,'low':[99.0]*62,'volume':[1000.0]*62},index=index)
    def strategy(row, params):
        if row.name == index[60]:
            return SimpleNamespace(risk_parameters={'limit_price':99.0,'time_in_force':'POST_ONLY'})
        return None
    result = HyperoptObjective().create_objective_function({'ETH-USDT':bars},{},strategy)({})
    assert result['status'] == STATUS_FAIL
    assert result['loss'] == float('inf')


def test_instance_wrapper_preserves_explicit_replay_clock_markers(monkeypatch):
    from datetime import datetime, timezone, timedelta
    observed = []
    class Strategy:
        def update_with_market_data(self, data):
            observed.append(data)
        def generate_signal(self, symbol):
            return None
    class Backtester:
        def __init__(self, **kwargs): pass
        def run_backtest(self, data, strategy_function, strategy_params):
            for _, row in data.iterrows(): strategy_function(row, strategy_params)
            return {'sharpe_ratio':0.0}
    opened = datetime(2023,1,1,tzinfo=timezone.utc)
    rows = []
    for i in range(2):
        start = opened+timedelta(minutes=15*i)
        close = start+timedelta(minutes=15)
        rows.append({'close':1.0,'timestamp':close,'_replay_available_at':close,
                     '_replay_bar_open_at':start,'_replay_bar_duration_seconds':900})
    monkeypatch.setattr(objective_module,'RealisticBacktester',Backtester)
    result = HyperoptObjective().create_objective_function({'ETH-USDT':pd.DataFrame(rows)}, {}, Strategy())({})
    assert result['status']=='ok'
    assert len(observed)==2
    for actual, expected in zip(observed,rows):
        for key in ('timestamp','_replay_available_at','_replay_bar_open_at','_replay_bar_duration_seconds'):
            assert actual[key]==expected[key]


def test_factory_supplies_each_asset_identity_to_strategy(monkeypatch):
    observed = []
    class Strategy:
        def update_with_market_data(self, data):
            pass
        def generate_signal(self, symbol):
            observed.append(symbol.value)
            return None
    class Backtester:
        def __init__(self, **kwargs):
            pass
        def run_backtest(self, data, strategy_function, strategy_params):
            for _, row in data.iterrows():
                strategy_function(row, strategy_params)
            return {"sharpe_ratio": 0.0}
    monkeypatch.setattr(objective_module, "RealisticBacktester", Backtester)
    frame = pd.DataFrame({"close": [1.0, 1.0]})
    result = HyperoptObjective().create_objective_function(
        {"ETH-USDT": frame, "SOL-USDT": frame}, {}, Strategy(), ["sharpe_ratio"])({})
    assert observed == ["ETH-USDT", "ETH-USDT", "SOL-USDT", "SOL-USDT"]
    assert result["status"] == "ok"


@pytest.mark.parametrize("metrics", [{}, {"sharpe_ratio": float("nan")}, {"sharpe_ratio": float("inf")}, {"sharpe_ratio": float("-inf")}])
def test_missing_or_nonfinite_objective_metric_fails_trial(monkeypatch, metrics):
    from hyperopt import STATUS_FAIL
    handler = HyperoptObjective()
    monkeypatch.setattr(handler, "_calculate_metrics_for_asset", lambda *args: metrics)
    result = handler.create_objective_function({"SYNTHETIC": pd.DataFrame({"close": [1.0, 1.0]})}, {}, None, ["sharpe_ratio"])({})
    assert result["status"] == STATUS_FAIL
    assert result["loss"] == float("inf")


def test_empty_asset_population_is_not_successful_trial():
    from hyperopt import STATUS_FAIL
    result = HyperoptObjective().create_objective_function({}, {}, None, ["sharpe_ratio"])({})
    assert result["status"] == STATUS_FAIL
    assert result["loss"] == float("inf")


@pytest.mark.parametrize('metrics,objectives', [
    ({}, ['sharpe_ratio']),
    ({'total_return': 0.0}, ['profit_factor']),
    ({'sharpe_ratio': 2.0}, ['sharpe_ratio', 'total_return']),
])
def test_actual_metrics_wrapper_does_not_manufacture_absent_objectives(monkeypatch, metrics, objectives):
    from hyperopt import STATUS_FAIL
    class Backtester:
        def __init__(self, **kwargs): pass
        def run_backtest(self, **kwargs): return dict(metrics)
    monkeypatch.setattr(objective_module, 'RealisticBacktester', Backtester)
    frame = pd.DataFrame({'close': [1.0, 1.0]})
    result = HyperoptObjective().create_objective_function(
        {'ETHUSDT': frame}, {}, lambda row, params: 0, objectives)({})
    assert result['status'] == STATUS_FAIL
    assert result['loss'] == float('inf')


def test_actual_metrics_wrapper_preserves_reported_zero_without_inventing_other_metrics(monkeypatch):
    class Backtester:
        def __init__(self, **kwargs): pass
        def run_backtest(self, **kwargs): return {'sharpe_ratio': 0.0}
    monkeypatch.setattr(objective_module, 'RealisticBacktester', Backtester)
    frame = pd.DataFrame({'close': [1.0, 1.0]})
    handler = HyperoptObjective()
    metrics = handler._calculate_metrics_for_asset({}, frame, {}, lambda row, params: 0, 'ETHUSDT')
    assert metrics == {'sharpe_ratio': 0.0}
    result = handler.create_objective_function(
        {'ETHUSDT': frame}, {}, lambda row, params: 0, ['sharpe_ratio'])({})
    assert result['status'] == 'ok'
    assert result['loss'] == 0.0


def test_finite_asset_metrics_with_overflowed_sum_fail_trial(monkeypatch):
    from hyperopt import STATUS_FAIL
    handler = HyperoptObjective()
    monkeypatch.setattr(handler, "_calculate_metrics_for_asset", lambda *args: {"sharpe_ratio": 1e308})
    frame = pd.DataFrame({"close": [1.0, 1.0]})
    result = handler.create_objective_function({"A": frame, "B": frame}, {}, None, ["sharpe_ratio"])({})
    assert result["status"] == STATUS_FAIL
    assert result["loss"] == float("inf")


def test_successful_synthetic_trial_preserves_score(monkeypatch):
    from hyperopt import STATUS_OK
    handler = HyperoptObjective()
    monkeypatch.setattr(handler, "_calculate_metrics_for_asset", lambda *args: {"sharpe_ratio": 2.5})
    objective = handler.create_objective_function({"SYNTHETIC": pd.DataFrame({"close": [1.0, 1.0]})}, {}, None, ["sharpe_ratio"])
    result = objective({})
    assert result["status"] == STATUS_OK
    assert result["loss"] == -2.5


@pytest.mark.parametrize("failure", ["copy", "backtest", "insufficient"])
def test_invalid_synthetic_evaluation_is_not_successful_trial(monkeypatch, failure):
    from hyperopt import STATUS_FAIL
    class Strategy:
        def __deepcopy__(self, memo):
            raise TypeError("synthetic noncopyable")
        def generate_signal(self, symbol):
            raise AssertionError("must not evaluate")
    class FakeBacktester:
        def __init__(self, **kwargs):
            pass
        def run_backtest(self, **kwargs):
            assert failure == "backtest"
            return {"error": "synthetic rejected evaluation"}
    monkeypatch.setattr(objective_module, "RealisticBacktester", FakeBacktester)
    frame = pd.DataFrame({"close": [1.0] if failure == "insufficient" else [1.0, 1.0]})
    strategy = Strategy() if failure == "copy" else None
    objective = HyperoptObjective().create_objective_function({"SYNTHETIC": frame}, {}, strategy, ["sharpe_ratio"])
    result = objective({})
    assert result["status"] == STATUS_FAIL
    assert result["loss"] == float("inf")


@pytest.mark.parametrize("mutate_cache_hit", [False, True])
def test_caller_cannot_mutate_cached_parameter_result(monkeypatch, mutate_cache_hit):
    calls = []
    adapter = module.HyperoptAdapter(cache_results=True)
    def factory(*args, **kwargs):
        def forbidden(_params):
            raise AssertionError("economic evaluation forbidden")
        return forbidden
    def fake_fmin(**kwargs):
        calls.append(True)
        return {"window": [4, 5]}
    monkeypatch.setattr(adapter.objective_handler, "create_objective_function", factory)
    monkeypatch.setattr(module, "fmin", fake_fmin)
    frame = pd.DataFrame({"close": [1.0, 1.0]})
    result = adapter.optimize(frame, {})
    if mutate_cache_hit:
        result = adapter.optimize(frame, {})
    result["window"][0] = 999
    assert adapter.optimize(frame, {}) == {"window": [4, 5]}
    assert len(calls) == 1


@pytest.mark.parametrize("method_name", ["_calculate_metrics_for_asset", "_calculate_score_for_asset"])
def test_strategy_instance_state_is_fresh_per_synthetic_evaluation(monkeypatch, method_name):
    """Expected signals independently specified by fixture_review; no real outcomes."""
    captured = []
    class Strategy:
        def __init__(self):
            self.updates = 0
        def update_with_market_data(self, data):
            self.updates += 1
        def generate_signal(self, symbol):
            kind = {1: objective_module.SignalType.BUY, 2: objective_module.SignalType.SELL}.get(self.updates)
            return SimpleNamespace(signal_type=kind) if kind else None
    class FakeBacktester:
        def __init__(self, **kwargs):
            pass
        def run_backtest(self, data, strategy_function, strategy_params):
            captured.append([strategy_function(row, strategy_params) for _, row in data.iterrows()])
            return dict(sharpe_ratio=0.0, total_return=0.0, max_drawdown=0.0,
                        win_rate=0.5, profit_factor=1.0, total_trades=5)
    monkeypatch.setattr(objective_module, "RealisticBacktester", FakeBacktester)
    frame = pd.DataFrame({"close": [100.0, 100.0]})
    strategy = Strategy()
    evaluator = getattr(HyperoptObjective(), method_name)
    evaluator({}, frame, {}, strategy)
    evaluator({}, frame, {}, strategy)
    assert captured == [[1, -1], [1, -1]]
    assert strategy.updates == 0


@pytest.mark.parametrize("method_name", ["_calculate_metrics_for_asset", "_calculate_score_for_asset"])
@pytest.mark.parametrize("copy_mode", ["self", "error"])
def test_unisolatable_strategy_never_reaches_fake_backtest(monkeypatch, method_name, copy_mode):
    calls = []
    class Strategy:
        def __deepcopy__(self, memo):
            if copy_mode == "self":
                return self
            raise TypeError("synthetic noncopyable strategy")
        def generate_signal(self, symbol):
            raise AssertionError("must never evaluate caller strategy")
    monkeypatch.setattr(objective_module, "RealisticBacktester", lambda **kwargs: SimpleNamespace(
        run_backtest=lambda **options: calls.append("forbidden evaluation")))
    result = getattr(HyperoptObjective(), method_name)({}, pd.DataFrame({"close": [1.0, 1.0]}), {}, Strategy())
    assert calls == []
    if isinstance(result, dict):
        assert result["sharpe_ratio"] == -1000.0
    else:
        assert result == -1000.0

@pytest.mark.parametrize("context", ["risk", "strategy"])
def test_changed_objective_context_never_reuses_cached_result(monkeypatch, context):
    frame = pd.DataFrame({"close": [1.0, 2.0]})
    strategy = type("SyntheticState", (), {"state": 0})() if context == "strategy" else None
    adapter = module.HyperoptAdapter(strategy, {"fee_rate": 0.001})
    calls = []
    def factory(*args, **kwargs):
        def forbidden(_params):
            raise AssertionError("economic evaluation forbidden")
        return forbidden
    def fake_fmin(**kwargs):
        calls.append(True)
        return {"window": len(calls)}
    monkeypatch.setattr(adapter.objective_handler, "create_objective_function", factory)
    monkeypatch.setattr(module, "fmin", fake_fmin)
    assert adapter.optimize(frame, {}) == {"window": 1}
    if context == "risk":
        adapter.risk_config["fee_rate"] = 0.002
    else:
        strategy.state = 1
    assert adapter.optimize(frame, {}) == {"window": 2}
def test_cache_identity_includes_training_tail():
    adapter = module.HyperoptAdapter()
    first = pd.DataFrame({"close": list(range(20))})
    second = first.copy()
    second.loc[19, "close"] = 999
    assert adapter._generate_cache_key(first, {}, None) != adapter._generate_cache_key(second, {}, None)


def test_cache_identity_includes_training_index():
    adapter = module.HyperoptAdapter()
    first = pd.DataFrame({"close": list(range(20))})
    second = first.copy()
    second.index = pd.RangeIndex(100, 120)
    assert adapter._generate_cache_key(first, {}, None) != adapter._generate_cache_key(second, {}, None)


def test_adapter_constructs_the_existing_objective_handler():
    adapter = module.HyperoptAdapter(cache_results=False)
    assert isinstance(adapter.objective_handler, HyperoptObjective)


def test_supplied_training_data_and_strategy_reach_objective_factory(monkeypatch):
    frame = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.date_range(
        "2026-01-01", periods=2, freq="h", tz="UTC"))
    strategy = object()
    risk = {"fee_rate": 0.001, "slippage_factor": 0.0005}
    seen = {}

    def never_evaluate(_params):
        raise AssertionError("test must not evaluate economic outcomes")

    def factory(self, data, risk_config, strategy_function, objectives):
        seen.update(data=data, risk=risk_config, strategy=strategy_function,
                    objectives=objectives)
        return never_evaluate

    def fake_fmin(**kwargs):
        assert kwargs["fn"] is never_evaluate
        assert kwargs["max_evals"] == 3
        return {"window": np.int64(4)}

    monkeypatch.setattr(HyperoptObjective, "create_objective_function", factory)
    monkeypatch.setattr(module, "fmin", fake_fmin)
    adapter = module.HyperoptAdapter(strategy, risk, max_evals=3, cache_results=False)
    assert adapter.optimize(frame, {"window": 4}, ["sharpe_ratio"]) == {"window": 4}
    assert seen["data"]["data"] is frame
    assert seen["strategy"] is strategy
    assert seen["risk"] is risk
    assert seen["objectives"] == ["sharpe_ratio"]


def test_multi_asset_wrapper_preserves_asset_keys_to_factory(monkeypatch):
    seen = []
    def factory(self, data, *args):
        seen.extend(data)
        return lambda params: (_ for _ in ()).throw(AssertionError("no outcomes"))
    monkeypatch.setattr(HyperoptObjective, "create_objective_function", factory)
    monkeypatch.setattr(module, "fmin", lambda **kwargs: {"window": 4})
    frame = pd.DataFrame({"close": [1.0, 1.0]})
    result = module.MultiAssetHyperoptAdapter(max_workers=1).optimize(
        {"ETH-USDT": frame, "SOL-USDT": frame}, {"window": 4})
    assert sorted(seen) == ["ETH-USDT", "SOL-USDT"]
    assert set(result) == {"ETH-USDT", "SOL-USDT"}


def test_multi_asset_wrapper_constructs_inner_adapter(monkeypatch):
    frame = pd.DataFrame({"close": [1.0, 2.0]})
    seen = []

    def fake_optimize(self, data, parameter_space, optimization_objectives):
        assert isinstance(self.objective_handler, HyperoptObjective)
        seen.append(data)
        return {"window": 4}

    monkeypatch.setattr(module.HyperoptAdapter, "optimize", fake_optimize)
    wrapper = module.MultiAssetHyperoptAdapter(max_workers=1)
    assert wrapper.optimize({"SYNTHETIC": frame}, {"window": 4}) == {
        "SYNTHETIC": {"window": 4}}
    assert len(seen) == 1 and seen[0] is frame
