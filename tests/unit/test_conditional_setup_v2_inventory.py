"""Pre-outcome causal checks for existing structural-state inventory."""

import socket
from datetime import datetime, timezone
from pathlib import Path

from infrastructure.research.conditional_setup_v2_inventory import inventory, counts
from infrastructure.replay.preintent_candle_capture import load_frozen_capture


ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "data/research/pre_intent/candle_capture_v1/capture_manifest.json"


def test_structure_agreement_inventory_is_causal_repeated_and_symbol_isolated(monkeypatch):
    def deny_connect(*_args, **_kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    bars, _ = load_frozen_capture(CAPTURE, ROOT)
    full = inventory(bars)
    assert inventory(bars) == full
    assert counts(full)["selected_directional"] == 163
    assert counts(full)["all_directional"] == 417
    assert counts(full)["all_agreement"] == 291
    assert counts(full)["all_nonagreement"] == 126
    assert counts(full)["comparable_symbol_week_side_strata"] == 16
    assert counts(full)["comparable_eligible"] == 266
    assert counts(full)["comparable_controls"] == 126
    assert counts(full)["eligible_structure_agreement"] == 118
    assert counts(full)["nonagreement_controls"] == 45
    for cut in (datetime(2026, 6, day, tzinfo=timezone.utc) for day in (8, 18, 28)):
        prefix_bars = tuple(bar for bar in bars if bar.close_time <= cut)
        prefix = inventory(prefix_bars)
        assert prefix == tuple(row for row in full if datetime.fromisoformat(row[0]) <= cut)
    btc_only = inventory(tuple(bar for bar in bars if bar.symbol == "BTCUSDT"))
    assert btc_only == tuple(row for row in full if row[1] == "BTCUSDT")
