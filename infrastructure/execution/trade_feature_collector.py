"""Persistent Trade Dataset Collector & Continuous Trade Journal (E12 / Research).

A non-blocking, fail-safe background data collection service that continuously builds
and maintains `data/trade_journal.csv` from real executed order records, exchange position
histories, and execution truth ledgers.

STRICT RESEARCH CONSTRAINTS:
- One CSV row represents ONE COMPLETED TRADE (or B1 Emergency Unwind).
- Incomplete orders / unclosed entry orders / failed pre-send orders are excluded.
- Entry fill price, exit fill price, realized PnL, fees, and timestamps are authoritative from exchange position histories.
- Read-only with respect to trading state / order flows.
- Best-effort background thread execution with strict exception isolation.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("TradeJournalCollector")

CSV_HEADER = [
    "trade_id",
    "symbol",
    "strategy",
    "side",
    "entry_timestamp",
    "exit_timestamp",
    "entry_price",
    "exit_price",
    "quantity",
    "pnl_usdt",
    "fees_usdt",
    "exit_reason",
    "actual_fill_price",
    "initial_stop_loss",
    "initial_take_profit",
    "risk_usdt",
    "r_multiple",
    "confidence",
    "regime",
    "timeframe",
    "signal_direction",
    "duration_seconds",
    "sl_distance_pct",
    "tp_distance_pct",
    "order_id",
    "order_ref",
    "client_order_id",
    "exchange",
    "execution_latency_ms",
    "is_execution_unwind",
    "status",
]


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def default_journal_csv_path() -> str:
    return os.getenv("TRADE_JOURNAL_CSV_PATH") or os.path.join(_project_root(), "data", "trade_journal.csv")


def default_features_csv_path() -> str:
    return os.getenv("TRADE_FEATURES_CSV_PATH") or os.path.join(_project_root(), "data", "trade_features.csv")


def default_journal_path() -> str:
    return os.getenv("LIVE_ORDER_JOURNAL_PATH") or os.path.join(_project_root(), "data", "live_order_journal.json")


def default_ledger_path() -> str:
    return os.getenv("EXECUTION_TRUTH_LEDGER_PATH") or os.path.join(_project_root(), "logs", "execution_truth_ledger.jsonl")


def default_forensic_path() -> str:
    return os.getenv("FORENSIC_LOG_PATH") or os.path.join(_project_root(), "logs", "forensic.log")


class TradeFeatureCollector:
    """Non-blocking background collector for canonical data/trade_journal.csv."""

    def __init__(
        self,
        csv_path: Optional[str] = None,
        journal_path: Optional[str] = None,
        ledger_path: Optional[str] = None,
        forensic_path: Optional[str] = None,
        poll_interval_seconds: float = 30.0,
    ):
        self.enabled = os.getenv("TRADE_JOURNAL_COLLECTOR_ENABLED", "true").lower() in ("true", "1", "yes")
        self.csv_path = csv_path or default_journal_csv_path()
        self.alt_csv_path = default_features_csv_path() if csv_path is None else None
        self.journal_path = journal_path or default_journal_path()
        self.ledger_path = ledger_path or default_ledger_path()
        self.forensic_path = forensic_path or default_forensic_path()
        self.poll_interval_seconds = poll_interval_seconds

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._recorded_ids: Set[str] = set()

        if self.enabled:
            self._ensure_csv_headers()
            self._load_recorded_ids()
        else:
            logger.info("TRADE_JOURNAL: TradeFeatureCollector is currently DISABLED via configuration toggle.")

    def _ensure_csv_headers(self) -> None:
        """Create data directory and CSV headers for trade_journal.csv."""
        paths = [p for p in (self.csv_path, self.alt_csv_path) if p]
        try:
            for p in paths:
                os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
                if not os.path.exists(p) or os.path.getsize(p) == 0:
                    with open(p, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(CSV_HEADER)
                    logger.info(f"TRADE_JOURNAL: Initialized canonical research CSV at {p}")
        except Exception as e:
            logger.error(f"TRADE_JOURNAL: Failed to initialize CSV header: {e}")

    def _load_recorded_ids(self) -> None:
        """Load already recorded trade_ids from CSV for idempotency."""
        with self._lock:
            self._recorded_ids.clear()
            paths = [p for p in (self.csv_path, self.alt_csv_path) if p]
            for p in paths:
                if not os.path.exists(p):
                    continue
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            tid = row.get("trade_id")
                            if tid:
                                self._recorded_ids.add(tid)
                            ref = row.get("order_ref")
                            if ref:
                                self._recorded_ids.add(ref)
                            oid = row.get("order_id")
                            if oid:
                                self._recorded_ids.add(oid)
                except Exception as e:
                    logger.error(f"TRADE_JOURNAL: Error loading recorded IDs from {p}: {e}")
            logger.info(f"TRADE_JOURNAL: Loaded {len(self._recorded_ids)} recorded trade keys from CSV")

    # -- Dynamic Symbol Discovery -----------------------------------------------

    def _discover_all_symbols(self, adapter: Optional[Any] = None) -> List[str]:
        """Dynamically discover all traded symbols across config, CSV, journal, ledger, and broker."""
        discovered: Set[str] = set()

        # 1. Parse dynamically from active settings / config watchlist
        try:
            from bootstrap.settings.loaders import load_settings
            st = load_settings()
            sym_cfg = getattr(st, "symbols", None) or getattr(st, "trading", None)
            watchlist = getattr(sym_cfg, "watchlist", None) or getattr(sym_cfg, "active_symbols", None) or []
            for s in watchlist:
                clean = str(s).upper().replace("-", "").replace("_", "").replace("/", "")
                if clean.endswith("USDT"):
                    base = clean[:-4]
                    discovered.add(f"{base}-USDT")
        except Exception as e:
            logger.debug(f"TRADE_JOURNAL: Settings watchlist parsing skipped: {e}")

        # 2. Parse from existing CSV records (data/trade_journal.csv)
        if os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sym = row.get("symbol")
                        if sym:
                            clean = str(sym).upper().replace("-", "").replace("_", "").replace("/", "")
                            if clean.endswith("USDT"):
                                base = clean[:-4]
                                discovered.add(f"{base}-USDT")
            except Exception as e:
                logger.warning(f"TRADE_JOURNAL: Could not parse symbols from CSV: {e}")

        # 1. Parse from live_order_journal.json
        if os.path.exists(self.journal_path):
            try:
                with open(self.journal_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            sym = entry.get("symbol")
                            if sym:
                                clean = str(sym).upper().replace("-", "").replace("_", "").replace("/", "")
                                if clean.endswith("USDT"):
                                    base = clean[:-4]
                                    discovered.add(f"{base}-USDT")
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"TRADE_JOURNAL: Could not parse symbols from journal: {e}")

        # 2. Parse from execution_truth_ledger.jsonl
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            sym = entry.get("symbol")
                            if sym:
                                clean = str(sym).upper().replace("-", "").replace("_", "").replace("/", "")
                                if clean.endswith("USDT"):
                                    base = clean[:-4]
                                    discovered.add(f"{base}-USDT")
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"TRADE_JOURNAL: Could not parse symbols from ledger: {e}")

        # 3. Parse active positions from broker if connected
        if adapter is not None:
            try:
                positions = adapter.get_all_positions() or []
                for p in positions:
                    raw_sym = getattr(p, "symbol", "")
                    if raw_sym:
                        clean = str(raw_sym).upper().replace("-", "").replace("_", "").replace("/", "")
                        if clean.endswith("USDT"):
                            base = clean[:-4]
                            discovered.add(f"{base}-USDT")
            except Exception as e:
                logger.warning(f"TRADE_JOURNAL: Could not parse symbols from broker positions: {e}")

        return sorted(list(discovered))

    # -- Intent Metadata Cross-Referencing --------------------------------------

    def _load_intent_metadata_map(self) -> Dict[str, Dict[str, Any]]:
        """Load strategy-level metadata (stop_loss, take_profit, confidence, regime, strategy) from journal/ledger keyed by order_ref and order_id."""
        meta_map: Dict[str, Dict[str, Any]] = {}

        # 1. Read live_order_journal.json
        if os.path.exists(self.journal_path):
            try:
                with open(self.journal_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            ref = entry.get("order_ref") or entry.get("client_order_id")
                            oid = entry.get("order_id")
                            sl = entry.get("stop_loss") or entry.get("initial_stop_loss")
                            tp = entry.get("take_profit") or entry.get("initial_take_profit")
                            conf = entry.get("confidence")
                            reg = entry.get("regime")
                            strat = entry.get("strategy") or entry.get("strategy_name")

                            meta = {
                                "initial_stop_loss": str(sl) if sl is not None else "",
                                "initial_take_profit": str(tp) if tp is not None else "",
                                "confidence": str(conf) if conf is not None else "",
                                "regime": str(reg) if reg is not None else "",
                                "strategy": str(strat) if strat is not None else "",
                            }
                            if ref:
                                meta_map[str(ref)] = meta
                            if oid:
                                meta_map[str(oid)] = meta
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"TRADE_JOURNAL: Could not load metadata from journal: {e}")

        # 2. Read execution_truth_ledger.jsonl
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            ref = entry.get("order_ref") or entry.get("client_order_id")
                            oid = entry.get("order_id")
                            sl = entry.get("stop_loss") or entry.get("initial_stop_loss")
                            tp = entry.get("take_profit") or entry.get("initial_take_profit")
                            conf = entry.get("confidence")
                            reg = entry.get("regime")
                            strat = entry.get("strategy") or entry.get("strategy_name")

                            keys = [k for k in [ref, oid] if k]
                            for k in keys:
                                sk = str(k)
                                meta = meta_map.get(sk, {})
                                if sl is not None and not meta.get("initial_stop_loss"):
                                    meta["initial_stop_loss"] = str(sl)
                                if tp is not None and not meta.get("initial_take_profit"):
                                    meta["initial_take_profit"] = str(tp)
                                if conf is not None and not meta.get("confidence"):
                                    meta["confidence"] = str(conf)
                                if reg is not None and not meta.get("regime"):
                                    meta["regime"] = str(reg)
                                if strat is not None and not meta.get("strategy"):
                                    meta["strategy"] = str(strat)
                                meta_map[sk] = meta
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"TRADE_JOURNAL: Could not load metadata from ledger: {e}")

        return meta_map

    # -- Exchange Position History & Reconstructed Completed Trades ---------------

    def reconstruct_exchange_completed_trades(self) -> List[Dict[str, Any]]:
        """Fetch exchange order histories (including VST demo account) and group Entry + Exit by positionID."""
        completed_trades: List[Dict[str, Any]] = []
        try:
            import time
            from bootstrap.settings.loaders import load_settings
            from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter

            settings = load_settings()
            config = {
                "api_key": settings.broker.bingx_api_key,
                "secret_key": settings.broker.bingx_secret_key,
                "passphrase": settings.broker.bingx_passphrase,
            }
            adapter = BingXBrokerAdapter(config)
            adapter.connect()

            intent_meta = self._load_intent_metadata_map()

            now_ms = int(time.time() * 1000)
            seven_days_ms = 7 * 24 * 3600 * 1000
            all_orders: List[Any] = []

            # 1. Query VST Demo Account allOrders in 7-day chunks across past 35 days
            for i in range(5):
                end_ms = now_ms - (i * seven_days_ms)
                start_ms = end_ms - seven_days_ms
                try:
                    res = adapter._broker._make_request(
                        "GET",
                        "/openApi/swap/v2/trade/allOrders",
                        data={"marginCoin": "VST", "startTime": start_ms, "endTime": end_ms, "limit": 500},
                        signed=True,
                    )
                    if res.get("code") == 0:
                        all_orders.extend(res.get("data", {}).get("orders", []) or [])
                except Exception as vst_err:
                    logger.warning(f"TRADE_JOURNAL: VST chunk #{i+1} fetch error: {vst_err}")

            # 2. Query per-symbol order history
            symbols = self._discover_all_symbols(adapter)
            for sym in symbols:
                try:
                    hist = adapter._broker.get_order_history(sym, limit=100) or []
                    all_orders.extend(hist)
                except Exception:
                    pass

            by_pos: Dict[str, Dict[str, List[Any]]] = {}
            for o in all_orders:
                pos_id = str(o.get("positionID") or "")
                if not pos_id or pos_id == "0":
                    continue
                if pos_id not in by_pos:
                    by_pos[pos_id] = {"entries": [], "exits": []}

                st = str(o.get("status", "")).upper()
                is_reduce = o.get("reduceOnly") in (True, "true", "TRUE")
                o_type = str(o.get("type", "")).upper()

                if st == "FILLED":
                    if is_reduce or o_type in ("STOP_MARKET", "TAKE_PROFIT_MARKET", "LIQUIDATION"):
                        by_pos[pos_id]["exits"].append(o)
                    else:
                        by_pos[pos_id]["entries"].append(o)

            for pos_id, data in by_pos.items():
                if data["entries"] and data["exits"]:
                    e = data["entries"][0]
                    x = data["exits"][0]

                    sym_raw = str(e.get("symbol") or "")
                    clean_sym = sym_raw.replace("-", "").replace("_", "").replace("/", "")
                    side = str(e.get("side") or "").upper()
                    entry_price = str(e.get("avgPrice") or "")
                    exit_price = str(x.get("avgPrice") or "")
                    pnl = str(x.get("profit") or "")
                    fee = str(x.get("commission") or "")
                    qty = str(e.get("origQty") or "")
                    exit_reason = str(x.get("type") or "").upper()

                    e_ms = int(e.get("time") or 0)
                    x_ms = int(x.get("time") or 0)
                    ts_entry = datetime.fromtimestamp(e_ms / 1000.0, tz=timezone.utc).isoformat() if e_ms else ""
                    ts_exit = datetime.fromtimestamp(x_ms / 1000.0, tz=timezone.utc).isoformat() if x_ms else ""

                    duration_sec = str((x_ms - e_ms) / 1000.0) if (e_ms and x_ms and x_ms >= e_ms) else "0.0"
                    is_unwind = "unwound=True" in str(e.get("clientOrderId") or "") or "unwound=True" in str(x.get("clientOrderId") or "")

                    order_ref = str(e.get("clientOrderId") or "")
                    order_id = str(e.get("orderId") or "")
                    meta = intent_meta.get(order_ref) or intent_meta.get(order_id) or {}

                    sl_val = meta.get("initial_stop_loss", "")
                    tp_val = meta.get("initial_take_profit", "")
                    conf_val = meta.get("confidence", "")
                    reg_val = meta.get("regime", "")
                    strat_val = meta.get("strategy") or "trend_following"

                    risk_usdt = ""
                    r_multiple = ""
                    sl_dist_pct = ""
                    tp_dist_pct = ""

                    try:
                        ep_num = float(entry_price)
                        sl_num = float(sl_val) if sl_val else 0.0
                        tp_num = float(tp_val) if tp_val else 0.0
                        pnl_num = float(pnl) if pnl else 0.0
                        qty_num = float(qty) if qty else 0.0

                        if ep_num > 0 and sl_num > 0 and qty_num > 0:
                            dist = abs(ep_num - sl_num)
                            risk_tot = dist * qty_num
                            risk_usdt = f"{risk_tot:.4f}"
                            sl_dist_pct = f"{(dist / ep_num * 100.0):.2f}"
                            if risk_tot > 0:
                                r_mult = pnl_num / risk_tot
                                r_multiple = f"{r_mult:.2f}"

                        if ep_num > 0 and tp_num > 0:
                            tp_dist = abs(tp_num - ep_num)
                            tp_dist_pct = f"{(tp_dist / ep_num * 100.0):.2f}"
                    except Exception:
                        pass

                    row = {
                        "trade_id": pos_id,
                        "symbol": clean_sym,
                        "strategy": strat_val,
                        "side": side,
                        "entry_timestamp": ts_entry,
                        "exit_timestamp": ts_exit,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "quantity": qty,
                        "pnl_usdt": pnl,
                        "fees_usdt": fee,
                        "exit_reason": exit_reason,
                        "actual_fill_price": entry_price,
                        "initial_stop_loss": sl_val,
                        "initial_take_profit": tp_val,
                        "risk_usdt": risk_usdt,
                        "r_multiple": r_multiple,
                        "confidence": conf_val,
                        "regime": reg_val,
                        "timeframe": "1m",
                        "signal_direction": side,
                        "duration_seconds": duration_sec,
                        "sl_distance_pct": sl_dist_pct,
                        "tp_distance_pct": tp_dist_pct,
                        "order_id": order_id,
                        "order_ref": order_ref,
                        "client_order_id": order_ref,
                        "exchange": "bingx",
                        "execution_latency_ms": "",
                        "is_execution_unwind": "True" if is_unwind else "False",
                        "status": "FILLED",
                    }
                    completed_trades.append(row)
        except Exception as e:
            logger.error(f"TRADE_JOURNAL: Failed to connect to exchange history: {e}")
        return completed_trades

    def backfill_historical_trades(self, purge_incomplete: bool = True) -> int:
        """Purge invalid incomplete rows and backfill verified exchange completed trades."""
        if not self.enabled:
            logger.info("TRADE_JOURNAL: backfill skipped because TradeFeatureCollector is disabled.")
            return 0

        logger.info("TRADE_JOURNAL: Starting authoritative completed trade reconstruction...")

        if purge_incomplete:
            self._purge_and_recreate_csvs()

        completed_rows = self.reconstruct_exchange_completed_trades()
        reconstructed_count = 0
        skipped_count = 0

        with self._lock:
            for row in completed_rows:
                tid = row["trade_id"]
                if tid in self._recorded_ids:
                    skipped_count += 1
                    continue

                self._append_row(row)
                self._recorded_ids.add(tid)
                reconstructed_count += 1
                logger.info(f"TRADE_JOURNAL: recorded completed trade {row['symbol']} / {tid}")

        logger.info(
            f"TRADE_JOURNAL: Reconstruction complete. "
            f"Verified Completed Trades: {reconstructed_count}, Skipped/Duplicates: {skipped_count}"
        )
        return reconstructed_count

    def _purge_and_recreate_csvs(self) -> None:
        """Purge old incomplete order-level CSVs and recreate headers."""
        paths = list(dict.fromkeys([p for p in (self.csv_path, self.alt_csv_path) if p]))
        for p in paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
                os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
                with open(p, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(CSV_HEADER)
                logger.info(f"TRADE_JOURNAL: Recreated clean CSV header at {p}")
            except Exception as e:
                logger.error(f"TRADE_JOURNAL: Error recreating CSV {p}: {e}")
        self._recorded_ids.clear()

    def _append_row(self, row: Dict[str, Any]) -> None:
        """Safely append a single dictionary row to trade_journal.csv."""
        paths = list(dict.fromkeys([p for p in (self.csv_path, self.alt_csv_path) if p]))
        for p in paths:
            try:
                with open(p, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
                    writer.writerow(row)
                    f.flush()
            except Exception as e:
                logger.error(f"TRADE_JOURNAL: Failed to append row {row.get('trade_id')} to {p}: {e}")

    # -- Background Lifecycle ----------------------------------------------------

    def start(self) -> None:
        """Start the background collector thread."""
        if not self.enabled:
            logger.info("TRADE_JOURNAL: TradeFeatureCollector start skipped because feature is disabled.")
            return
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                logger.info("TRADE_JOURNAL: Collector thread already running.")
                return
            self._stop_event.clear()
            self.backfill_historical_trades(purge_incomplete=False)
            self._thread = threading.Thread(target=self._run_loop, name="TradeJournalCollectorThread", daemon=True)
            self._thread.start()
            logger.info("TRADE_JOURNAL: Background collector thread started successfully.")

    def stop(self) -> None:
        """Stop the background collector thread cleanly."""
        logger.info("TRADE_JOURNAL: Stopping background collector thread...")
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("TRADE_JOURNAL: Collector stopped cleanly.")

    def _run_loop(self) -> None:
        """Periodic background loop to poll durable records for new completed trades."""
        while not self._stop_event.is_set():
            try:
                self.backfill_historical_trades(purge_incomplete=False)
            except Exception as e:
                logger.error(f"TRADE_JOURNAL: Error in background collection loop: {e}")
            self._stop_event.wait(self.poll_interval_seconds)


# Module-level singleton instance
trade_feature_collector = TradeFeatureCollector()
