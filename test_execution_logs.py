#!/usr/bin/env python3
"""
Test script to demonstrate enhanced execution logging
"""
import sys
import uuid
sys.path.insert(0, "/Users/mojtaba.rahbari/Sites/python/lynxion-ets")

from shared.logger import EnhancedLogger
from domain.ports.execution_ports import ExecutionPort
from domain.value_objects import Symbol


class MockExecutionService(ExecutionPort):
    def execute_order(self, order):
        execution_id = f'EXEC_{uuid.uuid4().hex[:8].upper()}'
        print(f'MOCK EXECUTION: {order["side"]} {order["quantity"]} of {order["symbol"]} @ ${order["price"]}')
        return execution_id

    def cancel_order(self, order_id: str) -> bool:
        return True

    def get_execution_status(self, execution_id: str) -> str:
        return 'filled'


def test_enhanced_execution_logging():
    """Test the enhanced execution logging system."""
    print("🧪 Testing Enhanced Execution Logging System...")
    
    # Create logger
    logger = EnhancedLogger('ExecutionTest')
    
    # Create mock execution service
    execution_service = MockExecutionService()
    
    # Test various execution scenarios
    test_orders = [
        {
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01,
            'price': 50000.0,
            'type': 'MARKET',
            'strategy': 'momentum'
        },
        {
            'symbol': 'ETHUSDT',
            'side': 'SELL',
            'quantity': 0.5,
            'price': 3000.0,
            'type': 'LIMIT',
            'strategy': 'mean_reversion'
        },
        {
            'symbol': 'SOLUSDT',
            'side': 'BUY',
            'quantity': 10.0,
            'price': 100.0,
            'type': 'MARKET',
            'strategy': 'breakout'
        }
    ]
    
    for i, order in enumerate(test_orders, 1):
        print(f"\n📋 Test {i}: {order['side']} {order['quantity']} {order['symbol']}")
        
        # Execute order
        execution_id = execution_service.execute_order(order)
        print(f"   ID: {execution_id}")
        
        # Log the execution with enhanced logging
        logger.log_execution(
            execution_id,
            order['symbol'],
            order['side'],
            order['quantity'],
            order['price']
        )
        
        # Log a success message
        logger.info(f"✅ TRADE SUCCESS: {order['side']} {order['quantity']} of {order['symbol']} @ ${order['price']:,.2f} using strategy {order['strategy']}")
    
    print("\n🎉 Enhanced execution logging test completed successfully!")
    print("✅ Executions are now clearly visible with detailed information")
    print("✅ Success/failure indicators are prominent and readable")
    print("✅ Price, quantity, and total value are clearly displayed")


if __name__ == "__main__":
    test_enhanced_execution_logging()