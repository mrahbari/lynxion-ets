
-Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md


We added a new feature to check and only pass the approved symbols for using in the flows and system. 
I found that, we use spot available symbols which is incorrect. on the other hand I need an active/deactive flag for this feature which default is true(active).
can you take care of the below description and resolve and improve them. 
it seems the implementations in this file is correct: ./runner_sync_approved_symbols.py

utils/symbol_validator.py
used in: 
    - infrastructure.brokers.multi_broker_service.MultiBrokerExecutionService.is_symbol_available
    - infrastructure.data.configurable_historical_data_provider.ConfigurableHistoricalDataProvider.get_historical_data
    - infrastructure.data.enhanced_data_provider.EnhancedDataProviderAdapter.is_symbol_available
    - infrastructure.services.broker_execution_service.BrokerExecutionService.execute_order
    - infrastructure.watchers.market_opportunity_watcher.MarketOpportunityWatcher._validate_symbol_data_availability





2026-01-15 07:01:55,037 ℹ️INFO SymbolValidator - Loaded 440 approved symbols from /Users/mojtaba.rahbari/Sites/python/lynxion-ets/application/configs/approved_symbols.json


infrastructure/brokers/adapters/bingx_adapter.py
infrastructure.brokers.adapters.bingx_adapter._BingXBroker.get_available_symbols
line 715:
            response = self._make_request('GET', '/openApi/spot/v1/public/exchangeInfo', signed=False)



> I am using the BingX API and need to retrieve **Futures (Perpetual / Swap) trading symbols**, not Spot symbols.
>
> * Uses the correct **BingX Futures (swap) endpoint**
> * Returns **only active Futures contracts**
> * Optionally you can use  **additional contract metadata** such as leverage limits, price precision, quantity precision, and contract size.

---

## Sample Code – BingX Futures Symbols (Python)

### 1️⃣ Get Futures Symbols Only

```python
def get_bingx_futures_symbols(self) -> set:
    """
    Retrieve active Futures (Perpetual / Swap) symbols from BingX.
    Returns: set[str] like {'BTCUSDT', 'ETHUSDT'}
    """
    symbols = set()

    try:
        response = self._make_request(
            method='GET',
            path='/openApi/swap/v2/quote/contracts',
            signed=False
        )

        if response.get('code') != 0:
            self.logger.error(f"BingX futures API error: {response}")
            return set()

        contracts = response.get('data', [])
        if not isinstance(contracts, list):
            return set()

        for contract in contracts:
            if not isinstance(contract, dict):
                continue

            # status == 1 means tradable
            if contract.get('status') == 1:
                raw_symbol = contract.get('symbol')
                if raw_symbol:
                    # Convert BTC-USDT -> BTCUSDT
                    symbols.add(raw_symbol.replace('-', ''))

        self.logger.debug(f"Fetched {len(symbols)} BingX futures symbols")
        return symbols

    except Exception as e:
        self.logger.error(f"Error fetching BingX futures symbols: {e}")
        return set()
```

---

### 2️⃣ Get Futures Symbols With Metadata (Sample)

```python
def get_bingx_futures_symbols_info(self) -> dict:
    """
    Retrieve active Futures symbols with contract metadata.

    Returns:
    {
        'BTCUSDT': {
            'raw_symbol': 'BTC-USDT',
            'min_leverage': 1,
            'max_leverage': 125,
            'price_precision': 2,
            'quantity_precision': 3,
            'contract_size': 0.001
        }
    }
    """
    symbols = {}

    try:
        response = self._make_request(
            method='GET',
            path='/openApi/swap/v2/quote/contracts',
            signed=False
        )

        if response.get('code') != 0:
            self.logger.error(f"BingX futures API error: {response}")
            return {}

        for c in response.get('data', []):
            if c.get('status') != 1:
                continue

            raw_symbol = c.get('symbol')
            if not raw_symbol:
                continue

            symbol = raw_symbol.replace('-', '')

            symbols[symbol] = {
                'raw_symbol': raw_symbol,
                'min_leverage': c.get('minLeverage'),
                'max_leverage': c.get('maxLeverage'),
                'price_precision': c.get('pricePrecision'),
                'quantity_precision': c.get('quantityPrecision'),
                'contract_size': c.get('contractSize'),
            }

        return symbols

    except Exception as e:
        self.logger.error(f"Error fetching BingX futures symbol info: {e}")
        return {}
```

---

## Notes / Best Practices

* ✅ Always use `/swap/...` endpoints for Futures
* ❌ Never rely on `/spot/...` for futures markets
* 🔹 `status == 1` → active contract
* 🔹 Use metadata for:
  * position sizing
  * precision handling
  * leverage validation

---






## All Critical Rules Implemented - FINAL VERIFICATION CHECKLIST

## CRITICAL EXECUTION REALITY RULE

This task must be treated as a production hedge fund system investigation.

You are strictly forbidden to:

- Assume any component is correct by default
- Assume configuration changes will solve execution problems
- Conclude that architecture is sound without execution proof
- Use optimistic, hypothetical, or expectation-based reasoning

### Mandatory Mindset

You must operate under this principle:

> If an action is not proven by logs or execution traces, it did NOT happen.

### Evidence-Based Requirement

For every claim you make, you must provide:

- The exact log evidence OR
- The exact execution path in code that proves it

If neither exists, you must explicitly declare the component or assumption as FAILED or UNVERIFIED.

### Execution Priority

System success is defined ONLY by:

> A confirmed, successful broker order execution.

Anything before that is considered incomplete.

### Configuration Rule

Configuration changes are NOT considered valid solutions unless:

- The execution path is proven reachable
- The component is proven to consume that configuration
- The configuration change produces a verifiable execution difference in logs

### Final Principle

This is not a design review.
This is not a configuration review.
This is not a theoretical analysis.

This is an execution failure investigation in a real hedge fund trading system.

Your responsibility is to expose the truth, not to preserve optimism.
