"""Per-environment settings profiles.

Each profile builds a frozen :class:`Settings` whose field values equal those
produced by the current configuration system for that environment. The values
are sourced from the existing ``EnhancedConfigLoader`` (the same producer that
backs ``Configs``) so equality with current behavior is guaranteed.

Additive only: nothing imports these yet (E1.T1).
"""

from application.configs.environments import Environment
from bootstrap.settings.loaders import load_settings
from bootstrap.settings.schema import Settings


def build_for(environment: Environment) -> Settings:
    """Build the frozen settings aggregate for ``environment``."""
    return load_settings(environment)


__all__ = ["build_for"]
