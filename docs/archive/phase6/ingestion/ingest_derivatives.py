"""Derivatives ingestion use case (Phase-6): orchestrates funding-rate and
open-interest ingestion over a symbol set + date range, via injected ports.

Per-symbol failures are isolated so one bad symbol cannot abort a backfill.
Ingestion only — no SL/TP, strategy logic, or trading simulation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from domain.ports.derivatives_data import DerivativesDataDownloader, DerivativesStore

FUNDING_COLS = ["timestamp", "funding_rate"]
OI_COLS = ["timestamp", "open_interest", "open_interest_value"]


@dataclass
class DerivativesIngestRequest:
    symbols: List[str]
    start_ms: int
    end_ms: int
    classes: List[str] = field(default_factory=lambda: ["funding", "open_interest"])
    oi_timeframe: str = "1h"
    exchange: str = "binance"


class IngestDerivativesUseCase:
    def __init__(self, downloader: DerivativesDataDownloader, store: DerivativesStore):
        self._dl = downloader
        self._store = store

    def execute(self, req: DerivativesIngestRequest) -> dict:
        summary: dict = {"symbols": len(req.symbols), "exchange": req.exchange}
        if "funding" in req.classes:
            summary["funding"] = self._ingest(
                req, "funding", FUNDING_COLS,
                lambda s: self._dl.fetch_funding_rate_history(s, req.start_ms, req.end_ms),
                "ccxt:fundingRateHistory")
        if "open_interest" in req.classes:
            summary["open_interest"] = self._ingest(
                req, "open_interest", OI_COLS,
                lambda s: self._dl.fetch_open_interest_history(
                    s, req.oi_timeframe, req.start_ms, req.end_ms),
                f"ccxt:openInterestHistory@{req.oi_timeframe}")
        return summary

    def _ingest(self, req: DerivativesIngestRequest, data_class: str,
                columns: List[str], fetch: Callable[[str], list], source: str) -> dict:
        ok, errors = [], []
        for sym in req.symbols:
            try:
                rows = fetch(sym)
                res = self._store.write_series(data_class, sym, rows, columns, source, req.exchange)
                res["rows_fetched"] = len(rows)
                ok.append(res)
            except Exception as e:  # noqa: BLE001 — isolate per-symbol failures
                errors.append({"symbol": sym, "error": str(e)[:200]})
        return {"ok": len(ok), "errors": len(errors), "results": ok, "error_detail": errors}
