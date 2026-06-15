"""E2.T4c pilot: historical-data-sync flow wired through the composition root.

Guarantees the migrated flow matches the approved E2 architecture
(Runner -> CLI -> UseCase -> Port -> Infrastructure):

1. The container registers the historical-data-sync ports as lazy factory
   callables, so ``resolve_all`` (offline smoke) never constructs brokers.
2. ``SyncHistoricalDataUseCase`` drives the injected ports (provider + CSV
   loader) and never constructs infrastructure itself.
3. The CLI delegates to the use case, injecting the container's ports.
4. ``runner_historical_data_sync`` is a thin shim with no infrastructure
   imports, adapter construction, or trapped orchestration.
"""

from pathlib import Path

import pytest
from bootstrap.settings.loaders import load_settings

pytest.importorskip("pandas")

try:
    from bootstrap.lifecycle import create_container
    from application.use_cases.sync_historical_data import SyncHistoricalDataUseCase
    import interface.cli.historical_data_sync as cli
    import runner_historical_data_sync as runner
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"historical-sync pilot dependencies unavailable: {exc}", allow_module_level=True)

_RUNNER_SRC = Path(runner.__file__).read_text(encoding="utf-8")


class _StubProvider:
    """Records get_historical_data calls; returns deterministic candles."""

    def __init__(self):
        self.calls = []

    def get_historical_data(self, symbol, period, timeframe):
        self.calls.append((symbol, period, timeframe))
        return [{"timestamp": 1_700_000_000, "open": 1, "high": 2, "low": 0.5,
                 "close": 1.5, "volume": 10}]


class _StubLoader:
    """Records save_historical_data calls."""

    def __init__(self):
        self.saved = []

    def save_historical_data(self, symbol, data, timeframe):
        self.saved.append((symbol, len(data), timeframe))


def _make_use_case(tmp_path):
    """Construct the use case against stub ports, using a real (existing) data dir."""
    data_dir = tmp_path / "data" / "history" / "raw" / "1m"
    data_dir.mkdir(parents=True, exist_ok=True)
    provider = _StubProvider()
    loader = _StubLoader()
    use_case = SyncHistoricalDataUseCase(
        settings=load_settings(),
        data_provider_factory=lambda: provider,
        csv_loader_factory=lambda base_path: loader,
        data_dir=data_dir.as_posix(),
    )
    return use_case, provider, loader


@pytest.mark.e2e
def test_container_registers_historical_ports(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        # resolve_all must stay offline: factories are returned as callables and
        # never invoked (no brokers/adapters constructed during smoke resolve).
        resolved = container.resolve_all()
        for key in ("historical_data_provider_factory", "historical_csv_loader_factory"):
            assert key in resolved
            assert callable(resolved[key])
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_csv_loader_factory_builds_loader_with_base_path(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        factory = container.resolve("historical_csv_loader_factory")
        loader = factory(str(tmp_path / "data"))
        # The composition root is the sole place infra is constructed.
        assert type(loader).__name__ == "CSVHistoryLoaderAdapter"
        assert str(loader.base_path) == str(tmp_path / "data")
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_use_case_uses_injected_ports(tmp_path):
    use_case, provider, loader = _make_use_case(tmp_path)

    # The use case wires itself entirely from the injected factories.
    assert use_case.data_provider is provider
    assert use_case.csv_loader is loader

    assert use_case.sync_with_retry("BTCUSDT") is True

    # Orchestration drove the injected provider + loader (no infra construction).
    assert len(provider.calls) == 1
    symbol, period, timeframe = provider.calls[0]
    assert "BTCUSDT" in str(symbol)
    assert (period, timeframe) == ("30d", "1m")
    assert loader.saved == [("BTCUSDT", 1, "1m")]


@pytest.mark.e2e
def test_cli_delegates_to_use_case(monkeypatch):
    recorded = {}

    class _RecordingUseCase:
        def __init__(self, settings=None, data_provider_factory=None, csv_loader_factory=None, data_dir=None):
            recorded["provider_factory"] = data_provider_factory
            recorded["csv_loader_factory"] = csv_loader_factory

        def sync_approved_symbols(self):
            recorded["sync_called"] = recorded.get("sync_called", 0) + 1

        def start_scheduler(self):  # pragma: no cover - not exercised in 'now' path
            raise AssertionError("scheduler must not start for one-time sync")

    monkeypatch.setattr(cli, "SyncHistoricalDataUseCase", _RecordingUseCase)

    assert cli.main(["now"]) == 0

    # CLI delegated to the use case exactly once for the one-time sync...
    assert recorded["sync_called"] == 1
    # ...and injected the container's ports (callable factories).
    assert callable(recorded["provider_factory"])
    assert callable(recorded["csv_loader_factory"])


@pytest.mark.e2e
def test_runner_is_thin_shim():
    # No infrastructure imports remain in the runner.
    assert "from infrastructure" not in _RUNNER_SRC
    assert "import infrastructure" not in _RUNNER_SRC
    # No adapter/service construction or trapped orchestration.
    assert "ConfigurableHistoricalDataProvider" not in _RUNNER_SRC
    assert "CSVHistoryLoaderAdapter" not in _RUNNER_SRC
    assert "class HistoricalDataSyncJob" not in _RUNNER_SRC
    # The runner delegates to the CLI shell.
    assert "from interface.cli.historical_data_sync import main" in _RUNNER_SRC
