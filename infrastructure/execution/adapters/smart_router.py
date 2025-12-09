from typing import Dict, List, Optional
from shared.types import Order, Fill
from shared.logger import logger
from datetime import datetime
import time


class SmartOrderRouter:
    """Smart order router that selects the best execution venue based on market conditions"""
    
    def __init__(self, broker_gateways: Dict[str, any], config: Dict = None):
        self.broker_gateways = broker_gateways
        self.config = config or {}
        
        # Routing parameters
        self.price_improvement_threshold = config.get('price_improvement_threshold', 0.001)  # 0.1% improvement needed
        self.liquidity_threshold = config.get('liquidity_threshold', 1000)  # Min liquidity required
        self.min_spread_ratio = config.get('min_spread_ratio', 0.0005)  # Min spread to consider
        self.max_spread_ratio = config.get('max_spread_ratio', 0.01)  # Max spread to consider
        self.latency_weight = config.get('latency_weight', 0.3)  # Weight of latency in decision
        self.liquidity_weight = config.get('liquidity_weight', 0.4)  # Weight of liquidity in decision
        self.price_weight = config.get('price_weight', 0.3)  # Weight of price in decision
        
        # Market data cache
        self.market_data_cache = {}
        self.last_update_time = {}
        self.broker_performance = {}
        self.broker_latency = {}
        
        # Fee structures for different brokers
        self.broker_fees = config.get('broker_fees', {})
        
    def route_order(self, order: Order) -> Optional[str]:
        """Route an order to the optimal broker based on current conditions"""
        # Get all available brokers for this symbol
        eligible_brokers = self._get_eligible_brokers(order.symbol)
        
        if not eligible_brokers:
            logger.error(f"No eligible brokers found for symbol {order.symbol}")
            return None
        
        # Score each broker based on current conditions
        broker_scores = {}
        for broker_name in eligible_brokers:
            broker_scores[broker_name] = self._score_broker(broker_name, order)
        
        # Select the best broker
        if broker_scores:
            best_broker = max(broker_scores.keys(), key=lambda k: broker_scores[k])
            logger.debug(f"Routing order to {best_broker} with score {broker_scores[best_broker]:.4f}")
            return self._submit_order_to_broker(best_broker, order)
        else:
            logger.error(f"No suitable broker found for order routing")
            return None
    
    def _get_eligible_brokers(self, symbol: str) -> List[str]:
        """Get list of brokers that support this symbol"""
        eligible = []
        for broker_name, broker in self.broker_gateways.items():
            try:
                # Check if broker supports the symbol
                # This is a simplified check - in reality you'd query symbol info
                symbol_info = broker.get_symbol_info(symbol)
                if symbol_info:
                    eligible.append(broker_name)
            except:
                # If we can't get symbol info, assume it's supported
                eligible.append(broker_name)
        return eligible
    
    def _score_broker(self, broker_name: str, order: Order) -> float:
        """Score a broker for the given order based on various factors"""
        # Get market data for the broker
        market_data = self._get_market_data(broker_name, order.symbol)
        if not market_data:
            return 0.0  # Can't score if no market data
        
        # Calculate various factors
        price_score = self._calculate_price_score(market_data, order.side)
        liquidity_score = self._calculate_liquidity_score(market_data)
        latency_score = self._calculate_latency_score(broker_name)
        fee_score = self._calculate_fee_score(broker_name, order, market_data)
        performance_score = self._calculate_performance_score(broker_name)
        
        # Weighted combination of scores
        total_score = (
            price_score * self.price_weight +
            liquidity_score * self.liquidity_weight +
            latency_score * self.latency_weight +
            fee_score * 0.1 +  # Fees are important but not the main factor
            performance_score * 0.1  # Past performance matters
        )
        
        return max(0.0, min(1.0, total_score))
    
    def _calculate_price_score(self, market_data: Dict, side: str) -> float:
        """Calculate score based on bid/ask prices"""
        try:
            bid = market_data.get('bid', 0)
            ask = market_data.get('ask', 0)
            last_price = market_data.get('last_price', 0)
            
            if bid == 0 or ask == 0:
                return 0.0
            
            # Calculate spread
            spread = ask - bid if ask > bid else 0.0001  # Prevent division by zero
            mid_price = (bid + ask) / 2
            
            if mid_price == 0:
                return 0.0
            
            spread_ratio = spread / mid_price
            
            # Score based on spread (lower spread is better)
            # Normalize to 0-1 scale
            max_spread_ratio = self.max_spread_ratio
            spread_score = 1.0 - min(1.0, spread_ratio / max_spread_ratio)
            
            # If we want to buy and there's a better bid elsewhere, lower the score
            # If we want to sell and there's a better ask elsewhere, lower the score
            # This is where we'd compare with other venues in a real implementation
            
            return spread_score
        except:
            return 0.0
    
    def _calculate_liquidity_score(self, market_data: Dict) -> float:
        """Calculate score based on market liquidity"""
        try:
            bid_volume = market_data.get('bid_volume', 0)
            ask_volume = market_data.get('ask_volume', 0)
            total_volume = bid_volume + ask_volume
            
            # Calculate liquidity score based on volume
            # Higher volume = higher liquidity = better score
            if total_volume < self.liquidity_threshold:
                return 0.0
            
            # Logarithmic scale so very high liquidity doesn't dominate
            liquidity_score = min(1.0, (total_volume / self.liquidity_threshold) ** 0.5)
            return liquidity_score
        except:
            return 0.0
    
    def _calculate_latency_score(self, broker_name: str) -> float:
        """Calculate score based on broker latency"""
        latency = self.broker_latency.get(broker_name, float('inf'))
        
        if latency == float('inf'):
            return 0.2  # Default low score for unknown latency
        
        # Lower latency is better - invert and normalize
        # Assume 100ms is very high latency
        max_latency = 0.1  # 100ms
        latency_score = max(0.1, 1.0 - (min(max_latency, latency) / max_latency))
        
        return latency_score
    
    def _calculate_fee_score(self, broker_name: str, order: Order, market_data: Dict) -> float:
        """Calculate score based on broker fees"""
        try:
            # Get fee structure for this broker
            fee_info = self.broker_fees.get(broker_name, {})
            
            if not fee_info:
                return 0.8  # Default medium-high score for unknown fees
            
            # Calculate expected fees for this order
            # This is a simplified calculation
            trade_value = order.quantity * market_data.get('last_price', 100.0)
            
            if order.order_type.value == 'MARKET':
                fee_rate = fee_info.get('taker_fee', 0.002)
            else:
                fee_rate = fee_info.get('maker_fee', 0.001)
            
            expected_fees = trade_value * fee_rate
            
            # Lower fees = higher score
            # Scale from 0.1 (high fees) to 1.0 (low/no fees)
            max_acceptable_fee_rate = 0.005  # 0.5%
            fee_ratio = fee_rate / max_acceptable_fee_rate
            fee_score = max(0.1, 1.0 - fee_ratio)
            
            return fee_score
        except:
            return 0.5  # Default score for fee calculation issues
    
    def _calculate_performance_score(self, broker_name: str) -> float:
        """Calculate score based on broker's past performance"""
        performance = self.broker_performance.get(broker_name, {})
        
        if not performance:
            return 0.6  # Default score for new brokers
        
        # Calculate performance score based on fill rates, etc.
        fill_rate = performance.get('fill_rate', 0.95)  # Default 95% fill rate
        avg_slippage = performance.get('avg_slippage', 0.001)  # Default 0.1% slippage
        success_rate = performance.get('success_rate', 0.98)  # Default 98% success rate
        
        # Combine performance metrics
        performance_score = (fill_rate * 0.4) + (success_rate * 0.4) + ((0.01 - avg_slippage) * 0.2)
        
        return max(0.0, min(1.0, performance_score))
    
    def _get_market_data(self, broker_name: str, symbol: str) -> Optional[Dict]:
        """Get current market data from a broker"""
        try:
            broker = self.broker_gateways[broker_name]
            
            # Check if we have cached data that's recent enough
            cache_key = f"{broker_name}:{symbol}"
            if cache_key in self.market_data_cache:
                last_update = self.last_update_time.get(cache_key, datetime.min)
                if (datetime.now() - last_update).seconds < 1:  # Cache for 1 second
                    return self.market_data_cache[cache_key]
            
            # Fetch fresh market data
            # Get ticker data
            ticker = broker.get_ticker_price(symbol)
            if not ticker:
                return None
                
            # Get order book data
            orderbook = broker.get_orderbook(symbol)
            if not orderbook:
                return None
            
            # Construct market data dict
            market_data = {
                'symbol': symbol,
                'last_price': float(ticker.get('price', 0)),
                'bid': float(orderbook['bids'][0][0]) if orderbook.get('bids') else 0,
                'bid_volume': float(orderbook['bids'][0][1]) if orderbook.get('bids') else 0,
                'ask': float(orderbook['asks'][0][0]) if orderbook.get('asks') else 0,
                'ask_volume': float(orderbook['asks'][0][1]) if orderbook.get('asks') else 0,
                'timestamp': datetime.now()
            }
            
            # Update cache
            self.market_data_cache[cache_key] = market_data
            self.last_update_time[cache_key] = datetime.now()
            
            return market_data
        except Exception as e:
            logger.error(f"Error getting market data from {broker_name}: {e}")
            return None
    
    def _submit_order_to_broker(self, broker_name: str, order: Order) -> Optional[str]:
        """Submit an order to a specific broker"""
        try:
            start_time = time.time()
            
            broker = self.broker_gateways[broker_name]
            order_id = broker.place_order(order)
            
            end_time = time.time()
            latency = end_time - start_time
            
            # Update latency tracking
            self.broker_latency[broker_name] = latency
            
            if order_id:
                logger.debug(f"Order submitted to {broker_name}, ID: {order_id}, latency: {latency:.4f}s")
                
                # Update performance metrics
                if broker_name not in self.broker_performance:
                    self.broker_performance[broker_name] = {
                        'total_orders': 0,
                        'successful_orders': 0,
                        'total_fill_value': 0,
                        'fill_rate': 0.95,  # Initial value
                        'success_rate': 0.98,  # Initial value
                        'avg_slippage': 0.001  # Initial value
                    }
                
                # Update performance tracking
                perf = self.broker_performance[broker_name]
                perf['total_orders'] += 1
                perf['successful_orders'] += 1
                
            return order_id
        except Exception as e:
            logger.error(f"Error submitting order to {broker_name}: {e}")
            return None
    
    def update_broker_performance(self, broker_name: str, success: bool, slippage: float = 0.0):
        """Update performance metrics for a broker"""
        if broker_name not in self.broker_performance:
            self.broker_performance[broker_name] = {
                'total_orders': 0,
                'successful_orders': 0,
                'fill_rate': 0.95,
                'success_rate': 0.98,
                'avg_slippage': 0.001
            }
        
        perf = self.broker_performance[broker_name]
        perf['total_orders'] += 1
        
        if success:
            perf['successful_orders'] += 1
        
        # Update success rate
        perf['success_rate'] = perf['successful_orders'] / perf['total_orders']
        
        # Update average slippage (exponential moving average)
        alpha = 0.1  # Smoothing factor
        perf['avg_slippage'] = alpha * slippage + (1 - alpha) * perf['avg_slippage']
    
    def get_routing_report(self) -> Dict:
        """Get a report on routing performance"""
        return {
            'broker_performance': self.broker_performance,
            'broker_latency': self.broker_latency,
            'cached_markets': len(self.market_data_cache),
            'brokers_connected': len(self.broker_gateways)
        }
    
    def manual_route_order(self, order: Order, preferred_broker: str) -> Optional[str]:
        """Route an order to a specific broker"""
        if preferred_broker not in self.broker_gateways:
            logger.error(f"Preferred broker {preferred_broker} not available")
            return None
        
        return self._submit_order_to_broker(preferred_broker, order)