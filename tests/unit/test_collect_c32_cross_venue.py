import json

import pytest

from scripts.collect_c32_cross_venue import (
    BOUNDARY,
    InvalidObservation,
    append_observation,
    build_observation,
    depth_vwap,
    parse_book,
)


def raw_book(*, bid, ask, timestamp, bingx=False, bid_qty=20, ask_qty=20):
    book = {"T": timestamp, "bids": [[str(bid), str(bid_qty)]], "asks": [[str(ask), str(ask_qty)]]}
    payload = {"code": 0, "data": book} if bingx else book
    return json.dumps(payload, separators=(",", ":")).encode()


def test_parse_book_normalizes_both_venues():
    assert parse_book("binance", json.loads(raw_book(bid=99, ask=100, timestamp=1)))["bids"] == [(99.0, 20.0)]
    assert parse_book("bingx", json.loads(raw_book(bid=99, ask=100, timestamp=1, bingx=True)))["asks"] == [(100.0, 20.0)]


def test_depth_vwap_walks_levels_and_rejects_partial_depth():
    assert depth_vwap([(100.0, 2.0), (101.0, 3.0)], 4.0) == pytest.approx(100.5)
    with pytest.raises(InvalidObservation, match="insufficient depth"):
        depth_vwap([(100.0, 1.0)], 2.0)


def test_observation_uses_identical_quantity_and_executable_direction():
    now = 1_800_000_000_000
    result = build_observation(
        scheduled_minute=1_800_000_000,
        symbol="BTCUSDT",
        binance_raw=raw_book(bid=101, ask=102, timestamp=now - 500),
        bingx_raw=raw_book(bid=99, ask=100, timestamp=now - 400, bingx=True),
        comparison_time_ms=now,
        receipt_monotonic_ns={"binance": 1_000_000_000, "bingx": 1_100_000_000},
    )
    assert result["base_quantity"] == pytest.approx(1_000 / 102)
    assert result["signal_direction"] == "SELL_BINANCE_BUY_BINGX"
    assert result["gross_spreads"]["SELL_BINANCE_BUY_BINGX"] == pytest.approx(0.01)


@pytest.mark.parametrize(
    "binance_ts,bingx_ts,now,message",
    [
        (1000, 3001, 3001, "timestamp skew"),
        (1000, 1001, 5002, "stale"),
        (5001, 5000, 5000, "future-dated"),
    ],
)
def test_time_validation_fails_closed(binance_ts, bingx_ts, now, message):
    with pytest.raises(InvalidObservation, match=message):
        build_observation(
            scheduled_minute=1_800_000_000,
            symbol="BTCUSDT",
            binance_raw=raw_book(bid=99, ask=100, timestamp=binance_ts),
            bingx_raw=raw_book(bid=99, ask=100, timestamp=bingx_ts, bingx=True),
            comparison_time_ms=now,
            receipt_monotonic_ns={"binance": 1_000_000_000, "bingx": 1_100_000_000},
        )


def test_malformed_or_crossed_book_fails_closed():
    with pytest.raises(InvalidObservation, match="crossed"):
        parse_book("binance", {"T": 1, "bids": [["101", "1"]], "asks": [["100", "1"]]})
    with pytest.raises(InvalidObservation, match="valid JSON"):
        build_observation(
            scheduled_minute=1_800_000_000,
            symbol="BTCUSDT",
            binance_raw=b"not-json",
            bingx_raw=b"{}",
            comparison_time_ms=1,
            receipt_monotonic_ns={"binance": 1_000_000_000, "bingx": 1_100_000_000},
        )
    with pytest.raises(InvalidObservation, match="malformed level"):
        parse_book("binance", {"T": 1, "bids": [None], "asks": [["100", "1"]]})
    with pytest.raises(InvalidObservation, match="numeric"):
        parse_book("binance", {"T": 1, "bids": [["x", "1"]], "asks": [["100", "1"]]})


def test_receipt_skew_fails_closed():
    now = 1_800_000_000_000
    with pytest.raises(InvalidObservation, match="receipt skew"):
        build_observation(
            scheduled_minute=1_800_000_000,
            symbol="BTCUSDT",
            binance_raw=raw_book(bid=99, ask=100, timestamp=now - 10),
            bingx_raw=raw_book(bid=99, ask=100, timestamp=now - 10, bingx=True),
            comparison_time_ms=now,
            receipt_monotonic_ns={"binance": 1, "bingx": 2_000_000_002},
        )


def test_boundary_and_duplicate_append_are_fail_closed(tmp_path):
    path = tmp_path / "observations.jsonl"
    observation = {"key": "1800000000:BTCUSDT", "scheduled_minute": 1_800_000_000}
    assert append_observation(path, observation) is True
    assert append_observation(path, observation) is False
    with pytest.raises(InvalidObservation, match="pre-boundary"):
        append_observation(path, {"key": "old", "scheduled_minute": BOUNDARY})


def test_existing_preboundary_or_duplicate_ledger_is_rejected(tmp_path):
    path = tmp_path / "observations.jsonl"
    path.write_text(json.dumps({"key": "old", "scheduled_minute": BOUNDARY}) + "\n")
    with pytest.raises(InvalidObservation, match="pre-boundary"):
        append_observation(path, {"key": "new", "scheduled_minute": 1_800_000_000})

    path.write_text("not-json\n")
    with pytest.raises(InvalidObservation, match="malformed JSON"):
        append_observation(path, {"key": "new", "scheduled_minute": 1_800_000_000})
