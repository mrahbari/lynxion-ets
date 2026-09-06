import json
import asyncio

import pytest

from scripts.collect_c33_liquidation_events import (
    BOUNDARY,
    InvalidC33Event,
    activate,
    append_record,
    lifecycle_record,
    parse_heartbeat,
    parse_stream_message,
)
import scripts.collect_c33_liquidation_events as collector


def raw(payload):
    return json.dumps(payload, separators=(",", ":")).encode()


def liquidation(**overrides):
    trade_time = (BOUNDARY + 10) * 1000
    payload = {
        "e": "forceOrder",
        "E": trade_time + 1,
        "ps": "BTCUSDT",
        "st": 1,
        "o": {"s": "BTCUSDT", "S": "SELL", "q": "2", "z": "2", "ap": "50000", "X": "FILLED", "T": trade_time},
    }
    payload.update(overrides)
    return payload


def test_liquidation_parser_preserves_raw_identity_and_censored_notional():
    body = raw({"stream": "!forceOrder@arr", "data": liquidation()})
    result = parse_stream_message(body, receipt_monotonic_ns=10, session_id="run")
    assert result["record_type"] == "liquidation"
    assert result["observed_notional"] == 100_000
    assert result["snapshot_censored"] is True
    assert result["raw_sha256"] and result["raw_base64"]


def test_non_usdm_and_outside_universe_snapshots_are_ignored():
    assert parse_stream_message(raw(liquidation(st=2)), receipt_monotonic_ns=10, session_id="run") is None
    payload = liquidation(ps="UNIUSDT")
    payload["o"]["s"] = "UNIUSDT"
    assert parse_stream_message(raw(payload), receipt_monotonic_ns=10, session_id="run") is None


def test_pair_mismatch_fails_closed_and_nested_discriminator_is_accepted():
    with pytest.raises(InvalidC33Event, match="inconsistent"):
        parse_stream_message(raw(liquidation(ps="ETHUSDT")), receipt_monotonic_ns=10, session_id="run")
    payload = liquidation()
    payload["o"]["ps"] = payload.pop("ps")
    payload["o"]["st"] = payload.pop("st")
    assert parse_stream_message(raw(payload), receipt_monotonic_ns=10, session_id="run")["symbol"] == "BTCUSDT"


def test_invalid_fill_and_preboundary_fail_closed():
    payload = liquidation()
    payload["o"]["X"] = "NEW"
    with pytest.raises(InvalidC33Event, match="fill status"):
        parse_stream_message(raw(payload), receipt_monotonic_ns=10, session_id="run")
    payload = liquidation()
    payload["o"]["T"] = BOUNDARY * 1000
    with pytest.raises(InvalidC33Event, match="pre-boundary"):
        parse_stream_message(raw(payload), receipt_monotonic_ns=10, session_id="run")

    payload = liquidation()
    payload["o"]["q"] = "1"
    with pytest.raises(InvalidC33Event, match="exceeds original"):
        parse_stream_message(raw(payload), receipt_monotonic_ns=10, session_id="run")


def test_semantically_identical_decimal_format_has_same_dedupe_key():
    first = liquidation()
    second = liquidation()
    second["o"]["q"] = second["o"]["z"] = "2.00"
    second["o"]["ap"] = "50000.0"
    first_record = parse_stream_message(raw(first), receipt_monotonic_ns=10, session_id="run")
    second_record = parse_stream_message(raw(second), receipt_monotonic_ns=11, session_id="run")
    assert first_record["key"] == second_record["key"]


def test_only_closed_exact_one_minute_kline_is_persisted():
    start = ((BOUNDARY + 100) * 1000 // 60_000 + 1) * 60_000
    payload = {"e": "kline", "E": start + 60_000, "s": "BTCUSDT", "k": {
        "s": "BTCUSDT", "i": "1m", "x": False, "t": start, "T": start + 59_999,
        "o": "100", "h": "102", "l": "99", "c": "101",
    }}
    assert parse_stream_message(raw(payload), receipt_monotonic_ns=10, session_id="run") is None
    payload["k"]["x"] = True
    result = parse_stream_message(raw(payload), receipt_monotonic_ns=10, session_id="run")
    assert result["key"] == f"kline:BTCUSDT:{start}"
    assert result["close"] == 101

    payload["k"]["h"] = "100"
    with pytest.raises(InvalidC33Event, match="OHLC"):
        parse_stream_message(raw(payload), receipt_monotonic_ns=10, session_id="run")


def test_heartbeat_and_lifecycle_are_boundary_guarded():
    heartbeat = parse_heartbeat(
        raw({"serverTime": (BOUNDARY + 100) * 1000}), receipt_monotonic_ns=10, session_id="run"
    )
    assert heartbeat["record_type"] == "heartbeat"
    assert lifecycle_record("run", "STARTED", (BOUNDARY + 1) * 1000, 10)["state"] == "STARTED"
    with pytest.raises(InvalidC33Event):
        lifecycle_record("run", "STARTED", BOUNDARY * 1000, 10)


def test_append_is_idempotent_and_corruption_fails_closed(tmp_path):
    path = tmp_path / "events.jsonl"
    record = lifecycle_record("run", "STARTED", (BOUNDARY + 1) * 1000, 10)
    assert append_record(path, record) is True
    assert append_record(path, record) is False
    path.write_text("bad-json\n")
    with pytest.raises(InvalidC33Event, match="malformed JSON"):
        append_record(path, record)


def test_append_rejects_unknown_or_preboundary_records(tmp_path):
    with pytest.raises(InvalidC33Event, match="unknown or pre-boundary"):
        append_record(tmp_path / "events.jsonl", {"record_type": "unknown", "key": "x"})


def test_activation_creates_frozen_manifest_only_for_empty_output(tmp_path):
    output = tmp_path / "events.jsonl"
    manifest_path = tmp_path / "activation.json"
    manifest = activate(manifest_path, output, now=BOUNDARY + 100, commit="abc")
    assert manifest["activation_boundary"] == BOUNDARY + 100
    assert manifest["historical_import_allowed"] is False
    assert activate(manifest_path, output, now=BOUNDARY + 200, commit="abc") == manifest

    other_output = tmp_path / "nonempty.jsonl"
    other_output.write_text("x")
    with pytest.raises(InvalidC33Event, match="empty output"):
        activate(tmp_path / "other.json", other_output, now=BOUNDARY + 100, commit="abc")


def test_activation_rejects_commit_drift_and_post_prereg_pre_activation_row(tmp_path):
    output = tmp_path / "events.jsonl"
    manifest_path = tmp_path / "activation.json"
    activate(manifest_path, output, now=BOUNDARY + 100, commit="abc")
    with pytest.raises(InvalidC33Event, match="current launch"):
        activate(manifest_path, output, now=BOUNDARY + 200, commit="def")

    record = lifecycle_record("run", "STARTED", (BOUNDARY + 50) * 1000, 10)
    output.write_text(json.dumps(record) + "\n")
    with pytest.raises(InvalidC33Event, match="pre-boundary"):
        activate(manifest_path, output, now=BOUNDARY + 200, commit="abc")


def test_collect_waits_until_strictly_after_activation_boundary(monkeypatch, tmp_path):
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(collector.time, "time", lambda: BOUNDARY + 10.25)
    monkeypatch.setattr(collector.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(collector, "lifecycle_record", lambda *args: (_ for _ in ()).throw(RuntimeError("stop")))
    with pytest.raises(RuntimeError, match="stop"):
        asyncio.run(collector.collect(tmp_path / "events.jsonl", BOUNDARY + 10))
    assert sleeps == [pytest.approx(0.75)]
