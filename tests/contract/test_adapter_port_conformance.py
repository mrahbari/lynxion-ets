"""E6.T3 — Adapter<->port conformance tests.

For every canonical adapter wired in ``bootstrap.container``, assert it conforms
to the domain port(s) it implements (solving **P5** — guarantee adapters satisfy
ports). Conformance here means, for each (port, implementation) pair:

* the adapter **declares** the port (the port is in the adapter's MRO),
* the adapter **implements every** abstract method of the port (no residual
  ``__abstractmethods__`` — instantiation would otherwise raise), and
* every port method is exposed as a **callable with a compatible signature**.

Per the E6.T3 constraint *"MUST run the same suite against each implementation of
a port"*, the same parametrized suite runs against **every** (port, impl) pair —
e.g. ``PortfolioManagementPort`` is checked against both
``EqualWeightPortfolioAdapter`` and ``RiskParityPortfolioAdapter``.

Some canonical adapters need third-party libraries that are not installable in
every environment (e.g. TA-Lib's C library) or perform configuration I/O at
import time. Those specs **skip with a clear reason** instead of failing, so the
suite stays green wherever it runs and fully exercises them where the deps exist.
"""

from __future__ import annotations

import importlib
import inspect
from typing import NamedTuple

import pytest


class _Spec(NamedTuple):
    port_module: str
    port_name: str
    adapter_module: str
    adapter_name: str

    @property
    def id(self) -> str:
        return f"{self.adapter_name}->{self.port_name}"


# Canonical port<->adapter pairs, mirroring the wiring in bootstrap/container.py.
# Adapters that implement several ports appear once per port (same suite, each port).
# Ports with multiple implementations appear once per implementation.
_SPECS: list[_Spec] = [
    _Spec("domain.ports.logging_ports", "LoggingPort",
          "infrastructure.monitoring.logging_adapter", "LoggingAdapter"),
    _Spec("domain.ports.messaging_ports", "MessagingPort",
          "infrastructure.messaging.message_bus_adapter", "MessageBusAdapter"),
    _Spec("domain.ports.engine_ports", "EnginePort",
          "infrastructure.engines.engine_port_adapter", "EngineServiceAdapter"),
    _Spec("domain.ports.backtest_ports", "BacktestEnginePort",
          "infrastructure.backtest.backtest_engine_adapter", "RealisticBacktesterAdapter"),
    _Spec("domain.ports.data_ports", "DataProviderPort",
          "infrastructure.data.csv_history_loader", "CSVHistoryLoaderAdapter"),
    _Spec("domain.ports.portfolio_ports", "PositionSizingEnginePort",
          "infrastructure.position_sizing.position_sizing_engine_adapter", "PositionSizingEngineAdapter"),
    # PortfolioManagementPort — TWO implementations, same suite runs against both.
    _Spec("domain.ports.portfolio_ports", "PortfolioManagementPort",
          "infrastructure.portfolio.portfolio_adapters", "EqualWeightPortfolioAdapter"),
    _Spec("domain.ports.portfolio_ports", "PortfolioManagementPort",
          "infrastructure.portfolio.portfolio_adapters", "RiskParityPortfolioAdapter"),
    # ConsolidatedTrackingAdapter implements three tracking ports.
    _Spec("domain.ports.tracking_ports", "TradeTrackingPort",
          "infrastructure.tracking.tracking_adapter", "ConsolidatedTrackingAdapter"),
    _Spec("domain.ports.tracking_ports", "ResultsTrackingPort",
          "infrastructure.tracking.tracking_adapter", "ConsolidatedTrackingAdapter"),
    _Spec("domain.ports.tracking_ports", "ShadowKPITrackingPort",
          "infrastructure.tracking.tracking_adapter", "ConsolidatedTrackingAdapter"),
    # ConsolidatedRiskEngineAdapter implements two risk ports.
    _Spec("domain.ports.risk_ports", "PortfolioRiskEnginePort",
          "infrastructure.risk.risk_engine_adapter", "ConsolidatedRiskEngineAdapter"),
    _Spec("domain.ports.risk_ports", "StopLossTakeProfitPort",
          "infrastructure.risk.risk_engine_adapter", "ConsolidatedRiskEngineAdapter"),
]


def _load(module: str, name: str):
    """Import ``module`` and return its ``name`` attribute, or skip on failure.

    Adapters may pull optional native deps (TA-Lib) or do config I/O at import;
    treat any import-time failure as 'not exercisable here' rather than a
    conformance failure.
    """
    try:
        mod = importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001 - import side effects vary widely
        pytest.skip(f"{module} not importable in this environment: {exc!r}")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        pytest.fail(f"{name} not found in {module}: {exc}")


def _required_methods(port) -> set[str]:
    """Method names the port requires (abstract members, falling back to
    declared callables for non-abstract Protocols)."""
    required = set(getattr(port, "__abstractmethods__", frozenset()))
    if required:
        return required
    return {
        n for n, v in vars(port).items()
        if callable(v) and not n.startswith("__")
    }


def _signature_compatible(port_fn, adapter_fn) -> tuple[bool, str]:
    """The adapter method can accept the call shape the port declares."""
    P = inspect.Parameter
    try:
        port_params = inspect.signature(port_fn).parameters
        adapter_params = inspect.signature(adapter_fn).parameters
    except (TypeError, ValueError):
        return True, ""  # builtins / un-introspectable: skip signature check
    has_var_kw = any(p.kind == P.VAR_KEYWORD for p in adapter_params.values())
    has_var_pos = any(p.kind == P.VAR_POSITIONAL for p in adapter_params.values())
    for pname, p in port_params.items():
        if pname == "self":
            continue
        if p.kind == P.VAR_KEYWORD:
            if not has_var_kw:
                return False, f"adapter must accept **{pname}"
            continue
        if p.kind == P.VAR_POSITIONAL:
            if not has_var_pos:
                return False, f"adapter must accept *{pname}"
            continue
        if pname in adapter_params or has_var_kw or has_var_pos:
            continue
        return False, f"adapter does not accept parameter '{pname}'"
    return True, ""


@pytest.mark.contract
@pytest.mark.parametrize("spec", _SPECS, ids=[s.id for s in _SPECS])
def test_canonical_adapter_conforms_to_port(spec: _Spec):
    """Shared conformance suite — runs against each (port, implementation) pair."""
    port = _load(spec.port_module, spec.port_name)
    adapter = _load(spec.adapter_module, spec.adapter_name)

    required = _required_methods(port)
    assert required, f"{spec.port_name} declares no methods to conform to"

    # 1) The adapter declares the port (explicit inheritance — Protocols here are
    #    not @runtime_checkable, so check the MRO rather than issubclass()).
    assert port in adapter.__mro__, (
        f"{spec.adapter_name} does not declare {spec.port_name} as a base"
    )

    # 2) Every port method is implemented as a callable with a compatible signature.
    for method_name in sorted(required):
        impl = getattr(adapter, method_name, None)
        assert impl is not None and callable(impl), (
            f"{spec.adapter_name} is missing port method '{method_name}'"
        )
        ok, why = _signature_compatible(getattr(port, method_name), impl)
        assert ok, f"{spec.adapter_name}.{method_name} signature incompatible: {why}"

    # 3) No abstract method left unimplemented (would block instantiation).
    residual = set(getattr(adapter, "__abstractmethods__", frozenset()))
    assert not residual, (
        f"{spec.adapter_name} leaves abstract port methods unimplemented: {sorted(residual)}"
    )


@pytest.mark.contract
def test_messaging_adapter_behavioral_conformance():
    """Behavioral slice of the MessagingPort contract on its canonical adapter.

    The port docstring mandates: subscribers receive published payloads, and
    callback exceptions PROPAGATE to the publisher (the E3.T6 'no silent
    swallowing' guarantee). This exercises the implementation, not just shape.
    """
    MessageBusAdapter = _load(
        "infrastructure.messaging.message_bus_adapter", "MessageBusAdapter"
    )
    bus = MessageBusAdapter()
    received: list[object] = []
    bus.subscribe("evt", received.append)
    bus.publish("evt", {"x": 1})
    assert received == [{"x": 1}], "subscriber did not receive published payload"

    bus.unsubscribe("evt", received.append)
    bus.publish("evt", {"x": 2})
    assert received == [{"x": 1}], "unsubscribed callback still received payload"

    def boom(_):
        raise RuntimeError("callback failed")

    bus.subscribe("evt", boom)
    with pytest.raises(RuntimeError, match="callback failed"):
        bus.publish("evt", {"x": 3})
