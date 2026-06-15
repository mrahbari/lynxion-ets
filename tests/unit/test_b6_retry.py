"""B6 — retry/backoff utility (deterministic; injected sleep)."""

import pytest

from shared.retry import retry_with_backoff


def test_succeeds_after_transient_failures():
    calls = {"n": 0}
    delays = []

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    out = retry_with_backoff(flaky, max_attempts=5, base_delay=1, factor=2,
                             sleep=delays.append)
    assert out == "ok" and calls["n"] == 3
    assert delays == [1, 2]            # exponential backoff between the 3 attempts


def test_raises_after_max_attempts():
    calls = {"n": 0}

    def always_fail():
        calls["n"] += 1
        raise TimeoutError("down")

    with pytest.raises(TimeoutError):
        retry_with_backoff(always_fail, max_attempts=3, base_delay=0, sleep=lambda d: None)
    assert calls["n"] == 3


def test_should_retry_predicate_short_circuits():
    calls = {"n": 0}

    def rejected():
        calls["n"] += 1
        raise ValueError("4xx rejection — do not retry")

    with pytest.raises(ValueError):
        retry_with_backoff(rejected, max_attempts=5,
                           should_retry=lambda e: "do not retry" not in str(e),
                           sleep=lambda d: None)
    assert calls["n"] == 1             # not retried


def test_delay_capped_at_max_delay():
    delays = []
    calls = {"n": 0}

    def fail():
        calls["n"] += 1
        raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        retry_with_backoff(fail, max_attempts=5, base_delay=1, factor=10, max_delay=5,
                           sleep=delays.append)
    assert max(delays) <= 5            # capped
