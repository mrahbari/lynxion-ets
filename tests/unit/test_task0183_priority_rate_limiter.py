import threading
import time

from shared.rate_limiter import RateLimiter


def test_zero_timeout_fails_without_consuming_capacity():
    limiter = RateLimiter(max_requests=1, time_window=3600)
    limiter.tokens = 0

    assert limiter.wait_for_tokens(priority=True, timeout=0) is False
    assert 0 <= limiter.tokens < 1


def test_priority_waiter_precedes_ordinary_waiter():
    limiter = RateLimiter(max_requests=1, time_window=3600)
    limiter.tokens = 0
    order = []

    ordinary = threading.Thread(
        target=lambda: order.append(
            "ordinary" if limiter.wait_for_tokens(timeout=1.0) else "ordinary-timeout"
        )
    )
    priority = threading.Thread(
        target=lambda: order.append(
            "priority" if limiter.wait_for_tokens(priority=True, timeout=1.0)
            else "priority-timeout"
        )
    )
    ordinary.start()
    priority.start()

    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        with limiter.lock:
            if len(limiter._priority_waiters) == 1:
                break
        time.sleep(0.005)
    with limiter._condition:
        limiter.tokens = 1
        limiter._condition.notify_all()

    priority.join(timeout=1.0)
    assert order[0] == "priority"

    with limiter._condition:
        limiter.tokens = 1
        limiter._condition.notify_all()
    ordinary.join(timeout=1.0)
    assert order == ["priority", "ordinary"]


def test_priority_waiters_preserve_fifo_order():
    limiter = RateLimiter(max_requests=1, time_window=3600)
    limiter.tokens = 0
    order = []

    threads = []
    for label in ("first", "second"):
        thread = threading.Thread(
            target=lambda value=label: order.append(value)
            if limiter.wait_for_tokens(priority=True, timeout=1.0) else None
        )
        thread.start()
        threads.append(thread)
        deadline = time.monotonic() + 0.5
        expected = len(threads)
        while time.monotonic() < deadline:
            with limiter.lock:
                if len(limiter._priority_waiters) == expected:
                    break
            time.sleep(0.005)

    for expected in ("first", "second"):
        with limiter._condition:
            limiter.tokens = 1
            limiter._condition.notify_all()
        deadline = time.monotonic() + 0.5
        while len(order) < (1 if expected == "first" else 2) and time.monotonic() < deadline:
            time.sleep(0.005)
        assert order[-1] == expected

    for thread in threads:
        thread.join(timeout=1.0)
