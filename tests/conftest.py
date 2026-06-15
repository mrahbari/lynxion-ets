"""Root test configuration.

Ensures the project root is importable so tests can import the
``application`` / ``domain`` / ``infrastructure`` / ``shared`` packages
without the project being installed as a distribution.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def approved_symbols_config(tmp_path):
    """Factory fixture: write an approved-symbols JSON file and return its path.

    Lets tests build a SymbolValidator against a known, isolated symbol list
    instead of the committed application/configs/approved_symbols.json.
    Usage: ``SymbolValidator(config_path=approved_symbols_config(["BTCUSDT"]))``.
    """
    def _make(symbols):
        path = tmp_path / "approved_symbols.json"
        path.write_text(json.dumps(symbols), encoding="utf-8")
        return str(path)
    return _make
