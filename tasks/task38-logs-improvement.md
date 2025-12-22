Currently i see the below logs lets call it A, but in reallity i eager to see completly isolated logs of displaing symbls like B 
I mean separate section for each of them not mixed like A. 
can you fix it? 
Also for this stage, i'm interested to improve the logs in each flow (Watcher → Engine → Fusion → Strategy → Broker) to make it more clear to me what happens in each step. i mean for example 
HYPEUSDT accepted by Engine, passed to Fusion, pssed to Strategy, rejected by BreakoutStrategy becuase of ...  
HYPEUSDT accepted by Engine, rejected by Fusion becuase of ...  
You are allowed to imporve it as much as possible to make it clear, readable, standard and advanced... 




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