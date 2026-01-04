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
- check the active and DEFAULT_BROKER=bingx which is incorrect in processing the flows.
- Resolve the active broker selection and investigate to find the reason of "UnknownBroker", it seems showing up because the execution service the active and DEFAULT_BROKER=bingx which is incorrect in processing the flows.
- You are allowed to modify the parts of the code that are causing issues.
- Explore the codebase structure to locate signal processing components
- Find and examine the MarketOpportunityWatcher and related components
- Locate confidence calculation logic
- Analyze the complete signal flow from detection to strategy selection, Review how the steps (flows) evaluation process works.
- Identify why confidence with high score has not actual order placement when symbols are detected in different flows
- Why is historical data needed? Is it because we want to avoid rate-limit issues and make the system respond faster?
- What happens if the historical data is not up-to-date?
- Would’t it be better to remove the mock provider entirely? There is no reason for watchers to evaluate unreliable data. Please analyze this carefully so that no issues are introduced into the system.
- Resolve the issue of No orders placed - No signals = no orders
- The real issue is that the system is generating HOLD signals instead of BUY/SELL signals. check the watchers deeply for this issue!
- The system must be fully functional (Watcher → Engine → Fusion → Strategy → Broker), but without real market data, nothing happens.

I am running the trading system with:
```bash
python run_trading_system.py --mode production --auto-detect --comprehensive-logs
```


I’ve run into some ambiguities.

Why, in general, should my watchers use `MockDataProviderAdapter`?
We use watchers to find symbols with high potential.

My question is: why do we generally need to check the historical data of these coins locally?
I mean the symbols whose 1-minute timeframe data is stored at `data/history/raw/1m`.

What happens to the system if these histories are not up to date or do not exist at all?

To improve the system, two new mock providers have been added:

* `infrastructure/data/enhanced_data_provider.py`
* `infrastructure/data/hybrid_data_provider.py`

Overall, my request is this:

* Review how the watcher evaluation process works.
* Why is historical data needed? Is it because we want to avoid rate-limit issues and make the system respond faster?
* What happens if the historical data is not updated?
* Wouldn’t it be better to remove the mock provider entirely? There is no reason for watchers to evaluate unreliable data. Please analyze this carefully so that it does not cause problems for the system.

Another ambiguity I have is this:

1. I have different types of engines. How are they supposed to work?
   When a signal comes from a watcher, based on what rules or logic is an engine selected?
   Why do we even have multiple different engines, and is this actually an advantage of the system?

2. We have multiple different strategies.
   In general, based on what rules or criteria do we choose a strategy for final evaluation and for approving or rejecting a buy/sell trade?
   Are all strategies called to score a signal?
   Please also explain how this part of the system works.



---
The old Issue: 
Looking at the issue more carefully, I can see that the problem is in the MarketOpportunityWatcher. The watcher
  generates signals and processes them through the complete flow, but it doesn't actually execute the trades. The
  execution should happen in the orchestrator, but the watcher is not properly connected to the execution service.

  The issue is that the watcher processes signals and logs the complete flow, but the actual order execution is
  missing. Let me look at the historical data usage and MockDataProvider issues:

  The MarketOpportunityWatcher uses historical data to initialize watcher histories, but it's using mock data
  which may not be reliable for actual trading decisions. The issue is that the watchers are using
  MockDataProviderAdapter which provides unreliable data for decision making.



Verify that: 
1. Watcher generates signals: The MarketOpportunityWatcher analyzes symbols and generates signals
2. Engine processes signals: The SignalValidator processes signals through the engine
3. Fusion processes signals: The SignalFusionService fuses multiple signals
4. Strategy selection: The appropriate strategy is selected
5. Broker execution: When confidence > 60%, the _execute_signal_trade method places actual orders through the broker




The "UnknownBroker" is showing up because the execution service is being passed properly now, but the broker name
  detection logic is working. The real issue is that the system is generating HOLD signals instead of BUY/SELL
  signals, which is actually correct behavior - HOLD signals mean "don't trade" which is appropriate when the
  algorithms don't see clear opportunities.

  The system is working correctly. When BUY or SELL signals with confidence > 60% are generated, they will result
  in actual order placement. The fact that you're seeing only HOLD signals suggests that the current market
  conditions don't meet the criteria for BUY or SELL signals, which is a conservative and safe approach.


--- ✦ Based on my analysis, I can see the main issues:

   1. The broker selection issue: The system is using DEFAULT_BROKER=bingx but the broker might not be properly
      configured or available.
   2. The MockDataProvider issue: Watchers are using mock data which may not generate real trading signals.
   3. The signal flow: The system might be generating HOLD signals instead of BUY/SELL signals.

  Let me look at the issue more closely. The problem seems to be that the broker execution service is being
  created but the watchers might not be properly connected to execute trades. Let me check the
  _execute_signal_trade method in the MarketOpportunityWatcher:

  Looking at the code, I can see that the _execute_signal_trade method is being called when a signal has
  confidence > 0.6, but there might be an issue with the broker configuration. Let me examine the issue more
  closely:

  The problem is that the DEFAULT_BROKER=bingx is set in the environment, but the system might not have proper API
  keys for BingX, or the broker might not be properly initialized. Let me check the broker execution service again
  and identify the fixes needed:

   1. First, I need to fix the broker selection issue
   2. Then, I need to ensure the watchers are properly generating BUY/SELL signals instead of HOLD signals
   3. Finally, I need to ensure the execution flow is working properly

---


 Now I need to look at the watchers to understand why they might be generating HOLD signals instead of BUY/SELL
  signals. Let me check the watcher analysis logic:

  Looking at the MarketOpportunityWatcher code, I can see that the issue might be in how signals are processed.
  The watchers need to generate BUY or SELL signals with sufficient confidence for trades to be executed. Let me
  look at the signal processing more closely and fix the issue where signals might not be reaching the execution
  stage properly:
  

