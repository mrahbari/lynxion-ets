import json
import asyncio

import pytest

from scripts.collect_c33_liquidation_events import BOUNDARY, InvalidC33Event, lifecycle_record
from scripts.resume_c33_liquidation_collector import (
    recover_stale_session,
    resolve_pinned_commit,
    supervise,
)


def _write_rows(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_recover_stale_session_closes_exact_sole_session_without_backfill(tmp_path):
    path = tmp_path / "events.jsonl"
    session_id = "session-a"
    started_ms = (BOUNDARY + 100) * 1000
    closed_ms = started_ms + 1_000_000
    _write_rows(path, [lifecycle_record(session_id, "STARTED", started_ms, 1)])
    result = recover_stale_session(
        path, BOUNDARY, session_id, now_ms=closed_ms, monotonic_ns=2
    )
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert result == {
        "candidate": "C-33",
        "status": "STALE_SESSION_CLOSED",
        "session_id": session_id,
        "previous_latest_ms": started_ms,
        "closed_at_ms": closed_ms,
        "missing_interval_policy": "INELIGIBLE_NO_BACKFILL",
    }
    assert rows[-1] == lifecycle_record(session_id, "ENDED", closed_ms, 2)


def test_recover_stale_session_rejects_fresh_or_wrong_active_session(tmp_path):
    path = tmp_path / "events.jsonl"
    started_ms = (BOUNDARY + 100) * 1000
    _write_rows(path, [lifecycle_record("session-a", "STARTED", started_ms, 1)])
    with pytest.raises(InvalidC33Event, match="not stale"):
        recover_stale_session(
            path, BOUNDARY, "session-a", now_ms=started_ms + 100_000, monotonic_ns=2
        )
    with pytest.raises(InvalidC33Event, match="sole active"):
        recover_stale_session(
            path, BOUNDARY, "session-b", now_ms=started_ms + 1_000_000, monotonic_ns=2
        )


def test_resume_retains_pinned_commit_only_for_identical_collector_blob(tmp_path):
    manifest_path = tmp_path / "activation.json"
    manifest_path.write_text(json.dumps({"collector_commit": "pinned"}))
    values = {
        ("rev-parse", "HEAD:scripts/collect_c33_liquidation_events.py"): "same-blob",
        ("rev-parse", "pinned:scripts/collect_c33_liquidation_events.py"): "same-blob",
    }
    assert resolve_pinned_commit(manifest_path, lambda args: values[tuple(args)]) == "pinned"


def test_resume_rejects_changed_collector_blob(tmp_path):
    manifest_path = tmp_path / "activation.json"
    manifest_path.write_text(json.dumps({"collector_commit": "pinned"}))
    values = {
        ("rev-parse", "HEAD:scripts/collect_c33_liquidation_events.py"): "changed-blob",
        ("rev-parse", "pinned:scripts/collect_c33_liquidation_events.py"): "original-blob",
    }
    with pytest.raises(InvalidC33Event, match="source differs"):
        resolve_pinned_commit(manifest_path, lambda args: values[tuple(args)])


def test_resume_rejects_missing_manifest_commit(tmp_path):
    manifest_path = tmp_path / "activation.json"
    manifest_path.write_text("{}")
    with pytest.raises(InvalidC33Event, match="commit is invalid"):
        resolve_pinned_commit(manifest_path, lambda args: "unused")


def test_supervisor_retries_transient_disconnect_with_bounded_backoff(tmp_path, capsys):
    calls = []
    sleeps = []

    async def failing_collect(output, boundary):
        calls.append((output, boundary))
        raise ConnectionResetError("transient")

    async def fake_sleep(delay):
        sleeps.append(delay)

    asyncio.run(supervise(
        tmp_path / "events.jsonl", 100, collect_fn=failing_collect,
        sleep_fn=fake_sleep, monotonic_fn=lambda: 0, max_attempts=3,
    ))
    assert len(calls) == 3
    assert sleeps == [1, 2, 4]
    errors = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert errors == [{
        "attempt": attempt,
        "error": "transient",
        "error_type": "ConnectionResetError",
        "event": "c33_transient_disconnect",
    } for attempt in (1, 2, 3)]


def test_supervisor_caps_reconnect_delay(tmp_path):
    sleeps = []

    async def failing_collect(*_):
        raise OSError("transient")

    async def fake_sleep(delay):
        sleeps.append(delay)

    asyncio.run(supervise(
        tmp_path / "events.jsonl", 100, collect_fn=failing_collect,
        sleep_fn=fake_sleep, monotonic_fn=lambda: 0, max_attempts=8,
    ))
    assert sleeps == [1, 2, 4, 8, 16, 32, 60, 60]
