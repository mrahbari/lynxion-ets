"""Sync-market-data use case (E2.T4b - Composition Root Hardening).

Application-layer entry point for the data/sync features (F1, F2, F3, F6). All
orchestration lives here; every infrastructure dependency is received through a
port resolved from the composition root (``file_repository``, ``data_downloader``,
``sync_manager``, ``watcher_retune``). This module imports only stdlib /
third-party libraries plus the ``shared``/``utils`` loggers, ``bootstrap``
settings, and ``application`` symbol helpers; it never imports
``infrastructure``, ``runner_*`` or ``interface``.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from shared.logger import EnhancedLogger
from shared.sync_logger import logger, OperationType, StatusType
from application.use_cases._sync_history import run_history_download, validate_downloaded_data
from application.use_cases._sync_timeframe import run_multitimeframe_update, validate_mtf_data
from application.use_cases._sync_resync import run_full_resync_process


@dataclass
class HistoryDownloadRequest:
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    timeframes: Optional[List[str]] = None
    exchange: str = "binance"


@dataclass
class MultiTimeframeUpdateRequest:
    symbols: List[str]
    timeframes: Optional[List[str]] = None
    force_update: bool = False


@dataclass
class ResyncRequest:
    symbols: Optional[List[str]] = None
    run_downloader: bool = True
    run_timeframes: bool = True
    run_retune: bool = True


class SyncMarketDataUseCase:
    """Run the data/sync features using container-provided ports."""

    def __init__(self,
                 settings,
                 file_repository: Optional[Any] = None,
                 data_downloader: Optional[Any] = None,
                 sync_manager: Optional[Any] = None,
                 watcher_retune: Optional[Any] = None) -> None:
        # Settings injected by the composition root (E1.T5); forwarded to the
        # _sync_resync flow instead of importing bootstrap.settings.loaders.
        self._settings = settings
        self._file_repository = file_repository
        self._data_downloader = data_downloader
        self._sync_manager = sync_manager
        self._watcher_retune = watcher_retune

    async def download_history(self, request: HistoryDownloadRequest) -> Dict[str, Any]:
        return await run_history_download(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            timeframes=request.timeframes,
            exchange=request.exchange,
            file_repo=self._file_repository,
            data_downloader=self._data_downloader,
            sync_manager=self._sync_manager,
        )

    def validate_download(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return validate_downloaded_data(results, self._file_repository)

    def update_multitimeframe(self, request: MultiTimeframeUpdateRequest) -> Dict[str, Any]:
        return run_multitimeframe_update(
            symbols=request.symbols,
            timeframes=request.timeframes,
            force_update=request.force_update,
            file_repo=self._file_repository,
        )

    def validate_mtf(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return validate_mtf_data(results, self._file_repository)

    async def resync(self, request: ResyncRequest) -> Dict[str, Any]:
        return await run_full_resync_process(
            settings=self._settings,
            symbols=request.symbols,
            run_downloader=request.run_downloader,
            run_timeframes=request.run_timeframes,
            run_retune=request.run_retune,
            file_repo=self._file_repository,
            data_downloader=self._data_downloader,
            sync_manager=self._sync_manager,
            watcher_retune=self._watcher_retune,
        )
