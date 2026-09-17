import gzip
import json
import zipfile

from scripts.audit_lead_b_clock_phase_readiness import audit


def make_root(tmp_path, timestamps, *, raw=False):
    base = tmp_path / "data/research/btc_aggtrades"
    daily = base / "daily"
    daily.mkdir(parents=True)
    manifest = {
        "days": {
            "2026-01-01": {"rows": len(timestamps), "checks": {"raw_rows": 100}}
        }
    }
    (base / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with gzip.open(daily / "2026-01-01.csv.gz", "wt", encoding="utf-8") as handle:
        handle.write("timestamp,trade_count\n")
        for timestamp in timestamps:
            handle.write(f"{timestamp},1\n")
    if raw:
        raw_dir = base / "raw"
        raw_dir.mkdir()
        with zipfile.ZipFile(raw_dir / "BTCUSDT-aggTrades-2026-01-01.zip", "w") as archive:
            archive.writestr(
                "BTCUSDT-aggTrades-2026-01-01.csv",
                "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
                "1,1,1,1,1,1000,true\n2,1,1,2,2,2100,false\n",
            )
    return tmp_path


def test_fifteen_minute_aggregate_cannot_resolve_first_ten_seconds(tmp_path):
    result = audit(make_root(tmp_path, [0, 900, 1800]))

    assert result["retained_resolution_seconds"] == 900
    assert not result["first_10_seconds_resolvable"]
    assert result["verdict"] == "INSUFFICIENT_TEMPORAL_RESOLUTION"


def test_raw_millisecond_archive_passes_only_readiness_not_edge(tmp_path):
    result = audit(make_root(tmp_path, [0, 900, 1800], raw=True))

    assert result["first_10_seconds_resolvable"]
    assert result["raw_archives_retained"] == 1
    assert result["verdict"] == "READY_FOR_REPLICATION_DIAGNOSTIC"
