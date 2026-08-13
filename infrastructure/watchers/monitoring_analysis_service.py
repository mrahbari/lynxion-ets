"""
Monitoring and Analysis Module for Market Opportunity Watcher
Handles the main monitoring loop and analysis of market opportunities
"""
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from domain.entities import MarketObservation
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from infrastructure.messaging.event_system import EventType


class MonitoringAnalysisService:
    """Service class for monitoring markets and analyzing opportunities."""
    
    def __init__(self, logger: EnhancedLogger = None, event_router=None, market_data_repo=None):
        self.logger = logger or EnhancedLogger("MonitoringAnalysisService")
        self.event_router = event_router
        self.market_data_repo = market_data_repo
        self.is_running = False
        self.monitoring_thread = None
        self.watchers = {}
        self.symbols = []
        self.last_observations = {}
        self.on_update_symbols = None
        self.auto_discover_symbols = False
    
    def set_watchers_and_symbols(self, watchers: Dict, symbols: List[Symbol]):
        """Set the watchers and symbols to monitor."""
        self.watchers = watchers
        self.symbols = symbols
    
    def start_monitoring(self):
        """Start continuous market monitoring."""
        if self.is_running:
            self.logger.warning("Market opportunity watcher is already running")
            return

        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        # Start periodic symbol updates if auto-discovery is enabled
        if getattr(self, 'auto_discover_symbols', False):
            # Check if there is a watcher configuration for update interval
            interval = 30
            if hasattr(self, '_settings') and self._settings.watcher and hasattr(self._settings.watcher, 'data_refresh_interval_minutes'):
                interval = self._settings.watcher.data_refresh_interval_minutes
            self.start_periodic_symbol_updates(update_interval_minutes=interval)

        self.logger.log_auto_detection_status(len(self.symbols), 0, 0)

    def stop_monitoring(self):
        """Stop market monitoring."""
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish

        # Stop all watchers
        for symbol_watchers in self.watchers.values():
            for watcher in symbol_watchers.values():
                if hasattr(watcher, 'stop'):
                    watcher.stop()

        self.logger.info("🛑 Market opportunity monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop that continuously checks for opportunities."""
        self.logger.info("🔄 Market opportunity monitoring loop started")

        # Track statistics for periodic reporting
        last_report_time = time.time()
        report_interval = 60  # seconds between detailed reports
        analysis_count = 0
        signals_found = 0

        # Track symbol-specific analytics to ensure balanced processing
        symbol_analysis_count = {symbol.value: 0 for symbol in self.symbols}
        symbol_signal_count = {symbol.value: 0 for symbol in self.symbols}

        while self.is_running:
            try:
                opportunities = self._check_market_opportunities()
                analysis_count += len(self.symbols)

                # Update symbol-specific counts
                for symbol in self.symbols:
                    if symbol.value not in symbol_analysis_count:
                        symbol_analysis_count[symbol.value] = 0
                    symbol_analysis_count[symbol.value] += 1

                # Count signals found and track which symbols generated them
                for opportunity in opportunities:
                    if opportunity.get('recommendation') and opportunity['confidence'] > 0.6:
                        signals_found += 1
                        # Track which symbol generated the signal
                        symbol_val = opportunity.get('symbol')
                        if symbol_val:
                            if symbol_val not in symbol_signal_count:
                                symbol_signal_count[symbol_val] = 0
                            symbol_signal_count[symbol_val] += 1


                # Log periodic detailed reports
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    # Create a summary of signal distribution across symbols
                    active_symbols = {sym: cnt for sym, cnt in symbol_signal_count.items() if cnt > 0}

                    self.logger.info(
                        f"📊 WATCHER ANALYTICS: Analyzed {analysis_count} symbol checks in last {report_interval}s | "
                        f"Signals found: {signals_found} | Monitored symbols: {len(self.symbols)}")

                    if active_symbols:
                        self.logger.info(f"📈 SIGNAL DISTRIBUTION: {active_symbols}")

                    # Log analysis distribution to ensure all symbols are being processed
                    analysis_distribution = {sym: cnt for sym, cnt in symbol_analysis_count.items() if cnt > 0}
                    if analysis_distribution:
                        self.logger.debug(f"🔍 ANALYSIS DISTRIBUTION: {analysis_distribution}")

                    analysis_count = 0
                    signals_found = 0
                    last_report_time = current_time

                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Continue monitoring even if there's an error

    def _check_market_opportunities(self):
        """Check each symbol for trading opportunities."""
        all_opportunities = []

        # First, fetch market data and update all watchers with fresh data
        for symbol in self.symbols:
            self._update_watchers_with_market_data(symbol)
            # Add a small delay to ensure data is processed by watchers
            import time
            time.sleep(0.1)  # Small delay to allow data processing

        # Then analyze each symbol with a time limit to ensure fair processing
        total_start_time = time.time()

        # Process symbols in their original order to ensure systematic processing
        for symbol in self.symbols:
            # Add logging to track which symbol is being processed
            self.logger.debug(f"🔍 Processing symbol: {symbol.value}")

            start_time = time.time()
            opportunities = self._analyze_symbol(symbol)

            # Log processing time for this symbol
            processing_time = time.time() - start_time
            self.logger.debug(f"⏱️ Symbol {symbol.value} processed in {processing_time:.2f}s")

            if opportunities:
                self._process_opportunities(symbol, opportunities)
                all_opportunities.append(opportunities)

        # Log the total processing time for all symbols
        total_processing_time = time.time() - total_start_time
        self.logger.info(f"📊 Total processing for {len(self.symbols)} symbols completed in {total_processing_time:.2f}s")

        return all_opportunities

    def _update_watchers_with_market_data(self, symbol: Symbol):
        """Fetch market data and update all watchers for this symbol."""
        if not self.market_data_repo:
            self.logger.warning(f"No market data repository available for {symbol.value}")
            return

        # Check if symbol is available on exchange before processing
        if hasattr(self.market_data_repo, 'is_symbol_available'):
            if not self.market_data_repo.is_symbol_available(symbol.value):
                self.logger.debug(f"Skipping unavailable symbol: {symbol.value}")
                return

        try:
            # Fetch latest market data for the symbol
            # The market_data_repo should have a method to fetch data
            # This is a generic approach that should work with different data providers
            market_data = None

            # Try different possible methods to fetch data
            if hasattr(self.market_data_repo, 'get_historical_data'):
                # Get historical data for initializing watchers with sufficient history
                try:
                    historical_data = self.market_data_repo.get_historical_data(symbol=Symbol(symbol.value), period="30m", timeframe="1m")
                    if historical_data:
                        # Use the most recent data point to initialize, but the historical data will help populate history
                        market_data = historical_data[0] if historical_data else None
                        # Initialize watcher histories with historical data
                        self._initialize_watcher_histories_with_historical_data(symbol, historical_data)
                    else:
                        # Fallback to current price if no historical data
                        market_data = None
                        # Try to get current price as fallback
                        if hasattr(self.market_data_repo, 'get_current_price'):
                            price = self.market_data_repo.get_current_price(Symbol(symbol.value))
                            market_data = {'price': price, 'timestamp': datetime.now().timestamp(), 'symbol': symbol.value}
                except Exception as e:
                    # If get_historical_data fails, try current price as fallback
                    if hasattr(self.market_data_repo, 'get_current_price'):
                        price = self.market_data_repo.get_current_price(Symbol(symbol.value))
                        market_data = {'price': price, 'timestamp': datetime.now().timestamp(), 'symbol': symbol.value}
                    else:
                        market_data = None
            elif hasattr(self.market_data_repo, 'get_latest_data'):
                market_data = self.market_data_repo.get_latest_data(symbol.value)
            elif hasattr(self.market_data_repo, 'fetch_market_data'):
                market_data = self.market_data_repo.fetch_market_data(symbol.value)
            elif hasattr(self.market_data_repo, 'get_market_data'):
                market_data = self.market_data_repo.get_market_data(symbol.value)
            elif hasattr(self.market_data_repo, 'get_current_price'):
                # For mock data provider, get current price
                price = self.market_data_repo.get_current_price(Symbol(symbol.value))
                market_data = {'price': price, 'timestamp': datetime.now().timestamp(), 'symbol': symbol.value}
            elif hasattr(self.market_data_repo, 'get_data'):
                market_data = self.market_data_repo.get_data(symbol.value)
            else:
                # If no standard method exists, try to use it as a callable
                try:
                    market_data = self.market_data_repo(symbol.value)
                except:
                    self.logger.warning(f"Unable to fetch market data for {symbol.value} - no compatible method found")
                    return

            if market_data is None:
                self.logger.warning(f"No market data returned for {symbol.value}")
                return

            # Update all watchers for this symbol with the market data
            symbol_str = symbol.value
            if symbol_str in self.watchers:
                for watcher_name, watcher in self.watchers[symbol_str].items():
                    try:
                        # Convert market_data to the format expected by the watcher's update_data method
                        # The watchers expect a dictionary with market data
                        formatted_data = self._format_market_data_for_watcher(market_data)
                        watcher.update_data(formatted_data)
                    except Exception as e:
                        self.logger.warning(f"Error updating watcher {watcher_name} with market data: {e}")
                
                # Update last market data heartbeat immediately after ingestion
                try:
                    from infrastructure.messaging.event_system import signal_processor
                    signal_processor.update_market_data_heartbeat(symbol)
                except Exception as heartbeat_err:
                    self.logger.warning(f"Failed to update heartbeat timestamp for {symbol_str}: {heartbeat_err}")


        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol.value}: {e}")

    def _format_market_data_for_watcher(self, market_data):
        """Format market data to the structure expected by watchers."""
        # The format depends on the data source, but typically includes:
        # price, volume, high, low, open, close, timestamp
        formatted_data = {}

        if isinstance(market_data, dict):
            # If it's already a dictionary, extract common fields
            formatted_data.update({
                'close': market_data.get('close') or market_data.get('price') or market_data.get('last'),
                'open': market_data.get('open'),
                'high': market_data.get('high'),
                'low': market_data.get('low'),
                'volume': market_data.get('volume') or market_data.get('quoteVolume'),
                'timestamp': market_data.get('timestamp'),
                'bid': market_data.get('bid'),
                'ask': market_data.get('ask'),
            })
        elif hasattr(market_data, '__dict__'):
            # If it's an object, try to extract attributes
            data_dict = market_data.__dict__
            formatted_data.update({
                'close': data_dict.get('close') or data_dict.get('price') or data_dict.get('last'),
                'open': data_dict.get('open'),
                'high': data_dict.get('high'),
                'low': data_dict.get('low'),
                'volume': data_dict.get('volume') or data_dict.get('quoteVolume'),
                'timestamp': data_dict.get('timestamp'),
                'bid': data_dict.get('bid'),
                'ask': data_dict.get('ask'),
            })
        else:
            # If it's a single value, assume it's a price
            formatted_data['close'] = market_data

        # Remove None values
        formatted_data = {k: v for k, v in formatted_data.items() if v is not None}
        return formatted_data

    def _initialize_watcher_histories_with_historical_data(self, symbol: Symbol, historical_data: List[Dict[str, Any]]):
        """Initialize watcher histories with historical data to enable immediate signal generation."""
        symbol_str = symbol.value

        if symbol_str not in self.watchers:
            return

        # Update each watcher with all historical data points to build up their history
        for data_point in historical_data:
            for watcher_name, watcher in self.watchers[symbol_str].items():
                try:
                    formatted_data = self._format_market_data_for_watcher(data_point)
                    watcher.update_data(formatted_data)
                except Exception as e:
                    self.logger.warning(f"Error updating watcher {watcher_name} with historical data point: {e}")

    def _analyze_symbol(self, symbol: Symbol) -> Dict[str, Any]:
        """Analyze a symbol using all available watchers - only if enabled.
        Implements correct architecture: Watcher → Engine → Fusion → Strategy → Broker"""
        symbol_str = symbol.value

        # Validate symbol against approved list before processing
        from infrastructure.services.symbol_validator import symbol_validator
        if not symbol_validator.is_symbol_approved(symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Skipping processing.")
            return {
                'symbol': symbol_str,
                'timestamp': datetime.now(),
                'observations': {},
                'indicators': {},
                'recommendation': None,
                'confidence': 0.0,
                'strategy_suggestion': 'SKIPPED',  # Mark as skipped due to validation
                'execution_intent': None
            }

        # Log that the symbol analysis is starting
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            self.logger.log_background_activity(
                "Symbol Analysis",
                f"Starting analysis for {symbol_str}",
                symbol=symbol_str
            )

        opportunities = {
            'symbol': symbol_str,
            'timestamp': datetime.now(),
            'observations': {},
            'indicators': {},
            'recommendation': None,
            'confidence': 0.0,
            'strategy_suggestion': 'PENDING',  # Strategy selection happens in Strategy layer
            'execution_intent': None
        }

        # Get priority order for watchers based on their predictive power
        # This allows us to implement early exit logic if initial key indicators show no opportunity
        watcher_priority_order = self._get_watcher_priority_order()

        # Process each watcher individually - only emit raw market observations
        for watcher_name in watcher_priority_order:
            # Check if this watcher exists for this symbol
            if watcher_name not in self.watchers[symbol_str]:
                continue

            watcher = self.watchers[symbol_str][watcher_name]

            # Log that we're starting to analyze with this watcher
            if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                self.logger.log_background_activity(
                    "Watcher Analysis",
                    f"Analyzing {symbol_str} with {watcher_name}",
                    symbol=symbol_str,
                    watcher=watcher_name
                )

            # Check if the specific watcher has an enabled attribute and if it's enabled
            watcher_is_enabled = True  # Default assumption

            # Check if the watcher has an enabled attribute
            if hasattr(watcher, 'enabled'):
                watcher_is_enabled = watcher.enabled

            # Only call analyze if the watcher is enabled
            if watcher_is_enabled:
                try:
                    # Step 1: Watcher generates raw market observation (no strategy selection)
                    observation = watcher.analyze(symbol)

                    # Log the complete flow for this watcher regardless of whether it generated an observation
                    if observation:
                        # Store raw observation from watcher
                        raw_observation_data = {
                            'observation_type': observation.observation_type,
                            'observation_value': observation.observation_value,
                            'confidence': float(observation.confidence.value) if hasattr(observation.confidence,
                                                                                        'value') else float(
                                observation.confidence),
                            'timestamp': observation.timestamp.isoformat() if hasattr(observation,
                                                                                     'timestamp') else datetime.now().isoformat(),
                            'metadata': observation.metadata if hasattr(observation, 'metadata') else {},
                            'watcher_name': watcher_name
                        }
                        opportunities['observations'][watcher_name] = raw_observation_data

                        # Log the individual watcher observation
                        self.logger.log_watcher_analysis(
                            watcher=watcher_name,
                            symbol=symbol_str,
                            result=f"Observation Generated: {observation.observation_type}",
                            confidence=float(observation.confidence.value) if hasattr(observation.confidence, 'value') else float(
                                observation.confidence),
                            signal_type=observation.observation_type
                        )

                        # Ensure observation metadata has watcher_name attached
                        if observation.metadata is None:
                            observation.metadata = {}
                        if 'watcher_name' not in observation.metadata:
                            observation.metadata['watcher_name'] = watcher_name

                        # Emit the raw market observation to the event system for proper processing
                        if self.event_router:
                            try:
                                self.event_router.publish_observation(
                                    observation=observation,
                                    source=f"Watcher_{watcher_name}",
                                    correlation_id=f"{symbol_str}_{datetime.now().timestamp()}"
                                )
                                self.logger.info(f"Emitting market observation to event system: {observation.observation_type} for {symbol_str}")
                            except Exception as e:
                                self.logger.error(f"Error emitting observation to event system: {e}")
                        else:
                            self.logger.warning("No event router available to emit observation")

                        # Implement early exit logic: if this is an early watcher and it indicates no opportunity,
                        # we might want to skip remaining watchers for efficiency
                        if self._should_skip_remaining_watchers(observation, watcher_name):
                            self.logger.info(f"Early exit triggered for {symbol_str} after {watcher_name} - no profitable opportunity detected")
                            break

                    else:
                        # No observation was generated by the watcher
                        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                            self.logger.log_background_activity(
                                "Observation Analysis",
                                f"No observation generated by {watcher_name} for {symbol_str}",
                                symbol=symbol_str,
                                watcher=watcher_name
                            )

                        # Log that the watcher didn't generate an observation
                        self.logger.log_watcher_analysis(
                            watcher=watcher_name,
                            symbol=symbol_str,
                            result="No Observation Generated"
                        )

                except Exception as e:
                    self.logger.error(f"Error analyzing {symbol_str} with {watcher_name}: {e}")
                    # Log the error in watcher analysis (don't show confidence for errors)
                    self.logger.log_watcher_analysis(
                        watcher=watcher_name,
                        symbol=symbol_str,
                        result=f"Error: {str(e)}"
                        # Don't pass confidence when there's an error
                    )
                    continue

        # Log the final analysis result for this symbol with complete flow tracking
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            if opportunities['recommendation']:
                self.logger.log_background_activity(
                    "Symbol Analysis Complete",
                    f"Opportunity found for {symbol_str}: {opportunities['recommendation']} with confidence {opportunities['confidence']:.2%}",
                    symbol=symbol_str,
                    recommendation=opportunities['recommendation'],
                    confidence=opportunities['confidence']
                )
            else:
                self.logger.log_background_activity(
                    "Symbol Analysis Complete",
                    f"No opportunities found for {symbol_str}",
                    symbol=symbol_str
                )

        return opportunities

    def _get_watcher_priority_order(self) -> List[str]:
        """Get the priority order for watchers based on their predictive power."""
        # Define priority order - most predictive watchers first
        # This allows for early exit if initial key indicators show no opportunity
        priority_order = [
            'market_pulse',      # Market pulse often indicates immediate opportunities
            'trend_mtf',         # Multi-timeframe trend is fundamental
            'volatility',        # Volatility can indicate trade viability
            'anomaly_ml',        # ML anomalies can be predictive
            'liquidity',         # Liquidity affects trade execution
            'funding_rate',      # Funding rates affect perpetual positions
            'cmc_screener',      # General market conditions
            'orderflow_ws',      # Order flow for execution timing
            'historical_candle', # Historical patterns
            'tick_watcher'       # Tick-level analysis (usually confirmatory)
        ]

        return priority_order

    def _should_skip_remaining_watchers(self, observation, watcher_name: str) -> bool:
        """Determine if remaining watchers should be skipped based on early indicators."""
        # DISABLED: Never skip remaining watchers to ensure all observations flow through the system
        # The architectural flow should be: Watcher → Engine → Fusion → Strategy → Broker
        # Watchers should only emit observations, not make trading decisions
        return False  # Always return False to ensure all watchers run

    def _process_opportunities(self, symbol: Symbol, opportunities: Dict[str, Any]):
        """Process detected opportunities - but in the correct architecture,
        the watcher should only emit observations and not handle callbacks directly."""

        # The watcher should only emit raw market observations to the event system
        # The actual processing should happen through the event-driven flow

        # Log that we're processing opportunities
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            self.logger.log_background_activity(
                "Opportunity Processing",
                f"Processing opportunities for {symbol.value}",
                symbol=symbol.value
            )

    def start_periodic_symbol_updates(self, update_interval_minutes=30):
        """Start a background thread to periodically update symbols."""
        import threading
        import time

        def update_loop():
            while self.is_running:
                try:
                    self._update_symbol_list()
                    # Sleep for the specified interval
                    for _ in range(update_interval_minutes * 60):  # Convert minutes to seconds
                        if not self.is_running:  # Check if we should stop
                            break
                        time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Error in periodic symbol update: {e}")
                    time.sleep(60)  # Wait a minute before retrying

        # Start the update thread
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        self.logger.info(f"🔄 Started periodic symbol updates every {update_interval_minutes} minutes")

    def _update_symbol_list(self):
        """Dynamically update the list of symbols to monitor based on market conditions."""
        self.logger.info("🔄 Updating symbol list based on market conditions")
        if hasattr(self, 'on_update_symbols') and self.on_update_symbols:
            self.on_update_symbols()