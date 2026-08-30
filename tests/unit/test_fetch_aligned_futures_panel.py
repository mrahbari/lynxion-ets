import importlib.util
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_aligned_futures_panel.py"
    spec = importlib.util.spec_from_file_location("futures_panel", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def kline(opened, price=100):
    return [opened, str(price), str(price + 1), str(price - 1), str(price), "10", opened + 899_999]


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_fetch_paginates_deduplicates_and_filters_closed_range():
    evaluator = module()
    step = evaluator.INTERVAL_MS
    pages = [
        [kline(index * step) for index in range(1500)],
        [kline(index * step) for index in range(1500, 1502)],
    ]
    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs["params"]["startTime"])
        return Response(pages.pop(0))

    rows = evaluator.fetch_symbol("BTCUSDT", 0, 1500 * step, get=get, pause=0)

    assert calls == [0, 1500 * step]
    assert [row[0] for row in rows] == [index * step for index in range(1501)]


def test_fetch_rejects_non_advancing_page():
    evaluator = module()

    def get(*args, **kwargs):
        return Response([kline(kwargs["params"]["startTime"] - evaluator.INTERVAL_MS)])

    with pytest.raises(ValueError, match="did not advance"):
        evaluator.fetch_symbol("BTCUSDT", 0, evaluator.INTERVAL_MS, get=get, pause=0)


def test_validate_detects_gap_bad_ohlc_and_nonpositive():
    evaluator = module()
    step = evaluator.INTERVAL_MS
    rows = [kline(0), [2 * step, "0", "90", "95", "100", "10", 3 * step - 1]]

    result = evaluator.validate(rows, 0, 2 * step)

    assert result["missing_interval_count"] == 1
    assert result["nonpositive_count"] == 1
    assert result["ohlc_violation_count"] == 1


def test_write_csv_has_reproducible_hash(tmp_path):
    evaluator = module()
    rows = [kline(0), kline(evaluator.INTERVAL_MS)]
    first = evaluator.write_csv(tmp_path / "first.csv", rows)
    second = evaluator.write_csv(tmp_path / "second.csv", rows)

    assert first == second


def test_build_panel_records_explicit_task_and_bounds(tmp_path, monkeypatch):
    evaluator = module()
    monkeypatch.setattr(evaluator, "SYMBOLS", ("BTCUSDT",))
    monkeypatch.setattr(evaluator, "fetch_symbol", lambda *args, **kwargs: [kline(0)])

    manifest = evaluator.build_panel(
        tmp_path, pause=0, start="1970-01-01T00:00:00+00:00",
        end="1970-01-01T00:00:00+00:00", task="TASK-TEST",
    )

    assert manifest["task"] == "TASK-TEST"
    assert manifest["requested_start"] == "1970-01-01T00:00:00+00:00"
