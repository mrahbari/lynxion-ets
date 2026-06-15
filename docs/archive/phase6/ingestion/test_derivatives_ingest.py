"""Validation for the hexagonal derivatives ingestion (Phase-6, Option A).

Offline only — a fake DerivativesDataDownloader port stands in for the exchange.
    .venv/bin/python3 -m pytest tests/unit/test_derivatives_ingest.py -q
"""
import pytest

from domain.ports.derivatives_data import DerivativesDataDownloader
from application.use_cases.ingest_derivatives import (
    IngestDerivativesUseCase, DerivativesIngestRequest, FUNDING_COLS, OI_COLS)
from infrastructure.data_sync.derivatives_store_adapter import CsvDerivativesStore, storage_symbol

BASE = 1_700_000_000


class FakeDownloader(DerivativesDataDownloader):
    def __init__(self, fail=()):
        self.fail = set(fail)

    def fetch_funding_rate_history(self, symbol, start_ms, end_ms):
        if symbol in self.fail:
            raise RuntimeError("boom")
        return [{"timestamp": BASE + i * 28800, "funding_rate": 0.0001 * (i + 1)} for i in range(5)]

    def fetch_open_interest_history(self, symbol, timeframe, start_ms, end_ms):
        if symbol in self.fail:
            raise RuntimeError("boom")
        return [{"timestamp": BASE + i * 3600, "open_interest": 100.0 + i,
                 "open_interest_value": (100.0 + i) * 50000} for i in range(5)]


def _store(tmp_path):
    return CsvDerivativesStore(raw_root=str(tmp_path / "raw"), prov_root=str(tmp_path / "prov"))


# ---- store ----
def test_storage_symbol():
    assert storage_symbol("BTCUSDT") == "BTC-USDT"
    assert storage_symbol("ETH/USDT:USDT") == "ETH-USDT"


def test_store_sort_dedup_merge(tmp_path):
    s = _store(tmp_path)
    s.write_series("funding", "BTCUSDT",
                   [{"timestamp": 30, "funding_rate": 0.3}, {"timestamp": 10, "funding_rate": 0.1},
                    {"timestamp": 30, "funding_rate": 0.9}], FUNDING_COLS, "x", "binance")
    r2 = s.write_series("funding", "BTCUSDT", [{"timestamp": 20, "funding_rate": 0.2}],
                        FUNDING_COLS, "x", "binance")
    assert r2["rows_total"] == 3                      # merged 10,20,30 — sorted, de-duped


def test_store_rejects_ms(tmp_path):
    with pytest.raises(ValueError):
        _store(tmp_path).write_series("funding", "BTCUSDT",
                                      [{"timestamp": 1_700_000_000_000, "funding_rate": 0.1}],
                                      FUNDING_COLS, "x", "binance")


# ---- use case ----
def test_usecase_funding_and_oi(tmp_path):
    uc = IngestDerivativesUseCase(FakeDownloader(), _store(tmp_path))
    summary = uc.execute(DerivativesIngestRequest(["BTCUSDT", "ETHUSDT"], 0, 9_999_999_999_000))
    assert summary["funding"]["ok"] == 2 and summary["funding"]["errors"] == 0
    assert summary["open_interest"]["ok"] == 2
    assert (tmp_path / "raw" / "funding" / "BTC-USDT.csv").exists()
    assert (tmp_path / "prov" / "BTC-USDT_funding_provenance.json").exists()
    assert (tmp_path / "raw" / "open_interest" / "ETH-USDT.csv").exists()


def test_usecase_failure_isolation(tmp_path):
    uc = IngestDerivativesUseCase(FakeDownloader(fail={"BADUSDT"}), _store(tmp_path))
    summary = uc.execute(DerivativesIngestRequest(["BTCUSDT", "BADUSDT"], 0, 9e12, classes=["funding"]))
    assert summary["funding"]["ok"] == 1 and summary["funding"]["errors"] == 1
    assert summary["funding"]["error_detail"][0]["symbol"] == "BADUSDT"


# ---- container wiring (offline; adapters build lazily, no network) ----
def test_container_resolves_derivatives_ports():
    from bootstrap.settings.loaders import load_settings
    from bootstrap.container import Container
    c = Container(load_settings())
    assert c.resolve("derivatives_downloader") is not None
    assert c.resolve("derivatives_store") is not None


# ---- cli date parsing ----
def test_cli_to_ms():
    from interface.cli.derivatives_ingest import _to_ms
    assert _to_ms("2021-01-01") == 1609459200000
    assert _to_ms("today") > _to_ms("30d")
