import json

from scripts.freeze_lead_b_replication_sample import freeze


def test_selection_uses_earliest_complete_raw_day_per_month(tmp_path):
    base = tmp_path / "data/research/btc_aggtrades"
    raw = base / "raw"
    raw.mkdir(parents=True)
    days = {}
    for year in (2024, 2025):
        for month in range(1, 13):
            for day, rows in (("01", 95), ("02", 96), ("03", 96)):
                key = f"{year:04d}-{month:02d}-{day}"
                days[key] = {"rows": rows}
                (raw / f"BTCUSDT-aggTrades-{key}.zip").touch()
    (base / "manifest.json").write_text(json.dumps({"days": days}), encoding="utf-8")

    result = freeze(tmp_path)

    assert result["selected_count"] == 24
    assert all(day.endswith("-02") for day in result["selected_dates"])
    assert all(len(fold) == 6 for fold in result["folds"].values())
    assert result["status"] == "FROZEN_BEFORE_OUTCOMES"
