import pytest

from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE
from scripts.verify_c35_funding_ledger import verify


def _coverage():
    return [{
        "candidate": "C-35", "symbol": symbol,
        "requested_start_ms": (BOUNDARY_EPOCH + 1) * 1000,
        "requested_end_ms": (BOUNDARY_EPOCH + 30_000) * 1000,
        "source_sha256": symbol.lower().ljust(64, "a"),
        "response_records": 1, "status": "COMPLETE_PUBLIC_RESPONSE",
    } for symbol in UNIVERSE]


def _funding():
    return [{
        "candidate": "C-35", "symbol": symbol,
        "funding_time": BOUNDARY_EPOCH + 10_000,
        "funding_rate": "0.0001", "source_sha256": symbol.lower().ljust(64, "a"),
    } for symbol in UNIVERSE]


def test_accepts_uniquely_sourced_complete_universe():
    report = verify(_funding(), _coverage())
    assert report["integrity"] == "PASS"
    assert report["funding_records"] == len(UNIVERSE)


def test_rejects_missing_coverage_symbol():
    with pytest.raises(ValueError, match="missing"):
        verify(_funding(), _coverage()[:-1])


def test_rejects_duplicate_settlement():
    funding = _funding()
    with pytest.raises(ValueError, match="duplicate"):
        verify(funding + [funding[0]], _coverage())


def test_rejects_unbound_source_hash():
    funding = _funding()
    funding[0]["source_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="source coverage"):
        verify(funding, _coverage())


def test_accepts_repeated_overlapping_query_with_same_source_body():
    coverage = _coverage()
    repeated = dict(coverage[0])
    repeated["requested_end_ms"] += 1000
    assert verify(_funding(), coverage + [repeated])["integrity"] == "PASS"
