from typing import Dict, List, Optional
from shared.types import Position, Order
from shared.logger import logger
from datetime import datetime


class ExposureManager:
    """Manages and limits exposure across different dimensions"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Exposure limits
        self.max_asset_exposure = config.get('max_asset_exposure', 0.1)  # 10% max per asset
        self.max_sector_exposure = config.get('max_sector_exposure', 0.3)  # 30% max per sector
        self.max_currency_exposure = config.get('max_currency_exposure', 0.5)  # 50% max per currency
        self.max_strategy_exposure = config.get('max_strategy_exposure', 0.4)  # 40% max per strategy
        self.max_timeframe_exposure = config.get('max_timeframe_exposure', 0.4)  # 40% max per timeframe
        
        # Current exposures
        self.asset_exposures: Dict[str, float] = {}
        self.sector_exposures: Dict[str, float] = {}
        self.currency_exposures: Dict[str, float] = {}
        self.strategy_exposures: Dict[str, float] = {}
        self.timeframe_exposures: Dict[str, float] = {}
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        self.total_portfolio_value = config.get('initial_capital', 100000)
        self.order_exposure_map: Dict[str, float] = {}  # Map orders to their exposure value
        
        # Asset to sector mapping (simplified)
        self.asset_to_sector: Dict[str, str] = config.get('asset_to_sector', {})
        
    def update_portfolio_value(self, new_value: float):
        """Update the total portfolio value"""
        self.total_portfolio_value = new_value
    
    def register_position(self, position: Position):
        """Register a new position and update exposures"""
        # Remove old position if it exists
        if position.symbol in self.positions:
            self._remove_position_exposure(self.positions[position.symbol])
        
        if position.quantity > 0:
            self.positions[position.symbol] = position
            self._add_position_exposure(position)
        else:
            # Position closed or quantity is 0
            if position.symbol in self.positions:
                self._remove_position_exposure(position)
                del self.positions[position.symbol]
    
    def _add_position_exposure(self, position: Position):
        """Add exposure from a position"""
        value = position.quantity * position.entry_price
        
        # Asset exposure
        self.asset_exposures[position.symbol] = self.asset_exposures.get(position.symbol, 0) + value
        
        # Sector exposure
        sector = self.asset_to_sector.get(position.symbol, 'unknown')
        self.sector_exposures[sector] = self.sector_exposures.get(sector, 0) + value
        
        # Currency exposure (simplified - assume quote currency is part of symbol)
        currency = position.symbol.split('USDT')[1] if 'USDT' in position.symbol else position.symbol[-3:]
        self.currency_exposures[currency] = self.currency_exposures.get(currency, 0) + value
    
    def _remove_position_exposure(self, position: Position):
        """Remove exposure from a position"""
        value = position.quantity * position.entry_price
        
        # Asset exposure
        if position.symbol in self.asset_exposures:
            self.asset_exposures[position.symbol] = max(0, self.asset_exposures[position.symbol] - value)
            if self.asset_exposures[position.symbol] == 0:
                del self.asset_exposures[position.symbol]
        
        # Sector exposure
        sector = self.asset_to_sector.get(position.symbol, 'unknown')
        if sector in self.sector_exposures:
            self.sector_exposures[sector] = max(0, self.sector_exposures[sector] - value)
            if self.sector_exposures[sector] == 0:
                del self.sector_exposures[sector]
        
        # Currency exposure
        currency = position.symbol.split('USDT')[1] if 'USDT' in position.symbol else position.symbol[-3:]
        if currency in self.currency_exposures:
            self.currency_exposures[currency] = max(0, self.currency_exposures[currency] - value)
            if self.currency_exposures[currency] == 0:
                del self.currency_exposures[currency]
    
    def check_order_exposure(self, order: Order, current_price: float) -> Dict:
        """Check if an order would violate exposure limits"""
        result = {
            'approved': True,
            'reasons': [],
            'adjusted_size': order.quantity
        }
        
        # Calculate order value
        order_value = order.quantity * current_price
        current_total_exposure = sum(pos.quantity * pos.entry_price for pos in self.positions.values())
        new_total_exposure = current_total_exposure + order_value
        
        # Check asset exposure limit
        current_asset_value = self.asset_exposures.get(order.symbol, 0)
        new_asset_exposure = (current_asset_value + order_value) / self.total_portfolio_value
        if new_asset_exposure > self.max_asset_exposure:
            result['approved'] = False
            result['reasons'].append(f"Asset exposure would exceed limit: {new_asset_exposure:.3f} > {self.max_asset_exposure}")
            # Calculate adjusted size
            max_asset_value = self.max_asset_exposure * self.total_portfolio_value
            max_additional_value = max_asset_value - current_asset_value
            result['adjusted_size'] = min(order.quantity, max(0, max_additional_value / current_price))
        
        # Check sector exposure limit
        sector = self.asset_to_sector.get(order.symbol, 'unknown')
        current_sector_value = self.sector_exposures.get(sector, 0)
        new_sector_exposure = (current_sector_value + order_value) / self.total_portfolio_value
        if new_sector_exposure > self.max_sector_exposure:
            result['approved'] = False
            result['reasons'].append(f"Sector exposure would exceed limit: {new_sector_exposure:.3f} > {self.max_sector_exposure}")
            max_sector_value = self.max_sector_exposure * self.total_portfolio_value
            max_additional_value = max_sector_value - current_sector_value
            result['adjusted_size'] = min(result['adjusted_size'], max(0, max_additional_value / current_price))
        
        # Check currency exposure limit
        currency = order.symbol.split('USDT')[1] if 'USDT' in order.symbol else order.symbol[-3:]
        current_currency_value = self.currency_exposures.get(currency, 0)
        new_currency_exposure = (current_currency_value + order_value) / self.total_portfolio_value
        if new_currency_exposure > self.max_currency_exposure:
            result['approved'] = False
            result['reasons'].append(f"Currency exposure would exceed limit: {new_currency_exposure:.3f} > {self.max_currency_exposure}")
            max_currency_value = self.max_currency_exposure * self.total_portfolio_value
            max_additional_value = max_currency_value - current_currency_value
            result['adjusted_size'] = min(result['adjusted_size'], max(0, max_additional_value / current_price))
        
        return result
    
    def get_asset_exposure(self, asset: str) -> float:
        """Get exposure to a specific asset as a percentage of portfolio"""
        asset_value = self.asset_exposures.get(asset, 0)
        return asset_value / self.total_portfolio_value if self.total_portfolio_value > 0 else 0
    
    def get_sector_exposure(self, sector: str) -> float:
        """Get exposure to a specific sector as a percentage of portfolio"""
        sector_value = self.sector_exposures.get(sector, 0)
        return sector_value / self.total_portfolio_value if self.total_portfolio_value > 0 else 0
    
    def get_currency_exposure(self, currency: str) -> float:
        """Get exposure to a specific currency as a percentage of portfolio"""
        currency_value = self.currency_exposures.get(currency, 0)
        return currency_value / self.total_portfolio_value if self.total_portfolio_value > 0 else 0
    
    def get_exposure_report(self) -> Dict:
        """Get a comprehensive report of all exposures"""
        return {
            'asset_exposures': {asset: value / self.total_portfolio_value for asset, value in self.asset_exposures.items() if self.total_portfolio_value > 0},
            'sector_exposures': {sector: value / self.total_portfolio_value for sector, value in self.sector_exposures.items() if self.total_portfolio_value > 0},
            'currency_exposures': {currency: value / self.total_portfolio_value for currency, value in self.currency_exposures.items() if self.total_portfolio_value > 0},
            'total_exposure': sum(pos.quantity * pos.entry_price for pos in self.positions.values()),
            'total_portfolio_value': self.total_portfolio_value,
            'exposure_ratio': sum(pos.quantity * pos.entry_price for pos in self.positions.values()) / self.total_portfolio_value if self.total_portfolio_value > 0 else 0
        }
    
    def enforce_exposure_limits(self, order: Order, current_price: float) -> Optional[float]:
        """Enforce exposure limits and return adjusted order size, or None if order should be rejected"""
        check_result = self.check_order_exposure(order, current_price)
        
        if check_result['approved']:
            return order.quantity
        else:
            logger.warning(f"Order exposure limit violation for {order.symbol}: {', '.join(check_result['reasons'])}")
            return check_result['adjusted_size'] if check_result['adjusted_size'] > 0 else None
    
    def get_concentration_risk(self) -> Dict[str, float]:
        """Calculate concentration risk metrics"""
        concentration = {}
        
        # Top assets by exposure
        sorted_assets = sorted(self.asset_exposures.items(), key=lambda x: x[1], reverse=True)
        for asset, value in sorted_assets[:5]:  # Top 5 assets
            concentration[f'top_asset_{asset}'] = value / self.total_portfolio_value if self.total_portfolio_value > 0 else 0
        
        # Max single asset exposure
        max_asset_exposure = max(self.asset_exposures.values()) / self.total_portfolio_value if self.asset_exposures and self.total_portfolio_value > 0 else 0
        concentration['max_single_asset'] = max_asset_exposure
        
        return concentration