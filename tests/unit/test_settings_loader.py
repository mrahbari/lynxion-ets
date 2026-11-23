"""E1.T2 validation: the single loader equals the legacy ``EnhancedConfigLoader`` output per profile.

The committed-snapshot tests were removed 2026-11-23: they compared the settings loaded from the
operator's live .env with values baked months earlier, so every intended config change failed them.
"""

import pytest

pytest.importorskip("pydantic")
try:
    from application.configs.enhanced_config_loader import EnhancedConfigLoader
    from application.configs.environments import Environment
    from bootstrap.settings.loaders import load_settings
    from bootstrap.settings.schema import DOMAINS
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"settings/config dependencies unavailable: {exc}", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.parametrize("environment", [Environment.DEV, Environment.STAGING, Environment.LIVE])
def test_loader_matches_legacy_loader(environment):
    actual = load_settings(environment)
    expected = EnhancedConfigLoader().load_config(environment)
    for domain in DOMAINS:
        assert getattr(actual, domain) == expected[domain]
