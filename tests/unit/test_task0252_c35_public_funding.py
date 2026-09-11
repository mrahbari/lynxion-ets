import json

import pytest

from scripts.collect_c35_public_funding import append_page, parse_page


def _body():
    return json.dumps([
        {"symbol": "BTCUSDT", "fundingTime": 1789113600000, "fundingRate": "0.0001"}
    ]).encode()


def test_parses_public_rate_and_complete_query_coverage():
    records, coverage = parse_page(
        "BTCUSDT", _body(), requested_start_ms=1789100000000, requested_end_ms=1789120000000
    )
    assert records[0]["funding_time"] == 1789113600
    assert records[0]["funding_rate"] == "0.0001"
    assert coverage["status"] == "COMPLETE_PUBLIC_RESPONSE"


def test_empty_response_still_proves_query_coverage():
    records, coverage = parse_page(
        "BTCUSDT", b"[]", requested_start_ms=1789100000000, requested_end_ms=1789120000000
    )
    assert records == []
    assert coverage["response_records"] == 0


def test_append_is_idempotent_for_rates_and_receipts(tmp_path):
    kwargs = {"requested_start_ms": 1789100000000, "requested_end_ms": 1789120000000}
    assert append_page(tmp_path, "BTCUSDT", _body(), **kwargs) == {"funding_records": 1, "coverage_receipts": 1}
    assert append_page(tmp_path, "BTCUSDT", _body(), **kwargs) == {"funding_records": 0, "coverage_receipts": 0}


def test_rejects_out_of_request_record():
    with pytest.raises(ValueError, match="outside request"):
        parse_page("BTCUSDT", _body(), requested_start_ms=1789120000001, requested_end_ms=1789130000000)
