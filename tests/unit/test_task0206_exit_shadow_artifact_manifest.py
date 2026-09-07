from pathlib import Path

import pytest

from scripts.build_exit_shadow_artifact_manifest import ARTIFACT_PATHS, build_manifest


def test_repository_manifest_is_complete_and_deterministic():
    root = Path(__file__).resolve().parents[2]
    first = build_manifest(root)
    second = build_manifest(root)
    assert first == second
    assert first["status"] == "EVALUATOR_FROZEN_OUTCOMES_UNOPENED"
    assert len(first["artifacts"]) == len(ARTIFACT_PATHS)
    assert len(first["artifact_set_sha256"]) == 64


def test_missing_required_artifact_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError, match="required exit-shadow artifact missing"):
        build_manifest(tmp_path)
