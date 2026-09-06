import pytest

from scripts.check_c33_checkpoint import checkpoint_status


def test_no_checkpoint_before_next_sparse_milestone():
    result = checkpoint_status(25, 99)
    assert result["checkpoint_due"] is False
    assert result["crossed_milestones"] == []
    assert result["next_milestone"] == 100


def test_reports_all_crossed_milestones_after_delayed_check():
    result = checkpoint_status(25, 1_050)
    assert result["checkpoint_due"] is True
    assert result["crossed_milestones"] == [100, 500, 1_000]
    assert result["next_milestone"] == 2_000


def test_final_warmup_milestone_has_no_successor():
    result = checkpoint_status(8_000, 8_640)
    assert result["crossed_milestones"] == [8_640]
    assert result["next_milestone"] is None


@pytest.mark.parametrize("previous,current", [(10, 9), (-1, 0), (True, 1), (1.0, 2)])
def test_invalid_or_regressed_counts_fail_closed(previous, current):
    with pytest.raises(ValueError):
        checkpoint_status(previous, current)
