"""Unit tests for the LIVE_EXECUTION_GUARD (Phase-9 execution-safety layer).

Verifies the single decision matrix: paper_trading override, testnet-only-selects-
endpoint, explicit LIVE_TRADING opt-in for live sends, per-broker order-placement
permission, and kill-switch precedence. Each test uses a fresh guard instance so the
process singleton's runtime state does not leak between cases.
"""

from types import SimpleNamespace

import pytest

from shared.live_execution_guard import LiveExecutionGuard, ExecutionMode


def _settings(paper, placement, testnet, broker="bingx"):
    b = SimpleNamespace(paper_trading=paper, testnet=True)
    setattr(b, f"{broker}_order_placement_enabled", placement)
    setattr(b, f"{broker}_testnet", testnet)
    return SimpleNamespace(broker=b)


_ORDER = SimpleNamespace(symbol=SimpleNamespace(value="TEST/USDT"))


@pytest.fixture
def guard():
    g = LiveExecutionGuard()
    g._risk_enforcer = lambda o: (True, "")
    return g


@pytest.fixture(autouse=True)
def _clear_live_trading(monkeypatch):
    monkeypatch.delenv("LIVE_TRADING", raising=False)
    # Reset the process-global circuit breakers so OPEN state doesn't bleed between tests.
    from shared.circuit_breaker import circuit_breaker_manager
    circuit_breaker_manager.circuit_breakers.clear()
    from shared.live_execution_guard import live_execution_guard
    live_execution_guard.disengage_kill_switch()
    old_enforcer = live_execution_guard._risk_enforcer
    live_execution_guard._risk_enforcer = lambda o: (True, "")
    yield
    circuit_breaker_manager.circuit_breakers.clear()
    live_execution_guard.disengage_kill_switch()
    live_execution_guard._risk_enforcer = old_enforcer


def test_paper_trading_is_absolute_override(guard, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    d = guard.evaluate("bingx", _settings(paper=True, placement=True, testnet=False), _ORDER)
    assert d.mode is ExecutionMode.PAPER
    assert d.simulate and d.allowed and not d.is_live_send


def test_no_placement_permission_blocks(guard):
    d = guard.evaluate("bingx", _settings(paper=False, placement=False, testnet=True), _ORDER)
    assert d.mode is ExecutionMode.BLOCKED and not d.allowed


def test_testnet_allowed_without_live_trading(guard):
    d = guard.evaluate("bingx", _settings(paper=False, placement=True, testnet=True), _ORDER)
    assert d.mode is ExecutionMode.TESTNET and d.allowed and not d.is_live_send


def test_live_endpoint_blocked_without_explicit_opt_in(guard):
    d = guard.evaluate("bingx", _settings(paper=False, placement=True, testnet=False), _ORDER)
    assert d.mode is ExecutionMode.BLOCKED, "live endpoint must require LIVE_TRADING=true"


def test_live_endpoint_allowed_with_explicit_opt_in(guard, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    d = guard.evaluate("bingx", _settings(paper=False, placement=True, testnet=False), _ORDER)
    assert d.mode is ExecutionMode.LIVE and d.is_live_send


def test_testnet_does_not_grant_live_permission(guard, monkeypatch):
    """BROKER_TESTNET only selects the endpoint; it must not, alone, authorize live."""
    monkeypatch.setenv("LIVE_TRADING", "true")
    d = guard.evaluate("bingx", _settings(paper=False, placement=True, testnet=True), _ORDER)
    assert d.mode is ExecutionMode.TESTNET  # still testnet, not live


def test_kill_switch_has_highest_precedence(guard, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    guard.engage_kill_switch("manual halt")
    d = guard.evaluate("bingx", _settings(paper=False, placement=True, testnet=False), _ORDER)
    assert d.mode is ExecutionMode.BLOCKED
    assert guard.is_killed()
    guard.disengage_kill_switch()
    assert not guard.is_killed()
    d2 = guard.evaluate("bingx", _settings(paper=False, placement=True, testnet=False), _ORDER)
    assert d2.mode is ExecutionMode.LIVE


def test_missing_settings_defaults_to_paper(guard):
    d = guard.evaluate("bingx", None, _ORDER)
    assert d.mode is ExecutionMode.PAPER, "no settings must fail safe to simulated paper"


def test_unknown_broker_requires_explicit_flag(guard, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    d = guard.evaluate("kraken", _settings(paper=False, placement=True, testnet=False, broker="bingx"), _ORDER)
    assert d.mode is ExecutionMode.BLOCKED  # no kraken_order_placement_enabled -> blocked


def test_simulated_order_id_is_marked_and_unique(guard):
    a = guard.simulated_order_id(_ORDER, "bingx")
    b = guard.simulated_order_id(_ORDER, "bingx")
    assert a.startswith("PAPER-BINGX-TESTUSDT-") and a != b


def test_circuit_breaker_blocks_when_open(guard):
    # Drive the per-broker breaker to OPEN via repeated failures, then expect BLOCKED.
    for _ in range(6):
        guard.record_send_result("bingx", success=False)
    blocked, reason = guard.breaker_blocks("bingx")
    assert blocked and "circuit breaker OPEN" in reason
    d = guard.evaluate("bingx", _settings(paper=False, placement=True, testnet=True), _ORDER)
    assert d.mode is ExecutionMode.BLOCKED
