"""Bounded exponential-backoff retry (E11 / B6 — reliability layer).

A small, dependency-free retry helper for transient broker/network faults. Use it for:
  * idempotent READS (order status, positions, balances) — always safe;
  * idempotent WRITES — safe only when paired with a stable client_order_id (B2), so the
    exchange deduplicates a re-sent order.

Deterministic for tests: the sleep function is injectable (defaults to time.sleep), and
backoff is computed without randomness.
"""

from __future__ import annotations

import time
from typing import Callable, Optional, Tuple, Type


def retry_with_backoff(fn: Callable, *, max_attempts: int = 3, base_delay: float = 0.5,
                       max_delay: float = 8.0, factor: float = 2.0,
                       retry_on: Tuple[Type[BaseException], ...] = (Exception,),
                       should_retry: Optional[Callable[[BaseException], bool]] = None,
                       sleep: Callable[[float], None] = time.sleep,
                       on_retry: Optional[Callable[[int, BaseException, float], None]] = None):
    """Call ``fn()`` with bounded exponential backoff; return its result or raise the last error.

    Args:
        max_attempts: total attempts (>=1).
        base_delay/factor/max_delay: delay = min(max_delay, base_delay * factor**(attempt-1)).
        retry_on: exception types that trigger a retry.
        should_retry: optional predicate; if provided and returns False, the error is raised
            immediately (e.g. don't retry a 4xx rejection).
        sleep: injectable sleep (for deterministic tests).
        on_retry: optional callback(attempt, exc, delay) for logging.
    """
    if max_attempts < 1:
        max_attempts = 1
    last_exc: Optional[BaseException] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except retry_on as exc:
            last_exc = exc
            if should_retry is not None and not should_retry(exc):
                raise
            if attempt >= max_attempts:
                raise
            delay = min(max_delay, base_delay * (factor ** (attempt - 1)))
            if on_retry is not None:
                try:
                    on_retry(attempt, exc, delay)
                except Exception:
                    pass
            sleep(delay)
    if last_exc is not None:  # pragma: no cover - loop always returns or raises
        raise last_exc


__all__ = ["retry_with_backoff"]
