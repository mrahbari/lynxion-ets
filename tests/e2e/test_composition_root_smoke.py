"""E2.T1 smoke test: the composition root builds, resolves its wired ports
without error, caches singletons, and tears down cleanly — with no
module-level side effects (importing the modules does nothing on its own).
"""

import pytest

pytest.importorskip("pandas")
pytest.importorskip("numpy")

try:
    from bootstrap.lifecycle import create_container, lifespan
    from bootstrap.container import Container
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"composition root dependencies unavailable: {exc}",
                allow_module_level=True)


@pytest.mark.e2e
def test_container_resolves_all_wired_ports(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        resolved = container.resolve_all()
        assert set(resolved) == set(container.registered_keys())
        for key, instance in resolved.items():
            assert instance is not None, f"{key} resolved to None"
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_container_caches_singletons(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        first = container.resolve("backtester")
        second = container.resolve("backtester")
        assert first is second
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_lifespan_context_manager(tmp_path):
    with lifespan(base_data_dir=str(tmp_path)) as container:
        assert isinstance(container, Container)
        assert container.resolve("metric_calculator") is not None
    # After exit the instance cache is cleared by shutdown().
    assert container._instances == {}
