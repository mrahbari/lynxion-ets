"""Frozen V2 capture checks do not inspect any future outcome."""

import json
import socket

import pytest

from infrastructure.replay.conditional_setup_v2_capture import CAPTURE, ROOT, qualify_capture


def test_frozen_v2_capture_is_complete_causal_and_network_free(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("network forbidden")))
    bars, facts = qualify_capture()
    assert len(bars) == 4176
    assert facts["rows_per_symbol"] == 2088
    assert facts["warmup_per_symbol"] == 72
    assert facts["evaluation_per_symbol"] == 2016
    assert (facts["gaps"], facts["duplicates"], facts["invalid_ohlcv"]) == (0, 0, 0)
    assert facts["capture_manifest_sha256"] == "38813362968e9f9c696fe754badeea5bb0a765b79ac05ee8ee80cf1572beac36"
    assert all(bar.close_time >= bar.open_time for bar in bars)


def test_frozen_v2_capture_rejects_modified_provenance(tmp_path):
    manifest = json.loads(CAPTURE.read_text())
    manifest["records"][0]["request_url"] = "https://example.invalid/klines"
    altered = tmp_path / "manifest.json"
    altered.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="request/provenance"):
        qualify_capture(ROOT, altered)
