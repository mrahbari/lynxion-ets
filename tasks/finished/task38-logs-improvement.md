Currently, i see the below logs lets call it A, but in reality i eager to see logs like B 
I mean separate section for each of them not mixed like A. 
can you fix it? 
Also for this stage, I'm interested to improve the logs in each flow (Watcher → Engine → Fusion → Strategy → Broker) to make it more clear to me what happens in each step. i mean for example 
HYPEUSDT accepted by Engine, passed to Fusion, passed to Strategy, rejected by BreakoutStrategy because of ...  
HYPEUSDT accepted by Engine, rejected by Fusion because of ...  
You are allowed to improve it as much as possible to make it clear, readable, standard and advanced... 

   1. clear flow Logs: Each flow activity is good to display in logs for debugging purpose.
   2. Clear Flow Tracking: Complete flow from Watcher → Engine → Fusion → Strategy → Broker
   3. Enhanced Visibility: Detailed reasons for each decision at every step
   4. Backward Compatibility: Existing logging functionality preserved


A: 
2025-12-22 12:31:18,105 - INFO - MarketOpportunityWatcher - ✅ Auto-discovered 23 symbols to monitor: ['BATUSDT', 'PAXGUSDT', 'BTCUSDT', 'ICXUSDT', 'TAOUSDT', 'ETHUSDT', 'WBTCUSDT', 'ZECUSDT', 'LEOUSDT', 'ONTUSDT', 'FETUSDT', 'XMRUSDT', 'HYPEUSDT', 'IOSTUSDT', 'AAVEUSDT', 'TRXUSDT', 'XLMUSDT', 'BCHUSDT', 'TOMOUSDT', 'THETAUSDT', 'BNBUSDT', 'GTOUSDT', 'LTCUSDT']
2025-12-22 12:31:18,105 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: BATUSDT
2025-12-22 12:31:18,105 - INFO - HedgeFund - Started watcher: Volatility for symbol: BATUSDT
2025-12-22 12:31:18,105 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: PAXGUSDT
2025-12-22 12:31:18,106 - INFO - HedgeFund - Started watcher: Volatility for symbol: PAXGUSDT
2025-12-22 12:31:18,106 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: BTCUSDT
2025-12-22 12:31:18,106 - INFO - HedgeFund - Started watcher: Volatility for symbol: BTCUSDT
2025-12-22 12:31:18,106 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: ICXUSDT
2025-12-22 12:31:18,106 - INFO - HedgeFund - Started watcher: Volatility for symbol: ICXUSDT
2025-12-22 12:31:18,106 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: TAOUSDT
2025-12-22 12:31:18,106 - INFO - HedgeFund - Started watcher: Volatility for symbol: TAOUSDT
2025-12-22 12:31:18,107 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: ETHUSDT
2025-12-22 12:31:18,107 - INFO - HedgeFund - Started watcher: Volatility for symbol: ETHUSDT
2025-12-22 12:31:18,107 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: WBTCUSDT
2025-12-22 12:31:18,107 - INFO - HedgeFund - Started watcher: Volatility for symbol: WBTCUSDT
2025-12-22 12:31:18,107 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: ZECUSDT
2025-12-22 12:31:18,107 - INFO - HedgeFund - Started watcher: Volatility for symbol: ZECUSDT
2025-12-22 12:31:18,107 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: LEOUSDT
2025-12-22 12:31:18,108 - INFO - HedgeFund - Started watcher: Volatility for symbol: LEOUSDT
2025-12-22 12:31:18,108 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: ONTUSDT
2025-12-22 12:31:18,108 - INFO - HedgeFund - Started watcher: Volatility for symbol: ONTUSDT
2025-12-22 12:31:18,108 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: FETUSDT



B:
2025-12-22 00:34:15,172 - INFO - MarketOpportunityWatcher - ✅ Auto-discovered 13 symbols to monitor: ['HYPEUSDT', 'ZECUSDT', 'TRXUSDT', 'WBTCUSDT', 'LTCUSDT', 'XLMUSDT', 'LEOUSDT', 'PAXGUSDT', 'BTCUSDT', 'BNBUSDT', 'ETHUSDT', 'XMRUSDT', 'AAVEUSDT']
2025-12-22 00:34:15,173 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: HYPEUSDT
2025-12-22 00:34:15,173 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: ZECUSDT
2025-12-22 00:34:15,173 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: TRXUSDT
2025-12-22 00:34:15,173 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: WBTCUSDT
2025-12-22 00:34:15,173 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: LTCUSDT
2025-12-22 00:34:15,173 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: XLMUSDT
2025-12-22 00:34:15,173 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: LEOUSDT
2025-12-22 00:34:15,174 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: PAXGUSDT
2025-12-22 00:34:15,174 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: BTCUSDT
2025-12-22 00:34:15,174 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: BNBUSDT
2025-12-22 00:34:15,174 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: ETHUSDT
2025-12-22 00:34:15,174 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: XMRUSDT
2025-12-22 00:34:15,174 - INFO - HedgeFund - Started watcher: MarketPulse for symbol: AAVEUSDT
2025-12-22 00:34:15,175 - INFO - MarketOpportunityWatcher - 🔍 Discovering symbols to monitor automatically...
2025-12-22 00:34:15,175 - INFO - MarketOpportunityWatcher - 🔍 Discovering symbols to monitor automatically...
2025-12-22 00:34:19,038 - INFO - MarketOpportunityWatcher - ✅ Auto-discovered 10 symbols to monitor: ['VETUSDT', 'ZILUSDT', 'FETUSDT', 'BATUSDT', 'XMRUSDT', 'ZECUSDT', 'IOSTUSDT', 'DASHUSDT', 'THETAUSDT', 'GTOUSDT']
2025-12-22 00:34:19,038 - INFO - MarketOpportunityWatcher - ✅ Auto-discovered 10 symbols to monitor: ['VETUSDT', 'ZILUSDT', 'FETUSDT', 'BATUSDT', 'XMRUSDT', 'ZECUSDT', 'IOSTUSDT', 'DASHUSDT', 'THETAUSDT', 'GTOUSDT']
2025-12-22 00:34:19,038 - INFO - HedgeFund - Started watcher: Volatility for symbol: VETUSDT
2025-12-22 00:34:19,038 - INFO - HedgeFund - Started watcher: Volatility for symbol: ZILUSDT
2025-12-22 00:34:19,038 - INFO - HedgeFund - Started watcher: Volatility for symbol: FETUSDT
2025-12-22 00:34:19,038 - INFO - HedgeFund - Started watcher: Volatility for symbol: BATUSDT
2025-12-22 00:34:19,039 - INFO - HedgeFund - Started watcher: Volatility for symbol: XMRUSDT
2025-12-22 00:34:19,039 - INFO - HedgeFund - Started watcher: Volatility for symbol: ZECUSDT
2025-12-22 00:34:19,039 - INFO - HedgeFund - Started watcher: Volatility for symbol: IOSTUSDT
2025-12-22 00:34:19,039 - INFO - HedgeFund - Started watcher: Volatility for symbol: DASHUSDT
2025-12-22 00:34:19,039 - INFO - HedgeFund - Started watcher: Volatility for symbol: THETAUSDT
2025-12-22 00:34:19,039 - INFO - HedgeFund - Started watcher: Volatility for symbol: GTOUSDT



for example in need to see the details for the below sections : 

python run_trading_system.py --mode production --auto-detect
/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/site-packages/hyperopt/atpe.py:19: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  import pkg_resources
🚀 Starting Trading System in production mode...
🚀 Starting auto-detection mode...
📊 System will automatically discover and monitor market opportunities across multiple symbol


2025-12-22 19:29:56,302 ℹ️INFO AutoDetectionOrchestrator - 🤖 Starting auto-detection mode...
2025-12-22 19:29:56,302 ℹ️INFO AutoDetectionOrchestrator - 🚀 Initializing Auto-Detection Orchestrator...
2025-12-22 19:29:56,302 ℹ️INFO MarketOpportunityWatcher - 🔄 Market opportunity monitoring loop started
2025-12-22 19:29:56,302 ℹ️INFO MarketOpportunityWatcher - 🤖 AUTO-DETECTION STATUS: Monitoring 22 symbols | Active strategies: 0 | Opportunities: 0 | symbols_monitored=22 | active_strategies=0 | opportunities_found=0
2025-12-22 19:29:56,303 ℹ️INFO AutoDetectionOrchestrator - 🔄 Opportunity processing loop started
2025-12-22 19:29:56,303 ℹ️INFO AutoDetectionOrchestrator - 🛡️ Risk monitoring started
2025-12-22 19:29:56,303 ℹ️INFO AutoDetectionOrchestrator - ⚙️ Started 2 background services
2025-12-22 19:29:56,304 ℹ️INFO AutoDetectionOrchestrator - ✅ Auto-Detection Orchestrator initialized successfully