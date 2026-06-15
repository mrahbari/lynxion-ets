"""E4.T1 — unit tests for shared/config_helper.py (relocated from utils/ in E8.T2).

Pure, stateless config-accessor helpers (cfg_get*). No I/O, no fakes beyond a
stdlib SimpleNamespace standing in for a config object. Pins the coercion and
fallback contract of each helper.
"""

from types import SimpleNamespace

import pytest

from shared.config_helper import (
    cfg_get,
    cfg_get_bool,
    cfg_get_int,
    cfg_get_float,
    cfg_get_list,
    cfg_get_str,
)


def _cfg(**kwargs):
    return SimpleNamespace(**kwargs)


# --- cfg_get ---------------------------------------------------------------

@pytest.mark.unit
def test_cfg_get_returns_attr_when_present():
    assert cfg_get(_cfg(host="db1"), "host") == "db1"


@pytest.mark.unit
def test_cfg_get_falls_back_on_missing_attr_and_none_config():
    assert cfg_get(_cfg(host="db1"), "port", 5432) == 5432
    assert cfg_get(None, "host", "default") == "default"
    assert cfg_get(None, "host") is None


# --- cfg_get_bool ----------------------------------------------------------

@pytest.mark.unit
def test_cfg_get_bool_none_config_returns_default():
    assert cfg_get_bool(None, "flag", default=True) is True
    assert cfg_get_bool(None, "flag") is False


@pytest.mark.unit
def test_cfg_get_bool_non_scalar_value_uses_truthiness():
    # Non-bool/str/numeric falls through to bool(value): empty vs non-empty.
    assert cfg_get_bool(_cfg(flag=[1]), "flag") is True
    assert cfg_get_bool(_cfg(flag=[]), "flag") is False


@pytest.mark.unit
@pytest.mark.parametrize("raw,expected", [
    (True, True), (False, False),
    ("true", True), ("True", True), ("1", True), ("yes", True), ("ON", True),
    ("false", False), ("no", False), ("", False), ("anything", False),
    (1, True), (0, False), (2.5, True), (0.0, False),
])
def test_cfg_get_bool_coercion(raw, expected):
    assert cfg_get_bool(_cfg(flag=raw), "flag") is expected


# --- cfg_get_int / cfg_get_float ------------------------------------------

@pytest.mark.unit
def test_cfg_get_int_coerces_and_falls_back():
    assert cfg_get_int(_cfg(n="42"), "n") == 42
    assert cfg_get_int(_cfg(n=3.9), "n") == 3          # int() truncates
    assert cfg_get_int(_cfg(n="not-a-number"), "n", default=7) == 7   # ValueError -> default
    assert cfg_get_int(_cfg(n=None), "n", default=7) == 7             # TypeError -> default
    assert cfg_get_int(None, "n", default=9) == 9


@pytest.mark.unit
def test_cfg_get_float_coerces_and_falls_back():
    assert cfg_get_float(_cfg(x="1.5"), "x") == 1.5
    assert cfg_get_float(_cfg(x=2), "x") == 2.0
    assert cfg_get_float(_cfg(x="bad"), "x", default=0.5) == 0.5
    assert cfg_get_float(None, "x", default=0.25) == 0.25


# --- cfg_get_list ----------------------------------------------------------

@pytest.mark.unit
def test_cfg_get_list_passthrough_and_split():
    assert cfg_get_list(_cfg(items=["a", "b"]), "items") == ["a", "b"]
    assert cfg_get_list(_cfg(items="a, b ,c"), "items") == ["a", "b", "c"]   # strip + drop empties
    assert cfg_get_list(_cfg(items="a|b|c"), "items", delimiter="|") == ["a", "b", "c"]
    assert cfg_get_list(_cfg(items="x,,y, "), "items") == ["x", "y"]


@pytest.mark.unit
def test_cfg_get_list_defaults():
    # default None is normalized to a fresh empty list
    assert cfg_get_list(None, "items") == []
    assert cfg_get_list(_cfg(items=None), "items", default=["d"]) == ["d"]
    assert cfg_get_list(_cfg(), "items", default=["d"]) == ["d"]            # missing attr
    assert cfg_get_list(_cfg(items=123), "items", default=["d"]) == ["d"]   # non-str/list -> default


@pytest.mark.unit
def test_cfg_get_list_default_is_not_shared_mutable():
    a = cfg_get_list(None, "items")
    a.append("x")
    b = cfg_get_list(None, "items")
    assert b == []          # second call must not see the mutation


# --- cfg_get_str -----------------------------------------------------------

@pytest.mark.unit
def test_cfg_get_str_coerces_and_falls_back():
    assert cfg_get_str(_cfg(name="hello"), "name") == "hello"
    assert cfg_get_str(_cfg(name=123), "name") == "123"
    assert cfg_get_str(_cfg(name=None), "name", default="d") == "d"
    assert cfg_get_str(None, "name", default="d") == "d"
    assert cfg_get_str(_cfg(), "name") == ""        # missing attr -> "" default
