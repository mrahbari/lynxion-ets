"""Phase-15 Controlled VST Execution Harness.

Triggers a single controlled VST trade for XLMUSDT using the production execution service,
to verify that the sizing boundary enforcer caps order quantity below the configured maximum
position exposure limit before submitting to the broker, and logs the transaction.
"""

import os
import sys
from decimal import Decimal

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bootstrap.lifecycle import lifespan
from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol

def main():
    print("🚀 Initializing container and resolving execution services...")
    with lifespan() as container:
        settings = container.settings
        
        # Ensure paper trading is disabled and testnet is enabled for BingX
        # so that it routes to the actual BingX VST exchange API!
        settings.broker.paper_trading = False
        settings.broker.testnet = True
        settings.broker.bingx_testnet = True
        settings.broker.bingx_order_placement_enabled = True
        
        # Wire risk enforcement into live_execution_guard (mimicking orchestrator)
        from shared.live_execution_guard import live_execution_guard
        from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
        from infrastructure.risk.risk_enforcement import RiskEnforcement
        
        risk_enforcement = RiskEnforcement(EnterpriseRiskManager())
        live_execution_guard.set_risk_enforcer(risk_enforcement.enforce)
        live_execution_guard.set_risk_state_provider(risk_enforcement.state)
        
        broker_registry = container.resolve("broker_registry")
        execution_service = broker_registry.get_execution_service(
            settings=settings,
            use_multi_broker=True,
            primary_broker='bingx'
        )
        
        max_exposure = getattr(risk_enforcement._rm, 'max_position_exposure', 50000.0)
        print(f"📈 Configured max position exposure: ${max_exposure:.2f}")
        
        # We want to place an order that exceeds the limit slightly (e.g. by $5)
        # XLMUSDT entry price: 0.1835
        entry_price = 0.1835
        excess_exposure = max_exposure + 5.00
        uncapped_qty = excess_exposure / entry_price
        
        print(f"📊 Sizing: Price = {entry_price}, Un-capped Exposure = ${excess_exposure:.2f}, Quantity = {uncapped_qty:.6f}")
        
        # Build the Order entity
        # Using wider stop loss and take profit to satisfy exchange distance rules
        order = Order(
            symbol=Symbol("XLMUSDT"),
            side=OrderSide.BUY,
            order_type="MARKET",
            quantity=Decimal(f"{uncapped_qty:.6f}"),
            price=Money(Decimal(str(entry_price)), "USDT"),
            strategy_name="VWAPReversal",
            stop_loss_price=Money(Decimal("0.1700"), "USDT"),
            take_profit_price=Money(Decimal("0.1950"), "USDT")
        )
        
        print(f"📥 Submitting XLMUSDT order of {order.quantity} units to execution service...")
        
        order_id = execution_service.execute_order(order)
        
        print("\n=== EXECUTION RESULT ===")
        print(f"Order ID: {order_id}")
        if order_id:
            print(f"Final approved quantity: {order.quantity}")
            print(f"Final approved notional: ${float(order.quantity) * entry_price:.4f}")
            print("✅ Order successfully routed and accepted on BingX VST!")
        else:
            print("❌ Order execution failed or was rejected.")

if __name__ == "__main__":
    main()
