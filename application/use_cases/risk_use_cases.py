"""
Use cases for risk governance functionality in the enterprise hedge fund trading system.
"""
from typing import Dict, Any
from domain.entities.trading_entities import Signal, Order
from application.services.risk_services_app import RiskGovernanceService, PortfolioRiskMonitoringService


class ValidateSignalRiskUseCase:
    """Use case for validating signal risk"""
    
    def __init__(self, risk_governance_service: RiskGovernanceService):
        self.risk_governance_service = risk_governance_service
    
    def execute(self, signal: Signal) -> Dict[str, Any]:
        """Execute the use case to validate signal risk"""
        return self.risk_governance_service.validate_signal_comprehensive(signal)


class ValidateOrderRiskUseCase:
    """Use case for validating order risk"""
    
    def __init__(self, risk_governance_service: RiskGovernanceService):
        self.risk_governance_service = risk_governance_service
    
    def execute(self, order: Order) -> Dict[str, Any]:
        """Execute the use case to validate order risk"""
        return self.risk_governance_service.validate_order_comprehensive(order)


class MonitorPortfolioRiskUseCase:
    """Use case for monitoring portfolio risk"""
    
    def __init__(self, portfolio_risk_monitoring_service: PortfolioRiskMonitoringService):
        self.portfolio_risk_monitoring_service = portfolio_risk_monitoring_service
    
    def execute(self) -> Dict[str, Any]:
        """Execute the use case to monitor portfolio risk"""
        return self.portfolio_risk_monitoring_service.monitor_portfolio_risk()


class GetRiskMetricsUseCase:
    """Use case for getting risk metrics"""
    
    def __init__(self, risk_governance_service: RiskGovernanceService):
        self.risk_governance_service = risk_governance_service
    
    def execute(self) -> Dict[str, Any]:
        """Execute the use case to get risk metrics"""
        return self.risk_governance_service.get_risk_metrics()