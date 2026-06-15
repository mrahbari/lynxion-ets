"""Startup preflight checks (E11 / R2).

A fail-fast gate the production runtime runs before trading: it resolves the effective
execution mode (PAPER / TESTNET / LIVE) from settings + the LIVE_TRADING env opt-in and
reports blocking issues and warnings. The runtime should refuse to start LIVE when there
are blocking issues (missing/placeholder keys, inconsistent flags, kill switch engaged).

Pure/deterministic: settings and env are injected, so it is unit-testable without I/O.
This complements (does not replace) the per-order LIVE_EXECUTION_GUARD — it catches an
unsafe configuration before the first order is ever evaluated.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

_PLACEHOLDER_HINTS = ("your_", "changeme", "xxx", "placeholder", "<", "example")
_TRUTHY = {"1", "true", "yes", "on", "y", "t"}


def _is_truthy(v: Optional[str]) -> bool:
    return str(v).strip().lower() in _TRUTHY if v is not None else False


def _looks_placeholder(v: str) -> bool:
    s = (v or "").strip().lower()
    return (not s) or any(h in s for h in _PLACEHOLDER_HINTS)


def run_preflight(settings: Any, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Return {mode, ok, blocking, warnings, broker}. ``ok`` is False if there are blocking issues."""
    env = env if env is not None else os.environ
    blocking, warnings = [], []
    broker_cfg = getattr(settings, "broker", None)

    broker = (getattr(broker_cfg, "default_broker", "bingx") or "bingx").lower()
    paper = bool(getattr(broker_cfg, "paper_trading", True)) if broker_cfg is not None else True
    global_testnet = bool(getattr(broker_cfg, "testnet", True)) if broker_cfg is not None else True
    testnet = bool(getattr(broker_cfg, f"{broker}_testnet", global_testnet)) if broker_cfg is not None else True
    placement = bool(getattr(broker_cfg, f"{broker}_order_placement_enabled", False)) if broker_cfg is not None else False
    live_trading = _is_truthy(env.get("LIVE_TRADING"))

    # Effective mode (mirrors the guard's precedence).
    if paper:
        mode = "PAPER"
    elif not placement:
        mode = "BLOCKED"
    elif testnet:
        mode = "TESTNET"
    elif live_trading:
        mode = "LIVE"
    else:
        mode = "BLOCKED"

    # Credential checks (needed for any real send: TESTNET or LIVE).
    if mode in ("TESTNET", "LIVE") and broker_cfg is not None:
        api_key = getattr(broker_cfg, f"{broker}_api_key", "") or ""
        secret = getattr(broker_cfg, f"{broker}_secret_key", "") or ""
        if _looks_placeholder(api_key) or _looks_placeholder(secret):
            blocking.append(f"{broker} API key/secret missing or placeholder for {mode} mode")

    # LIVE requires the explicit opt-in AND must be deliberate.
    if mode == "LIVE":
        if not live_trading:  # defensive; mode==LIVE already implies it
            blocking.append("LIVE mode without explicit LIVE_TRADING=true")
        warnings.append("LIVE (real-funds) mode: orders will hit the live exchange endpoint")

    # Inconsistency: live endpoint selected (paper off, testnet off) but no opt-in -> everything blocked.
    if not paper and not testnet and not live_trading and placement:
        warnings.append("live endpoint selected but LIVE_TRADING not set — all orders will be BLOCKED by the guard")

    # Kill switch already engaged at startup -> nothing will trade.
    try:
        from shared.live_execution_guard import live_execution_guard
        if live_execution_guard.is_killed():
            warnings.append("LIVE_EXECUTION_GUARD kill switch is ENGAGED at startup — orders blocked until disengaged")
    except Exception:
        pass

    return {
        "mode": mode,
        "ok": len(blocking) == 0,
        "blocking": blocking,
        "warnings": warnings,
        "broker": broker,
        "flags": {"paper_trading": paper, "testnet": testnet,
                  "order_placement_enabled": placement, "live_trading": live_trading},
    }


__all__ = ["run_preflight"]
