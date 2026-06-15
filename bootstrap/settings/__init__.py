"""Typed, frozen settings schema and per-environment profiles.

Additive only (Epic E1, task E1.T1). The single settings loader (E1.T2) and
the ``Configs`` shim (E1.T3) build on top of this; until then nothing is wired.
"""

from bootstrap.settings.schema import Settings

__all__ = ["Settings"]
