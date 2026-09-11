import json

import pytest

from scripts.collect_c35_public_candles import append_page, parse_public_page
from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH


def _body(open_seconds, close_ms=None):
    open_ms = open_seconds * 1000
    close_ms = close_ms if close_ms is not None else open_ms + 899_999
    return json.dumps([[open_ms, "100", "101", "99", "100.5", "12", close_ms]]).encode()


def test_tags_warmup_and_prospective_strictly_at_boundary():
    warmup_open = BOUNDARY_EPOCH - (BOUNDARY_EPOCH % 900)
    warmup = parse_public_page("BTCUSDT", _body(warmup_open), now_ms=(BOUNDARY_EPOCH + 1000) * 1000)
    prospective_open = warmup_open + 900
    prospective = parse_public_page("BTCUSDT", _body(prospective_open), now_ms=(prospective_open + 1000) * 1000)
    assert warmup[0]["role"] == "WARMUP_ONLY"
    assert prospective[0]["role"] == "PROSPECTIVE"


def test_excludes_unclosed_candle():
    body = _body(1789092000, close_ms=1789092899999)
    assert parse_public_page("BTCUSDT", body, now_ms=1789092800000) == []


def test_append_is_idempotent_and_preserves_source_hash(tmp_path):
    path = tmp_path / "candles.jsonl"
    body = _body(1789092000)
    assert append_page(path, "BTCUSDT", body, now_ms=1789094000000) == 1
    assert append_page(path, "BTCUSDT", body, now_ms=1789094000000) == 0
    row = json.loads(path.read_text())
    assert len(row["source_sha256"]) == 64


def test_rejects_symbol_outside_frozen_universe(tmp_path):
    with pytest.raises(ValueError, match="outside frozen"):
        append_page(tmp_path / "candles.jsonl", "DOGEUSDT", _body(1789092000), now_ms=1789094000000)
