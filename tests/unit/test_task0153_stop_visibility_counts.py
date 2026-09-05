import json

from scripts.attribute_stop_visibility_failures import attribute


def _event(event_id, event_type, symbol="ADAUSDT", attempt=None, causal=None, accepted=None):
    event = {"event_id": event_id, "event_type": event_type, "symbol": symbol}
    if attempt is not None:
        event["attempt"] = attempt
    if causal is not None:
        event["causal_event_id"] = causal
    if accepted is not None:
        event["accepted"] = accepted
    return event


def test_counts_separate_response_and_visibility_outcomes_and_are_read_only(tmp_path):
    root = tmp_path / "forward"
    path = root / "events" / "2026-09-05.jsonl"
    path.parent.mkdir(parents=True)
    events = [
        _event("r1", "STOP_REPLACE_REQUESTED", attempt=1),
        _event("p1", "STOP_REPLACE_RESPONDED", causal="r1", accepted=True),
        _event("v1", "STOP_VISIBILITY_FAILED", causal="p1"),
        _event("r2", "STOP_REPLACE_REQUESTED", symbol="NEARUSDT", attempt=2),
        _event("p2", "STOP_REPLACE_RESPONDED", symbol="NEARUSDT", causal="r2", accepted=False),
        _event("r3", "STOP_REPLACE_REQUESTED", symbol="XRPUSDT", attempt=3),
    ]
    path.write_text("".join(json.dumps(event) + "\n" for event in events))
    before = path.read_bytes()
    first = attribute(root)
    assert first == attribute(root)
    assert path.read_bytes() == before
    assert first["request_count"] == 3
    assert first["cells"] == [
        {"symbol": "ADAUSDT", "attempt": 1, "response": "ACCEPTED", "visibility": "FAILED", "count": 1},
        {"symbol": "NEARUSDT", "attempt": 2, "response": "REJECTED", "visibility": "NOT_APPLICABLE", "count": 1},
        {"symbol": "XRPUSDT", "attempt": 3, "response": "MISSING_OR_AMBIGUOUS", "visibility": "NOT_APPLICABLE", "count": 1},
    ]
