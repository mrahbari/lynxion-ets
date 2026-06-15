"""Staging settings profile."""

from application.configs.environments import Environment
from bootstrap.settings.profiles import build_for
from bootstrap.settings.schema import Settings


def build_settings() -> Settings:
    return build_for(Environment.STAGING)
