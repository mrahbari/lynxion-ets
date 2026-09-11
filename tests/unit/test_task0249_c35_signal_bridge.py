from scripts.evaluate_c35_compression_release import UNIVERSE
from scripts.update_c35_signals import _decision_times, _input_hash, find_first_signal


def _panel():
    return {
        symbol: [
            {"symbol": symbol, "open_time": 1789087500, "close": "1"},
            {"symbol": symbol, "open_time": 1789091100, "close": "2"},
        ] for symbol in UNIVERSE
    }


def test_decisions_require_common_exact_hour_bar():
    panel = _panel()
    assert _decision_times(panel) == [1789088400, 1789092000]
    panel["ADAUSDT"].pop()
    assert _decision_times(panel) == [1789088400]


def test_causal_hash_is_deterministic_and_changes_with_input():
    panel = _panel()
    first = _input_hash(panel, 1789092000)
    assert first == _input_hash(panel, 1789092000)
    panel["BTCUSDT"][0]["close"] = "1.1"
    assert first != _input_hash(panel, 1789092000)


def test_returns_first_ranked_signal_only():
    calls = []
    def evaluator(panel, decision_time, boundary):
        calls.append(decision_time)
        return None if len(calls) == 1 else {
            "candidate": "C-35", "symbol": "BTCUSDT", "decision_time": decision_time,
        }
    signal, digest = find_first_signal(_panel(), evaluator=evaluator)
    assert signal["decision_time"] == 1789092000
    assert len(digest) == 64
    assert calls == [1789088400, 1789092000]
