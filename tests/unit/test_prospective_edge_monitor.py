from infrastructure.monitoring.prospective_edge_monitor import build_prospective_edge_report


def _row(pnl: str, **overrides):
    row = {
        "entry_timestamp": "2026-08-13T12:00:00+00:00",
        "exit_timestamp": "2026-08-13T13:00:00+00:00",
        "pnl_usdt": pnl,
        "strategy": "trend_following",
        "side": "BUY",
        "regime": "trending_up",
        "confidence": "0.8",
        "initial_stop_loss": "90",
        "initial_take_profit": "120",
        "risk_usdt": "10",
        "r_multiple": "1.0",
    }
    row.update(overrides)
    return row


def test_withholds_edge_verdict_when_attribution_is_incomplete():
    report = build_prospective_edge_report([_row("1.0", regime="")], "2026-08-13T00:00:00+00:00")
    assert report["verdict"] == "INSUFFICIENT_ATTRIBUTION"
    assert report["incomplete_attribution_count"] == 1


def test_segments_candidate_by_strategy_side_and_regime():
    rows = [_row("1.0") for _ in range(30)]
    rows.extend(_row("-1.0", side="SELL", regime="trending_down") for _ in range(30))
    report = build_prospective_edge_report(rows, "2026-08-13T00:00:00+00:00")
    assert report["verdict"] == "GO"
    assert len(report["cells"]) == 2
    assert report["overall"]["largest_win_share_of_gross_profit"] == 1 / 30


def test_excludes_rows_before_the_explicit_cohort_boundary():
    report = build_prospective_edge_report(
        [_row("1.0", entry_timestamp="2026-08-12T23:59:59+00:00")],
        "2026-08-13T00:00:00+00:00",
    )
    assert report["cohort_trade_count"] == 0
    assert report["verdict"] == "INSUFFICIENT_DATA"
