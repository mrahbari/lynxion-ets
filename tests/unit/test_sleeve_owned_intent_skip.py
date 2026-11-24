"""E16-U11: intents for v2-sleeve-owned symbols are dropped before the queue (adapter still rejects)."""
import json
from types import SimpleNamespace

from infrastructure.orchestrators._auto_detection_intent import _AutoDetectionIntentMixin


class Stub(_AutoDetectionIntentMixin):
    def __init__(self):
        self.opportunity_queue = []
        self.broker_checked = False
        self.logger = SimpleNamespace(debug=lambda *a, **k: None, info=lambda *a, **k: None,
                                      warning=lambda *a, **k: None, error=lambda *a, **k: None,
                                      log_decision_reason=lambda **k: None)

    def _calculate_opportunity_score(self, intent):
        return 1.0

    def _check_broker_active_orders_for_duplicate(self, intent):
        self.broker_checked = True
        return True

    def _check_duplicate_execution_intent(self, intent):
        return False


def intent(sym):
    return SimpleNamespace(symbol=SimpleNamespace(value=sym), side=SimpleNamespace(name="BUY"),
                           intent_confidence=SimpleNamespace(value=0.6), strategy_name="s")


def test_sleeve_owned_symbol_is_skipped_before_broker_checks(tmp_path, monkeypatch):
    f = tmp_path / "owned.json"
    f.write_text(json.dumps({"symbols": ["BTC-USDT"]}))
    monkeypatch.setenv("V2_OWNED_SYMBOLS_FILE", str(f))
    o = Stub()
    o._handle_execution_intent_event(SimpleNamespace(data=intent("BTCUSDT")))
    assert o.opportunity_queue == [] and not o.broker_checked
    o._handle_execution_intent_event(SimpleNamespace(data=intent("ETHUSDT")))
    assert len(o.opportunity_queue) == 1 and o.broker_checked


def test_missing_file_skips_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("V2_OWNED_SYMBOLS_FILE", str(tmp_path / "absent.json"))
    assert Stub._is_sleeve_owned("BTCUSDT") is False
