import pandas as pd

from scripts.audit_funding_clock_readiness import range_summary


def test_range_summary_uses_declared_epoch_seconds():
    result = range_summary(pd.Series([1672531200, 1672532100]))

    assert result["records"] == 2
    assert result["start"] == "2023-01-01T00:00:00+00:00"
    assert result["end"] == "2023-01-01T00:15:00+00:00"
