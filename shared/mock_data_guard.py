"""Explicit, settings-independent gate for synthetic / mock market data.

E-P5.2 T3 — "Single authoritative backtester + remove mock-data fallback".

Validation and production must NEVER run on fabricated data: a backtest or
portfolio-validation run that silently falls back to generated OHLCV produces a
fictional edge, which is worse than no result. Historically the decision to use
mock data was read from ``settings.infrastructure.use_mock_data`` (True under the
``dev`` profile), so any validation run launched in a dev environment could
quietly fabricate its inputs.

This module makes mock data a hard error everywhere by default. Mock generation
is permitted ONLY when explicitly enabled in-code, which is intended exclusively
for unit tests exercising the generators / backtester mechanics. The opt-in is
deliberately NOT derived from any profile, environment variable, or settings
field, so "0 mock-data executions outside unit tests" holds by construction.

Usage in a unit test::

    from shared.mock_data_guard import allow_mock_data

    with allow_mock_data():
        df = backtester.generate_mock_data(symbol, start, end)
"""
from contextlib import contextmanager

# Process-wide flag. False by default and never set from settings/env/profile —
# only the allow_mock_data() context manager flips it.
_MOCK_DATA_EXPLICITLY_ALLOWED = False


def mock_data_allowed() -> bool:
    """Return True only when mock data has been explicitly enabled in-code."""
    return _MOCK_DATA_EXPLICITLY_ALLOWED


def assert_mock_data_allowed(explicit: bool = False, context: str = "") -> None:
    """Raise unless mock data is explicitly permitted.

    Args:
        explicit: A local, in-code opt-in (e.g. a backtester constructed with
            ``use_mock_data=True`` by a unit test). Treated as an explicit
            permission, equivalent to being inside ``allow_mock_data()``.
        context: Optional caller description included in the error message.
    """
    if explicit or _MOCK_DATA_EXPLICITLY_ALLOWED:
        return
    where = f" ({context})" if context else ""
    raise RuntimeError(
        "Mock/synthetic market data is forbidden outside unit tests"
        f"{where}: validation and production must run on real data only "
        "(E-P5.2 T3). To use mock data in a unit test, wrap the call in "
        "shared.mock_data_guard.allow_mock_data()."
    )


@contextmanager
def allow_mock_data():
    """Unit-test-only: explicitly permit mock data within this context."""
    global _MOCK_DATA_EXPLICITLY_ALLOWED
    previous = _MOCK_DATA_EXPLICITLY_ALLOWED
    _MOCK_DATA_EXPLICITLY_ALLOWED = True
    try:
        yield
    finally:
        _MOCK_DATA_EXPLICITLY_ALLOWED = previous
