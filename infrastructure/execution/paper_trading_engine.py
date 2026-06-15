"""Paper Trading Engine — deterministic fill simulation, position lifecycle, and PnL.

Phase-11 (production-infrastructure completion). This is the missing fill layer for
PAPER-routed orders: it consumes an order the LIVE_EXECUTION_GUARD has authorized as
PAPER, simulates a fill (price + slippage + fee from the system's configured
parameters), maintains the net position per symbol, books realized PnL on reductions,
marks unrealized PnL, and tracks portfolio equity. It NEVER contacts a broker and
places no real capital at risk.

It is intentionally free of strategy/signal logic — it only accounts for fills.

Position model (netting, signed):
  * a symbol holds one net position: a side (LONG/SHORT/FLAT), an absolute quantity,
    and a volume-weighted average entry price;
  * a same-direction fill increases the position and re-weights the average entry;
  * an opposite fill reduces/closes it (booking realized PnL on the closed portion)
    and, if it exceeds the open quantity, flips to the opposite side at the fill price.

Accounting:
  * realized_pnl accrues on closed portions; total_fees accrues on every fill;
  * cash  = initial_capital + realized_pnl - total_fees   (settled)
  * equity = cash + unrealized_pnl(marked at last fill price per symbol)

State is persisted (atomically) to JSON so it survives restarts (see save/load).
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from domain.entities import Fill, Order, OrderSide, Position, PositionSide
from domain.value_objects import Money, Symbol


def _d(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


@dataclass
class PaperPosition:
    """Net position for one symbol (quantity is always >= 0; direction is `side`)."""
    symbol: str
    side: PositionSide
    quantity: Decimal
    avg_entry: Decimal
    currency: str
    last_mark: Decimal
    strategy_name: Optional[str] = None

    def unrealized_pnl(self) -> Decimal:
        if self.side == PositionSide.LONG:
            return (self.last_mark - self.avg_entry) * self.quantity
        if self.side == PositionSide.SHORT:
            return (self.avg_entry - self.last_mark) * self.quantity
        return Decimal("0")

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol, "side": self.side.value,
            "quantity": str(self.quantity), "avg_entry": str(self.avg_entry),
            "currency": self.currency, "last_mark": str(self.last_mark),
            "strategy_name": self.strategy_name,
        }

    @staticmethod
    def from_dict(d: Dict) -> "PaperPosition":
        return PaperPosition(
            symbol=d["symbol"], side=PositionSide(d["side"]),
            quantity=_d(d["quantity"]), avg_entry=_d(d["avg_entry"]),
            currency=d["currency"], last_mark=_d(d["last_mark"]),
            strategy_name=d.get("strategy_name"),
        )


class PaperTradingEngine:
    """Simulates fills and maintains positions / PnL / equity for PAPER orders."""

    def __init__(self, initial_capital: float = 10000.0, fee_rate: float = 0.001,
                 slippage_factor: float = 0.0005, currency: str = "USDT",
                 persist_path: Optional[str] = None):
        self._lock = threading.RLock()
        self.initial_capital = _d(initial_capital)
        self.fee_rate = _d(fee_rate)
        self.slippage_factor = _d(slippage_factor)
        self.currency = currency
        self.realized_pnl = Decimal("0")
        self.total_fees = Decimal("0")
        self.positions: Dict[str, PaperPosition] = {}
        self.fills: List[Dict] = []
        self.closed_trades: List[Dict] = []   # one record per realized (closed) portion
        self.equity_curve: List[Dict] = []
        self._fill_seq = 0
        self._persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load()

    # -- public API ---------------------------------------------------------------

    def simulate_fill(self, order: Order, ts: Optional[str] = None) -> Dict:
        """Simulate a fill for a PAPER-authorized order; update state; return a summary.

        Returns a JSON-able dict suitable for the Execution Truth Ledger result record.
        """
        with self._lock:
            side = order.side if isinstance(order.side, OrderSide) else OrderSide(str(order.side))
            symbol = order.symbol.value if hasattr(order.symbol, "value") else str(order.symbol)
            currency = getattr(getattr(order, "price", None), "currency", None) or self.currency
            ref_price = _d(order.price.amount) if getattr(order, "price", None) is not None else Decimal("0")
            qty = _d(order.quantity)

            if ref_price <= 0 or qty <= 0:
                return {"filled": False, "reason": "non-positive price/quantity", "order_id": None}

            # Slippage models an adverse fill: buys fill higher, sells fill lower.
            slip = ref_price * self.slippage_factor
            fill_price = ref_price + slip if side == OrderSide.BUY else ref_price - slip
            notional = fill_price * qty
            fee = notional * self.fee_rate
            self.total_fees += fee

            realized_delta = self._apply_fill(symbol, side, qty, fill_price, currency,
                                              getattr(order, "strategy_name", None), ts)
            self.realized_pnl += realized_delta

            self._fill_seq += 1
            order_id = f"PAPER-FILL-{self._fill_seq:08d}"
            stamp = ts or datetime.now(timezone.utc).isoformat()

            fill = Fill(symbol=Symbol(symbol), side=side, quantity=qty,
                        price=Money(fill_price, currency), timestamp=datetime.now(timezone.utc),
                        order_id=order_id, fee=Money(fee, currency), fee_currency=currency,
                        trade_id=order_id)
            pos = self.positions.get(symbol)
            equity = self._equity()
            record = {
                "filled": True, "order_id": order_id, "ts": stamp, "symbol": symbol,
                "side": side.value, "quantity": str(qty),
                "reference_price": str(ref_price), "fill_price": str(fill_price),
                "slippage": str(slip), "slippage_cost": str(slip * qty),
                "fee": str(fee), "notional": str(notional),
                "realized_pnl_delta": str(realized_delta),
                "cumulative_realized_pnl": str(self.realized_pnl),
                "position_after": pos.to_dict() if pos else {"side": "FLAT", "quantity": "0"},
                "unrealized_pnl": str(self._unrealized()),
                "cash": str(self._cash()), "equity": str(equity),
            }
            self.fills.append(record)
            self.equity_curve.append({"ts": stamp, "equity": str(equity),
                                      "realized_pnl": str(self.realized_pnl),
                                      "unrealized_pnl": str(self._unrealized())})
            self._save()
            return record

    def replay_fill(self, symbol: str, side, qty, fill_price, fee=0) -> Decimal:
        """Apply an already-priced fill (no slippage re-derivation) — for ledger replay/reconciliation.

        Uses the recorded fill price/fee directly so a rebuilt engine reproduces the exact
        position state implied by the immutable Execution Truth Ledger.
        """
        with self._lock:
            side = side if isinstance(side, OrderSide) else OrderSide(str(side))
            qty = _d(qty)
            fill_price = _d(fill_price)
            self.total_fees += _d(fee)
            realized = self._apply_fill(symbol, side, qty, fill_price, self.currency, None, None)
            self.realized_pnl += realized
            return realized

    def mark_prices(self, prices: Dict[str, float]) -> None:
        """Update last-mark for open positions (e.g. from a data feed) for unrealized PnL."""
        with self._lock:
            for sym, px in prices.items():
                if sym in self.positions:
                    self.positions[sym].last_mark = _d(px)

    def snapshot(self) -> Dict:
        with self._lock:
            return {
                "initial_capital": str(self.initial_capital),
                "cash": str(self._cash()),
                "realized_pnl": str(self.realized_pnl),
                "unrealized_pnl": str(self._unrealized()),
                "total_fees": str(self.total_fees),
                "equity": str(self._equity()),
                "open_positions": {s: p.to_dict() for s, p in self.positions.items() if p.side != PositionSide.FLAT},
                "num_fills": len(self.fills),
                "num_closed_trades": len(self.closed_trades),
            }

    # -- position lifecycle -------------------------------------------------------

    def _apply_fill(self, symbol: str, side: OrderSide, qty: Decimal, price: Decimal,
                    currency: str, strategy: Optional[str], ts: Optional[str]) -> Decimal:
        """Net the fill into the position; return realized PnL booked by this fill."""
        signed = qty if side == OrderSide.BUY else -qty
        pos = self.positions.get(symbol)
        cur = Decimal("0")
        if pos and pos.side != PositionSide.FLAT:
            cur = pos.quantity if pos.side == PositionSide.LONG else -pos.quantity
        new_net = cur + signed
        realized = Decimal("0")
        is_opposing = cur != 0 and (cur > 0) != (signed > 0)

        # A fill opposing the open position closes part/all of it and books realized PnL.
        if is_opposing:
            closing = min(qty, abs(cur))
            if pos.side == PositionSide.LONG:
                realized = (price - pos.avg_entry) * closing
            else:
                realized = (pos.avg_entry - price) * closing
            self.closed_trades.append({
                "ts": ts or datetime.now(timezone.utc).isoformat(), "symbol": symbol,
                "closed_side": pos.side.value, "quantity": str(closing),
                "entry_price": str(pos.avg_entry), "exit_price": str(price),
                "realized_pnl": str(realized), "strategy_name": pos.strategy_name,
            })

        if new_net == 0:
            # Fully closed -> flat.
            self.positions[symbol] = PaperPosition(symbol, PositionSide.FLAT, Decimal("0"),
                                                   Decimal("0"), currency, price, strategy)
        elif not is_opposing:
            # Fresh open or same-direction increase -> volume-weighted average entry.
            new_side = PositionSide.LONG if new_net > 0 else PositionSide.SHORT
            if pos and pos.side == new_side and pos.quantity > 0:
                total_qty = pos.quantity + qty
                new_avg = (pos.avg_entry * pos.quantity + price * qty) / total_qty
            else:
                new_avg = price
            self.positions[symbol] = PaperPosition(symbol, new_side, abs(new_net), new_avg,
                                                   currency, price, strategy)
        elif (cur > 0) == (new_net > 0):
            # Opposing fill that only REDUCED the position (no flip) -> average entry unchanged.
            self.positions[symbol] = PaperPosition(symbol, pos.side, abs(new_net), pos.avg_entry,
                                                   currency, price, pos.strategy_name)
        else:
            # Opposing fill that FLIPPED the position -> open opposite at the fill price.
            new_side = PositionSide.LONG if new_net > 0 else PositionSide.SHORT
            self.positions[symbol] = PaperPosition(symbol, new_side, abs(new_net), price,
                                                   currency, price, strategy)
        return realized

    # -- accounting ---------------------------------------------------------------

    def _unrealized(self) -> Decimal:
        return sum((p.unrealized_pnl() for p in self.positions.values()), Decimal("0"))

    def _cash(self) -> Decimal:
        return self.initial_capital + self.realized_pnl - self.total_fees

    def _equity(self) -> Decimal:
        return self._cash() + self._unrealized()

    # -- persistence (atomic) -----------------------------------------------------

    def _state(self) -> Dict:
        return {
            "initial_capital": str(self.initial_capital), "fee_rate": str(self.fee_rate),
            "slippage_factor": str(self.slippage_factor), "currency": self.currency,
            "realized_pnl": str(self.realized_pnl), "total_fees": str(self.total_fees),
            "fill_seq": self._fill_seq,
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "closed_trades": self.closed_trades, "equity_curve": self.equity_curve,
        }

    def _save(self) -> None:
        if not self._persist_path:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path) or ".", exist_ok=True)
            tmp = self._persist_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._state(), f, default=str)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, ValueError):
                    pass
            os.replace(tmp, self._persist_path)
        except Exception:
            pass  # persistence must never break the paper trading path

    def _load(self) -> None:
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                s = json.load(f)
            self.initial_capital = _d(s.get("initial_capital", self.initial_capital))
            self.fee_rate = _d(s.get("fee_rate", self.fee_rate))
            self.slippage_factor = _d(s.get("slippage_factor", self.slippage_factor))
            self.currency = s.get("currency", self.currency)
            self.realized_pnl = _d(s.get("realized_pnl", 0))
            self.total_fees = _d(s.get("total_fees", 0))
            self._fill_seq = int(s.get("fill_seq", 0))
            self.positions = {k: PaperPosition.from_dict(v) for k, v in s.get("positions", {}).items()}
            self.closed_trades = s.get("closed_trades", [])
            self.equity_curve = s.get("equity_curve", [])
        except Exception:
            pass

    def load(self) -> None:
        """Public: reload persisted state (used by restart-recovery validation)."""
        with self._lock:
            if self._persist_path and os.path.exists(self._persist_path):
                self._load()


__all__ = ["PaperTradingEngine", "PaperPosition"]
