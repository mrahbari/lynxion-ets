import importlib.util
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_funding_holdout_c10.py"
    spec = importlib.util.spec_from_file_location("funding_c10", path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded


class Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


def row(timestamp, rate="-0.0001"):
    return {"symbol": "BTCUSDT", "fundingTime": timestamp, "fundingRate": rate}


def test_fetch_paginates_and_filters_end_range():
    evaluator = module(); pages = [[row(index) for index in range(1000)], [row(1000), row(1001)]]; calls = []
    def get(*args, **kwargs):
        calls.append(kwargs["params"]["startTime"]); return Response(pages.pop(0))
    rows = evaluator.fetch_symbol("BTCUSDT", 0, 1000, get=get, pause=0)
    assert calls == [0, 1000]
    assert [item["fundingTime"] for item in rows] == list(range(1001))


def test_fetch_rejects_non_increasing_page():
    evaluator = module()
    with pytest.raises(ValueError, match="non-increasing"):
        evaluator.fetch_symbol("BTCUSDT", 0, 10, get=lambda *a, **k: Response([row(1), row(1)]), pause=0)


def test_validate_detects_duplicate_invalid_and_range():
    evaluator = module(); rows = [row(0), row(0), row(20, "0.2")]
    checks = evaluator.validate(rows, 0, 10)
    assert checks["duplicate_count"] == 1
    assert checks["invalid_rate_count"] == 1
    assert checks["out_of_range_count"] == 1


def test_write_is_reproducible(tmp_path):
    evaluator = module(); rows = [row(0), row(1)]
    assert evaluator.write_csv(tmp_path / "a.csv", rows) == evaluator.write_csv(tmp_path / "b.csv", rows)
