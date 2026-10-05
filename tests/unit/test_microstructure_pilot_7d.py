import base64
import asyncio
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from types import SimpleNamespace

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


def test_post_stop_depth_is_rejected_before_raw_file_creation(tmp_path, monkeypatch):
    pilot = module()
    monkeypatch.setattr(pilot.time, "time_ns", lambda: 1_000)
    monkeypatch.setattr(pilot.time, "monotonic_ns", lambda: 900)
    raw = pilot.RawCapture(tmp_path, "BTCUSDT", "boundary")
    with pytest.raises(pilot.StopBoundaryReached):
        raw.append("depth", b"raw", deadline_ns=1_000)
    assert not list(tmp_path.iterdir())


def test_wall_monotonic_discontinuity_is_fail_closed_without_ntp_claim():
    pilot = module()
    pilot.require_continuous_clocks(100, 100, 1_000_000_100, 1_000_000_100)
    with pytest.raises(RuntimeError, match="wall_monotonic_discontinuity_ns=2000000000"):
        pilot.require_continuous_clocks(100, 100, 3_000_000_100, 1_000_000_100)


def test_hash_file_matches_finalized_chunk(tmp_path):
    pilot = module()
    raw = pilot.RawCapture(tmp_path, "ETHUSDT", "hash")
    raw.append("depth", b"exact raw bytes")
    item = raw.close()[0]
    assert pilot.hash_file(Path(item["path"])) == item["sha256"]


def test_technical_soak_cannot_be_confused_with_formal_pilot(tmp_path):
    pilot = module()
    contract = tmp_path / "contract.md"
    contract.write_text("frozen test contract")
    activation_path = tmp_path / "activation.json"
    base = {"symbols": list(pilot.SYMBOLS),
            "contract_sha256": pilot.hash_file(contract),
            "collector_sha256": pilot.hash_file(Path(pilot.__file__)),
            "websocket_base": pilot.WS_BASE,
            "rest_snapshot": f"{pilot.REST_BASE}?symbol=<symbol>&limit=1000",
            "start_utc_ns": 0, "stop_utc_ns": 20 * 60 * 10**9,
            "output_root": str(tmp_path / "not_a_soak"), "mode": "TECHNICAL_SOAK"}
    activation_path.write_text(json.dumps(base))
    with pytest.raises(ValueError, match="isolated soak"):
        asyncio.run(pilot.run(activation_path, contract))
    base["mode"] = "PILOT_7D"
    activation_path.write_text(json.dumps(base))
    with pytest.raises(ValueError, match="seven complete UTC days"):
        asyncio.run(pilot.run(activation_path, contract))


def test_disk_guard_refuses_soak_before_network_or_raw_writes(tmp_path, monkeypatch):
    pilot = module()
    contract = tmp_path / "contract.md"
    contract.write_text("frozen test contract")
    root = tmp_path / "soak" / "capture"
    start = time.time_ns() + 1_000_000_000
    activation = {"symbols": list(pilot.SYMBOLS), "mode": "TECHNICAL_SOAK",
                  "contract_sha256": pilot.hash_file(contract),
                  "collector_sha256": pilot.hash_file(Path(pilot.__file__)),
                  "websocket_base": pilot.WS_BASE,
                  "rest_snapshot": f"{pilot.REST_BASE}?symbol=<symbol>&limit=1000",
                  "start_utc_ns": start, "stop_utc_ns": start + 20 * 60 * 10**9,
                  "output_root": str(root)}
    activation_path = tmp_path / "activation.json"
    activation_path.write_text(json.dumps(activation))
    monkeypatch.setattr(pilot.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(RuntimeError, match="insufficient disk reserve"):
        asyncio.run(pilot.run(activation_path, contract))
    assert not (root / "capture_manifest.json").exists()
    assert not (root / "raw").exists()


def test_injected_transport_loss_starts_new_snapshot_epoch(tmp_path, monkeypatch):
    pilot = module()

    class FakeResponse:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        def raise_for_status(self):
            pass

        async def read(self):
            return json.dumps(snapshot()).encode()

    class FakeHttp:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        def get(self, *_args, **_kwargs):
            return FakeResponse()

    class FakeWs:
        def __init__(self):
            self.sent = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def recv(self):
            await asyncio.sleep(.01)
            if self.sent:
                raise ConnectionError("injected_transport_disconnect")
            self.sent = True
            now_ms = time.time_ns() // 1_000_000
            return json.dumps({"e": "depthUpdate", "s": "BTCUSDT", "E": now_ms,
                               "T": now_ms, **event()})

    monkeypatch.setattr(pilot.aiohttp, "ClientSession", lambda **_: FakeHttp())
    monkeypatch.setattr(pilot.websockets, "connect", lambda *_args, **_kwargs: FakeWs())
    root = tmp_path / "soak"
    root.mkdir()
    manifest = {"sessions": [], "failures": []}
    health = {"pid": 1, "symbols": {}}
    asyncio.run(pilot.capture_symbol("BTCUSDT", root, time.time_ns() + 3_100_000_000,
                                     manifest, health))
    assert len(manifest["sessions"]) >= 2
    assert len({s["session"] for s in manifest["sessions"]}) == len(manifest["sessions"])
    assert all(s["snapshots"] == 1 and s["applied"] >= 1 for s in manifest["sessions"])
    assert all(s["status"] == "CLOSED" and not s["book_valid_at_stop"]
               for s in manifest["sessions"])
    assert all(s["errors"][0]["detail"] == "injected_transport_disconnect"
               for s in manifest["sessions"])
