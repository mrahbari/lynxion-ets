import zipfile

from scripts.run_lead_b_clock_replication import aggregate_archive, finalize_bucket


def test_raw_windows_are_separated_and_aggressor_side_is_signed(tmp_path):
    archive_path = tmp_path / "sample.zip"
    rows = [
        [1, 100, 2, 1, 1, 0, "false"],
        [2, 101, 1, 2, 2, 5000, "true"],
        [3, 102, 1, 3, 3, 300000, "false"],
        [4, 103, 1, 4, 4, 600000, "true"],
    ]
    with zipfile.ZipFile(archive_path, "w") as archive:
        content = "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
        content += "\n".join(",".join(map(str, row)) for row in rows) + "\n"
        archive.writestr("sample.csv", content)

    buckets = aggregate_archive(archive_path)

    opening = finalize_bucket(buckets[(0, "opening")])
    assert opening["trade_count"] == 2
    assert opening["signed_imbalance"] > 0
    assert buckets[(0, "control_5m")]["trade_count"] == 1
    assert buckets[(0, "control_10m")]["trade_count"] == 1
