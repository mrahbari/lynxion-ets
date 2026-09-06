from scripts.materialize_c33_warmup import materialize, write_atomic
from tests.unit.test_audit_c33_collection import fixture


def test_materializer_emits_every_symbol_and_explicit_eligible_zeroes(tmp_path):
    manifest, _, start = fixture(tmp_path)
    result = materialize(manifest)
    assert result["verdict"] == "COLLECTING"
    assert result["eligible_bucket_count"] == 1
    assert len(result["rows"]) == 6
    btc = next(row for row in result["rows"] if row["symbol"] == "BTCUSDT")
    assert btc == {
        "bucket_start_ms": start, "bucket_end_ms": start + 300_000, "symbol": "BTCUSDT",
        "observed_buy_count": 0, "observed_buy_notional": 0.0,
        "observed_sell_count": 1, "observed_sell_notional": 125.0,
    }
    assert result["source_sha256"]


def test_materializer_excludes_ineligible_bucket_and_writes_atomically(tmp_path):
    manifest, _, _ = fixture(tmp_path, missing_heartbeat=True)
    result = materialize(manifest)
    assert result["eligible_bucket_count"] == 0
    assert result["rows"] == []
    output = tmp_path / "warmup.json"
    write_atomic(output, result)
    assert output.read_text().endswith("\n")
