"""Research universe loader — reads the repo's symbol configs directly.

Uses application/configs/{sync,approved}_symbols.json (flattening nested
category lists). Direct read rather than CentralizedSymbolManager because the
manager's unified list depends on an approved-symbols path that isn't populated
in this environment (resolves to 0); the raw config is the reliable source for
research. Run from repo root.
"""
from __future__ import annotations

import json
import os

CONFIG_DIR = os.path.join("application", "configs")


def _flatten(obj) -> list[str]:
    found = []

    def walk(x):
        if isinstance(x, str):
            s = x.strip().upper()
            if s.endswith("USDT"):
                found.append(s)
        elif isinstance(x, list):
            for i in x:
                walk(i)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
    walk(obj)
    seen, out = set(), []
    for s in found:
        if s not in seen:
            seen.add(s); out.append(s)
    return out


def load_universe(scope: str = "sync") -> list[str]:
    fname = {"sync": "sync_symbols.json", "approved": "approved_symbols.json"}.get(scope)
    if not fname:
        raise ValueError(f"unknown scope {scope!r}")
    with open(os.path.join(CONFIG_DIR, fname)) as f:
        return _flatten(json.load(f))
