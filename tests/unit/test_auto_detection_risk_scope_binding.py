"""The queued execution owner can use explicit per-run Risk dependencies."""

from types import SimpleNamespace

from infrastructure.orchestrators._auto_detection_execution import _AutoDetectionExecutionMixin


class Owner(_AutoDetectionExecutionMixin):
    pass


def test_explicit_risk_and_cooldown_do_not_resolve_live_globals(monkeypatch):
    from application.containers.container import container
    import infrastructure.risk.symbol_cooldown_gate as cooldown_module

    monkeypatch.setattr(container, "resolve", lambda *args: (_ for _ in ()).throw(
        AssertionError("global risk resolved")))
    monkeypatch.setattr(cooldown_module, "symbol_cooldown_gate", None)
    owner = Owner()
    risk = object()
    gate = object()
    owner._risk_engine = risk
    owner._cooldown_gate = gate
    assert owner._get_risk_engine() is risk
    assert owner._get_cooldown_gate() is gate


def test_default_bindings_remain_live_compatibility_paths(monkeypatch):
    from application.containers.container import container
    import infrastructure.risk.symbol_cooldown_gate as cooldown_module

    risk = object()
    gate = object()
    monkeypatch.setattr(container, "resolve", lambda name: risk if name == "risk_engine" else None)
    monkeypatch.setattr(cooldown_module, "symbol_cooldown_gate", gate)
    owner = Owner()
    assert owner._get_risk_engine() is risk
    assert owner._get_cooldown_gate() is gate


def test_execution_cooldown_rejection_uses_injected_gate():
    class Gate:
        def __init__(self):
            self.symbols = []

        def is_symbol_allowed(self, symbol):
            self.symbols.append(symbol.value)
            return False, "offline-block"

    gate = Gate()
    owner = Owner()
    owner.is_running = True
    owner.logger = SimpleNamespace(warning=lambda *a: None, error=lambda *a: None)
    owner._cooldown_gate = gate
    owner._intent_claim_store = SimpleNamespace(claim=lambda _: True)
    owner._settings = SimpleNamespace(execution=SimpleNamespace(
        prevent_same_direction_trade_per_symbol=False))
    owner._check_broker_active_orders_for_duplicate = lambda _: True
    owner._remove_pending_execution_intent = lambda _: None
    owner._stablecoin_filter_config = lambda: (False, set())
    intent = SimpleNamespace(
        intent_id="scoped-risk-unit", symbol=SimpleNamespace(value="BTCUSDT"),
        side=SimpleNamespace(name="BUY"), strategy_name="UNIT",
        intent_confidence=SimpleNamespace(value=1.0),
    )
    result = owner._execute_trade_from_intent(intent)
    assert result["status"] == "failed"
    assert "offline-block" in result["error"]
    assert gate.symbols == ["BTCUSDT"]
