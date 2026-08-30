import importlib.util
from pathlib import Path

import pandas as pd


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "update_c11_prospective_funding.py"
    spec = importlib.util.spec_from_file_location("edge_c11", path)
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded


def funding_frame():
    return pd.DataFrame({"timestamp": range(400), "funding_rate": [-0.001] * 365 + [-0.003] + [-0.001] * 34})


def test_boundary_excludes_preboundary_event_and_threshold_is_causal():
    evaluator = module(); frame = funding_frame()
    assert evaluator.candidate_events(frame, boundary=365) == []
    events = evaluator.candidate_events(frame, boundary=364)
    assert len(events) == 1
    assert events[0]["threshold"] == -0.001


def test_severity_below_two_is_rejected():
    evaluator = module(); frame = funding_frame(); frame.loc[365, "funding_rate"] = -0.0019
    assert evaluator.candidate_events(frame, boundary=364) == []


def test_non_overlapping_drops_signals_before_prior_exit():
    evaluator = module()
    events = [{"funding_timestamp": 1, "expected_entry_timestamp": 10, "expected_exit_timestamp": 100},
              {"funding_timestamp": 2, "expected_entry_timestamp": 20, "expected_exit_timestamp": 110},
              {"funding_timestamp": 3, "expected_entry_timestamp": 100, "expected_exit_timestamp": 200}]
    assert [item["funding_timestamp"] for item in evaluator.non_overlapping(events)] == [1, 3]


def test_metrics_cannot_leave_collecting_before_minimum_sample():
    evaluator = module(); records = [{"status": "COMPLETE", "net_return": 0.01}] * 99
    assert evaluator.metrics(records)["verdict"] == "COLLECTING"
