"""E4.T2 — unit tests for infrastructure/services/symbol_validator.py.

Deterministic, no network: the validator is built against an isolated temp
approved-symbols file (via the `approved_symbols_config` conftest fixture),
not the committed config. Pins the normalization + approval-matching contract.
"""

import pytest

from domain.value_objects import Symbol
from infrastructure.services.symbol_validator import SymbolValidator


@pytest.mark.unit
def test_loads_and_normalizes_both_formats(approved_symbols_config):
    # Input uses lower-case + slash; loader normalizes to upper, storing both
    # the slash and no-slash forms.
    v = SymbolValidator(config_path=approved_symbols_config(["btc/usdt"]))
    approved = v.get_approved_symbols()
    assert "BTCUSDT" in approved
    assert "BTC/USDT" in approved


@pytest.mark.unit
def test_is_symbol_approved_true_for_listed_symbol(approved_symbols_config):
    v = SymbolValidator(config_path=approved_symbols_config(["BTCUSDT", "ETHUSDT"]))
    assert v.is_symbol_approved(Symbol("BTCUSDT")) is True
    assert v.is_symbol_approved(Symbol("ETHUSDT")) is True


@pytest.mark.unit
def test_is_symbol_approved_false_for_unlisted_symbol(approved_symbols_config):
    v = SymbolValidator(config_path=approved_symbols_config(["BTCUSDT"]))
    assert v.is_symbol_approved(Symbol("DOGEUSDT")) is False


@pytest.mark.unit
def test_slash_listed_symbol_matches_plain_symbol(approved_symbols_config):
    # Approved list carries "BTC/USDT"; a plain Symbol("BTCUSDT") should match
    # via the no-slash normalized form.
    v = SymbolValidator(config_path=approved_symbols_config(["BTC/USDT"]))
    assert v.is_symbol_approved(Symbol("BTCUSDT")) is True


@pytest.mark.unit
def test_get_approved_symbols_returns_a_copy(approved_symbols_config):
    v = SymbolValidator(config_path=approved_symbols_config(["BTCUSDT"]))
    snapshot = v.get_approved_symbols()
    snapshot.add("TAMPERED")
    assert "TAMPERED" not in v.get_approved_symbols()   # internal set untouched


@pytest.mark.unit
def test_missing_config_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        SymbolValidator(config_path=str(tmp_path / "does_not_exist.json"))


@pytest.mark.unit
def test_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    import json
    with pytest.raises(json.JSONDecodeError):
        SymbolValidator(config_path=str(bad))
