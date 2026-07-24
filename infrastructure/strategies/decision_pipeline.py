"""
Unified, Strategy-Agnostic Decision Pipeline.
Handles execution flow: CandidateSetup -> ExecutionConfirmationEngine -> ExecutionOptimizer -> ExecutionIntent.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from domain.entities import FusedSignal, ExecutionIntent
from domain.value_objects import Money, Percentage
from domain.enums.order_side import OrderSide
from domain.entities.research import CandidateSetup
from infrastructure.execution.execution_confirmation_engine import ExecutionConfirmationEngine
from infrastructure.execution.execution_optimizer import ExecutionOptimizer


class DecisionPipeline:
    """
    Unified, strategy-agnostic decision pipeline.
    Responsible for executing only the confirmation and optimization stages.
    """

    def __init__(self,
                 confirmation_engine: Optional[ExecutionConfirmationEngine] = None,
                 optimizer: Optional[ExecutionOptimizer] = None):
        self.confirmation_engine = confirmation_engine or ExecutionConfirmationEngine()
        self.optimizer = optimizer or ExecutionOptimizer()

    def process_execution_intent(self,
                                 setup: CandidateSetup,
                                 fused_signal: FusedSignal,
                                 latest_bar: Dict[str, Any],
                                 current_price: float,
                                 max_position_size: float,
                                 strategy_name: str) -> Optional[ExecutionIntent]:
        """
        Executes confirmation and optimization stages on a CandidateSetup.
        """
        # 1. Execution Confirmation using OBI and CVD
        obi_ratio = latest_bar.get("obi_ratio", 0.15 if setup.direction == "BUY" else -0.15)
        cvd = latest_bar.get("cvd", 1.0 if setup.direction == "BUY" else -1.0)

        confirmed = self.confirmation_engine.confirm_execution(setup, obi_ratio, cvd)
        if not confirmed:
            return None

        # 2. Execution Optimization
        best_bid = latest_bar.get("best_bid", current_price - 0.0001 * current_price)
        best_ask = latest_bar.get("best_ask", current_price + 0.0001 * current_price)

        optimized_order = self.optimizer.optimize_order(
            symbol=fused_signal.symbol,
            direction=setup.direction,
            current_price=current_price,
            best_bid=best_bid,
            best_ask=best_ask,
            quantity=max_position_size
        )

        if not optimized_order:
            return None

        # 3. Create ExecutionIntent
        side = OrderSide.BUY if setup.direction == "BUY" else OrderSide.SELL
        stop_loss_val = float(setup.stop_loss_level)
        take_profit_val = float(setup.take_profit_level)

        intent = ExecutionIntent(
            symbol=fused_signal.symbol,
            strategy_name=strategy_name,
            side=side,
            intent_confidence=Percentage(Decimal("0.8")),
            risk_parameters={
                "stop_loss": stop_loss_val,
                "take_profit": take_profit_val,
                "limit_price": float(optimized_order["price"]),
                "time_in_force": optimized_order["time_in_force"]
            },
            timestamp=getattr(fused_signal, 'timestamp', None) or datetime.now(),
            fused_signal=fused_signal,
            metadata={
                "setup_type": setup.setup_type,
                "direction": setup.direction,
                "trigger_price": float(setup.trigger_price),
                "limit_price": float(optimized_order["price"]),
                "time_in_force": optimized_order["time_in_force"],
                "watcher_name": (fused_signal.metadata.get('watcher_name') or fused_signal.metadata.get('primary_watcher') or fused_signal.metadata.get('source_watcher')) if fused_signal and fused_signal.metadata else 'N/A',
                "primary_watcher": (fused_signal.metadata.get('primary_watcher') or fused_signal.metadata.get('watcher_name')) if fused_signal and fused_signal.metadata else 'N/A'
            }
        )

        # Attach Money representations
        intent.stop_loss_price = Money(amount=Decimal(str(stop_loss_val)), currency="USDT")
        intent.take_profit_price = Money(amount=Decimal(str(take_profit_val)), currency="USDT")

        return intent
