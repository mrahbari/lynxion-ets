"""Append-only, non-blocking signal decision census for prospective research."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _default_path() -> str:
    return os.getenv("SIGNAL_CENSUS_JOURNAL_PATH") or os.path.join(_project_root(), "data", "signal_census.jsonl")


def _scalar(value: Any) -> Any:
    value = getattr(value, "amount", getattr(value, "value", value))
    return value if isinstance(value, (str, int, float, bool)) or value is None else str(value)


class SignalCensusJournal:
    """Durably records strategy decisions without participating in those decisions."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or _default_path()
        self._lock = threading.RLock()

    def record(self, strategy: str, fused_signal: Any, decision: str, reason: str, intent: Any = None) -> None:
        metadata = getattr(fused_signal, "metadata", None) or {}
        risk = getattr(intent, "risk_parameters", None) or {}
        entry_price = metadata.get("current_price") or metadata.get("close_price")
        stop_loss = _scalar(getattr(intent, "stop_loss_price", None)) if intent else risk.get("stop_loss")
        take_profit = _scalar(getattr(intent, "take_profit_price", None)) if intent else risk.get("take_profit")
        expected_rr = None
        try:
            if entry_price and stop_loss and take_profit:
                expected_rr = abs(float(take_profit) - float(entry_price)) / abs(float(entry_price) - float(stop_loss))
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        rec: Dict[str, Any] = {
            "timestamp": (getattr(fused_signal, "timestamp", None) or datetime.now(timezone.utc)).isoformat(),
            "strategy": strategy,
            "symbol": _scalar(getattr(fused_signal, "symbol", None)),
            "decision": decision,
            "reason": reason,
            "side": _scalar(getattr(intent, "side", None)) if intent else None,
            "fused_confidence": _scalar(getattr(fused_signal, "confidence", None)),
            "regime": _scalar(getattr(fused_signal, "regime_context", None)),
            "direction": _scalar(getattr(fused_signal, "direction", None)),
            "dominant_bias": _scalar(getattr(fused_signal, "dominant_bias", None)),
            "dominance_score": _scalar(getattr(fused_signal, "dominance_score", None)),
            "entry_price": _scalar(entry_price),
            "atr": _scalar(metadata.get("atr")),
            "spread": _scalar(metadata.get("spread")),
            "timeframe": _scalar(metadata.get("timeframe")),
            "watcher": _scalar(metadata.get("watcher_name") or metadata.get("primary_watcher")),
            "stop_loss": _scalar(stop_loss),
            "take_profit": _scalar(take_profit),
            "expected_reward_risk": expected_rr,
        }
        with self._lock:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
                handle.flush()
                os.fsync(handle.fileno())


signal_census_journal = SignalCensusJournal()
