Below is my system flow.
The responsibility of each flow is clear in order to register an order symbol.
```
Watcher → Engine → Fusion → Strategy → Broker
```
Unfortunately, I realized that there is a problem in this flow that has caused no orders to be placed at all.
I initially thought the issue was related to the confidence calculation, but it seems the problem is much more serious than that.

What I want from you:
- Carefully analyze the code to understand what has been implemented so far.
- Then run the project and see if you can identify the problem from the logs.
- You are allowed to modify the parts of the code that are causing issues.
- Explore the codebase structure to locate signal processing components
- Find and examine the MarketOpportunityWatcher and related components
- Locate confidence calculation logic
- Analyze the complete signal flow from detection to strategy selection 
- Identify why confidence remains 0.00% when symbols are detected 
- Implement fixes and enhanced logging for better traceability 
- Review how the watcher evaluation process works.
- Why is historical data needed? Is it because we want to avoid rate-limit issues and make the system respond faster?
- What happens if the historical data is not up to date?
- Wouldn’t it be better to remove the mock provider entirely? There is no reason for watchers to evaluate unreliable data. Please analyze this carefully so that no issues are introduced into the system.
- Resolve the issue of No orders placed - No signals = no orders
- The system must be fully functional (Watcher → Engine → Fusion → Strategy → Broker), but without real market data, nothing happens.

I am running the trading system with:
```bash
python run_trading_system.py --mode production --auto-detect --comprehensive-logs
```

You are allowed to improve it as much as possible to make it clear, readable, standard and advanced...
   1. Clear Flow Logs: Each flow activity is good to display in logs for debugging purpose.
   2. Clear Flow Tracking: Complete flow from Watcher → Engine → Fusion → Strategy → Broker
   3. Enhanced Visibility: Detailed reasons for each decision at every step
   4. Backward Compatibility: Existing logging functionality preserved

---
Description:

I ran into some confusion. Why, in general, do my watchers have to use `MockDataProviderAdapter`?

What was the major issue:
we need to connect to a real market data provider instead of using the mock data provider. 
The system is working correctly with all watchers active, but it's using mock data that doesn't contain actual market information for the symbols being monitored.
This means the watchers are not getting real market data to analyze, which explains why there are no trading signals being generated. 
The watchers need actual market data to build up their histories before they can generate signals.


We use watchers to find symbols with high potential.
My question is: why do we generally need to check the historical data of these coins locally?
I mean the symbols that are stored with a 1-minute timeframe under `data/history/raw/1m`.

If these histories are not up to date, or do not exist at all, what happens to the system?

To improve the system, two new mock providers have been added:

* `infrastructure/data/enhanced_data_provider.py`
* `infrastructure/data/hybrid_data_provider.py`

I completely disagree with the implementations inside the methods `_get_minimal_data_for_symbol`, `_estimate_base_price_intelligently`, and `_calculate_price_by_market_category`, because in general there is no justification for hardcoding symbols, ranges, or similar things.
