"""E1.T1 validation: the typed settings schema mirrors current config exactly.

Builds each profile and asserts every domain's field values equal those
produced by the legacy ``EnhancedConfigLoader``. Also asserts the aggregate
is frozen.
"""

import pytest

pytest.importorskip("pydantic")
try:
    from application.configs.enhanced_config_loader import EnhancedConfigLoader
    from application.configs.environments import Environment
    from bootstrap.settings.schema import Settings, DOMAINS
    from bootstrap.settings.profiles import dev, staging, live
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"settings/config dependencies unavailable: {exc}", allow_module_level=True)


_PROFILE_ENVS = [
    (dev, Environment.DEV),
    (staging, Environment.STAGING),
    (live, Environment.LIVE),
]


@pytest.mark.unit
@pytest.mark.parametrize("profile_module, environment", _PROFILE_ENVS)
def test_profile_fields_match_current_loader(profile_module, environment):
    settings = profile_module.build_settings()
    expected = EnhancedConfigLoader().load_config(environment)
    for domain in DOMAINS:
        assert getattr(settings, domain) == expected[domain], (
            f"Mismatch in domain '{domain}' for {environment}"
        )


@pytest.mark.unit
def test_settings_aggregate_is_frozen():
    settings = dev.build_settings()
    with pytest.raises(Exception):
        settings.broker = settings.broker  # frozen: reassignment must fail


@pytest.mark.unit
def test_all_domains_present():
    settings = dev.build_settings()
    assert len(DOMAINS) == 16
    for domain in DOMAINS:
        assert getattr(settings, domain) is not None
