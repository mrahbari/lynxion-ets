"""E2.T6 pilot: retired global singletons are container-scoped.

Validates the E2.T6 contract:

* The 7 former module-level singletons are created by the composition root
  (``bootstrap/container.py``), not at import time.
* Importing each module has NO side effect (no instance constructed on import).
* Two containers hold INDEPENDENT instances for the per-run service singletons
  (strategy_manager / engine_service / fusion_service / regime_detector), so
  mutating one container's instance does not leak into another.
* The deliberate PROCESS-WIDE safety singletons (broker_registry /
  global_rate_limiter / pending_orders_tracker) remain a single instance per
  run by design — isolating them per container would regress trade-safety
  (one execution service per run, shared API rate budget, cross-broker
  duplicate-order prevention). The container mediates access to them.
"""

import importlib

import pytest

pytest.importorskip("pandas")
pytest.importorskip("numpy")

try:
    from bootstrap.lifecycle import create_container
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"composition root dependencies unavailable: {exc}",
                allow_module_level=True)


# (module, port-name) for per-run service singletons (independent per container)
_PER_CONTAINER_SERVICES = [
    ("infrastructure.strategies.strategy_manager", "strategy_manager"),
    ("infrastructure.engines.engine_service", "engine_service"),
    ("infrastructure.fusion.fusion_service", "fusion_service"),
    ("infrastructure.market_regime.regime_detector", "regime_detector"),
]

# (module, port-name) for the deliberate process-wide safety singletons that
# still exposed a module-level instance before E2.T6.
_PROCESS_SINGLETON_MODULES = [
    ("infrastructure.services.broker_registry", "broker_registry"),
    ("shared.rate_limiter", "global_rate_limiter"),
]

_PROCESS_SINGLETONS = ["broker_registry", "global_rate_limiter", "pending_orders_tracker"]

_ALL_PORTS = [name for _, name in _PER_CONTAINER_SERVICES] + _PROCESS_SINGLETONS


@pytest.mark.e2e
def test_no_module_level_instantiation():
    """No former singleton is instantiated at module level (E2.T6 constraint).

    The PEP 562 lazy accessor never binds the public name into the module dict,
    so its absence from ``vars(mod)`` is an order-independent proof that there is
    no eager (or stored) module-level instance.
    """
    for module_path, name in _PER_CONTAINER_SERVICES + _PROCESS_SINGLETON_MODULES:
        mod = importlib.import_module(module_path)
        assert hasattr(mod, "__getattr__"), (
            f"{module_path} must expose a lazy module accessor (no eager instance)"
        )
        assert name not in vars(mod), (
            f"{module_path}.{name} must not be instantiated at module level"
        )
        # The accessor still serves the back-compat instance on demand.
        assert getattr(mod, name) is not None


@pytest.mark.e2e
def test_all_singletons_registered_in_container(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        keys = set(container.registered_keys())
        for name in _ALL_PORTS:
            assert name in keys, f"{name} not registered in composition root"
            assert container.resolve(name) is not None
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_single_instance_within_a_container(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        for name in _ALL_PORTS:
            assert container.resolve(name) is container.resolve(name), (
                f"{name} must be a single instance within one container"
            )
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_two_containers_have_independent_service_state(tmp_path):
    """Per-run services are independent across containers (the core P4 fix)."""
    c1 = create_container(base_data_dir=str(tmp_path / "c1"))
    c2 = create_container(base_data_dir=str(tmp_path / "c2"))
    try:
        for _module_path, name in _PER_CONTAINER_SERVICES:
            a = c1.resolve(name)
            b = c2.resolve(name)
            assert a is not b, f"{name} must differ across containers"

        # Concrete mutable-state isolation: tag one container's engine_service and
        # confirm the other container's instance is untouched.
        sentinel = object()
        c1.resolve("engine_service").logger = sentinel
        assert c2.resolve("engine_service").logger is not sentinel
    finally:
        c1.shutdown()
        c2.shutdown()


@pytest.mark.e2e
def test_safety_singletons_stay_process_global(tmp_path):
    """broker_registry / rate limiter / pending orders are intentionally global."""
    c1 = create_container(base_data_dir=str(tmp_path / "c1"))
    c2 = create_container(base_data_dir=str(tmp_path / "c2"))
    try:
        for name in _PROCESS_SINGLETONS:
            assert c1.resolve(name) is c2.resolve(name), (
                f"{name} must remain a single process-wide instance (trade-safety)"
            )
    finally:
        c1.shutdown()
        c2.shutdown()
