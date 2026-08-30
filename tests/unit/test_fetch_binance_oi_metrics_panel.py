import hashlib
import importlib.util
import io
import zipfile
from pathlib import Path


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_binance_oi_metrics_panel.py"
    spec = importlib.util.spec_from_file_location("oi_panel", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def archive(rows):
    evaluator = module()
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as zipped:
        body = ",".join(evaluator.EXPECTED_COLUMNS) + "\n" + "\n".join(rows) + "\n"
        zipped.writestr("sample.csv", body)
    return payload.getvalue()


def test_checksum_parser_binds_hash_to_filename():
    evaluator = module()
    digest = "a" * 64
    assert evaluator.expected_checksum(f"{digest}  sample.zip\n", "sample.zip") == digest


def test_archive_parser_deduplicates_exact_rows_and_rejects_conflicts(tmp_path):
    evaluator = module()
    first = "2020-09-01 00:00:00,BTCUSDT,1,2,1,1,1,1"
    conflict = "2020-09-01 00:00:00,BTCUSDT,2,2,1,1,1,1"
    path = tmp_path / "sample.zip"
    path.write_bytes(archive([first, first, conflict]))
    rows, checks = evaluator.parse_archive(path, "BTCUSDT")
    assert len(rows) == 1
    assert checks["exact_duplicates"] == 1
    assert checks["conflicting_duplicates"] == 1


def test_download_verifies_official_sha256_and_resumes(tmp_path):
    evaluator = module()
    payload = archive(["2020-09-01 00:00:00,BTCUSDT,1,2,1,1,1,1"])
    digest = hashlib.sha256(payload).hexdigest()

    class Response:
        def __init__(self, content=b"", text=""):
            self.content, self.text = content, text
        def raise_for_status(self): return None

    def get(url, **kwargs):
        return Response(text=f"{digest}  BTCUSDT-metrics-2020-09-01.zip") if url.endswith("CHECKSUM") else Response(content=payload)

    key = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2020-09-01.zip"
    first = evaluator.download_archive(key, tmp_path, get=get)
    second = evaluator.download_archive(key, tmp_path, get=get)
    assert first["cached"] is False
    assert second["cached"] is True


def test_missing_optional_ratios_do_not_invalidate_core_oi(tmp_path):
    evaluator = module()
    path = tmp_path / "sample.zip"
    path.write_bytes(archive(["2020-09-01 00:00:00,BTCUSDT,1,2,,,,"]))
    _, checks = evaluator.parse_archive(path, "BTCUSDT")
    assert checks["oi_numeric_violations"] == 0
    assert checks["ratio_missing_rows"] == 1


def test_partial_optional_ratio_missingness_is_census_not_violation(tmp_path):
    evaluator = module()
    path = tmp_path / "sample.zip"
    path.write_bytes(archive(["2020-09-01 00:00:00,BTCUSDT,1,2,1,,1,"]))
    _, checks = evaluator.parse_archive(path, "BTCUSDT")
    assert checks["ratio_missing_rows"] == 1
    assert checks["ratio_numeric_violations"] == 0
