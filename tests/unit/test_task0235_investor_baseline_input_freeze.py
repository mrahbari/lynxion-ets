import hashlib

import pytest

from scripts.materialize_investor_baseline_input import extract_verified_prefix


def test_extract_verified_prefix_excludes_later_append_only_rows():
    frozen = b"header\nrow-1\nrow-2\n"
    current = frozen + b"row-3\n"

    result = extract_verified_prefix(current, 2, hashlib.sha256(frozen).hexdigest())

    assert result == frozen


def test_extract_verified_prefix_rejects_changed_history():
    with pytest.raises(ValueError, match="hash mismatch"):
        extract_verified_prefix(b"header\nchanged\n", 1, "0" * 64)
