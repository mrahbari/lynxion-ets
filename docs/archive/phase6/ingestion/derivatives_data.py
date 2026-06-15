"""Domain ports for derivatives market-data ingestion (Phase-6).

Funding rate and open interest — the free exchange-API data classes the
OHLCV-only system lacked. Kept SEPARATE from the streaming OHLCV ``DataDownloader``
(domain/ports/sync.py): those are low-volume historical pulls, so the port is
synchronous by design (no event-loop plumbing needed in the use case/CLI).
"""
from abc import ABC, abstractmethod
from typing import List


class DerivativesDataDownloader(ABC):
    """Port: fetch derivatives history from an exchange (funding, open interest)."""

    @abstractmethod
    def fetch_funding_rate_history(self, symbol: str, start_ms: int, end_ms: int) -> List[dict]:
        """Return [{timestamp(s), funding_rate}, ...] over [start_ms, end_ms]."""
        raise NotImplementedError

    @abstractmethod
    def fetch_open_interest_history(self, symbol: str, timeframe: str,
                                    start_ms: int, end_ms: int) -> List[dict]:
        """Return [{timestamp(s), open_interest, open_interest_value}, ...]."""
        raise NotImplementedError


class DerivativesStore(ABC):
    """Port: persist a derivatives time series (CSV + provenance), idempotently."""

    @abstractmethod
    def write_series(self, data_class: str, symbol: str, rows: List[dict],
                     columns: List[str], source: str, exchange: str) -> dict:
        """Persist rows for (data_class, symbol); return a summary dict."""
        raise NotImplementedError
