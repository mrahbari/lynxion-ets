"""Production-Grade Symbol Cooldown Gate (E11 / Phase 2).

Provides a single, thread-safe, centralized manager for per-symbol Stop Loss cooldowns
and active position lockout.

Rules:
1. When a trade exits via STOP_MARKET / STOP LOSS (is_profitable == False), a 60-minute (3600s)
   cooldown is strictly activated and persisted to disk at `data/sl_cooldown_journal.json`.
2. When a trade exits via TAKE_PROFIT (is_profitable == True), the 60-minute cooldown for that symbol
   is immediately CLEARED, allowing high-conviction continuation setups.
3. Symbol normalization (`BICO-USDT` vs `BICOUSDT` vs `BICO/USDT`) is handled uniformly.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from shared.logger import logger

COOLDOWN_JOURNAL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sl_cooldown_journal.json")


class SymbolCooldownGate:
    """Thread-safe singleton managing per-symbol Stop Loss cooldowns with atomic disk persistence."""

    _instance: Optional[SymbolCooldownGate] = None
    _lock = threading.RLock()

    def __init__(self):
        self._sl_cooldowns: Dict[str, float] = self._load_cooldown_journal()

    @classmethod
    def get_instance(cls) -> SymbolCooldownGate:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @staticmethod
    def normalize_symbol(sym: Any) -> str:
        s = getattr(sym, "value", None) or str(sym or "")
        return s.upper().replace("-", "").replace("/", "").replace("_", "")

    def _load_cooldown_journal(self) -> Dict[str, float]:
        """Load persistent Stop Loss cooldown timestamps from disk."""
        try:
            os.makedirs(os.path.dirname(COOLDOWN_JOURNAL_PATH), exist_ok=True)
            if os.path.exists(COOLDOWN_JOURNAL_PATH) and os.path.getsize(COOLDOWN_JOURNAL_PATH) > 0:
                with open(COOLDOWN_JOURNAL_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"⚠️ SymbolCooldownGate: Journal corrupt: {e}. Resetting.")
        return {}

    def _save_cooldown_journal(self) -> None:
        """Save persistent Stop Loss cooldown timestamps atomically."""
        try:
            os.makedirs(os.path.dirname(COOLDOWN_JOURNAL_PATH), exist_ok=True)
            tmp_path = f"{COOLDOWN_JOURNAL_PATH}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._sl_cooldowns, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, COOLDOWN_JOURNAL_PATH)
        except Exception as e:
            logger.error(f"⚠️ SymbolCooldownGate: Failed atomic save of journal: {e}")

    def record_stop_loss_exit(self, symbol: Any, exit_time: Optional[datetime] = None) -> None:
        """Activate 60-minute Stop Loss Cooldown for a symbol."""
        with self._lock:
            clean_sym = self.normalize_symbol(symbol)
            ts = (exit_time or datetime.now()).timestamp()
            self._sl_cooldowns[clean_sym] = ts
            self._save_cooldown_journal()
            logger.warning(f"🛑 SYMBOL COOLDOWN GATE: Activated 60m Stop Loss Cooldown for {symbol} ({clean_sym})")

    def record_take_profit_exit(self, symbol: Any) -> None:
        """Clear Stop Loss Cooldown for a symbol when trade exits via Take Profit."""
        with self._lock:
            clean_sym = self.normalize_symbol(symbol)
            if clean_sym in self._sl_cooldowns:
                del self._sl_cooldowns[clean_sym]
                self._save_cooldown_journal()
                logger.info(f"✅ SYMBOL COOLDOWN GATE: Cleared Stop Loss Cooldown for {symbol} ({clean_sym}) via Take Profit exit.")

    def is_symbol_allowed(self, symbol: Any, cooldown_minutes: int = 60) -> Tuple[bool, str]:
        """Check if trading is allowed for symbol under 60-minute SL cooldown rules."""
        with self._lock:
            clean_sym = self.normalize_symbol(symbol)
            now_ts = datetime.now().timestamp()
            cooldown_seconds = cooldown_minutes * 60

            last_sl_ts = self._sl_cooldowns.get(clean_sym)
            if last_sl_ts and (now_ts - last_sl_ts) < cooldown_seconds:
                rem_min = (cooldown_seconds - (now_ts - last_sl_ts)) / 60.0
                return False, f"60m Stop Loss Cooldown ACTIVE for {clean_sym} ({rem_min:.1f}m remaining)"

            return True, "ALLOWED"
        return None


# Global convenience accessor
symbol_cooldown_gate = SymbolCooldownGate.get_instance()
