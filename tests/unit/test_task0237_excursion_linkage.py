from scripts.audit_excursion_linkage import assess_linkage


def _journal(trade_id="1"):
    return {
        "trade_id": trade_id,
        "symbol": "BTCUSDT",
        "side": "BUY",
        "entry_timestamp": "2026-09-01T00:00:00+00:00",
        "entry_price": "100.00",
        "quantity": "0.20",
    }


def _diagnostic():
    return {
        "symbol": "BTC-USDT",
        "side": "LONG",
        "entry_time": "2026-09-01T00:00:00+00:00",
        "entry_price": 100.0,
        "quantity": 0.2,
        "mfe_roe_pct": 4.0,
        "mae_roe_pct": -1.0,
    }


def test_links_only_exact_unique_identity():
    report = assess_linkage([_journal()], [_diagnostic()])
    assert report["unique_links"] == 1
    assert report["coverage"] == 1.0
    assert report["linked_trades"][0]["trade_id"] == "1"


def test_rejects_ambiguous_identity():
    report = assess_linkage([_journal("1"), _journal("2")], [_diagnostic()])
    assert report["unique_links"] == 0
    assert report["ambiguous"] == 1


def test_rejects_missing_excursion_after_identity_match():
    diagnostic = _diagnostic()
    diagnostic["mfe_roe_pct"] = None
    report = assess_linkage([_journal()], [diagnostic])
    assert report["unique_links"] == 0
    assert report["missing_excursion"] == 1
