"""Acquire only the committed V2 public candle cohort; no signal or outcome work."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/path_integrity/canonical_replay/CONDITIONAL_SETUP_EDGE_V2_DATA_SPEC.md"
SPEC_SHA256 = "7df09233b82f6f6594b1963d4403a35f5323abde7acd48488743592e8775f86f"
SPEC_COMMIT = "4f5d9d4"
OUTPUT = ROOT / "data/research/conditional_setup_v2/candle_capture_v1"
ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
PAGES = ((1782864000000, 1788264000000, 1500),
         (1788264000000, 1790380800000, 588))


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def main():
    if hashlib.sha256(SPEC.read_bytes()).hexdigest() != SPEC_SHA256:
        raise ValueError("frozen acquisition specification hash mismatch")
    manifest_path = OUTPUT / "capture_manifest.json"
    if manifest_path.exists():
        raise FileExistsError("immutable capture manifest already exists")
    records = []
    for symbol in SYMBOLS:
        for page_number, (start_ms, end_ms, expected_rows) in enumerate(PAGES, 1):
            target_dir = OUTPUT / "raw" / symbol
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"page-{page_number:04d}.json"
            if target.exists():
                raise FileExistsError(f"immutable raw body already exists: {target}")
            url = (f"{ENDPOINT}?symbol={symbol}&interval=1h"
                   f"&startTime={start_ms}&endTime={end_ms-1}&limit=1500")
            with tempfile.NamedTemporaryFile(prefix=".capture-", dir=target_dir,
                                             delete=False) as temp:
                temp_path = Path(temp.name)
            requested_at = _utc_now()
            try:
                response = subprocess.run(
                    ["curl", "-q", "--proto", "=https", "--fail", "--silent",
                     "--show-error", "--max-time", "30", "--output", str(temp_path),
                     "--write-out", "%{http_code}", url],
                    check=True, capture_output=True, text=True,
                )
                received_at = _utc_now()
                raw = temp_path.read_bytes()
                rows = json.loads(raw)
                if response.stdout != "200" or not isinstance(rows, list) or len(rows) != expected_rows:
                    raise ValueError(f"unexpected public kline response for {symbol} page {page_number}")
                if any(not isinstance(row, list) or len(row) != 12 for row in rows):
                    raise ValueError("unexpected public kline row schema")
                if rows[0][0] != start_ms or rows[-1][0] != end_ms - 3_600_000:
                    raise ValueError("public response has wrong endpoint times")
                os.link(temp_path, target)
                records.append({
                    "symbol": symbol, "page": page_number,
                    "source": "Binance USD-M Futures public klines", "endpoint": ENDPOINT,
                    "request_url": url, "http_status": 200,
                    "requested_at_utc": requested_at, "received_at_utc": received_at,
                    "path": str(target.relative_to(ROOT)), "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(), "row_count": len(rows),
                    "first_open_time_ms": rows[0][0], "last_open_time_ms": rows[-1][0],
                    "first_close_time_ms": rows[0][6], "last_close_time_ms": rows[-1][6],
                })
            finally:
                temp_path.unlink(missing_ok=True)
    manifest = {
        "schema": "lynxion.conditional_setup_v2.public_candle_capture.v1",
        "status": "RAW_CAPTURED_NOT_QUALIFIED",
        "data_spec_sha256": SPEC_SHA256, "data_spec_commit": SPEC_COMMIT,
        "source_documentation": "https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data",
        "timeframe": "1h", "timezone": "UTC", "time_unit": "milliseconds",
        "acquisition_open_time_start_ms": PAGES[0][0],
        "acquisition_open_time_end_exclusive_ms": PAGES[-1][1],
        "warmup_open_time_start_utc": "2026-07-01T00:00:00+00:00",
        "evaluation_open_time_start_utc": "2026-07-04T00:00:00+00:00",
        "evaluation_open_time_end_exclusive_utc": "2026-09-26T00:00:00+00:00",
        "records": records,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print("V2 public raw candle capture complete; no signal or outcome calculated")


if __name__ == "__main__":
    main()
