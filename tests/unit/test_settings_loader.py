"""E1.T2 validation: the single loader reproduces the original config values.

Asserts the loaded settings (per profile) match a committed snapshot of the
original ``Configs`` values (baked before the legacy class was retired in
E1.T6) and that the loader output equals the legacy ``EnhancedConfigLoader``
output.

Bake/refresh the snapshot intentionally with ``GOLDEN_UPDATE=1``.
"""

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("pydantic")
try:
    from application.configs.enhanced_config_loader import EnhancedConfigLoader
    from application.configs.environments import Environment
    from bootstrap.settings.loaders import load_settings
    from bootstrap.settings.schema import DOMAINS
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"settings/config dependencies unavailable: {exc}", allow_module_level=True)

SNAPSHOT = Path(__file__).resolve().parent.parent / "fixtures" / "settings" / "configs_snapshot.json"


def _redact_broker_credentials(data: dict) -> dict:
    # Golden configuration tests must verify stable, non-secret settings only. Local
    # credentials intentionally vary between machines and must neither affect test
    # results nor be emitted in assertion diffs.
    broker = data.get("broker", {})
    for key in broker:
        if key in {"api_key", "secret_key", "bingx_passphrase"} or key.endswith(("_api_key", "_secret_key")):
            broker[key] = "<redacted>"
    return data


def _dump(settings) -> dict:
    return _redact_broker_credentials(
        {domain: getattr(settings, domain).model_dump(mode="json") for domain in DOMAINS}
    )


def _load_snapshot() -> dict:
    return _redact_broker_credentials(json.loads(SNAPSHOT.read_text(encoding="utf-8")))


@pytest.mark.unit
def test_loader_matches_committed_snapshot():
    actual = _dump(load_settings(Environment.DEV))
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    if os.environ.get("GOLDEN_UPDATE") == "1":
        SNAPSHOT.write_text(json.dumps(actual, indent=2, sort_keys=True), encoding="utf-8")
        return
    assert SNAPSHOT.exists(), "Run with GOLDEN_UPDATE=1 to create the snapshot."
    expected = _load_snapshot()
    assert actual == expected


@pytest.mark.unit
@pytest.mark.parametrize("environment", [Environment.DEV, Environment.STAGING, Environment.LIVE])
def test_loader_matches_legacy_loader(environment):
    actual = load_settings(environment)
    expected = EnhancedConfigLoader().load_config(environment)
    for domain in DOMAINS:
        assert getattr(actual, domain) == expected[domain]


@pytest.mark.unit
def test_loader_matches_committed_snapshot_default_env():
    # The loader on the default environment must still match the committed
    # snapshot baked from the original ``Configs`` values (no drift after the
    # legacy class was retired in E1.T6).
    assert SNAPSHOT.exists(), "Run with GOLDEN_UPDATE=1 to create the snapshot."
    expected = _load_snapshot()
    actual = _dump(load_settings())
    assert actual == expected
