"""Single settings loader.

Produces the frozen :class:`Settings` aggregate from environment + profile.
This is the one canonical loader the new ``bootstrap`` stack uses; the
per-environment profiles delegate here.

For the consolidation step (E1.T2) the loader sources values from the existing
``EnhancedConfigLoader`` so the result is byte-for-byte identical to the current
``Configs``. Later E1 tasks remove the legacy loaders (``loader.py`` and
``EnhancedConfigLoader``) once all callers go through the shim/composition root.
"""

from typing import Optional

from application.configs.enhanced_config_loader import EnhancedConfigLoader
from application.configs.environments import Environment, get_current_environment
from bootstrap.settings.schema import Settings, DOMAINS


def load_settings(environment: Optional[Environment] = None,
                  env_file_path: Optional[str] = None) -> Settings:
    """Load the frozen settings aggregate for ``environment``.

    Args:
        environment: Target environment; defaults to the current environment.
        env_file_path: Optional path to a ``.env`` file.
    """
    if environment is None:
        environment = get_current_environment()

    objects = EnhancedConfigLoader(env_file_path).load_config(environment)
    return Settings(**{domain: objects[domain] for domain in DOMAINS})


__all__ = ["load_settings"]
