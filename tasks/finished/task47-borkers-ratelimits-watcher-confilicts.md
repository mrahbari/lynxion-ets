I have a fundamental problem with the brokers.
> In some cases, I run into rate-limit issues.
> In some cases, a symbol does not exist on the Binance broker but does exist on BingX.
> I think the first step should be to fix and optimize these issues.
>
> In the downloader, we used a trick of switching between exchanges. 
> That means if a symbol is selected for download and it does not exist on the Binance broker (exchange), it automatically queries BingX, and then in order MaxC or phemex. Check readme.md file to understand the system deeply!
```
python runner_history_download.py --start 1d --end today --symbols FARTCOINUSDT
python runner_history_download.py --start 90d --end today --symbols TRUMPUSDT
python runner_history_download.py --start 90d --end today --symbols TRUMPUSDT --exchange bingx
```
> In my opinion, this should be implemented as a helper and used everywhere.
> So, do a thorough review of the current implementation and try to solve this problem.
> You are allowed to run the project multiple times so that you can analyze the logs and find the correct solution.



Below is my system flow.
The responsibility of each flow is clear in order to register an order symbol.
```
Watcher → Engine → Fusion → Strategy → Broker
```
Unfortunately, I also realized that there is a problem in this flow that has caused no orders to be placed.
I initially thought the issue was related to the confidence calculation, but it seems the problem is much more serious than that.

What I want from you:
- Carefully analyze the code to understand what has been implemented so far.
- You are allowed to modify the parts of the code that are causing issues.
- Explore the codebase structure to locate signal processing components
- In the downloader, we used a trick of switching between exchanges, use it in places that needed like downloader, for retune, sync , watchers etc. 
- Analyze the complete signal flow from detection to strategy selection 
- Identify why confidence with different score has not actual order placement when symbols are detected in different flows
- Review how the steps (flows) evaluation process works.
- Wouldn’t it be better to remove the mock provider entirely? There is no reason for watchers to evaluate unreliable data. Please analyze this carefully so that no issues are introduced into the system.
- Resolve the issue of No orders placed - No signals = no orders
- Resolve the issue of rate limits and take a look at logs sample for more clarification
- Refactor and make the infrastructure.brokers.adapters.bingx_adapter.BingXBrokerAdapter._format_symbol method clean, i guess a helper must be use for all exchanges as a resolver instead of hard code it!
- The system must be fully functional (Watcher → Engine → Fusion → Strategy → Broker), but without real market data, nothing happens.

I am running the trading system with:
```bash
python run_trading_system.py --mode production --auto-detect --comprehensive-logs
```

Sample of logs:
```
2025-12-30 09:04:32,990 🐞DEBUG EnhancedDataProvider - Got 0 available symbols from broker service, checking for QTUMUSDT
2025-12-30 09:04:32,990 🐞DEBUG EnhancedDataProvider - Symbol QTUMUSDT not found in broker service available symbols
2025-12-30 09:04:32,990 🐞DEBUG EnhancedDataProvider - Using fallback API call for symbol QTUMUSDT: https://api.binance.com/api/v3/ticker/price?symbol=QTUMUSDT
2025-12-30 09:04:33,370 🐞DEBUG EnhancedDataProvider - Direct API check for QTUMUSDT: Available
2025-12-30 09:04:33,798 ℹ️INFO HedgeFund - Successfully downloaded 30 klines for QTUMUSDT 1m
2025-12-30 09:04:33,800 ℹ️INFO EnhancedDataProvider - Fetched 30 historical data points from external source for QTUMUSDT
2025-12-30 09:04:33,800 ℹ️INFO EnhancedDataProvider - Successfully fetched 30 real historical data points for QTUMUSDT from external source
2025-12-30 09:04:33,906 🐞DEBUG EnhancedDataProvider - Checking symbol availability for ONTUSDT, cache valid: True, cache size: 0
2025-12-30 09:04:33,907 🐞DEBUG EnhancedDataProvider - Symbol ONTUSDT not found in valid cache (cache size: 0)
2025-12-30 09:04:33,907 🐞DEBUG EnhancedDataProvider - Checking symbol ONTUSDT using broker service: BrokerExecutionService
2025-12-30 09:04:33,907 🐞DEBUG EnhancedDataProvider - Broker service BrokerExecutionService has get_available_symbols method
2025-12-30 09:04:34,924 🐞DEBUG EnhancedDataProvider - Got 0 available symbols from broker service, checking for ONTUSDT
2025-12-30 09:04:34,924 🐞DEBUG EnhancedDataProvider - Symbol ONTUSDT not found in broker service available symbols
2025-12-30 09:04:34,924 🐞DEBUG EnhancedDataProvider - Using fallback API call for symbol ONTUSDT: https://api.binance.com/api/v3/ticker/price?symbol=ONTUSDT
2025-12-30 09:04:35,334 🐞DEBUG EnhancedDataProvider - Direct API check for ONTUSDT: Available
2025-12-30 09:04:35,846 ℹ️INFO HedgeFund - Successfully downloaded 30 klines for ONTUSDT 1m
2025-12-30 09:04:35,848 ℹ️INFO EnhancedDataProvider - Fetched 30 historical data points from external source for ONTUSDT
2025-12-30 09:04:35,848 ℹ️INFO EnhancedDataProvider - Successfully fetched 30 real historical data points for ONTUSDT from external source

```