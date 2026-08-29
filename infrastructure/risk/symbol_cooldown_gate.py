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
        self._sl_cooldowns: Dict[str, float] = {}
        self._symbol_loss_history: Dict[str, list[float]] = {}
        self._load_cooldown_journal()

    @classmethod
    def get_instance(cls) -> SymbolCooldownGate:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @staticmethod
    def normalize_symbol(sym: Any) -> str:
        s = getattr(sym, "value", None) or str(sym or "")
        return s.upper().replace("-", "").replace("/", "").replace("_", "").strip()

    def _load_cooldown_journal(self) -> None:
        """Load persistent Stop Loss cooldowns and loss history from disk."""
        try:
            os.makedirs(os.path.dirname(COOLDOWN_JOURNAL_PATH), exist_ok=True)
            if os.path.exists(COOLDOWN_JOURNAL_PATH) and os.path.getsize(COOLDOWN_JOURNAL_PATH) > 0:
                with open(COOLDOWN_JOURNAL_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "cooldowns" in data:
                            self._sl_cooldowns = data.get("cooldowns", {})
                            self._symbol_loss_history = data.get("loss_history", {})
                        else:
                            # Legacy format migration (convert start_ts to expiry_ts)
                            for sym, ts in data.items():
                                self._sl_cooldowns[sym] = float(ts) + 3600.0

            # Reconcile recent trade losses from trade_journal.csv on startup
            trade_journal_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "trade_journal.csv")
            if os.path.exists(trade_journal_path) and os.path.getsize(trade_journal_path) > 0:
                try:
                    import pandas as pd
                    df = pd.read_csv(trade_journal_path)
                    if not df.empty and "pnl_usdt" in df.columns and "symbol" in df.columns:
                        now_ts = datetime.now().timestamp()
                        df_unique = df.drop_duplicates(subset=["trade_id"]).copy() if "trade_id" in df.columns else df
                        for _, row in df_unique.iterrows():
                            pnl = float(row.get("pnl_usdt", 0) or 0)
                            sym = self.normalize_symbol(row.get("symbol", ""))
                            exit_ts_str = str(row.get("exit_timestamp") or row.get("entry_timestamp") or "")
                            if sym and pnl < 0 and exit_ts_str:
                                try:
                                    dt = datetime.fromisoformat(exit_ts_str.replace("Z", "+00:00"))
                                    exit_ts = dt.timestamp()
                                    if now_ts - exit_ts <= 86400.0:  # Within last 24h
                                        if sym not in self._symbol_loss_history:
                                            self._symbol_loss_history[sym] = []
                                        if exit_ts not in self._symbol_loss_history[sym]:
                                            self._symbol_loss_history[sym].append(exit_ts)
                                except Exception:
                                    pass
                        for sym, losses in self._symbol_loss_history.items():
                            if len(losses) >= 2:
                                latest_loss = max(losses)
                                expiry = latest_loss + 86400.0
                                if expiry > now_ts:
                                    self._sl_cooldowns[sym] = max(self._sl_cooldowns.get(sym, 0.0), expiry)
                            elif len(losses) == 1:
                                latest_loss = losses[0]
                                expiry = latest_loss + 3600.0
                                if expiry > now_ts:
                                    self._sl_cooldowns[sym] = max(self._sl_cooldowns.get(sym, 0.0), expiry)
                except Exception as ex:
                    logger.warning(f"Could not auto-reconcile cooldowns from trade_journal.csv: {ex}")
        except Exception as e:
            logger.error(f"⚠️ SymbolCooldownGate: Journal corrupt: {e}. Resetting.")

    def _save_cooldown_journal(self) -> None:
        """Save persistent Stop Loss cooldowns and loss history atomically."""
        try:
            os.makedirs(os.path.dirname(COOLDOWN_JOURNAL_PATH), exist_ok=True)
            payload = {
                "cooldowns": self._sl_cooldowns,
                "loss_history": self._symbol_loss_history
            }
            tmp_path = f"{COOLDOWN_JOURNAL_PATH}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, COOLDOWN_JOURNAL_PATH)
        except Exception as e:
            logger.error(f"⚠️ SymbolCooldownGate: Failed atomic save of journal: {e}")

    def record_stop_loss_exit(self, symbol: Any, exit_time: Optional[datetime] = None) -> None:
        """Activate 60-minute Stop Loss Cooldown (or 24-hour Circuit Breaker on rapid multi-loss)."""
        with self._lock:
            clean_sym = self.normalize_symbol(symbol)
            ts = (exit_time or datetime.now()).timestamp()

            # Track loss events in the last 2 hours (7200s)
            if clean_sym not in self._symbol_loss_history:
                self._symbol_loss_history[clean_sym] = []
            self._symbol_loss_history[clean_sym].append(ts)
            # Prune events older than 2 hours
            self._symbol_loss_history[clean_sym] = [t for t in self._symbol_loss_history[clean_sym] if ts - t <= 7200.0]

            if len(self._symbol_loss_history[clean_sym]) >= 2:
                # 24-Hour Circuit Breaker Lockout (86,400s)
                self._sl_cooldowns[clean_sym] = ts + 86400.0
                self._save_cooldown_journal()
                logger.warning(f"🛑 [SYMBOL HEALTH GATE] 24-Hour Circuit Breaker ACTIVATED for {symbol} ({clean_sym}) due to multiple rapid losses/unwinds in 2h window.")
            else:
                # Standard 60-minute Stop Loss Cooldown
                self._sl_cooldowns[clean_sym] = ts + 3600.0
                self._save_cooldown_journal()
                logger.warning(f"🛑 SYMBOL COOLDOWN GATE: Activated 60m Stop Loss Cooldown for {symbol} ({clean_sym})")

    def record_take_profit_exit(self, symbol: Any, exit_time: Optional[datetime] = None) -> None:
        """Register a 15-minute post-trade spacing window when trade exits via Take Profit."""
        with self._lock:
            clean_sym = self.normalize_symbol(symbol)
            ts = (exit_time or datetime.now()).timestamp()
            # Clear loss history on successful take profit
            if clean_sym in self._symbol_loss_history:
                self._symbol_loss_history[clean_sym].clear()
            # 15-minute post-trade spacing cooldown
            self._sl_cooldowns[clean_sym] = ts + 900.0
            self._save_cooldown_journal()
            logger.info(f"✅ SYMBOL COOLDOWN GATE: Registered 15m post-trade spacing window for {symbol} ({clean_sym}) via Take Profit exit.")

    def is_symbol_allowed(self, symbol: Any, cooldown_minutes: int = 60) -> Tuple[bool, str]:
        """Check if trading is allowed for symbol under cooldown, trade-spacing, and blacklist rules."""
        with self._lock:
            clean_sym = self.normalize_symbol(symbol)
            from infrastructure.services.symbol_validator import symbol_validator
            blacklisted = symbol_validator.get_blacklisted_symbols()
            if clean_sym in blacklisted or str(symbol or "").upper() in blacklisted:
                return False, f"PERMANENT_BLACKLIST: {clean_sym} is blacklisted from trading in configuration"

            now_ts = datetime.now().timestamp()

            expiry_ts = self._sl_cooldowns.get(clean_sym, 0.0)
            if now_ts < expiry_ts:
                rem_min = (expiry_ts - now_ts) / 60.0
                return False, f"60m Stop Loss Cooldown ACTIVE for {clean_sym} ({rem_min:.1f}m remaining)"

            return True, "ALLOWED"
        return True, "ALLOWED"


# Global convenience accessor
symbol_cooldown_gate = SymbolCooldownGate.get_instance()
