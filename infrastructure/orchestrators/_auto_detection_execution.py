"""E5.T4 (infra-only mechanical split): trade-execution method extracted from
``AutoDetectionOrchestrator``.

Behavior-preserving mixin — ``_execute_trade_from_intent`` moved verbatim (signatures,
``self`` semantics, Order/Money/Symbol construction and placement UNCHANGED) and composed
back via inheritance. No layer move, no port inversion, no trading-logic change.
"""
from datetime import datetime
from domain.value_objects import Symbol


class _AutoDetectionExecutionMixin:
    """Order construction + placement from an execution intent (trading execution)."""

    def _execute_trade_from_intent(self, execution_intent):
        """Execute trade based on execution intent from strategy layer."""
        try:
            # Check if the system is still running - if not, reject the execution
            if not self.is_running:
                self.logger.warning(f"System is shutting down, rejecting execution intent for {execution_intent.symbol.value}")
                # Remove from pending intents since we're not executing
                self._remove_pending_execution_intent(execution_intent)
                return {
                    'status': 'failed',
                    'error': f"SYSTEM_SHUTDOWN: Execution rejected as system is shutting down"
                }

            # Check for active orders on the broker before processing the intent
            # This prevents duplicate orders when the system doesn't have full awareness of broker state
            if not self._check_broker_active_orders_for_duplicate(execution_intent):
                # Remove from pending intents since we're not executing
                self._remove_pending_execution_intent(execution_intent)
                symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
                direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)
                confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                return {
                    'status': 'failed',
                    'error': f"DUPLICATE:{symbol}:{direction} - Active order already exists on broker"
                }

            # Double-check for duplicates right before execution to prevent race conditions
            # This catches cases where multiple threads might have passed the initial check
            # but are now trying to execute simultaneously
            # NOTE: The actual broker service will also perform this check, so we'll just log if found
            # but allow the broker service to handle the rejection to avoid duplicate messages
            prevent_same_direction = self._settings.execution.prevent_same_direction_trade_per_symbol if self._settings.execution and hasattr(self._settings.execution, 'prevent_same_direction_trade_per_symbol') else True
            if prevent_same_direction:
                symbol = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
                direction = execution_intent.side.name if hasattr(execution_intent.side, 'name') else str(execution_intent.side)

                # Check the shared tracker again right before execution
                from domain.value_objects import Symbol
                symbol_obj = Symbol(symbol)
                if self._pending_orders_tracker.has_pending_order_in_direction(symbol_obj, direction):
                    confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
                    self.logger.debug(f"DUPLICATE CHECK: Pending {direction} order exists in shared tracker for {symbol}. Broker service will handle rejection. | Intent Confidence: {confidence:.2%}")

                    # We'll let the broker service handle the actual rejection to avoid duplicate messages
                    # Continue to execution where the broker service will reject it

        # Check if this is a stablecoin pair that should be filtered out
            filter_stablecoin_pairs = self._settings.data.filter_out_stablecoin_pairs if self._settings.data and hasattr(self._settings.data, 'filter_out_stablecoin_pairs') else True
            allowed_stablecoins = (self._settings.data.allowed_stablecoins if self._settings.data and self._settings.data.allowed_stablecoins else 'USDT,BUSD,USDC,DAI,PAX,TUSD,USDD,FDUSD').split(',')

            symbol_str = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)

            if filter_stablecoin_pairs:
                # Check if both parts of the symbol are stablecoins (e.g., USDCUSDT)
                # Extract base and quote currencies assuming format like BTCUSDT
                if len(symbol_str) > 6:  # At least 3 chars for base + 3 chars for quote
                    # Look for common stablecoin endings
                    for stablecoin in allowed_stablecoins:
                        if symbol_str.endswith(stablecoin):
                            base_currency = symbol_str[:-len(stablecoin)]
                            if base_currency in allowed_stablecoins:
                                # Both base and quote are stablecoins (e.g., USDCUSDT, BUSDUSDT)
                                self.logger.info(f"❌ STABLECOIN PAIR REJECTED: {symbol_str} | Reason: Both base and quote are stablecoins | Strategy: {execution_intent.strategy_name} | Intent Confidence: {float(execution_intent.intent_confidence.value):.2%}")

                                # Remove from pending intents since we're not executing
                                self._remove_pending_execution_intent(execution_intent)
                                return {
                                    'status': 'failed',
                                    'error': f"Stablecoin pair {symbol_str} filtered out"
                                }

            # Create order from execution intent
            from domain.entities import Order, OrderSide
            from domain.value_objects import Money
            from decimal import Decimal

            # Get current price for the symbol to determine position size
            current_price = None
            if self.market_data_repo:
                try:
                    current_price = self.market_data_repo.get_current_price(execution_intent.symbol)
                except:
                    # If we can't get current price from data repo, try to get from exchange directly
                    pass

            # If we still don't have a price, use a fallback
            if current_price is None or current_price <= 0:
                # Try to get price from exchange directly
                try:
                    import ccxt
                    exchange = ccxt.binance()
                    ticker = exchange.fetch_ticker(execution_intent.symbol.value)
                    current_price = ticker['last'] if 'last' in ticker else ticker['close']
                except:
                    # If all methods fail, we'll still proceed but log the issue
                    self.logger.warning(f"Could not get current price for {execution_intent.symbol.value}, using default price")
                    # Use a more reasonable fallback price based on the symbol
                    # Extract base currency to estimate a reasonable price
                    symbol_str = execution_intent.symbol.value
                    if symbol_str.startswith(('BTC', 'WBTC')):
                        current_price = 45000.0  # Bitcoin price range
                    elif symbol_str.startswith(('ETH', 'WETH')):
                        current_price = 2500.0  # Ethereum price range
                    elif symbol_str.startswith(('SOL', 'AVAX', 'FTM', 'APT', 'AR')):
                        current_price = 90.0   # Mid-range altcoins
                    elif symbol_str.startswith(('BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC', 'LINK', 'UNI', 'LTC', 'BCH')):
                        current_price = 10.0   # Lower range altcoins
                    elif symbol_str.startswith(('XLM', 'TRX', 'ATOM', 'NEAR', 'FIL', 'ETC', 'VET', 'XTZ', 'ICX', 'HBAR', 'SUI')):
                        current_price = 0.5    # Penny stocks/crypto range
                    elif symbol_str.startswith(('SHIB', 'PEPE', 'FLOKI')):
                        current_price = 0.00001  # Meme coin range
                    else:
                        # For any other symbol, use a reasonable default based on common patterns
                        # Use a random price between $0.01 and $500 to cover most crypto ranges
                        import random
                        current_price = random.uniform(0.01, 500.0)

            # Use risk parameters from the execution intent
            risk_params = execution_intent.risk_parameters
            position_size_pct = risk_params.get('max_position_size', 0.02)  # Default 2%

            # Fixed Position Size Configuration (for testing purposes)
            fixed_position_size_enabled = self._settings.position_sizing.fixed_position_size_enabled if self._settings.position_sizing and hasattr(self._settings.position_sizing, 'fixed_position_size_enabled') else False
            fixed_position_amount = self._settings.position_sizing.fixed_position_amount if self._settings.position_sizing and hasattr(self._settings.position_sizing, 'fixed_position_amount') else 10.0  # Default to $10 for testing

            # Calculate quantity based on risk parameters and account balance
            try:
                if fixed_position_size_enabled:
                    # Use fixed position size for testing
                    quantity = fixed_position_amount / current_price
                    self.logger.info(f"Using fixed position size: ${fixed_position_amount} at ${current_price} = {quantity} units")
                else:
                    # In a real implementation, we'd get portfolio metrics from portfolio service
                    # For now, using a default account balance from environment variable
                    account_balance = self._settings.position_sizing.default_account_balance if self._settings.position_sizing and hasattr(self._settings.position_sizing, 'default_account_balance') else 10000.0  # Default to $10,000 if not available
                    position_value = account_balance * position_size_pct

                    # Calculate quantity based on position value and current price
                    quantity = position_value / current_price

                    # Apply any quantity adjustments from risk parameters
                    if 'position_quantity' in risk_params:
                        quantity = risk_params['position_quantity']

            except:
                # If portfolio service fails, use a default quantity
                if fixed_position_size_enabled:
                    # Use fixed position size for testing
                    quantity = fixed_position_amount / current_price
                    self.logger.info(f"Using fixed position size (fallback): ${fixed_position_amount} at ${current_price} = {quantity} units")
                else:
                    # Use default account balance from environment variable
                    default_account_balance = self._settings.position_sizing.default_account_balance if self._settings.position_sizing and hasattr(self._settings.position_sizing, 'default_account_balance') else 1000.0  # Default to $1,000 if not available
                    quantity = position_size_pct * default_account_balance / current_price

            # Ensure minimum quantity to avoid issues with small trades
            if quantity < 0.001:
                quantity = 0.001  # Minimum trade size

            # Create order object using domain entities
            from domain.entities import Order, OrderSide
            from domain.value_objects import Money

            # Use the side from the execution intent
            order_side = execution_intent.side

            # Ensure symbol is properly formatted for the broker
            symbol_value = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)

            # Determine position side based on order side for futures trading
            position_side = "LONG" if order_side.name == 'BUY' else "SHORT"

            # Create order with risk parameters from the execution intent (set by Strategy layer)
            # The Strategy layer should have already calculated all risk parameters including SL/TP
            order = Order(
                symbol=symbol_value,  # Use string value instead of Symbol object
                side=order_side,
                order_type="MARKET",  # Using string instead of enum
                quantity=quantity,
                price=Money(amount=float(current_price), currency='USDT') if current_price else None,
                strategy_name=execution_intent.strategy_name,  # Strategy name comes from intent
                timestamp=datetime.now(),
                position_side=position_side,  # Add position side for futures trading
                stop_loss_price=getattr(execution_intent, 'stop_loss_price', None),  # SL from strategy
                take_profit_price=getattr(execution_intent, 'take_profit_price', None),  # TP from strategy
                parent_execution_intent=execution_intent  # Link back to the execution intent
            )

            # Log the order creation with comprehensive details
            confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
            self.logger.info(f"📝 ORDER CREATED: {symbol_value} | Side: {order_side.name} | Quantity: {quantity:.6f} | Price: ${current_price:.4f} | Strategy: {execution_intent.strategy_name} | Confidence: {confidence:.2%}")

            # Log the decision to proceed with order execution
            self.logger.log_decision_reason(
                component="Orchestrator",
                symbol=symbol_value,
                decision="Order Created - Ready for Execution",
                reason="Order created with all required parameters from execution intent",
                confidence=confidence,
                details={
                    'quantity': quantity,
                    'price': current_price,
                    'position_side': position_side,
                    'stop_loss': getattr(execution_intent, 'stop_loss_price', 'N/A'),
                    'take_profit': getattr(execution_intent, 'take_profit_price', 'N/A')
                }
            )

            # Validate symbol availability before executing order
            if hasattr(self.execution_service, 'get_available_symbols'):
                try:
                    available_symbols = self.execution_service.get_available_symbols()
                    if symbol_value not in available_symbols:
                        self.logger.warning(f"⚠️ Symbol {symbol_value} not available on any configured broker. Skipping order.")
                        # Remove from pending intents since we're not executing
                        self._remove_pending_execution_intent(execution_intent)

                        # Log the rejection with clear reason
                        self.logger.info(
                            f"❌ REJECTED SYMBOL: {symbol_value} | Reason: Not available on any configured broker | Strategy: {execution_intent.strategy_name} | Intent Confidence: {float(execution_intent.intent_confidence.value):.2%}")

                        return {
                            'status': 'failed',
                            'error': f"Symbol {symbol_value} not available on broker"
                        }
                except Exception as e:
                    # If we can't check available symbols, log the error but continue with execution
                    self.logger.warning(f"⚠️ Could not check available symbols from execution service: {e}. Continuing with execution attempt.")
            else:
                # If the execution service doesn't have get_available_symbols method, log this
                self.logger.debug(f"Execution service doesn't have get_available_symbols method. Proceeding with execution attempt for {symbol_value}")

            # Execute order through execution service
            execution_id = self.execution_service.execute_order(order)

            # Check if execution was prevented by duplicate prevention (returns None)
            if execution_id is None:
                # Remove from pending intents since execution was prevented
                self._remove_pending_execution_intent(execution_intent)

                # Log the duplicate prevention with clear reason
                self.logger.info(
                    f"❌ DUPLICATE PREVENTION: {symbol_value} | Reason: Duplicate same-direction trade prevented | Strategy: {execution_intent.strategy_name} | Intent Confidence: {float(execution_intent.intent_confidence.value):.2%}")

                return {
                    'status': 'failed',
                    'error': f"DUPLICATE:{symbol_value}:{position_side}"
                }

            # If execution_id is valid, continue with successful execution
            # Remove from pending intents after successful execution
            self._remove_pending_execution_intent(execution_intent)

            # Log successful execution
            confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
            self.logger.info(f"✅ ORDER EXECUTED: {symbol_value} | ID: {execution_id} | Strategy: {execution_intent.strategy_name} | Confidence: {confidence:.2%}")

            # Log the successful execution decision
            self.logger.log_decision_reason(
                component="Orchestrator",
                symbol=symbol_value,
                decision="Order Executed Successfully",
                reason=f"Order executed successfully with ID: {execution_id}",
                confidence=confidence,
                details={
                    'execution_id': execution_id,
                    'quantity': quantity,
                    'side': execution_intent.side.name
                }
            )

            return {
                'status': 'executed',
                'execution_id': execution_id,
                'order': {
                    'side': execution_intent.side.name,
                    'quantity': quantity,
                    'symbol': execution_intent.symbol.value
                }
            }
        except Exception as e:
            # Remove from pending intents in case of exception
            try:
                self._remove_pending_execution_intent(execution_intent)
            except Exception as cleanup_error:
                self.logger.warning(f"Warning: Error during pending intent cleanup: {cleanup_error}")
            return {
                'status': 'failed',
                'error': str(e)
            }
