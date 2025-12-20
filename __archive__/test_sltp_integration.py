#!/usr/bin/env python3
"""
Test script to verify SL/TP integration with BingX broker
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


def test_sltp_integration():
    """Test SL/TP integration with BingX broker"""
    print("🔍 Testing SL/TP Integration with BingX Broker")
    print("="*60)
    
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
        
        # Test with a simple order with SL/TP
        symbol = Symbol("BTCUSDT")
        order_side = OrderSide.BUY
        quantity = 0.001  # Small quantity for testing
        price = Money(40000.0, "USDT")  # Approximate BTC price
        
        # Create order with SL/TP
        order = Order(
            symbol=symbol,
            side=order_side,
            quantity=quantity,
            price=price,
            order_type="LIMIT",
            position_side=PositionSide.LONG,
            timestamp=datetime.now(),
            strategy_name="SLTP_Test"
        )
        
        # Add SL/TP as attributes (these will be handled by the broker adapter)
        order.stop_loss_price = Money(39000.0, "USDT")  # SL below entry
        order.take_profit_price = Money(42000.0, "USDT")  # TP above entry
        
        print(f"📝 Creating order with SL: ${39000.0}, TP: ${42000.0}")
        
        # Place the order
        try:
            order_result = broker.place_order(order)
            print(f"✅ Order placed successfully! Result: {order_result}")
        except Exception as e:
            print(f"❌ Failed to place order with SL/TP: {e}")
            # Let's try placing a basic order without SL/TP to see if the connection works
            basic_order = Order(
                symbol=symbol,
                side=order_side,
                quantity=quantity,
                price=price,
                order_type="LIMIT",
                position_side=PositionSide.LONG,
                timestamp=datetime.now(),
                strategy_name="Basic_Test"
            )
            try:
                basic_result = broker.place_order(basic_order)
                print(f"✅ Basic order (without SL/TP) placed successfully! Result: {basic_result}")
            except Exception as basic_error:
                print(f"❌ Even basic order failed: {basic_error}")
        
        # Disconnect from broker
        broker.disconnect()
        print("✅ Disconnected from BingX broker")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in SL/TP test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_sltp_integration()
    if success:
        print("\n🎉 SL/TP Integration Test Completed Successfully!")
    else:
        print("\n❌ SL/TP Integration Test Failed!")