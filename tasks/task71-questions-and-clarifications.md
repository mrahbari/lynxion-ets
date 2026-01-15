

First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Why we need to check .csv file for order placements and many issues like this! 
- why system needs to check it for production! it's not backtest!!!!!

There are lots of strange issues which i confused! so track a symbol like  NEOUSDT and find out what happened?
- check the ./logs/* deeply as well
- remember, we still have problem with order placement!
- New Resource Issue: The system is now creating too many resources (threads, file handles) which causes "Too many open files" error.
- make sure The system properly handles execution intents without generating multiple duplicate rejections.
- The "Too many open files" error is a resource exhaustion issue. The system is creating multiple broker instances and data providers, which is consuming too
  many file descriptors.

  Looking at the log output, I can see that the system is initializing multiple broker instances:
   - Multiple "Binance broker initialized" messages
   - Multiple "BingX broker initialized" messages
   - Multiple "MEXC broker initialized" messages
   - Multiple "Phemex broker initialized" messages

  This suggests that there are multiple instances of the same services being created, which is causing
  resource exhaustion.

  The original issue is about order placement, but there's also a resource management issue. The system is
  creating too many threads and file handles. This is likely happening because:

   1. Multiple watchers are creating multiple instances of services
   2. The architecture orchestrator is being initialized multiple times
   3. Multiple broker services are being instantiated

  While my fixes for the duplicate prevention and order placement logic are correct, there's also a resource
  management issue that needs to be addressed. The system is creating too many instances of the same
  services.

  However, the core fixes I implemented for the original issue (duplicate order prevention and proper cleanup
  of pending orders) are correct. The "Too many open files" error is a separate issue related to resource
  management in the architecture.

  Let me summarize the situation:

   1. Original Issue Fixed: The duplicate order prevention and order placement issues have been successfully
      fixed with the changes I made to:
      - Proper cleanup of pending orders in finally blocks
      - Symbol-level locking to prevent race conditions
      - Better error handling to prevent system crashes

   2. New Resource Issue: The system is now creating too many resources (threads, file handles) which causes
      "Too many open files" error.

The resource management issue is
  a separate architectural concern that would require additional refactoring to ensure services are properly
  shared rather than duplicated.

-----



## All Critical Rules Implemented - FINAL VERIFICATION CHECKLIST

## CRITICAL EXECUTION REALITY RULE
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



--- Logs of issues:
DEBUG:ConfigurableHistoricalDataProvider:Attempting to fetch historical data for TAOUSDT from phemex
2026-01-15 21:32:30,701 ❌ERROR ConfigurableHistoricalDataProvider - Error fetching historical data from Phemex for TAOUSDT: HTTPSConnectionPool(host='api.phemex.com', port=443): Max retries exceeded with url: /md/kline?symbol=TAOUSDT&resolution=1&from=1768507350&to=1768509150 (Caused by NameResolutionError("HTTPSConnection(host='api.phemex.com', port=443): Failed to resolve 'api.phemex.com' ([Errno 8] nodename nor servname provided, or not known)"))
ERROR:ConfigurableHistoricalDataProvider:Error fetching historical data from Phemex for TAOUSDT: HTTPSConnectionPool(host='api.phemex.com', port=443): Max retries exceeded with url: /md/kline?symbol=TAOUSDT&resolution=1&from=1768507350&to=1768509150 (Caused by NameResolutionError("HTTPSConnection(host='api.phemex.com', port=443): Failed to resolve 'api.phemex.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:30,701 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for TAOUSDT from phemex: HTTPSConnectionPool(host='api.phemex.com', port=443): Max retries exceeded with url: /md/kline?symbol=TAOUSDT&resolution=1&from=1768507350&to=1768509150 (Caused by NameResolutionError("HTTPSConnection(host='api.phemex.com', port=443): Failed to resolve 'api.phemex.com' ([Errno 8] nodename nor servname provided, or not known)"))
WARNING:ConfigurableHistoricalDataProvider:⚠️ Failed to fetch historical data for TAOUSDT from phemex: HTTPSConnectionPool(host='api.phemex.com', port=443): Max retries exceeded with url: /md/kline?symbol=TAOUSDT&resolution=1&from=1768507350&to=1768509150 (Caused by NameResolutionError("HTTPSConnection(host='api.phemex.com', port=443): Failed to resolve 'api.phemex.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:30,701 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for TAOUSDT from bingx
DEBUG:ConfigurableHistoricalDataProvider:Attempting to fetch historical data for TAOUSDT from bingx
2026-01-15 21:32:30,703 ❌ERROR ConfigurableHistoricalDataProvider - Error fetching historical data from BingX for TAOUSDT: HTTPSConnectionPool(host='open-api.bingx.com', port=443): Max retries exceeded with url: /openApi/quote/v1/klines?symbol=TAOUSDT&interval=1m&startTime=1768507350701&endTime=1768509150701&limit=500 (Caused by NameResolutionError("HTTPSConnection(host='open-api.bingx.com', port=443): Failed to resolve 'open-api.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
ERROR:ConfigurableHistoricalDataProvider:Error fetching historical data from BingX for TAOUSDT: HTTPSConnectionPool(host='open-api.bingx.com', port=443): Max retries exceeded with url: /openApi/quote/v1/klines?symbol=TAOUSDT&interval=1m&startTime=1768507350701&endTime=1768509150701&limit=500 (Caused by NameResolutionError("HTTPSConnection(host='open-api.bingx.com', port=443): Failed to resolve 'open-api.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:30,703 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for TAOUSDT from bingx: HTTPSConnectionPool(host='open-api.bingx.com', port=443): Max retries exceeded with url: /openApi/quote/v1/klines?symbol=TAOUSDT&interval=1m&startTime=1768507350701&endTime=1768509150701&limit=500 (Caused by NameResolutionError("HTTPSConnection(host='open-api.bingx.com', port=443): Failed to resolve 'open-api.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
WARNING:ConfigurableHistoricalDataProvider:⚠️ Failed to fetch historical data for TAOUSDT from bingx: HTTPSConnectionPool(host='open-api.bingx.com', port=443): Max retries exceeded with url: /openApi/quote/v1/klines?symbol=TAOUSDT&interval=1m&startTime=1768507350701&endTime=1768509150701&limit=500 (Caused by NameResolutionError("HTTPSConnection(host='open-api.bingx.com', port=443): Failed to resolve 'open-api.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:30,703 ❌ERROR ConfigurableHistoricalDataProvider - Failed to fetch historical data for TAOUSDT from any data source. Tried: ['binance', 'mexc', 'phemex', 'bingx']
ERROR:ConfigurableHistoricalDataProvider:Failed to fetch historical data for TAOUSDT from any data source. Tried: ['binance', 'mexc', 'phemex', 'bingx']
2026-01-15 21:32:30,703 🐞DEBUG EnhancedDataProvider - Could not fetch real historical data for TAOUSDT from configurable source: Failed to fetch historical data for TAOUSDT from any data source. Tried: ['binance', 'mexc', 'phemex', 'bingx']
DEBUG:EnhancedDataProvider:Could not fetch real historical data for TAOUSDT from configurable source: Failed to fetch historical data for TAOUSDT from any data source. Tried: ['binance', 'mexc', 'phemex', 'bingx']
2026-01-15 21:32:30,705 ⚠️WARNING HedgeFund - Connection error for TAOUSDT 1m, retrying in 1.81s (attempt 1/5)
WARNING:HedgeFund:Connection error for TAOUSDT 1m, retrying in 1.81s (attempt 1/5)
2026-01-15 21:32:32,526 ⚠️WARNING HedgeFund - Connection error for TAOUSDT 1m, retrying in 2.75s (attempt 2/5)
WARNING:HedgeFund:Connection error for TAOUSDT 1m, retrying in 2.75s (attempt 2/5)
2026-01-15 21:32:35,277 ⚠️WARNING HedgeFund - Connection error for TAOUSDT 1m, retrying in 4.83s (attempt 3/5)
WARNING:HedgeFund:Connection error for TAOUSDT 1m, retrying in 4.83s (attempt 3/5)
2026-01-15 21:32:40,119 ⚠️WARNING HedgeFund - Connection error for TAOUSDT 1m, retrying in 8.26s (attempt 4/5)
WARNING:HedgeFund:Connection error for TAOUSDT 1m, retrying in 8.26s (attempt 4/5)
2026-01-15 21:32:48,394 ❌ERROR HedgeFund - Connection error for TAOUSDT 1m after 5 attempts
ERROR:HedgeFund:Connection error for TAOUSDT 1m after 5 attempts
2026-01-15 21:32:48,395 ❌ERROR HedgeFund - Failed to download klines for TAOUSDT 1m after 5 attempts
ERROR:HedgeFund:Failed to download klines for TAOUSDT 1m after 5 attempts
2026-01-15 21:32:48,395 ⚠️WARNING EnhancedDataProvider - Using minimal data for TAOUSDT after error: [Errno 24] Too many open files: 'data/history/raw/1m/TAO-USDT.csv'
WARNING:EnhancedDataProvider:Using minimal data for TAOUSDT after error: [Errno 24] Too many open files: 'data/history/raw/1m/TAO-USDT.csv'
2026-01-15 21:32:48,395 🐞DEBUG ImprovedDataCache - Cache MISS for multibroker_PRICE_TAOUSDT_tick
DEBUG:ImprovedDataCache:Cache MISS for multibroker_PRICE_TAOUSDT_tick
2026-01-15 21:32:48,395 🐞DEBUG EnhancedDataProvider - Fetching price for TAOUSDT using broker service: BrokerExecutionService
DEBUG:EnhancedDataProvider:Fetching price for TAOUSDT using broker service: BrokerExecutionService
2026-01-15 21:32:48,395 🐞DEBUG EnhancedDataProvider - Checking symbol TAOUSDT availability via broker service BrokerExecutionService
DEBUG:EnhancedDataProvider:Checking symbol TAOUSDT availability via broker service BrokerExecutionService
2026-01-15 21:32:48,397 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from binance
2026-01-15 21:32:48,397 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from binance
2026-01-15 21:32:48,397 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from binance
DEBUG:MultiBrokerExecutionService:Got 0 symbols from binance
ERROR:infrastructure.brokers.adapters.bingx_adapter:Request failed: HTTPSConnectionPool(host='open-api-vst.bingx.com', port=443): Max retries exceeded with url: /openApi/spot/v1/public/exchangeInfo (Caused by NameResolutionError("HTTPSConnection(host='open-api-vst.bingx.com', port=443): Failed to resolve 'open-api-vst.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/data/enhanced_data_provider.py", line 145, in get_historical_data
    historical_data = self.csv_provider.get_historical_data(symbol, period, timeframe)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/data/csv_history_loader.py", line 60, in get_historical_data
    df = self.load_symbol_data(symbol.value, timeframe)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/data/csv_history_loader.py", line 126, in load_symbol_data
    df = pd.read_csv(file_path)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/util/_decorators.py", line 211, in wrapper
    return func(*args, **kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/util/_decorators.py", line 331, in wrapper
    return func(*args, **kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/parsers/readers.py", line 950, in read_csv
    return _read(filepath_or_buffer, kwds)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/parsers/readers.py", line 605, in _read
    parser = TextFileReader(filepath_or_buffer, **kwds)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/parsers/readers.py", line 1442, in __init__
    self._engine = self._make_engine(f, self.engine)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/parsers/readers.py", line 1735, in _make_engine
    self.handles = get_handle(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/common.py", line 856, in get_handle
    handle = open(
OSError: [Errno 24] Too many open files: 'data/history/raw/1m/TAO-USDT.csv'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connection.py", line 204, in _new_conn
    sock = connection.create_connection(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/util/connection.py", line 60, in create_connection
    for res in socket.getaddrinfo(host, port, family, socket.SOCK_STREAM):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/socket.py", line 955, in getaddrinfo
    for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
socket.gaierror: [Errno 8] nodename nor servname provided, or not known

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 787, in urlopen
    response = self._make_request(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 488, in _make_request
    raise new_e
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 464, in _make_request
    self._validate_conn(conn)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 1093, in _validate_conn
    conn.connect()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connection.py", line 759, in connect
    self.sock = sock = self._new_conn()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connection.py", line 211, in _new_conn
    raise NameResolutionError(self.host, self, e) from e
urllib3.exceptions.NameResolutionError: HTTPSConnection(host='open-api-vst.bingx.com', port=443): Failed to resolve 'open-api-vst.bingx.com' ([Errno 8] nodename nor servname provided, or not known)

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/adapters.py", line 644, in send
    resp = conn.urlopen(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 841, in urlopen
    retries = retries.increment(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/util/retry.py", line 519, in increment
    raise MaxRetryError(_pool, url, reason) from reason  # type: ignore[arg-type]
urllib3.exceptions.MaxRetryError: HTTPSConnectionPool(host='open-api-vst.bingx.com', port=443): Max retries exceeded with url: /openApi/spot/v1/public/exchangeInfo (Caused by NameResolutionError("HTTPSConnection(host='open-api-vst.bingx.com', port=443): Failed to resolve 'open-api-vst.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/adapters/bingx_adapter.py", line 297, in _make_request
    response = self.session.get(url, headers=headers, params=params, timeout=timeout)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/sessions.py", line 602, in get
    return self.request("GET", url, **kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/sessions.py", line 589, in request
    resp = self.send(prep, **send_kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/sessions.py", line 703, in send
    r = adapter.send(request, **kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/adapters.py", line 677, in send
    raise ConnectionError(e, request=request)
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='open-api-vst.bingx.com', port=443): Max retries exceeded with url: /openApi/spot/v1/public/exchangeInfo (Caused by NameResolutionError("HTTPSConnection(host='open-api-vst.bingx.com', port=443): Failed to resolve 'open-api-vst.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))

ERROR:infrastructure.brokers.adapters.bingx_adapter:Error getting available symbols from BingX: HTTPSConnectionPool(host='open-api-vst.bingx.com', port=443): Max retries exceeded with url: /openApi/spot/v1/public/exchangeInfo (Caused by NameResolutionError("HTTPSConnection(host='open-api-vst.bingx.com', port=443): Failed to resolve 'open-api-vst.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
ERROR:infrastructure.brokers.adapters.bingx_adapter:Traceback: Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/data/enhanced_data_provider.py", line 145, in get_historical_data
    historical_data = self.csv_provider.get_historical_data(symbol, period, timeframe)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/data/csv_history_loader.py", line 60, in get_historical_data
    df = self.load_symbol_data(symbol.value, timeframe)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/data/csv_history_loader.py", line 126, in load_symbol_data
    df = pd.read_csv(file_path)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/util/_decorators.py", line 211, in wrapper
    return func(*args, **kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/util/_decorators.py", line 331, in wrapper
    return func(*args, **kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/parsers/readers.py", line 950, in read_csv
    return _read(filepath_or_buffer, kwds)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/parsers/readers.py", line 605, in _read
    parser = TextFileReader(filepath_or_buffer, **kwds)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/parsers/readers.py", line 1442, in __init__
    self._engine = self._make_engine(f, self.engine)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/parsers/readers.py", line 1735, in _make_engine
    self.handles = get_handle(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/pandas/io/common.py", line 856, in get_handle
    handle = open(
OSError: [Errno 24] Too many open files: 'data/history/raw/1m/TAO-USDT.csv'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connection.py", line 204, in _new_conn
    sock = connection.create_connection(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/util/connection.py", line 60, in create_connection
    for res in socket.getaddrinfo(host, port, family, socket.SOCK_STREAM):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/socket.py", line 955, in getaddrinfo
    for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
socket.gaierror: [Errno 8] nodename nor servname provided, or not known

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 787, in urlopen
    response = self._make_request(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 488, in _make_request
    raise new_e
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 464, in _make_request
    self._validate_conn(conn)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 1093, in _validate_conn
    conn.connect()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connection.py", line 759, in connect
    self.sock = sock = self._new_conn()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connection.py", line 211, in _new_conn
    raise NameResolutionError(self.host, self, e) from e
urllib3.exceptions.NameResolutionError: HTTPSConnection(host='open-api-vst.bingx.com', port=443): Failed to resolve 'open-api-vst.bingx.com' ([Errno 8] nodename nor servname provided, or not known)

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/adapters.py", line 644, in send
    resp = conn.urlopen(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/connectionpool.py", line 841, in urlopen
    retries = retries.increment(
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/urllib3/util/retry.py", line 519, in increment
    raise MaxRetryError(_pool, url, reason) from reason  # type: ignore[arg-type]
urllib3.exceptions.MaxRetryError: HTTPSConnectionPool(host='open-api-vst.bingx.com', port=443): Max retries exceeded with url: /openApi/spot/v1/public/exchangeInfo (Caused by NameResolutionError("HTTPSConnection(host='open-api-vst.bingx.com', port=443): Failed to resolve 'open-api-vst.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/adapters/bingx_adapter.py", line 715, in get_available_symbols
    response = self._make_request('GET', '/openApi/spot/v1/public/exchangeInfo', signed=False)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/adapters/bingx_adapter.py", line 297, in _make_request
    response = self.session.get(url, headers=headers, params=params, timeout=timeout)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/sessions.py", line 602, in get
    return self.request("GET", url, **kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/sessions.py", line 589, in request
    resp = self.send(prep, **send_kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/sessions.py", line 703, in send
    r = adapter.send(request, **kwargs)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/requests/adapters.py", line 677, in send
    raise ConnectionError(e, request=request)
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='open-api-vst.bingx.com', port=443): Max retries exceeded with url: /openApi/spot/v1/public/exchangeInfo (Caused by NameResolutionError("HTTPSConnection(host='open-api-vst.bingx.com', port=443): Failed to resolve 'open-api-vst.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))

2026-01-15 21:32:48,403 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from bingx
2026-01-15 21:32:48,403 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from bingx
2026-01-15 21:32:48,403 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from bingx
DEBUG:MultiBrokerExecutionService:Got 0 symbols from bingx
ERROR:root:Not connected to MEXC
2026-01-15 21:32:48,403 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from mexc
2026-01-15 21:32:48,403 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from mexc
2026-01-15 21:32:48,403 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from mexc
DEBUG:MultiBrokerExecutionService:Got 0 symbols from mexc
ERROR:root:Not connected to Phemex
2026-01-15 21:32:48,404 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from phemex
2026-01-15 21:32:48,404 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from phemex
2026-01-15 21:32:48,404 🐞DEBUG MultiBrokerExecutionService - Got 0 symbols from phemex
DEBUG:MultiBrokerExecutionService:Got 0 symbols from phemex
2026-01-15 21:32:48,405 🐞DEBUG EnhancedDataProvider - Symbol TAOUSDT not available on broker service
DEBUG:EnhancedDataProvider:Symbol TAOUSDT not available on broker service
2026-01-15 21:32:48,405 🐞DEBUG ImprovedDataCache - Cache MISS for multibroker_PRICE_TAOUSDT_tick
DEBUG:ImprovedDataCache:Cache MISS for multibroker_PRICE_TAOUSDT_tick
2026-01-15 21:32:48,406 🐞DEBUG EnhancedDataProvider - Fetching price for TAOUSDT using broker service: BrokerExecutionService
DEBUG:EnhancedDataProvider:Fetching price for TAOUSDT using broker service: BrokerExecutionService
2026-01-15 21:32:48,406 🐞DEBUG EnhancedDataProvider - Checking symbol TAOUSDT availability via broker service BrokerExecutionService
DEBUG:EnhancedDataProvider:Checking symbol TAOUSDT availability via broker service BrokerExecutionService
2026-01-15 21:32:48,406 🐞DEBUG EnhancedDataProvider - Symbol TAOUSDT not available on broker service
DEBUG:EnhancedDataProvider:Symbol TAOUSDT not available on broker service
2026-01-15 21:32:48,515 🐞DEBUG EnhancedDataProvider - Checking symbol availability for DOTUSDT, cache valid: True, cache size: 1585
DEBUG:EnhancedDataProvider:Checking symbol availability for DOTUSDT, cache valid: True, cache size: 1585
2026-01-15 21:32:48,515 🐞DEBUG EnhancedDataProvider - Symbol DOTUSDT found in valid cache
DEBUG:EnhancedDataProvider:Symbol DOTUSDT found in valid cache
2026-01-15 21:32:48,516 🐞DEBUG ImprovedDataCache - Cache MISS for multibroker_DOTUSDT_1m
DEBUG:ImprovedDataCache:Cache MISS for multibroker_DOTUSDT_1m
2026-01-15 21:32:48,516 ℹ️INFO ConfigurableHistoricalDataProvider - Fetching historical data for DOTUSDT from sources: ['binance', 'mexc', 'phemex', 'bingx']
INFO:ConfigurableHistoricalDataProvider:Fetching historical data for DOTUSDT from sources: ['binance', 'mexc', 'phemex', 'bingx']
2026-01-15 21:32:48,516 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for DOTUSDT from binance
DEBUG:ConfigurableHistoricalDataProvider:Attempting to fetch historical data for DOTUSDT from binance
2026-01-15 21:32:48,519 ❌ERROR ConfigurableHistoricalDataProvider - Error fetching historical data from Binance for DOTUSDT: HTTPSConnectionPool(host='api.binance.com', port=443): Max retries exceeded with url: /api/v3/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368516&endTime=1768509168516&limit=1000 (Caused by NameResolutionError("HTTPSConnection(host='api.binance.com', port=443): Failed to resolve 'api.binance.com' ([Errno 8] nodename nor servname provided, or not known)"))
ERROR:ConfigurableHistoricalDataProvider:Error fetching historical data from Binance for DOTUSDT: HTTPSConnectionPool(host='api.binance.com', port=443): Max retries exceeded with url: /api/v3/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368516&endTime=1768509168516&limit=1000 (Caused by NameResolutionError("HTTPSConnection(host='api.binance.com', port=443): Failed to resolve 'api.binance.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:48,519 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for DOTUSDT from binance: HTTPSConnectionPool(host='api.binance.com', port=443): Max retries exceeded with url: /api/v3/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368516&endTime=1768509168516&limit=1000 (Caused by NameResolutionError("HTTPSConnection(host='api.binance.com', port=443): Failed to resolve 'api.binance.com' ([Errno 8] nodename nor servname provided, or not known)"))
WARNING:ConfigurableHistoricalDataProvider:⚠️ Failed to fetch historical data for DOTUSDT from binance: HTTPSConnectionPool(host='api.binance.com', port=443): Max retries exceeded with url: /api/v3/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368516&endTime=1768509168516&limit=1000 (Caused by NameResolutionError("HTTPSConnection(host='api.binance.com', port=443): Failed to resolve 'api.binance.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:48,520 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for DOTUSDT from mexc
DEBUG:ConfigurableHistoricalDataProvider:Attempting to fetch historical data for DOTUSDT from mexc
2026-01-15 21:32:48,522 ❌ERROR ConfigurableHistoricalDataProvider - Error fetching historical data from MEXC for DOTUSDT: HTTPSConnectionPool(host='api.mexc.com', port=443): Max retries exceeded with url: /api/v3/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368520&endTime=1768509168520&limit=1000 (Caused by NameResolutionError("HTTPSConnection(host='api.mexc.com', port=443): Failed to resolve 'api.mexc.com' ([Errno 8] nodename nor servname provided, or not known)"))
ERROR:ConfigurableHistoricalDataProvider:Error fetching historical data from MEXC for DOTUSDT: HTTPSConnectionPool(host='api.mexc.com', port=443): Max retries exceeded with url: /api/v3/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368520&endTime=1768509168520&limit=1000 (Caused by NameResolutionError("HTTPSConnection(host='api.mexc.com', port=443): Failed to resolve 'api.mexc.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:48,522 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for DOTUSDT from mexc: HTTPSConnectionPool(host='api.mexc.com', port=443): Max retries exceeded with url: /api/v3/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368520&endTime=1768509168520&limit=1000 (Caused by NameResolutionError("HTTPSConnection(host='api.mexc.com', port=443): Failed to resolve 'api.mexc.com' ([Errno 8] nodename nor servname provided, or not known)"))
WARNING:ConfigurableHistoricalDataProvider:⚠️ Failed to fetch historical data for DOTUSDT from mexc: HTTPSConnectionPool(host='api.mexc.com', port=443): Max retries exceeded with url: /api/v3/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368520&endTime=1768509168520&limit=1000 (Caused by NameResolutionError("HTTPSConnection(host='api.mexc.com', port=443): Failed to resolve 'api.mexc.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:48,522 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for DOTUSDT from phemex
DEBUG:ConfigurableHistoricalDataProvider:Attempting to fetch historical data for DOTUSDT from phemex
2026-01-15 21:32:48,524 ❌ERROR ConfigurableHistoricalDataProvider - Error fetching historical data from Phemex for DOTUSDT: HTTPSConnectionPool(host='api.phemex.com', port=443): Max retries exceeded with url: /md/kline?symbol=DOTUSDT&resolution=1&from=1768507368&to=1768509168 (Caused by NameResolutionError("HTTPSConnection(host='api.phemex.com', port=443): Failed to resolve 'api.phemex.com' ([Errno 8] nodename nor servname provided, or not known)"))
ERROR:ConfigurableHistoricalDataProvider:Error fetching historical data from Phemex for DOTUSDT: HTTPSConnectionPool(host='api.phemex.com', port=443): Max retries exceeded with url: /md/kline?symbol=DOTUSDT&resolution=1&from=1768507368&to=1768509168 (Caused by NameResolutionError("HTTPSConnection(host='api.phemex.com', port=443): Failed to resolve 'api.phemex.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:48,525 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for DOTUSDT from phemex: HTTPSConnectionPool(host='api.phemex.com', port=443): Max retries exceeded with url: /md/kline?symbol=DOTUSDT&resolution=1&from=1768507368&to=1768509168 (Caused by NameResolutionError("HTTPSConnection(host='api.phemex.com', port=443): Failed to resolve 'api.phemex.com' ([Errno 8] nodename nor servname provided, or not known)"))
WARNING:ConfigurableHistoricalDataProvider:⚠️ Failed to fetch historical data for DOTUSDT from phemex: HTTPSConnectionPool(host='api.phemex.com', port=443): Max retries exceeded with url: /md/kline?symbol=DOTUSDT&resolution=1&from=1768507368&to=1768509168 (Caused by NameResolutionError("HTTPSConnection(host='api.phemex.com', port=443): Failed to resolve 'api.phemex.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:48,525 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for DOTUSDT from bingx
DEBUG:ConfigurableHistoricalDataProvider:Attempting to fetch historical data for DOTUSDT from bingx
2026-01-15 21:32:48,526 ❌ERROR ConfigurableHistoricalDataProvider - Error fetching historical data from BingX for DOTUSDT: HTTPSConnectionPool(host='open-api.bingx.com', port=443): Max retries exceeded with url: /openApi/quote/v1/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368525&endTime=1768509168525&limit=500 (Caused by NameResolutionError("HTTPSConnection(host='open-api.bingx.com', port=443): Failed to resolve 'open-api.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
ERROR:ConfigurableHistoricalDataProvider:Error fetching historical data from BingX for DOTUSDT: HTTPSConnectionPool(host='open-api.bingx.com', port=443): Max retries exceeded with url: /openApi/quote/v1/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368525&endTime=1768509168525&limit=500 (Caused by NameResolutionError("HTTPSConnection(host='open-api.bingx.com', port=443): Failed to resolve 'open-api.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:48,527 ⚠️WARNING ConfigurableHistoricalDataProvider - ⚠️ Failed to fetch historical data for DOTUSDT from bingx: HTTPSConnectionPool(host='open-api.bingx.com', port=443): Max retries exceeded with url: /openApi/quote/v1/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368525&endTime=1768509168525&limit=500 (Caused by NameResolutionError("HTTPSConnection(host='open-api.bingx.com', port=443): Failed to resolve 'open-api.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
WARNING:ConfigurableHistoricalDataProvider:⚠️ Failed to fetch historical data for DOTUSDT from bingx: HTTPSConnectionPool(host='open-api.bingx.com', port=443): Max retries exceeded with url: /openApi/quote/v1/klines?symbol=DOTUSDT&interval=1m&startTime=1768507368525&endTime=1768509168525&limit=500 (Caused by NameResolutionError("HTTPSConnection(host='open-api.bingx.com', port=443): Failed to resolve 'open-api.bingx.com' ([Errno 8] nodename nor servname provided, or not known)"))
2026-01-15 21:32:48,527 ❌ERROR ConfigurableHistoricalDataProvider - Failed to fetch historical data for DOTUSDT from any data source. Tried: ['binance', 'mexc', 'phemex', 'bingx']
ERROR:ConfigurableHistoricalDataProvider:Failed to fetch historical data for DOTUSDT from any data source. Tried: ['binance', 'mexc', 'phemex', 'bingx']
2026-01-15 21:32:48,527 🐞DEBUG EnhancedDataProvider - Could not fetch real historical data for DOTUSDT from configurable source: Failed to fetch historical data for DOTUSDT from any data source. Tried: ['binance', 'mexc', 'phemex', 'bingx']
DEBUG:EnhancedDataProvider:Could not fetch real historical data for DOTUSDT from configurable source: Failed to fetch historical data for DOTUSDT from any data source. Tried: ['binance', 'mexc', 'phemex', 'bingx']
2026-01-15 21:32:48,529 ⚠️WARNING HedgeFund - Connection error for DOTUSDT 1m, retrying in 1.58s (attempt 1/5)
WARNING:HedgeFund:Connection error for DOTUSDT 1m, retrying in 1.58s (attempt 1/5)
2026-01-15 21:32:50,114 ⚠️WARNING HedgeFund - Connection error for DOTUSDT 1m, retrying in 2.57s (attempt 2/5)
WARNING:HedgeFund:Connection error for DOTUSDT 1m, retrying in 2.57s (attempt 2/5)
2026-01-15 21:32:52,701 ⚠️WARNING HedgeFund - Connection error for DOTUSDT 1m, retrying in 4.82s (attempt 3/5)
WARNING:HedgeFund:Connection error for DOTUSDT 1m, retrying in 4.82s (attempt 3/5)
2026-01-15 21:32:57,521 ⚠️WARNING HedgeFund - Connection error for DOTUSDT 1m, retrying in 8.65s (attempt 4/5)
WARNING:HedgeFund:Connection error for DOTUSDT 1m, retrying in 8.65s (attempt 4/5)
2026-01-15 21:33:06,183 ❌ERROR HedgeFund - Connection error for DOTUSDT 1m after 5 attempts
ERROR:HedgeFund:Connection error for DOTUSDT 1m after 5 attempts
2026-01-15 21:33:06,184 ❌ERROR HedgeFund - Failed to download klines for DOTUSDT 1m after 5 attempts
ERROR:HedgeFund:Failed to download klines for DOTUSDT 1m after 5 attempts
2026-01-15 21:33:06,184 ❌ERROR EnhancedDataProvider - Error getting historical data for DOTUSDT: [Errno 24] Too many open files: 'data/history/raw/1m/DOT-USDT.csv'
ERROR:EnhancedDataProvider:Error getting historical data for DOTUSDT: [Errno 24] Too many open files: 'data/history/raw/1m/DOT-USDT.csv'
