import hashlib
import importlib.util
import io
import zipfile
from pathlib import Path
from unittest.mock import Mock


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_binance_premium_index_panel.py"
    spec = importlib.util.spec_from_file_location("premium_panel", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def archive(rows, header=False):
    evaluator = module(); payload = io.BytesIO()
    body = []
    if header:
        body.append(",".join(evaluator.COLUMNS))
    body.extend(",".join(map(str, row)) for row in rows)
    with zipfile.ZipFile(payload, "w") as zipped:
        zipped.writestr("sample.csv", "\n".join(body) + "\n")
    return payload.getvalue()


def row(opened, scale=1000, prices=(0.1, 0.2, -0.1, 0.05)):
    closed = opened + 900 * scale - 1
    return [opened, *prices, 0, closed, 0, 60, 0, 0, 0]


def test_parser_accepts_headerless_milliseconds_and_headered_microseconds(tmp_path):
    evaluator = module()
    first = tmp_path / "first.zip"; first.write_bytes(archive([row(0)], header=False))
    microsecond_epoch = 1_700_000_100 * 1_000_000
    second = tmp_path / "second.zip"; second.write_bytes(
        archive([row(microsecond_epoch, 1_000_000)], header=True)
    )

    first_rows, first_checks = evaluator.parse_archive(first)
    second_rows, second_checks = evaluator.parse_archive(second)

    assert first_rows[0][0] == 0
    assert second_rows[0][0] == 1_700_000_100
    assert sum(first_checks.values()) == 1
    assert sum(second_checks.values()) == 1


def test_parser_detects_bad_ohlc_and_timestamp(tmp_path):
    evaluator = module(); path = tmp_path / "bad.zip"
    bad_ohlc = row(0, prices=(0.1, 0.0, -0.1, 0.05))
    bad_time = row(1_000)
    path.write_bytes(archive([bad_ohlc, bad_time]))

    parsed, checks = evaluator.parse_archive(path)

    assert parsed == []
    assert checks["ohlc_violations"] == 1
    assert checks["timestamp_violations"] == 1


def test_downloader_binds_checksum_and_resumes(tmp_path):
    evaluator = module(); payload = archive([row(0)])
    filename = "BTCUSDT-15m-2020-01-01.zip"
    key = f"data/futures/um/daily/premiumIndexKlines/BTCUSDT/15m/{filename}"
    checksum = hashlib.sha256(payload).hexdigest()
    checksum_response = Mock(text=f"{checksum}  {filename}"); checksum_response.raise_for_status = Mock()
    archive_response = Mock(content=payload); archive_response.raise_for_status = Mock()
    get = Mock(side_effect=[checksum_response, archive_response])

    first = evaluator.download_archive(key, tmp_path, get=get)
    get = Mock(return_value=checksum_response)
    second = evaluator.download_archive(key, tmp_path, get=get)

    assert first["cached"] is False and second["cached"] is True
    assert get.call_count == 1


def test_normalizer_counts_exact_and_conflicting_duplicates(tmp_path):
    evaluator = module(); raw = tmp_path / "raw"; symbol = "BTCUSDT"
    (raw / symbol).mkdir(parents=True)
    files = []
    for name, prices in (("a.zip", (0.1, 0.2, -0.1, 0.05)),
                         ("b.zip", (0.1, 0.2, -0.1, 0.05)),
                         ("c.zip", (0.1, 0.3, -0.1, 0.05))):
        (raw / symbol / name).write_bytes(archive([row(0, prices=prices)])); files.append({"key": name})

    summary = evaluator.normalize_symbol(symbol, files, raw, tmp_path / "normalized")

    assert summary["exact_duplicates"] == 1
    assert summary["conflicting_duplicates"] == 1
    assert summary["unique_rows"] == 1


def test_gate_reports_source_gaps_without_calling_them_core_corruption():
    evaluator = module()
    summary = {"conflicting_duplicates": 0, "schema_violations": 0,
               "numeric_violations": 0, "timestamp_violations": 0, "ohlc_violations": 0,
               "missing_intervals": 123, "reverse_sample_rows": 35_040,
               "primary_sample_rows": 90_000}

    gate = evaluator.panel_gate({"BTCUSDT": summary})

    assert gate["core_integrity_violations"] == 0
    assert gate["source_gap_intervals"] == 123
    assert gate["verdict"] == "KEEP"
