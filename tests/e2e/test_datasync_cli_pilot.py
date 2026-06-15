"""E2.T3 pilot: data-sync runners wired through the composition root.

Two guarantees:
1. The container wires the data-sync ports correctly — ``sync_manager`` and
   ``watcher_retune`` share the container's single ``file_repository`` and
   ``data_downloader`` instances (dependency injection, offline).
2. The new ``SyncMarketDataUseCase.download_history`` path drives the canonical
   ``SyncManager`` and writes the same merged raw CSV as the data-sync golden
   path, using a deterministic offline stub downloader.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Optional

import pytest
from bootstrap.settings.loaders import load_settings

pytest.importorskip("pandas")

try:
    from bootstrap.lifecycle import create_container, lifespan
    from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
    from application.data_sync.sync_manager import SyncManager
    from application.use_cases.sync_market_data import (
        HistoryDownloadRequest, SyncMarketDataUseCase,
    )
    from runner_history_download import format_symbol_for_exchange
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"data-sync pilot dependencies unavailable: {exc}", allow_module_level=True)

from datetime import datetime

_SYMBOL = "BTCUSDT"
_BASE_TS = 1_700_000_000
_GOLDEN = Path(__file__).resolve().parent.parent / "fixtures" / "golden" / "datasync_result.json"


class _StubDownloader:
    """Deterministic, offline downloader with async-context support."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def fetch_range(self, symbol: str, start_ts: int, end_ts: int,
                          exchange: Optional[str] = None) -> List[dict]:
        candles = []
        for i in range(10):
            ts = _BASE_TS + i * 60
            base = 100.0 + i
            candles.append({
                "timestamp": ts, "open": base, "high": base + 2,
                "low": base - 1, "close": base + 0.5, "volume": 1000 + i * 10,
            })
        return candles


@pytest.mark.e2e
def test_container_wires_sync_ports(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        file_repo = container.resolve("file_repository")
        downloader = container.resolve("data_downloader")
        sync_manager = container.resolve("sync_manager")
        watcher_retune = container.resolve("watcher_retune")

        # The container injects its singletons (no re-instantiation of infra).
        assert sync_manager.file_repo is file_repo
        assert sync_manager.data_downloader is downloader
        assert watcher_retune.file_repo is file_repo
        assert watcher_retune.data_downloader is downloader
        assert watcher_retune.sync_manager is sync_manager
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_container_resolves_all_including_sync_ports(tmp_path):
    with lifespan(base_data_dir=str(tmp_path)) as container:
        resolved = container.resolve_all()
        for key in ("data_downloader", "sync_manager", "watcher_retune"):
            assert key in resolved and resolved[key] is not None


@pytest.mark.e2e
def test_download_history_writes_canonical_raw_csv(tmp_path):
    repo = FileRepositoryAdapter(base_data_dir=str(tmp_path))
    sync_manager = SyncManager(repo, _StubDownloader())
    use_case = SyncMarketDataUseCase(
        settings=load_settings(),
        file_repository=repo,
        data_downloader=_StubDownloader(),
        sync_manager=sync_manager,
    )

    # Round-trips back to the fixed base timestamps regardless of local tz.
    request = HistoryDownloadRequest(
        symbols=[_SYMBOL],
        start_date=datetime.fromtimestamp(_BASE_TS),
        end_date=datetime.fromtimestamp(_BASE_TS + 10 * 60),
        timeframes=["1m"],
    )

    results = asyncio.run(use_case.download_history(request))

    assert results["summary"]["total_candles"] == 10
    assert results["downloads"][_SYMBOL]["timeframes"]["1m"]["candles_count"] == 10

    formatted = format_symbol_for_exchange(_SYMBOL)
    raw_rows = repo.read_csv_rows(repo.get_raw_file_path(formatted))
    expected_rows = json.loads(_GOLDEN.read_text())["raw_rows"]
    assert raw_rows == expected_rows
