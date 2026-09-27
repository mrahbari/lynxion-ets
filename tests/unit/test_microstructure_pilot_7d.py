import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts/microstructure_pilot_7d.py"
    spec = importlib.util.spec_from_file_location("microstructure_pilot_7d", path)
    loaded = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def snapshot():
    return {"lastUpdateId": 100, "bids": [["10", "2"]], "asks": [["11", "3"]]}


def event(first=99, last=101, previous=98, bids=None, asks=None):
    return {"U": first, "u": last, "pu": previous,
            "b": bids if bids is not None else [["10", "4"]],
            "a": asks if asks is not None else []}


def test_bridge_continuity_and_zero_quantity_deletion():
    book = module().Book()
    book.snapshot(snapshot())
    assert not book.valid
    assert book.update(event(last=99)) == "pre_snapshot"
    assert book.update(event()) == "bridge"
    assert book.valid and book.last_u == 101
    assert book.update(event(102, 103, 101, bids=[["10", "0"], ["9", "1"]])) == "applied"
    assert list(book.bids) == [module().Decimal("9")]


def test_gap_invalidates_without_applying_unknown_state():
    book = module().Book()
    book.snapshot(snapshot())
    book.update(event())
    assert book.update(event(105, 106, 104, bids=[["20", "5"]])) == "gap"
    assert not book.valid and not book.bids and book.gaps == 1
    book.snapshot(snapshot())
    assert book.update(event()) == "bridge"


def test_duplicate_conflict_and_out_of_order_are_distinguished():
    book = module().Book()
    book.snapshot(snapshot())
    first = event()
    book.update(first)
    assert book.update(first) == "duplicate"
    assert book.duplicates == 1
    assert book.update(event(bids=[["10", "5"]])) == "conflicting_duplicate"
    assert not book.valid and book.out_of_order == 1
    book.snapshot(snapshot())
    book.update(first)
    assert book.update(event(98, 99, 97)) == "out_of_order"


def test_invalid_numeric_or_crossed_book_cannot_publish():
    book = module().Book()
    book.snapshot(snapshot())
    assert book.update(event(asks=[["9", "1"]])) == "invalid_book"
    assert not book.valid
    with pytest.raises(ValueError):
        book.snapshot({"lastUpdateId": 100, "bids": [["NaN", "1"]], "asks": [["11", "1"]]})


def test_raw_capture_retains_exact_payload_and_hash_and_refuses_overwrite(tmp_path):
    pilot = module()
    raw = pilot.RawCapture(tmp_path, "BTCUSDT", "fixed-session")
    payload = b'{"e":"depthUpdate", "U":99}'
    raw.append("depth", payload)
    files = raw.close()
    assert len(files) == 1
    path = Path(files[0]["path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == files[0]["sha256"]
    with gzip.open(path, "rb") as stream:
        envelope = json.loads(stream.readline())
    assert base64.b64decode(envelope["payload_b64"]) == payload
    second = pilot.RawCapture(tmp_path, "BTCUSDT", "fixed-session")
    with pytest.raises(FileExistsError):
        second.append("depth", payload)
