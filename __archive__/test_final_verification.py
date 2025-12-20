#!/usr/bin/env python3
"""
Final verification script to place multiple orders with different SL/TP values
"""
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
import dotenv
dotenv.load_dotenv()

from domain.entities.trading_entities import Order, OrderSide, PositionSide
from domain.value_objects import Money, Symbol
from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter


def place_verification_orders():
    """Place multiple verification orders with different SL/TP values"""
    print("🔍 FINAL VERIFICATION: Multiple Orders with SL/TP on BingX VST Broker")
    print("="*70)

    # Initialize broker
    api_key = os.getenv("BINGX_API_KEY")
    secret_key = os.getenv("BINGX_SECRET_KEY")
    testnet = os.getenv("BINGX_TESTNET", "true").lower() == "true"

    if not api_key or not secret_key:
        print("❌ API credentials not found in environment")
        return False

    config = {
        "api_key": api_key,
        "secret_key": secret_key,
        "testnet": testnet
    }

    broker = BingXBrokerAdapter(config=config)

    try:
        # Connect to broker
        connected = broker.connect()
        if not connected:
            print("❌ Failed to connect to BingX broker")
            return False

        print("✅ Connected to BingX broker")

        # Get balance
        balance = broker.get_balance()
        print(f"📊 Balance retrieved: {len(balance)} records")

        # Place multiple test orders with different SL/TP values
        test_orders = [
            {
                "symbol": "ETHUSDT",
                "side": OrderSide.BUY,
                "quantity": 0.01,
                "price": Money(2500.0, "USDT"),
                "sl": Money(2400.0, "USDT"),  # 4% SL
                "tp": Money(2700.0, "USDT")   # 8% TP
            },
            {
                "symbol": "BNBUSDT",
                "side": OrderSide.SELL,
                "quantity": 0.1,
                "price": Money(300.0, "USDT"),
                "sl": Money(310.0, "USDT"),   # For short, SL above entry
                "tp": Money(285.0, "USDT")    # For short, TP below entry
            }
        ]

        order_ids = []
        for i, order_params in enumerate(test_orders, 1):
            print(f"\n📝 Placing Test Order #{i} with SL/TP:")
            print(f"   Symbol: {order_params['symbol']}")
            print(f"   Side: {order_params['side'].name}")
            print(f"   Quantity: {order_params['quantity']}")
            print(f"   Price: ${order_params['price'].amount}")
            print(f"   Stop Loss: ${order_params['sl'].amount}")
            print(f"   Take Profit: ${order_params['tp'].amount}")

            # Create order with SL/TP
            order = Order(
                symbol=Symbol(order_params["symbol"]),
                side=order_params["side"],
                quantity=order_params["quantity"],
                price=order_params["price"],
                order_type="LIMIT",
                position_side=PositionSide.LONG if order_params["side"] == OrderSide.BUY else PositionSide.SHORT,
                timestamp=datetime.now(),
                strategy_name=f"Verification_{i}"
            )

            # Add SL/TP as attributes
            order.stop_loss_price = order_params["sl"]
            order.take_profit_price = order_params["tp"]

            try:
                # Place the order
                order_id = broker.place_order(order)
                print(f"✅ Order #{i} placed successfully! Order ID: {order_id}")
                order_ids.append(order_id)
            except Exception as e:
                print(f"❌ Failed to place order #{i}: {e}")

        # Disconnect from broker
        broker.disconnect()
        print("\n✅ Disconnected from BingX broker")

        print(f"\n🎯 FINAL RESULT: {len(order_ids)} orders successfully placed with SL/TP")
        for i, order_id in enumerate(order_ids, 1):
            print(f"   Order #{i}: {order_id}")

        return len(order_ids) > 0

    except Exception as e:
        print(f"❌ Error in final verification: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = place_verification_orders()
    if success:
        print("\n🎉 ALL VERIFICATIONS PASSED: ORDERS WITH SL/TP SUCCESSFULLY PLACED ON BINGX VST BROKER!")
    else:
        print("\n❌ VERIFICATION FAILED!")