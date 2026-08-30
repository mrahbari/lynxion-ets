import importlib.util
import io
import zipfile
from pathlib import Path
from unittest.mock import Mock


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_binance_bookdepth_panel.py"
    spec = importlib.util.spec_from_file_location("bookdepth", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def archive(rows):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zipped:
        zipped.writestr("sample.csv", "timestamp,percentage,depth,notional\n" + "\n".join(rows) + "\n")
    return payload.getvalue()


def snapshot(timestamp, missing=None):
    evaluator = module()
    return [f"{timestamp},{level},{abs(level)},{abs(level) * 10}"
            for level in evaluator.LEVELS if level != missing]


def test_parser_accepts_complete_snapshot_and_rejects_incomplete(tmp_path):
    evaluator = module(); path = tmp_path / "sample.zip"
    path.write_bytes(archive(snapshot("2023-01-01 00:00:01") + snapshot("2023-01-01 00:00:31", 5)))
    rows, checks = evaluator.parse_archive(path)
    assert len(rows) == 1
    assert checks["incomplete_snapshots"] == 1


def test_parser_detects_conflicting_level_duplicate(tmp_path):
    evaluator = module(); path = tmp_path / "sample.zip"
    rows = snapshot("2023-01-01 00:00:01")
    rows.append("2023-01-01 00:00:01,-5,999,999")
    path.write_bytes(archive(rows))
    _, checks = evaluator.parse_archive(path)
    assert checks["conflicting_duplicates"] == 1


def test_parser_accepts_integer_levels_rendered_as_decimals(tmp_path):
    evaluator = module(); path = tmp_path / "sample.zip"
    rows = [row.replace(f",{level},", f",{level:.2f},")
            for level, row in zip(evaluator.LEVELS, snapshot("2026-01-14 00:00:09"))]
    path.write_bytes(archive(rows))

    parsed, checks = evaluator.parse_archive(path)

    assert len(parsed) == 1
    assert checks["level_violations"] == 0
    assert checks["numeric_violations"] == 0


def test_parser_measures_official_fractional_extra_levels_without_rejecting_snapshot(tmp_path):
    evaluator = module(); path = tmp_path / "sample.zip"
    rows = snapshot("2026-03-01 00:00:09")
    rows.extend(("2026-03-01 00:00:09,-0.20,1,10", "2026-03-01 00:00:09,0.20,1,10"))
    path.write_bytes(archive(rows))

    parsed, checks = evaluator.parse_archive(path)

    assert len(parsed) == 1
    assert checks["extra_level_rows"] == 2
    assert checks["level_violations"] == 0


def test_downsample_keeps_latest_complete_snapshot_per_bucket():
    evaluator = module()
    snapshots = [{"timestamp": 1, "levels": {}}, {"timestamp": 299, "levels": {}},
                 {"timestamp": 300, "levels": {}}]
    assert [row["timestamp"] for row in evaluator.downsample_five_minutes(snapshots)] == [299, 300]


def test_downloader_uses_bookdepth_symbol_and_resumes_legacy_layout(tmp_path):
    evaluator = module()
    payload = archive(snapshot("2023-01-01 00:00:01"))
    filename = "BTCUSDT-bookDepth-2023-01-01.zip"
    legacy = tmp_path / filename / filename
    legacy.parent.mkdir()
    legacy.write_bytes(payload)
    checksum = evaluator.hashlib.sha256(payload).hexdigest()
    response = Mock(text=f"{checksum}  {filename}")
    response.raise_for_status = Mock()
    get = Mock(return_value=response)

    record = evaluator.download_archive(
        f"data/futures/um/daily/bookDepth/BTCUSDT/{filename}", tmp_path, get=get
    )

    assert record["cached"] is True
    assert (tmp_path / "BTCUSDT" / filename).read_bytes() == payload
    assert get.call_count == 1
