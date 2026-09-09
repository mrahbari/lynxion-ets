import json
import asyncio

import pytest

from scripts.collect_c33_liquidation_events import InvalidC33Event
from scripts.resume_c33_liquidation_collector import resolve_pinned_commit, supervise


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
