from scripts.decompose_small_notional_mean_reversion import build_report


def _row(trade_id, *, strategy="MeanReversion", price="10", quantity="2", pnl="1", fee="-0.1"):
    return {
        "trade_id": str(trade_id), "strategy": strategy, "symbol": "BTCUSDT", "side": "BUY",
        "entry_timestamp": "2026-09-01T00:00:00+00:00", "entry_price": price,
        "quantity": quantity, "pnl_usdt": pnl, "fees_usdt": fee,
    }


def test_cells_are_disjoint_and_cover_final_records():
    rows = [_row(1), _row(2, strategy="Trend", price="20"), _row(3, quantity="1")]
    report = build_report(rows, samples=100)
    assert sum(cell["n"] for cell in report["cells"].values()) == 3
    assert report["cells"]["small_true__mean_reversion_true"]["n"] == 2


def test_final_trade_record_wins_before_decomposition():
    rows = [_row(1, pnl="-10"), _row(1, pnl="2")]
    report = build_report(rows, samples=100)
    assert report["final_records"] == 1
    assert report["cells"]["small_true__mean_reversion_true"]["cost_adjusted_pnl_usdt"] == 1.9


def test_invalid_notional_is_counted():
    report = build_report([_row(1, price="0")], samples=100)
    assert report["cells"]["small_true__mean_reversion_true"]["invalid_notional"] == 1
