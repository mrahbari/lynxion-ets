"""
Unit tests for SymbolFormatHelper unification and exchange conversion.
"""
import pytest
from domain.value_objects import Symbol
from infrastructure.brokers.symbol_format_helper import SymbolFormatHelper


def test_normalize_symbol():
    assert SymbolFormatHelper.normalize_symbol("btc-usdt") == "BTCUSDT"
    assert SymbolFormatHelper.normalize_symbol("ETH/USDT") == "ETHUSDT"
    assert SymbolFormatHelper.normalize_symbol("sol_usdc") == "SOLUSDC"
    assert SymbolFormatHelper.normalize_symbol(Symbol("XRP-USDT")) == "XRPUSDT"


def test_split_base_quote():
    base, quote = SymbolFormatHelper.split_base_quote("BTCUSDT")
    assert base == "BTC" and quote == "USDT"

    base, quote = SymbolFormatHelper.split_base_quote("ETH-USDC")
    assert base == "ETH" and quote == "USDC"

    base, quote = SymbolFormatHelper.split_base_quote("DOGE/USD")
    assert base == "DOGE" and quote == "USD"


def test_format_symbol_for_exchange():
    # BingX expects hyphenated
    assert SymbolFormatHelper.format_symbol_for_exchange("BTCUSDT", "bingx") == "BTC-USDT"
    assert SymbolFormatHelper.format_symbol_for_exchange(Symbol("ETH-USDT"), "bingx") == "ETH-USDT"
    assert SymbolFormatHelper.format_symbol_for_exchange("SOL-USDT", "bingx") == "SOL-USDT"

    # Binance / CCXT expects slash
    assert SymbolFormatHelper.format_symbol_for_exchange("BTCUSDT", "binance") == "BTC/USDT"
    assert SymbolFormatHelper.format_symbol_for_exchange("BTC-USDT", "phemex") == "BTC/USDT"

    # MEXC expects underscore
    assert SymbolFormatHelper.format_symbol_for_exchange("BTCUSDT", "mexc") == "BTC_USDT"


def test_is_valid_symbol_format():
    assert SymbolFormatHelper.is_valid_symbol_format("BTCUSDT") is True
    assert SymbolFormatHelper.is_valid_symbol_format("ETH-USDC") is True
    assert SymbolFormatHelper.is_valid_symbol_format("X") is False
    assert SymbolFormatHelper.is_valid_symbol_format("") is False
