from infrastructure.strategies.strategy_manager import StrategyManager


def test_fresh_managers_own_fresh_registered_adapter_state():
    first = StrategyManager()
    second = StrategyManager()
    assert first is not second
    assert first.strategies.keys() == second.strategies.keys()
    assert first.strategies

    for name in first.strategies:
        left = first.strategies[name]
        right = second.strategies[name]
        assert left is not right
        for attr in (
            "data_buffer", "current_positions", "last_intent_timestamp",
            "intent_count_today", "consecutive_losses", "last_loss_time",
            "last_sl_exit_time", "last_entry_bar_index", "last_exit_time",
            "bar_counter", "last_signal_conditions",
        ):
            assert getattr(left, attr) is not getattr(right, attr), (name, attr)
        for attr in ("market_structure_engine", "setup_engine", "pipeline"):
            if hasattr(left, attr):
                assert getattr(left, attr) is not getattr(right, attr), (name, attr)

    name = next(iter(first.strategies))
    first.strategies[name].current_positions["BTCUSDT"] = object()
    first.strategies[name].data_buffer.append({"symbol": "ETHUSDT"})
    assert second.strategies[name].current_positions == {}
    assert second.strategies[name].data_buffer == []


def test_fresh_manager_registration_does_not_change_other_manager():
    first = StrategyManager()
    second = StrategyManager()
    name = next(iter(first.strategies))
    first.unregister_strategy(name)
    assert name in second.strategies
