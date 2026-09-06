import json

import pytest

from scripts.verify_c33_warmup_snapshot import InvalidC33WarmupSnapshot, verify


SNAPSHOT = "data/research/c33/warmup_snapshot_task0168.json"


def test_committed_task0168_snapshot_is_valid():
    result = verify(SNAPSHOT)
    assert result["valid"] is True
    assert result["verdict"] == "COLLECTING"
    assert result["eligible_bucket_count"] == 25
    assert result["row_count"] == 150
    assert result["eligible_observed_snapshot_count"] == 170
    assert result["eligible_observed_notional"] == pytest.approx(901_832.46278)


@pytest.mark.parametrize("mutation,match", [
    (lambda data: data["rows"].append(data["rows"][0]), "row count"),
    (lambda data: data["rows"][0].update(symbol="NOTUSDT"), "frozen universe"),
    (lambda data: data["rows"][0].update(bucket_end_ms=0), "bucket boundary"),
    (lambda data: data["rows"][0].update(observed_buy_notional=1), "zero observed count"),
    (lambda data: data.update(source_sha256="bad"), "SHA-256"),
])
def test_verifier_fails_closed_on_mutated_artifact(tmp_path, mutation, match):
    data = json.loads(open(SNAPSHOT, encoding="utf-8").read())
    mutation(data)
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(data))
    with pytest.raises(InvalidC33WarmupSnapshot, match=match):
        verify(path)
