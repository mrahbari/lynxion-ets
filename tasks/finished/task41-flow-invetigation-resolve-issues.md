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

I am running the trading system with:
```bash
python run_trading_system.py --mode production --auto-detect --comprehensive-logs
```

You are allowed to improve it as much as possible to make it clear, readable, standard and advanced...
   1. Clear Flow Logs: Each flow activity is good to display in logs for debugging purpose.
   2. Clear Flow Tracking: Complete flow from Watcher → Engine → Fusion → Strategy → Broker
   3. Enhanced Visibility: Detailed reasons for each decision at every step
   4. Backward Compatibility: Existing logging functionality preserved

Finally, 
Try to place orders via system flow 
```
Watcher → Engine → Fusion → Strategy → Broker
```