import json

import pytest

from scripts.collect_c33_liquidation_events import InvalidC33Event
from scripts.resume_c33_liquidation_collector import resolve_pinned_commit


def test_resume_retains_pinned_commit_only_for_identical_collector_blob(tmp_path):
    manifest_path = tmp_path / "activation.json"
    manifest_path.write_text(json.dumps({"collector_commit": "pinned"}))
    values = {
        ("rev-parse", "HEAD:scripts/collect_c33_liquidation_events.py"): "same-blob",
        ("rev-parse", "pinned:scripts/collect_c33_liquidation_events.py"): "same-blob",
    }
    assert resolve_pinned_commit(manifest_path, lambda args: values[tuple(args)]) == "pinned"


def test_resume_rejects_changed_collector_blob(tmp_path):
    manifest_path = tmp_path / "activation.json"
    manifest_path.write_text(json.dumps({"collector_commit": "pinned"}))
    values = {
        ("rev-parse", "HEAD:scripts/collect_c33_liquidation_events.py"): "changed-blob",
        ("rev-parse", "pinned:scripts/collect_c33_liquidation_events.py"): "original-blob",
    }
    with pytest.raises(InvalidC33Event, match="source differs"):
        resolve_pinned_commit(manifest_path, lambda args: values[tuple(args)])


def test_resume_rejects_missing_manifest_commit(tmp_path):
    manifest_path = tmp_path / "activation.json"
    manifest_path.write_text("{}")
    with pytest.raises(InvalidC33Event, match="commit is invalid"):
        resolve_pinned_commit(manifest_path, lambda args: "unused")
