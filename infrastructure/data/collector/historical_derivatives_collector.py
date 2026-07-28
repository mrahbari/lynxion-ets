"""Historical Derivatives Data Collector for Binance Futures REST API."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Set, Any
import httpx

from domain.ports.data_ports import DerivativesDataDownloaderPort
from domain.value_objects import Symbol, ExchangeTimestamp, Quantity, Money
from domain.entities.market_data import FundingRate, OpenInterest

logger = logging.getLogger("Lynxion.HistoricalDerivativesCollector")


class HistoricalDerivativesCollector(DerivativesDataDownloaderPort):
    """Production-grade historical derivatives data downloader and storage manager."""

    def __init__(
        self,
        rest_url: str = "https://fapi.binance.com",
        http_client: Optional[httpx.AsyncClient] = None,
        storage_dir: str = "data/cache/derivatives",
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ):
        self.rest_url = rest_url.rstrip("/")
        self._http_client = http_client
        self._owns_client = http_client is None
        self.storage_dir = storage_dir
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        os.makedirs(self.storage_dir, exist_ok=True)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=10.0)
            self._owns_client = True
        return self._http_client

    async def close(self) -> None:
        """Close http client if owned by this instance."""
        if self._owns_client and self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def fetch_funding_rates(
        self,
        symbol: Symbol,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[FundingRate]:
        """Fetch historical funding rates from Binance Futures REST API with pagination."""
        client = await self._get_client()
        url = f"{self.rest_url}/fapi/v1/fundingRate"

        start_ms = int(start_time.replace(tzinfo=timezone.utc).timestamp() * 1000) if start_time else None
        end_ms = int(end_time.replace(tzinfo=timezone.utc).timestamp() * 1000) if end_time else None

        all_rates: List[FundingRate] = []
        seen_keys: Set[int] = set()
        current_start_ms = start_ms

        while True:
            params: Dict[str, Any] = {
                "symbol": symbol.value,
                "limit": min(limit, 1000),
            }
            if current_start_ms is not None:
                params["startTime"] = current_start_ms
            if end_ms is not None:
                params["endTime"] = end_ms

            data = await self._request_with_retry(client, url, params)
            if not data or not isinstance(data, list):
                break

            new_count = 0
            max_item_time = 0

            for item in data:
                try:
                    ts_ms = int(item["fundingTime"])
                    if ts_ms in seen_keys:
                        continue
                    seen_keys.add(ts_ms)

                    rate_dec = Decimal(str(item["fundingRate"]))
                    next_ts_ms = int(item.get("nextFundingTime", ts_ms + 28_800_000))

                    entity = FundingRate(
                        symbol=symbol,
                        rate=rate_dec,
                        timestamp=ExchangeTimestamp(ts_ms),
                        next_funding_time=ExchangeTimestamp(next_ts_ms),
                    )
                    all_rates.append(entity)
                    new_count += 1
                    max_item_time = max(max_item_time, ts_ms)

                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Malformed funding rate item {item}: {e}")
                    continue

            if new_count == 0 or len(data) < min(limit, 1000):
                break

            current_start_ms = max_item_time + 1
            if end_ms is not None and current_start_ms >= end_ms:
                break

        all_rates.sort(key=lambda r: r.timestamp.millis)
        logger.info(f"Fetched {len(all_rates)} unique funding rates for {symbol.value}")
        return all_rates

    async def fetch_open_interest_history(
        self,
        symbol: Symbol,
        period: str = "1h",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OpenInterest]:
        """Fetch historical Open Interest series from Binance Futures REST API with pagination."""
        client = await self._get_client()
        url = f"{self.rest_url}/futures/data/openInterestHist"

        start_ms = int(start_time.replace(tzinfo=timezone.utc).timestamp() * 1000) if start_time else None
        end_ms = int(end_time.replace(tzinfo=timezone.utc).timestamp() * 1000) if end_time else None

        all_oi: List[OpenInterest] = []
        seen_keys: Set[int] = set()
        current_start_ms = start_ms

        while True:
            params: Dict[str, Any] = {
                "symbol": symbol.value,
                "period": period,
                "limit": min(limit, 500),
            }
            if current_start_ms is not None:
                params["startTime"] = current_start_ms
            if end_ms is not None:
                params["endTime"] = end_ms

            data = await self._request_with_retry(client, url, params)
            if not data or not isinstance(data, list):
                break

            new_count = 0
            max_item_time = 0

            for item in data:
                try:
                    ts_ms = int(item["timestamp"])
                    if ts_ms in seen_keys:
                        continue
                    seen_keys.add(ts_ms)

                    contracts = Decimal(str(item["sumOpenInterest"]))
                    quote_val = Decimal(str(item["sumOpenInterestValue"]))

                    entity = OpenInterest(
                        symbol=symbol,
                        value=Quantity(contracts, unit=symbol.value),
                        timestamp=ExchangeTimestamp(ts_ms),
                        value_quote=Money(quote_val, "USDT"),
                    )
                    all_oi.append(entity)
                    new_count += 1
                    max_item_time = max(max_item_time, ts_ms)

                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Malformed open interest item {item}: {e}")
                    continue

            if new_count == 0 or len(data) < min(limit, 500):
                break

            current_start_ms = max_item_time + 1
            if end_ms is not None and current_start_ms >= end_ms:
                break

        all_oi.sort(key=lambda o: o.timestamp.millis)
        logger.info(f"Fetched {len(all_oi)} unique open interest records for {symbol.value}")
        return all_oi

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Dict[str, Any],
    ) -> Optional[Any]:
        """Perform HTTP GET request with retries and rate limit handling."""
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code in (429, 418):
                    retry_after = float(resp.headers.get("Retry-After", 2.0))
                    logger.warning(f"Rate limited ({resp.status_code}). Waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                else:
                    logger.error(f"HTTP {resp.status_code} from {url}: {resp.text}")
                    if attempt == self.max_retries:
                        return None

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning(f"Network error on attempt {attempt}/{self.max_retries} for {url}: {e}")
                if attempt == self.max_retries:
                    return None

            await asyncio.sleep(self.backoff_factor * (2 ** (attempt - 1)))

        return None

    def save_funding_rates(self, symbol: Symbol, rates: List[FundingRate]) -> str:
        """Persist raw funding rate entities partitioned by symbol/year/month."""
        if not rates:
            return ""

        by_partition: Dict[str, List[Dict[str, Any]]] = {}
        for r in rates:
            dt = datetime.fromtimestamp(r.timestamp.millis / 1000.0, tz=timezone.utc)
            part_key = f"{dt.year}/{dt.month:02d}"
            if part_key not in by_partition:
                by_partition[part_key] = []
            by_partition[part_key].append(r.to_dict())

        saved_paths = []
        for part_key, records in by_partition.items():
            dir_path = os.path.join(self.storage_dir, "funding_rate", symbol.value, part_key)
            os.makedirs(dir_path, exist_ok=True)
            file_path = os.path.join(dir_path, "data.json")

            with open(file_path, "w") as f:
                json.dump(records, f, indent=2)
            saved_paths.append(file_path)

        return saved_paths[0] if saved_paths else ""

    def save_open_interest(self, symbol: Symbol, oi_list: List[OpenInterest]) -> str:
        """Persist raw open interest entities partitioned by symbol/year/month."""
        if not oi_list:
            return ""

        by_partition: Dict[str, List[Dict[str, Any]]] = {}
        for o in oi_list:
            dt = datetime.fromtimestamp(o.timestamp.millis / 1000.0, tz=timezone.utc)
            part_key = f"{dt.year}/{dt.month:02d}"
            if part_key not in by_partition:
                by_partition[part_key] = []
            by_partition[part_key].append(o.to_dict())

        saved_paths = []
        for part_key, records in by_partition.items():
            dir_path = os.path.join(self.storage_dir, "open_interest", symbol.value, part_key)
            os.makedirs(dir_path, exist_ok=True)
            file_path = os.path.join(dir_path, "data.json")

            with open(file_path, "w") as f:
                json.dump(records, f, indent=2)
            saved_paths.append(file_path)

        return saved_paths[0] if saved_paths else ""

    def load_funding_rates(self, symbol: Symbol, year: int, month: int) -> List[FundingRate]:
        """Load persisted funding rate entities for a given symbol, year, and month."""
        file_path = os.path.join(
            self.storage_dir, "funding_rate", symbol.value, f"{year}/{month:02d}", "data.json"
        )
        if not os.path.exists(file_path):
            return []

        with open(file_path, "r") as f:
            records = json.load(f)

        res = []
        for rec in records:
            res.append(
                FundingRate(
                    symbol=Symbol(rec["symbol"]),
                    rate=Decimal(rec["rate"]),
                    timestamp=ExchangeTimestamp(rec["timestamp"]),
                    next_funding_time=ExchangeTimestamp(rec["next_funding_time"]),
                )
            )
        res.sort(key=lambda r: r.timestamp.millis)
        return res

    def load_open_interest(self, symbol: Symbol, year: int, month: int) -> List[OpenInterest]:
        """Load persisted open interest entities for a given symbol, year, and month."""
        file_path = os.path.join(
            self.storage_dir, "open_interest", symbol.value, f"{year}/{month:02d}", "data.json"
        )
        if not os.path.exists(file_path):
            return []

        with open(file_path, "r") as f:
            records = json.load(f)

        res = []
        for rec in records:
            quote = (
                Money(Decimal(rec["value_quote"]["amount"]), rec["value_quote"]["currency"])
                if "value_quote" in rec
                else None
            )
            unit_val = rec["value"].get("unit", symbol.value)
            res.append(
                OpenInterest(
                    symbol=Symbol(rec["symbol"]),
                    value=Quantity(Decimal(rec["value"]["value"]), unit=unit_val),
                    timestamp=ExchangeTimestamp(rec["timestamp"]),
                    value_quote=quote,
                )
            )
        res.sort(key=lambda o: o.timestamp.millis)
        return res
