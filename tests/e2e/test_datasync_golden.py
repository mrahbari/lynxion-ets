"""Golden/characterization test for the canonical data-sync path.

Pins the result of ``SyncManager.sync_symbol_data`` and the merged raw CSV it
writes, using the real ``FileRepositoryAdapter`` against a temp directory and a
stubbed (in-memory) downloader so no live API is contacted. Protects the
E3/E5 data-provider + cache consolidations from silent drift (F7, F13).
"""

import asyncio
from typing import List, Optional

import pytest

# Heavy / production dependencies: skip cleanly if unavailable so collection
# stays error-free in a minimal environment (e.g. CI without project deps).
pytest.importorskip("pandas")
try:
    from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
    from application.data_sync.sync_manager import SyncManager
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"data-sync dependencies unavailable: {exc}", allow_module_level=True)

from golden_utils import assert_golden

_SYMBOL = "BTCUSDT"
_BASE_TS = 1_700_000_000  # fixed Unix second, minute-aligned region


class _StubDownloader:
    """Deterministic, offline DataDownloader stub (no network)."""

    async def fetch_range(self, symbol: str, start_ts: int, end_ts: int,
                          exchange: Optional[str] = None) -> List[dict]:
        candles = []
        for i in range(10):
            ts = _BASE_TS + i * 60
            base = 100.0 + i
            candles.append({
                "timestamp": ts,
                "open": base,
                "high": base + 2,
                "low": base - 1,
                "close": base + 0.5,
                "volume": 1000 + i * 10,
            })
        return candles


def _run_sync(tmp_path) -> dict:
    repo = FileRepositoryAdapter(base_data_dir=str(tmp_path))
    manager = SyncManager(file_repo=repo, data_downloader=_StubDownloader())

    result = asyncio.run(manager.sync_symbol_data(
        symbol=_SYMBOL, timeframes=["1m"],
        start_time=_BASE_TS, end_time=_BASE_TS + 10 * 60,
    ))

    raw_rows = repo.read_csv_rows(repo.get_raw_file_path(_SYMBOL))
    return {"result": result, "raw_rows": raw_rows}


@pytest.mark.e2e
def test_datasync_output_matches_golden(tmp_path):
    assert_golden("datasync_result.json", _run_sync(tmp_path))


@pytest.mark.e2e
def test_datasync_is_deterministic_across_runs(tmp_path):
    first = _run_sync(tmp_path / "a")
    second = _run_sync(tmp_path / "b")
    assert first == second
