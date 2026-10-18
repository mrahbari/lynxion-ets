"""Offline startup gates for broker-connected CLI modes."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("preflight_result", ["exception", "blocked_testnet"])
@pytest.mark.parametrize("auto_detect", [False, True])
def test_production_cli_refuses_failed_preflight(monkeypatch, preflight_result, auto_detect):
    from interface.cli import trading_system_production as cli
    from bootstrap.settings import loaders
    from shared import preflight

    @contextmanager
    def fake_lifespan():
        yield SimpleNamespace(resolve=lambda _name: object())

    started = []
    monkeypatch.setattr(cli, "lifespan", fake_lifespan)
    monkeypatch.setattr(loaders, "load_settings", lambda: object())
    monkeypatch.setattr(
        cli, "RunLiveTradingUseCase",
        lambda **_kwargs: SimpleNamespace(run=lambda **_kw: started.append("live") or 0),
    )
    monkeypatch.setattr(
        cli, "RunAutoDetectionUseCase",
        lambda **_kwargs: SimpleNamespace(run=lambda **_kw: started.append("auto") or 0),
    )
    if preflight_result == "exception":
        def broken_preflight(_settings):
            raise RuntimeError("bad preflight")
        monkeypatch.setattr(preflight, "run_preflight", broken_preflight)
    else:
        monkeypatch.setattr(preflight, "run_preflight", lambda _settings: {
            "mode": "TESTNET", "ok": False, "flags": {}, "warnings": [],
            "blocking": ["missing VST configuration"],
        })

    args = ["--mode", "production"]
    if auto_detect:
        args.append("--auto-detect")
    assert cli.main(args) == 2
    assert started == []


@pytest.mark.parametrize("mode,ok", [("TESTNET", True), ("PAPER", False)])
def test_production_cli_retains_allowed_startup(monkeypatch, mode, ok):
    from interface.cli import trading_system_production as cli
    from bootstrap.settings import loaders
    from shared import preflight

    @contextmanager
    def fake_lifespan():
        yield SimpleNamespace(resolve=lambda _name: object())

    started = []
    monkeypatch.setattr(cli, "lifespan", fake_lifespan)
    monkeypatch.setattr(loaders, "load_settings", lambda: object())
    monkeypatch.setattr(preflight, "run_preflight", lambda _settings: {
        "mode": mode, "ok": ok, "flags": {}, "warnings": [], "blocking": [],
    })
    monkeypatch.setattr(
        cli, "RunAutoDetectionUseCase",
        lambda **_kwargs: SimpleNamespace(run=lambda **_kw: started.append("auto") or 0),
    )

    assert cli.main(["--mode", "production", "--auto-detect"]) == 0
    assert started == ["auto"]
