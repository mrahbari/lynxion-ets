"""Fetch the frozen Phase 3A window from unauthenticated Binance perp public API."""
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.fetch_aligned_futures_panel import fetch_symbol, validate, write_csv, epoch_ms

PHASE = ROOT / "research/external_signal_study/phase3_point_in_time"
DATA = ROOT / "data/research/phase3_point_in_time/binance_futures_15m"
SPEC = PHASE / "preregistration/PHASE3_RESEARCH_SPEC.md"
EXPECTED_SPEC = "96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193"
EXCHANGE_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"
END = "2026-09-13T23:45:00+00:00"
DEFAULT_START = "2026-08-08T00:00:00+00:00"
BTC_START = "2026-07-08T00:00:00+00:00"  # 30 closed daily BTC bars for earliest M2 control
BAR_MS = 900_000


def main():
    assert hashlib.sha256(SPEC.read_bytes()).hexdigest() == EXPECTED_SPEC, "frozen spec changed"
    with (PHASE / "extracted/phase3_cases.csv").open(newline="", encoding="utf-8") as handle:
        cases = [r for r in csv.DictReader(handle) if r["primary_hmt_eligible"] == "YES"]
    assert len(cases) == 58
    symbols = sorted({r["symbol"] for r in cases} | {"BTCUSDT"})
    response = requests.get(EXCHANGE_INFO, timeout=30)
    response.raise_for_status()
    source_body = response.content
    listed = {r["symbol"]: r for r in response.json()["symbols"]}
    manifest = {
        "purpose": "Phase 3A frozen case/control point-in-time proxy coverage only; no outcomes",
        "source_venue": "Binance", "instrument": "USDT perpetual futures",
        "kline_endpoint": "https://fapi.binance.com/fapi/v1/klines",
        "exchange_info_endpoint": EXCHANGE_INFO,
        "exchange_info_sha256": hashlib.sha256(source_body).hexdigest(),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "interval": "15m", "timestamp_semantics": "CSV timestamp is bar OPEN epoch seconds; bar close is open+899 seconds; closed bar usable only if close_time<=event_time",
        "requested_end_open_utc": END,
        "preregistration_sha256": EXPECTED_SPEC,
        "symbols": {},
    }
    for symbol in symbols:
        info = listed.get(symbol)
        start = BTC_START if symbol == "BTCUSDT" else DEFAULT_START
        item = {"requested_start_open_utc": start, "requested_end_open_utc": END}
        if not info or info.get("contractType") != "PERPETUAL" or info.get("quoteAsset") != "USDT":
            item["status"] = "NO_VERIFIED_CURRENT_PERPETUAL_LISTING"
            manifest["symbols"][symbol] = item
            continue
        item.update(contract_status_at_retrieval=info.get("status"), onboard_date_ms=info.get("onboardDate"))
        if not isinstance(info.get("onboardDate"), int) or info["onboardDate"] > epoch_ms(start):
            item["status"] = "LISTING_NOT_VERIFIED_FOR_FULL_WINDOW"
            manifest["symbols"][symbol] = item
            continue
        start_ms, end_ms = epoch_ms(start), epoch_ms(END)
        rows = fetch_symbol(symbol, start_ms, end_ms, pause=0.12)
        checks = validate(rows, start_ms, end_ms)
        expected_rows = (end_ms - start_ms) // BAR_MS + 1
        close_semantics_ok = all(int(r[6]) == int(r[0]) + BAR_MS - 1 for r in rows)
        complete = (
            len(rows) == expected_rows and
            checks["first_timestamp"] == start_ms // 1000 and
            checks["last_timestamp"] == end_ms // 1000 and
            all(checks[k] == 0 for k in ("duplicate_count", "missing_interval_count", "nonpositive_count", "ohlc_violation_count", "out_of_range_count")) and
            close_semantics_ok
        )
        item.update(checks)
        item["expected_rows"] = expected_rows
        item["close_semantics_ok"] = close_semantics_ok
        item["status"] = "COMPLETE_VALIDATED" if complete else "INCOMPLETE_OR_INVALID"
        item["sha256"] = write_csv(DATA / f"{symbol}.csv", rows)
        manifest["symbols"][symbol] = item
        print(f"{symbol}: {item['status']} {len(rows)}/{expected_rows}", flush=True)
    path = PHASE / "manifests/phase3_proxy_source_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"manifest={path} complete={sum(x['status']=='COMPLETE_VALIDATED' for x in manifest['symbols'].values())}/{len(symbols)}")


if __name__ == "__main__":
    main()
