"""
Use cases for broker functionality in the enterprise hedge fund trading system.
"""
from typing import List, Dict, Any
from domain.entities import Order
from domain.value_objects import Symbol
from application.services.broker_services import BrokerManagementService


class PlaceOrderUseCase:
    """Use case for placing an order via the best broker"""
    
    def __init__(self, broker_management_service: BrokerManagementService):
        self.broker_management_service = broker_management_service
    
    def execute(self, order: Order) -> str:
        """Execute the use case to place an order"""
        return self.broker_management_service.place_order_via_best_broker(order)


class GetMarketDataUseCase:
    """Use case for getting market data across brokers"""
    
    def __init__(self, broker_management_service: BrokerManagementService):
        self.broker_management_service = broker_management_service
    
    def execute(self, symbol: Symbol) -> Dict[str, Any]:
        """Execute the use case to get market data"""
        return self.broker_management_service.get_market_data_across_brokers(symbol)


class GetAccountBalancesUseCase:
    """Use case for getting account balances"""
    
    def __init__(self, broker_management_service: BrokerManagementService):
        self.broker_management_service = broker_management_service
    
    def execute(self, broker_name: str = None) -> List:
        """Execute the use case to get account balances"""
        return self.broker_management_service.get_account_balances(broker_name)


class ExecuteArbitrageTradeUseCase:
    """Use case for executing arbitrage trades"""
    
    def __init__(self, multi_broker_execution_service):
        self.multi_broker_execution_service = multi_broker_execution_service
    
    def execute(self, buy_order: Order, sell_order: Order) -> Dict[str, str]:
        """Execute the use case to execute an arbitrage trade"""
        return self.multi_broker_execution_service.execute_arbitrage_trade(buy_order, sell_order)


class MonitorBrokerHealthUseCase:
    """Use case for monitoring broker health"""
    
    def __init__(self, broker_monitoring_service):
        self.broker_monitoring_service = broker_monitoring_service
    
    def execute(self) -> Dict[str, Dict[str, Any]]:
        """Execute the use case to monitor broker health"""
        return self.broker_monitoring_service.monitor_broker_health()