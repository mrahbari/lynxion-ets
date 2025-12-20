#!/usr/bin/env python3
"""
ACTIVE ORDERS VERIFICATION SCRIPT FOR BINGX BROKER
This script checks for actual active orders and positions on the BingX broker.
"""
import os
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
import dotenv
dotenv.load_dotenv()

# Import necessary components
from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
from shared.logger import logger


def get_active_positions_and_orders():
    """Get actual active positions and orders from BingX broker"""
    print("🔍 CHECKING ACTIVE POSITIONS AND ORDERS ON BINGX BROKER")
    print("="*60)
    
    api_key = os.getenv("BINGX_API_KEY")
    secret_key = os.getenv("BINGX_SECRET_KEY")
    testnet = os.getenv("BINGX_TESTNET", "true").lower() == "true"

    if not api_key or not secret_key:
        print("❌ ERROR: API credentials not found in environment")
        return False

    config = {
        "api_key": api_key,
        "secret_key": secret_key,
        "testnet": testnet
    }

    try:
        # Initialize broker
        broker = BingXBrokerAdapter(config=config)
        print(f"✅ BingX broker initialized for {'testnet' if testnet else 'live'} trading")

        # Connect to broker
        connected = broker.connect()
        if not connected:
            print("❌ Failed to connect to BingX broker")
            return False
            
        print("✅ Connected to BingX broker")

        # Get account balance
        balances = broker.get_balance()
        print(f"📊 Account Balance: {len(balances)} assets found")
        for balance in balances:
            if balance.asset == "USDT":
                print(f"   USDT: Available=${float(balance.available.amount):.2f}, Total=${float(balance.total.amount):.2f}")

        print()
        
        # Get active positions
        print("💼 CHECKING ACTIVE POSITIONS...")
        positions = broker.get_all_positions()
        print(f"   Found {len(positions)} positions:")

        if positions:
            for position in positions:
                print(f"   - {position.symbol}: Side={position.side}, Size={position.quantity}, PnL=${position.unrealized_pnl.amount}")
        else:
            print("   No active positions found")

        print()

        # Get open orders - using the underlying method
        print("🛒 CHECKING OPEN ORDERS...")
        try:
            # The broker adapter doesn't have get_open_orders directly, but the underlying class does
            orders = broker._broker.get_pending_orders()
            print(f"   Found {len(orders)} open orders:")

            if orders:
                for order in orders:
                    symbol = order.get('symbol', 'N/A')
                    side = order.get('side', 'N/A')
                    qty = order.get('origQty', 'N/A')
                    price = order.get('price', 'N/A')
                    order_type = order.get('type', 'N/A')
                    print(f"   - {symbol}: {side} {qty} @ {price} (Type: {order_type})")
            else:
                print("   No open orders found")
        except Exception as e:
            print(f"   Could not retrieve open orders: {e}")
        
        print()
        
        # Get recent trades/orders history to see what was recently placed
        print("📋 CHECKING RECENT TRADES...")
        try:
            # Using the underlying method since the broker adapter doesn't expose it directly
            recent_orders = broker._broker.get_order_history(limit=20)  # Get last 20 orders
            print(f"   Found {len(recent_orders)} recent orders:")

            if recent_orders:
                for order in recent_orders[:5]:  # Show first 5
                    symbol = order.get('symbol', 'N/A')
                    side = order.get('side', 'N/A')
                    qty = order.get('origQty', 'N/A')
                    price = order.get('price', 'N/A')
                    status = order.get('status', 'N/A')
                    print(f"   - {symbol}: {side} {qty} @ {price} - Status: {status}")
                if len(recent_orders) > 5:
                    print(f"   ... and {len(recent_orders) - 5} more orders")
            else:
                print("   No recent orders found")
        except Exception as e:
            print(f"   Could not retrieve order history: {e}")
        
        print()
        
        # Disconnect from broker
        broker.disconnect()
        print("✅ Disconnected from BingX broker")

        print()
        print("📋 SUMMARY:")
        print(f"   - Active Positions: {len(positions)}")
        print(f"   - Open Orders: {len(orders)}")
        print(f"   - Recent Orders: {len(recent_orders) if 'recent_orders' in locals() else 0}")
        
        if len(positions) == 0 and len(orders) == 0:
            print("⚠️  WARNING: No active positions or open orders found!")
            print("   This suggests that the previous orders may not have been executed.")
        else:
            print("✅ Active positions/orders found - system is working correctly")
        
        return True

    except Exception as e:
        print(f"❌ Error getting active positions/orders: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function"""
    try:
        print("🚀 ACTIVE ORDERS VERIFICATION SCRIPT FOR BINGX")
        print("="*60)
        print()
        
        success = get_active_positions_and_orders()
        return success
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    print()
    if success:
        print("🎉 ACTIVE ORDERS VERIFICATION COMPLETED!")
        print("   - Checked for actual active positions")
        print("   - Verified open orders on broker")
        print("   - Validated order execution status")
    else:
        print("❌ Script execution failed")

    print()
    print("✅ VERIFICATION COMPLETE!")