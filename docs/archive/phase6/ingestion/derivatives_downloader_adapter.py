"""CCXT adapter for derivatives ingestion (funding rate, open interest).

Implements domain.ports.derivatives_data.DerivativesDataDownloader against
Binance USDⓈ-M futures. Paginated history with bounded retry/backoff, mirroring
the posture of the OHLCV DataDownloaderAdapter. ccxt is imported lazily so this
module imports with no network/dependency surprise.

FREE endpoints only. Trade tape / L2 book / on-chain are approval-gated and not
implemented here.
"""
from __future__ import annotations

import time
from typing import List

from domain.ports.derivatives_data import DerivativesDataDownloader


def _with_retry(fn, attempts: int = 5, base: float = 0.5, factor: float = 2.0):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — bounded retry on transient exchange errors
            last = e
            if any(k in str(e).lower() for k in ("not found", "invalid symbol", "does not have")):
                raise
            time.sleep(base * (factor ** i))
    raise last


class CcxtDerivativesDownloader(DerivativesDataDownloader):
    def __init__(self, exchange: str = "binance", rate_limit_s: float = 0.2,
                 page_limit: int = 1000):
        self._exchange_name = exchange
        self._rate_limit_s = rate_limit_s
        self._page_limit = page_limit
        self._ex = None

    def _exchange(self):
        if self._ex is None:
            import ccxt  # lazy
            self._ex = getattr(ccxt, self._exchange_name)(
                {"enableRateLimit": True, "options": {"defaultType": "future"}})
            _with_retry(self._ex.load_markets)
        return self._ex

    @staticmethod
    def _sym(symbol: str) -> str:
        if "/" in symbol:
            return symbol
        s = symbol.replace("-", "").upper()
        base = s[:-4] if s.endswith("USDT") else s
        return f"{base}/USDT:USDT"   # binance perpetual

    def fetch_funding_rate_history(self, symbol: str, start_ms: int, end_ms: int) -> List[dict]:
        ex, sym, since, out = self._exchange(), self._sym(symbol), start_ms, []
        while since < end_ms:
            page = _with_retry(lambda s=since: ex.fetch_funding_rate_history(
                sym, since=s, limit=self._page_limit))
            if not page:
                break
            for f in page:
                ts = int(f["timestamp"])
                if ts > end_ms:
                    break
                out.append({"timestamp": ts // 1000, "funding_rate": float(f["fundingRate"])})
            nxt = int(page[-1]["timestamp"]) + 1
            if nxt <= since:
                break
            since = nxt
            time.sleep(self._rate_limit_s)
        return out

    def fetch_open_interest_history(self, symbol: str, timeframe: str,
                                    start_ms: int, end_ms: int) -> List[dict]:
        ex, sym, since, out = self._exchange(), self._sym(symbol), start_ms, []
        while since < end_ms:
            page = _with_retry(lambda s=since: ex.fetch_open_interest_history(
                sym, timeframe=timeframe, since=s, limit=500))
            if not page:
                break
            for o in page:
                ts = int(o["timestamp"])
                if ts > end_ms:
                    break
                info = o.get("info", {})
                out.append({
                    "timestamp": ts // 1000,
                    "open_interest": float(o.get("openInterestAmount")
                                           or info.get("sumOpenInterest") or 0.0),
                    "open_interest_value": float(o.get("openInterestValue")
                                                 or info.get("sumOpenInterestValue") or 0.0)})
            nxt = int(page[-1]["timestamp"]) + 1
            if nxt <= since:
                break
            since = nxt
            time.sleep(self._rate_limit_s)
        return out
