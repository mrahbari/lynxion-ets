from scripts.evaluate_c35_compression_release import evaluate_decision


def _candles(decision_time, decision_range=0.0062):
    start = decision_time - 2898 * 900
    rows = []
    for index in range(2898):
        compressed = index >= 2881
        high, low = (100.05, 99.95) if compressed else (100.5, 99.5)
        rows.append({
            "open_time": start + index * 900,
            "open": 100, "high": high, "low": low, "close": 100, "volume": 100,
        })
    rows[-1].update({"high": 100 + decision_range * 100, "low": 100, "close": 100.5, "volume": 200})
    return rows


def test_emits_long_only_after_strict_boundary_with_causal_windows():
    decision_time = 1789092000
    result = evaluate_decision({"BTCUSDT": _candles(decision_time)}, decision_time)
    assert result["side"] == "LONG"
    assert result["decision_bar_open"] > 1789087244
    assert result["entry_open_time"] == decision_time


def test_rejects_non_contiguous_window():
    decision_time = 1789092000
    rows = _candles(decision_time)
    rows[-100]["open_time"] += 1
    assert evaluate_decision({"BTCUSDT": rows}, decision_time) is None


def test_rejects_decision_bar_at_or_before_boundary():
    decision_time = 1789084800
    assert evaluate_decision({"BTCUSDT": _candles(decision_time)}, decision_time) is None


def test_ranks_by_range_then_symbol():
    decision_time = 1789092000
    result = evaluate_decision({
        "BTCUSDT": _candles(decision_time, 0.0062),
        "ETHUSDT": _candles(decision_time, 0.0080),
    }, decision_time)
    assert result["symbol"] == "ETHUSDT"
