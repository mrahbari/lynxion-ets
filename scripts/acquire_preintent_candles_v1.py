"""Acquire only the pre-frozen public 1h candle cohort; never call trading APIs.

The addendum and endpoint are constants so a changed date/source requires a
new reviewed protocol rather than a runtime flag. Raw responses are linked
into place without replacement. No outcome or signal calculation occurs here.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "docs/path_integrity/canonical_replay/PRE_INTENT_SIGNAL_STUDY_PREREGISTRATION.md"
ADDENDUM = ROOT / "docs/path_integrity/canonical_replay/DATA_ONLY_PREREGISTRATION_ADDENDUM_V1.md"
OUTPUT = ROOT / "data/research/pre_intent/candle_capture_v1"
PARENT_HASH = "454485ff11fad12a9ad355517d3c1461b1df1676e182937c6c2d7e02d10a8cac"
ADDENDUM_HASH = "b17e50a75591b26d08f435d460e9a9a8ca928ef0aab633b73de2ba495416bae5"
START_MS = 1780185600000
END_MS_INCLUSIVE = 1782950399999
EXPECTED_ROWS = 768
ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    if digest(PARENT) != PARENT_HASH or digest(ADDENDUM) != ADDENDUM_HASH:
        raise RuntimeError("frozen protocol hash mismatch; acquisition forbidden")
    if (OUTPUT / "capture_manifest.json").exists():
        raise FileExistsError("immutable capture manifest already exists")

    records = []
    for symbol in SYMBOLS:
        target_dir = OUTPUT / "raw" / symbol
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "page-0001.json"
        if target.exists():
            raise FileExistsError(f"immutable raw response already exists: {target}")
        url = (f"{ENDPOINT}?symbol={symbol}&interval=1h"
               f"&startTime={START_MS}&endTime={END_MS_INCLUSIVE}&limit=1500")
        with tempfile.NamedTemporaryFile(prefix=".capture-", dir=target_dir, delete=False) as temp:
            temp_path = Path(temp.name)
        request_at = now_utc()
        try:
            result = subprocess.run(
                ["curl", "-q", "--proto", "=https", "--fail", "--silent",
                 "--show-error", "--max-time", "30", "--output", str(temp_path),
                 "--write-out", "%{http_code}", url],
                check=True, capture_output=True, text=True,
            )
            received_at = now_utc()
            body = temp_path.read_bytes()
            rows = json.loads(body)
            if result.stdout != "200" or not isinstance(rows, list) or len(rows) != EXPECTED_ROWS:
                raise ValueError(f"unexpected public response metadata for {symbol}")
            if any(not isinstance(row, list) or len(row) != 12 for row in rows):
                raise ValueError(f"unexpected kline row schema for {symbol}")
            os.link(temp_path, target)  # fails rather than overwriting immutable data
            records.append({
                "symbol": symbol, "source": "Binance USD-M Futures public klines",
                "endpoint": ENDPOINT, "request_url": url, "http_status": 200,
                "request_at_utc": request_at, "received_at_utc": received_at,
                "path": str(target.relative_to(ROOT)), "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(), "row_count": len(rows),
                "first_open_time_ms": rows[0][0], "last_open_time_ms": rows[-1][0],
                "first_close_time_ms": rows[0][6], "last_close_time_ms": rows[-1][6],
            })
        finally:
            temp_path.unlink(missing_ok=True)

    manifest = {
        "schema": "lynxion.pre_intent.candle_capture.v1",
        "status": "RAW_CAPTURED_NOT_QUALIFIED",
        "parent_preregistration_sha256": PARENT_HASH,
        "data_addendum_sha256": ADDENDUM_HASH,
        "data_addendum_commit": "5dd7906",
        "source_documentation": "https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data",
        "timeframe": "1h", "timezone": "UTC", "time_unit": "milliseconds",
        "acquisition_open_time_start_ms": START_MS,
        "acquisition_open_time_end_exclusive_ms": END_MS_INCLUSIVE + 1,
        "evaluation_open_time_start_utc": "2026-06-03T02:00:00+00:00",
        "evaluation_open_time_end_exclusive_utc": "2026-07-01T00:00:00+00:00",
        "records": records,
    }
    target = OUTPUT / "capture_manifest.json"
    with target.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print("public candle raw capture complete; qualification and outcomes not run")


if __name__ == "__main__":
    main()
