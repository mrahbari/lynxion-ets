"""Fail-closed, outcome-blind qualification of the frozen V2 public candles."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path

from infrastructure.replay.historical_closed_bar_source import ClosedBar, HistoricalClosedBarSource


ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "data/research/conditional_setup_v2/candle_capture_v1/capture_manifest.json"
SPEC = ROOT / "docs/path_integrity/canonical_replay/CONDITIONAL_SETUP_EDGE_V2_DATA_SPEC.md"
SPEC_SHA256 = "7df09233b82f6f6594b1963d4403a35f5323abde7acd48488743592e8775f86f"
START_MS = 1782864000000
END_MS = 1790380800000
HOUR_MS = 3600000
SYMBOLS = ("BTCUSDT", "ETHUSDT")
PAGES = ((START_MS, 1788264000000, 1500), (1788264000000, END_MS, 588))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def qualify_capture(root=ROOT, manifest_path=CAPTURE):
    """Return closed bars and qualification facts, never future labels."""
    root = Path(root).resolve()
    manifest_path = Path(manifest_path)
    if digest((root / SPEC.relative_to(ROOT)).read_bytes()) != SPEC_SHA256:
        raise ValueError("frozen V2 data specification changed")
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    if (manifest.get("schema") != "lynxion.conditional_setup_v2.public_candle_capture.v1"
            or manifest.get("status") != "RAW_CAPTURED_NOT_QUALIFIED"
            or manifest.get("data_spec_sha256") != SPEC_SHA256
            or manifest.get("data_spec_commit") != "4f5d9d4"
            or manifest.get("acquisition_open_time_start_ms") != START_MS
            or manifest.get("acquisition_open_time_end_exclusive_ms") != END_MS
            or manifest.get("timeframe") != "1h" or manifest.get("timezone") != "UTC"
            or manifest.get("time_unit") != "milliseconds"
            or manifest.get("warmup_open_time_start_utc") != "2026-07-01T00:00:00+00:00"
            or manifest.get("evaluation_open_time_start_utc") != "2026-07-04T00:00:00+00:00"
            or manifest.get("evaluation_open_time_end_exclusive_utc") != "2026-09-26T00:00:00+00:00"):
        raise ValueError("frozen V2 capture manifest contract mismatch")
    records = manifest.get("records")
    if not isinstance(records, list) or len(records) != 4:
        raise ValueError("V2 capture must contain exactly four public pages")
    all_bars = []
    page_facts = []
    for index, record in enumerate(records):
        symbol = SYMBOLS[index // 2]
        page_number = index % 2 + 1
        start, end, count = PAGES[page_number - 1]
        expected_url = ("https://fapi.binance.com/fapi/v1/klines?"
                        f"symbol={symbol}&interval=1h&startTime={start}&endTime={end-1}&limit=1500")
        expected_path = (f"data/research/conditional_setup_v2/candle_capture_v1/raw/"
                         f"{symbol}/page-{page_number:04d}.json")
        if (record.get("symbol") != symbol or record.get("page") != page_number
                or record.get("path") != expected_path or record.get("request_url") != expected_url
                or record.get("endpoint") != "https://fapi.binance.com/fapi/v1/klines"
                or record.get("source") != "Binance USD-M Futures public klines"
                or record.get("http_status") != 200 or record.get("row_count") != count):
            raise ValueError(f"frozen V2 request/provenance mismatch: {symbol} page {page_number}")
        requested = datetime.fromisoformat(record["requested_at_utc"])
        received = datetime.fromisoformat(record["received_at_utc"])
        if (requested.tzinfo is None or received.tzinfo is None or requested > received
                or received.astimezone(timezone.utc) < datetime.fromtimestamp(END_MS / 1000, timezone.utc)):
            raise ValueError("capture timestamp invalid or final bar incomplete")
        raw_path = (root / expected_path).resolve()
        if root not in raw_path.parents:
            raise ValueError("capture path escapes repository")
        raw = raw_path.read_bytes()
        if digest(raw) != record.get("sha256") or len(raw) != record.get("bytes"):
            raise ValueError("immutable V2 raw response hash/size mismatch")
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) != count:
            raise ValueError("V2 raw page count mismatch")
        if (rows[0][0] != record.get("first_open_time_ms")
                or rows[-1][0] != record.get("last_open_time_ms")
                or rows[0][6] != record.get("first_close_time_ms")
                or rows[-1][6] != record.get("last_close_time_ms")):
            raise ValueError("V2 raw page boundary mismatch")
        for offset, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != 12:
                raise ValueError("V2 kline schema mismatch")
            open_ms = start + offset * HOUR_MS
            if (type(row[0]) is not int or type(row[6]) is not int
                    or row[0] != open_ms or row[6] != open_ms + HOUR_MS - 1):
                raise ValueError("V2 candle gap, duplicate, ordering, or close-time defect")
            try:
                o, h, l, c, v = (float(row[field]) for field in range(1, 6))
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("V2 nonnumeric OHLCV") from exc
            if (not all(isfinite(value) for value in (o, h, l, c, v))
                    or min(o, h, l, c) <= 0 or v < 0 or l > min(o, c) or h < max(o, c)):
                raise ValueError("V2 invalid OHLCV")
            all_bars.append(ClosedBar(
                symbol=symbol, timeframe=timedelta(hours=1),
                open_time=datetime.fromtimestamp(open_ms / 1000, timezone.utc),
                close_time=datetime.fromtimestamp((row[6] + 1) / 1000, timezone.utc),
                open=o, high=h, low=l, close=c, volume=v,
            ))
        page_facts.append({"symbol": symbol, "page": page_number,
                           "rows": count, "sha256": digest(raw)})
    bars = tuple(sorted(all_bars, key=lambda bar: (bar.close_time, bar.symbol)))
    HistoricalClosedBarSource(bars)
    return bars, {"capture_manifest_sha256": digest(manifest_raw),
                  "pages": page_facts, "rows_per_symbol": 2088,
                  "warmup_per_symbol": 72, "evaluation_per_symbol": 2016,
                  "first_open_time_utc": "2026-07-01T00:00:00+00:00",
                  "last_availability_utc": "2026-09-26T00:00:00+00:00",
                  "gaps": 0, "duplicates": 0, "invalid_ohlcv": 0}
