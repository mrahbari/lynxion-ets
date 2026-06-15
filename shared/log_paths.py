"""Project-root-anchored log directory.

Logs must always land in ``<project-root>/logs`` regardless of the current
working directory. Loggers previously used a relative ``logs/`` path, so when a
process ran from a subdirectory (e.g. pytest from ``tests/e2e``) logs were
written to ``tests/e2e/logs`` instead. Anchoring to the project root (this
file lives at ``<root>/shared/log_paths.py``) keeps log output consistent.
"""
import os
from pathlib import Path

# <root>/shared/log_paths.py -> project root is the parent of shared/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def logs_dir() -> Path:
    """Return (and create) the canonical ``<project-root>/logs`` directory."""
    d = PROJECT_ROOT / "logs"
    if d.exists() and not d.is_dir():
        # If it's a file, we have a problem. Rename it or raise.
        # For now, let's just raise a more helpful error.
        raise OSError(f"Path {d} exists but is not a directory. Please remove it.")
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path(filename: str) -> str:
    """Absolute path to ``<project-root>/logs/<filename>``."""
    return str(logs_dir() / filename)
