

First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md

- Check my observations that I shared below as a sample of logs!

There are lots of strange issues which i confused! so track a symbol like  NEOUSDT and find out what happened?
- check the ./logs/* deeply as well
- remember, we still have problem with order placement!
- New Resource Issue: The system is now creating too many resources (threads, file handles) which causes "Too many open files" error.
- make sure The system properly handles execution intents without generating multiple duplicate rejections.
- The "Too many open files" error is a resource exhaustion issue. The system is creating multiple broker instances and data providers, which is consuming too
  many file descriptors.

  
-----
## 1- Wrong Messages: DUPLICATE REJECTED . there's no active or booked ETHUSDT in my account.This 
```
INFO:BrokerExecutionService:🎯 EXECUTING ORDER ON MultiBroker: Order(symbol=Symbol(value='ETHUSDT'), side=<OrderSide.SELL: 'SELL'>, quantity=Decimal('0.0012197055630770732'), price=Money(amount=Decimal('3279.48'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 673888), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='ETHUSDT'), strategy_name='balanced_strategy', side=<OrderSide.SELL: 'SELL'>, intent_confidence=Percentage(value=Decimal('0.48')), risk_parameters={'max_position_size': 0.06334172174675397, 'stop_loss_pct': 0.024, 'take_profit_pct': 0.0264, 'stop_loss_price': 2502.5, 'take_profit_price': 2434.0, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 0.25336688698701587, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=0.6, position_size_multiplier=1.2, stop_loss_multiplier=1.2, take_profit_multiplier=0.88)}, timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 673888), fused_signal=FusedSignal(symbol=Symbol(value='ETHUSDT'), dominant_bias=<SignalType.NEUTRAL: 'NEUTRAL'>, direction=0.0, dominance_score=0.18, regime_context='stable', confidence=Percentage(value=Decimal('0.6')), timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 602676), metadata={'short_trend': {'direction': 0.0001287457539831966, 'strength': 1.290320991100469e-05}, 'medium_trend': {'direction': 0.00010737387730229672, 'strength': 2.5582713343485562e-05}, 'long_trend': {'direction': 1.1315122951000447e-05, 'strength': 1.6329295936724867e-07}, 'overall_trend_score': 6.361887546282856e-05, 'trend_alignment': 1.0, 'trend_source': 'TrendMTF', 'price_history_length': 31}), metadata={'strategy_reasoning': 'Signal aligned with balanced_strategy strategy criteria', 'dominant_bias': 'NEUTRAL', 'regime_context': 'stable'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('3358.18752'), currency='USDT'), take_profit_price=Money(amount=Decimal('2434.0'), currency='USDT'))
WARNING:root:Binance spot trading doesn't have positions. Only futures positions are available.
WARNING:root:MEXC spot trading doesn't have positions. Only futures positions are available.
ERROR:root:Not connected to Phemex
2026-01-16 18:34:13,492 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:13,492 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:13,492 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
INFO:MultiBrokerExecutionService:❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:13,492 ❌ERROR BrokerExecutionService - ❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
2026-01-16 18:34:13,492 ❌ERROR BrokerExecutionService - ❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
ERROR:BrokerExecutionService:❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
2026-01-16 18:34:13,493 ℹ️INFO ArchitectureOrchestrator - Executed order with ID: None
INFO:ArchitectureOrchestrator:Executed order with ID: None
2026-01-16 18:34:13,544 ℹ️INFO ArchitectureOrchestrator - 📥 RECEIVED EXECUTION INTENT: Processing execution intent from SignalAggregator for ETHUSDT with confidence 48.00%
INFO:ArchitectureOrchestrator:📥 RECEIVED EXECUTION INTENT: Processing execution intent from SignalAggregator for ETHUSDT with confidence 48.00%

```

### 2-Executed order with ID: None issue: do the order placement directly and after that via flow to ensure all is sorted out!!!!!!! 
```
2026-01-16 18:34:17,502 ℹ️INFO BrokerExecutionService - 🎯 EXECUTING ORDER ON MultiBroker: Order(symbol=Symbol(value='ETHUSDT'), side=<OrderSide.SELL: 'SELL'>, quantity=Decimal('0.0012197055630770732'), price=Money(amount=Decimal('3279.48'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 673888), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='ETHUSDT'), strategy_name='balanced_strategy', side=<OrderSide.SELL: 'SELL'>, intent_confidence=Percentage(value=Decimal('0.48')), risk_parameters={'max_position_size': 0.06334172174675397, 'stop_loss_pct': 0.024, 'take_profit_pct': 0.0264, 'stop_loss_price': 2502.5, 'take_profit_price': 2434.0, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 0.25336688698701587, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=0.6, position_size_multiplier=1.2, stop_loss_multiplier=1.2, take_profit_multiplier=0.88)}, timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 673888), fused_signal=FusedSignal(symbol=Symbol(value='ETHUSDT'), dominant_bias=<SignalType.NEUTRAL: 'NEUTRAL'>, direction=0.0, dominance_score=0.18, regime_context='stable', confidence=Percentage(value=Decimal('0.6')), timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 602676), metadata={'short_trend': {'direction': 0.0001287457539831966, 'strength': 1.290320991100469e-05}, 'medium_trend': {'direction': 0.00010737387730229672, 'strength': 2.5582713343485562e-05}, 'long_trend': {'direction': 1.1315122951000447e-05, 'strength': 1.6329295936724867e-07}, 'overall_trend_score': 6.361887546282856e-05, 'trend_alignment': 1.0, 'trend_source': 'TrendMTF', 'price_history_length': 31}), metadata={'strategy_reasoning': 'Signal aligned with balanced_strategy strategy criteria', 'dominant_bias': 'NEUTRAL', 'regime_context': 'stable'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('3358.18752'), currency='USDT'), take_profit_price=Money(amount=Decimal('2434.0'), currency='USDT'))
INFO:BrokerExecutionService:🎯 EXECUTING ORDER ON MultiBroker: Order(symbol=Symbol(value='ETHUSDT'), side=<OrderSide.SELL: 'SELL'>, quantity=Decimal('0.0012197055630770732'), price=Money(amount=Decimal('3279.48'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 673888), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='ETHUSDT'), strategy_name='balanced_strategy', side=<OrderSide.SELL: 'SELL'>, intent_confidence=Percentage(value=Decimal('0.48')), risk_parameters={'max_position_size': 0.06334172174675397, 'stop_loss_pct': 0.024, 'take_profit_pct': 0.0264, 'stop_loss_price': 2502.5, 'take_profit_price': 2434.0, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 0.25336688698701587, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=0.6, position_size_multiplier=1.2, stop_loss_multiplier=1.2, take_profit_multiplier=0.88)}, timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 673888), fused_signal=FusedSignal(symbol=Symbol(value='ETHUSDT'), dominant_bias=<SignalType.NEUTRAL: 'NEUTRAL'>, direction=0.0, dominance_score=0.18, regime_context='stable', confidence=Percentage(value=Decimal('0.6')), timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 602676), metadata={'short_trend': {'direction': 0.0001287457539831966, 'strength': 1.290320991100469e-05}, 'medium_trend': {'direction': 0.00010737387730229672, 'strength': 2.5582713343485562e-05}, 'long_trend': {'direction': 1.1315122951000447e-05, 'strength': 1.6329295936724867e-07}, 'overall_trend_score': 6.361887546282856e-05, 'trend_alignment': 1.0, 'trend_source': 'TrendMTF', 'price_history_length': 31}), metadata={'strategy_reasoning': 'Signal aligned with balanced_strategy strategy criteria', 'dominant_bias': 'NEUTRAL', 'regime_context': 'stable'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('3358.18752'), currency='USDT'), take_profit_price=Money(amount=Decimal('2434.0'), currency='USDT'))
WARNING:root:Binance spot trading doesn't have positions. Only futures positions are available.
WARNING:root:MEXC spot trading doesn't have positions. Only futures positions are available.
ERROR:root:Not connected to Phemex
2026-01-16 18:34:17,719 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:17,719 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:17,719 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
INFO:MultiBrokerExecutionService:❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:17,720 ❌ERROR BrokerExecutionService - ❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
2026-01-16 18:34:17,720 ❌ERROR BrokerExecutionService - ❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
ERROR:BrokerExecutionService:❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
2026-01-16 18:34:17,720 ℹ️INFO ArchitectureOrchestrator - Executed order with ID: None
INFO:ArchitectureOrchestrator:Executed order with ID: None
2026-01-16 18:34:17,762 ℹ️INFO AutoDetectionOrchestrator - 📥 RECEIVED EXECUTION INTENT: ETHUSDT | Side: SELL | Confidence: 48.00% | Score: 0.38 | Strategy: balanced_strategy
INFO:AutoDetectionOrchestrator:📥 RECEIVED EXECUTION INTENT: ETHUSDT | Side: SELL | Confidence: 48.00% | Score: 0.38 | Strategy: balanced_strategy
2026-01-16 18:34:17,762 ℹ️INFO AutoDetectionOrchestrator - DECISION REASON: Orchestrator | Symbol: ETHUSDT | Decision: Intent Processing Started | Reason: Received execution intent from strategy layer | Confidence: 48.00% | component=Orchestrator | symbol=ETHUSDT | decision=Intent Processing Started | reason=Received execution intent from strategy layer | confidence=0.48 | score=0.37801258262013093 | details={'strategy': 'balanced_strategy', 'side': 'SELL', 'regime_context': 'stable', 'dominant_bias': 'NEUTRAL', 'dominance_score': 0.18, 'opportunity_score': 0.37801258262013093}
INFO:AutoDetectionOrchestrator:DECISION REASON: Orchestrator | Symbol: ETHUSDT | Decision: Intent Processing Started | Reason: Received execution intent from strategy layer | Confidence: 48.00% | component=Orchestrator | symbol=ETHUSDT | decision=Intent Processing Started | reason=Received execution intent from strategy layer | confidence=0.48 | score=0.37801258262013093 | details={'strategy': 'balanced_strategy', 'side': 'SELL', 'regime_context': 'stable', 'dominant_bias': 'NEUTRAL', 'dominance_score': 0.18, 'opportunity_score': 0.37801258262013093}
2026-01-16 18:34:17,762 ℹ️INFO AutoDetectionOrchestrator - ❌ DUPLICATE REJECTED: Pending SELL order exists in shared tracker for ETHUSDT. Preventing duplicate same-direction intent. | Intent Confidence: 48.00%
INFO:AutoDetectionOrchestrator:❌ DUPLICATE REJECTED: Pending SELL order exists in shared tracker for ETHUSDT. Preventing duplicate same-direction intent. | Intent Confidence: 48.00%
2026-01-16 18:34:17,762 ℹ️INFO AutoDetectionOrchestrator - ❌ DUPLICATE INTENT REJECTED: ETHUSDT SELL | Intent Confidence: 48.00%
INFO:AutoDetectionOrchestrator:❌ DUPLICATE INTENT REJECTED: ETHUSDT SELL | Intent Confidence: 48.00%
```

### 3- the same issues for the rest LIKE DOGEUSDT
```
DEBUG:EnhancedDataProvider:Checking symbol availability for DOGEUSDT, cache valid: True, cache size: 1565
2026-01-16 18:34:22,213 🐞DEBUG EnhancedDataProvider - Symbol DOGEUSDT found in valid cache
DEBUG:EnhancedDataProvider:Symbol DOGEUSDT found in valid cache
2026-01-16 18:34:22,213 🐞DEBUG ImprovedDataCache - Cache EXPIRED for multibroker_DOGEUSDT_1m
DEBUG:ImprovedDataCache:Cache EXPIRED for multibroker_DOGEUSDT_1m
2026-01-16 18:34:22,213 🐞DEBUG ImprovedDataCache - Cache MISS for multibroker_DOGEUSDT_1m
DEBUG:ImprovedDataCache:Cache MISS for multibroker_DOGEUSDT_1m
2026-01-16 18:34:22,213 ℹ️INFO ConfigurableHistoricalDataProvider - Fetching historical data for DOGEUSDT from sources: ['binance', 'mexc', 'phemex', 'bingx']
INFO:ConfigurableHistoricalDataProvider:Fetching historical data for DOGEUSDT from sources: ['binance', 'mexc', 'phemex', 'bingx']
2026-01-16 18:34:22,214 🐞DEBUG ConfigurableHistoricalDataProvider - Attempting to fetch historical data for DOGEUSDT from binance
DEBUG:ConfigurableHistoricalDataProvider:Attempting to fetch historical data for DOGEUSDT from binance
WARNING:root:Binance spot trading doesn't have positions. Only futures positions are available.
WARNING:root:MEXC spot trading doesn't have positions. Only futures positions are available.
ERROR:root:Not connected to Phemex
2026-01-16 18:34:22,321 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:22,321 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:22,321 ℹ️INFO MultiBrokerExecutionService - ❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
INFO:MultiBrokerExecutionService:❌ DUPLICATE REJECTED: Pending SHORT order exists for ETHUSDT. Preventing duplicate same-direction trade.
2026-01-16 18:34:22,322 ❌ERROR BrokerExecutionService - ❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
2026-01-16 18:34:22,322 ❌ERROR BrokerExecutionService - ❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
ERROR:BrokerExecutionService:❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: None
2026-01-16 18:34:22,322 ℹ️INFO ArchitectureOrchestrator - Executed order with ID: None
INFO:ArchitectureOrchestrator:Executed order with ID: None
```


### 4- we reduce the confidence, what is the ree
```
) for ZILUSDT
INFO:ArchitectureOrchestrator:Processing observation from Watcher_anomaly_ml for HBARUSDT
2026-01-16 18:34:29,696 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $488.4731: SL=$488.9615, TP=$475.5774, ATR=$4.8847, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:29,664 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$325.51, Calculated size=0.4865, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:29,899 ℹ️INFO ArchitectureOrchestrator - Published interpreted signal: SELL for HBARUSDT
2026-01-16 18:34:29,681 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$416.58, Calculated size=0.3801, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:29,696 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $488.4731: SL=$488.9615, TP=$475.5774, ATR=$4.8847, SL_mult=2.40, TP_mult=2.64
INFO:Strategy_trend_following:REJECTED: Neutral signal (NEUTRAL) regardless of confidence (0.600) for ZILUSDT
INFO:AdvancedRiskManagementService:Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$325.51, Calculated size=0.4865, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
```

### 5- ZILUSDT symbole and rest, strange TP/SL and rejection reason
The below lines reapeat more than 400 lines? what is the reason! 
```
2026-01-16 18:34:30,398 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $116.6454: SL=$116.7621, TP=$113.5660, ATR=$1.1665, SL_mult=2.40, TP_mult=2.64
INFO:Strategy_mean_reversion:REJECTED: Neutral signal (NEUTRAL) regardless of confidence (0.600) for ZILUSDT
2026-01-16 18:34:30,186 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $416.5756: SL=$416.9922, TP=$405.5780, ATR=$4.1658, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,296 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$243.10, Calculated size=0.6514, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,398 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $116.6454: SL=$116.7621, TP=$113.5660, ATR=$1.1665, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,186 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $416.5756: SL=$416.9922, TP=$405.5780, ATR=$4.1658, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,296 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$243.10, Calculated size=0.6514, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,398 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $116.6454: SL=$116.7621, TP=$113.5660, ATR=$1.1665, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,410 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$272.12, Calculated size=0.5819, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,186 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $416.5756: SL=$416.9922, TP=$405.5780, ATR=$4.1658, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,296 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$243.10, Calculated size=0.6514, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,398 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $116.6454: SL=$116.7621, TP=$113.5660, ATR=$1.1665, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,410 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$272.12, Calculated size=0.5819, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,186 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $416.5756: SL=$416.9922, TP=$405.5780, ATR=$4.1658, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,296 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$243.10, Calculated size=0.6514, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,398 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $116.6454: SL=$116.7621, TP=$113.5660, ATR=$1.1665, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,186 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $416.5756: SL=$416.9922, TP=$405.5780, ATR=$4.1658, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,410 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$272.12, Calculated size=0.5819, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,296 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$243.10, Calculated size=0.6514, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,186 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $416.5756: SL=$416.9922, TP=$405.5780, ATR=$4.1658, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,398 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $116.6454: SL=$116.7621, TP=$113.5660, ATR=$1.1665, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,410 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$272.12, Calculated size=0.5819, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,296 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$243.10, Calculated size=0.6514, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,186 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $416.5756: SL=$416.9922, TP=$405.5780, ATR=$4.1658, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,410 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$272.12, Calculated size=0.5819, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,398 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $116.6454: SL=$116.7621, TP=$113.5660, ATR=$1.1665, SL_mult=2.40, TP_mult=2.64
2026-01-16 18:34:30,296 ℹ️INFO AdvancedRiskManagementService - Position sizing for ZILUSDT: Portfolio=$10000.00, Price=$243.10, Calculated size=0.6514, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-16 18:34:30,186 ℹ️INFO AdvancedRiskManagementService - SL/TP calculation for SHORT position at $416.5756: SL=$416.9922, TP=$405.5780, ATR=$4.1658, SL_mult=2.40, TP_mult=2.64
```


5- Use the below order requet in a simple script and make  sure broker 's working poroperly. check the reason of NEUTRL
```
2026-01-16 18:34:35,637 ℹ️INFO BrokerExecutionService - 🎯 EXECUTING ORDER ON MultiBroker: Order(symbol=Symbol(value='ETHUSDT'), side=<OrderSide.SELL: 'SELL'>, quantity=Decimal('0.001219954800674635'), price=Money(amount=Decimal('3278.81'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 774779), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='ETHUSDT'), strategy_name='balanced_strategy', side=<OrderSide.SELL: 'SELL'>, intent_confidence=Percentage(value=Decimal('0.40')), risk_parameters={'max_position_size': 0.04398730676857915, 'stop_loss_pct': 0.025, 'take_profit_pct': 0.0255, 'stop_loss_price': 2502.5, 'take_profit_price': 2436.25, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 0.1759492270743166, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=0.5, position_size_multiplier=1.0, stop_loss_multiplier=1.25, take_profit_multiplier=0.85)}, timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 774779), fused_signal=FusedSignal(symbol=Symbol(value='ETHUSDT'), dominant_bias=<SignalType.NEUTRAL: 'NEUTRAL'>, direction=0.0, dominance_score=0.125, regime_context='stable', confidence=Percentage(value=Decimal('0.5')), timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 606271), metadata={'anomaly_score': 0.006160383032582316, 'feature_vector': [-0.001067112211422369, 0.0010782776005173024, -0.00028926003134270356, -0.0007380749054532367, 0.0], 'feature_history_length': 30, 'price_history_length': 31, 'model_fitted': False, 'last_anomaly_timestamp': None, 'anomaly_source': 'AnomalyML', 'lookback_period': 50}), metadata={'strategy_reasoning': 'Signal aligned with balanced_strategy strategy criteria', 'dominant_bias': 'NEUTRAL', 'regime_context': 'stable'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('3360.78025'), currency='USDT'), take_profit_price=Money(amount=Decimal('2436.25'), currency='USDT'))
2026-01-16 18:34:35,637 ℹ️INFO BrokerExecutionService - 🎯 EXECUTING ORDER ON MultiBroker: Order(symbol=Symbol(value='ETHUSDT'), side=<OrderSide.SELL: 'SELL'>, quantity=Decimal('0.001219954800674635'), price=Money(amount=Decimal('3278.81'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 774779), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='ETHUSDT'), strategy_name='balanced_strategy', side=<OrderSide.SELL: 'SELL'>, intent_confidence=Percentage(value=Decimal('0.40')), risk_parameters={'max_position_size': 0.04398730676857915, 'stop_loss_pct': 0.025, 'take_profit_pct': 0.0255, 'stop_loss_price': 2502.5, 'take_profit_price': 2436.25, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 0.1759492270743166, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=0.5, position_size_multiplier=1.0, stop_loss_multiplier=1.25, take_profit_multiplier=0.85)}, timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 774779), fused_signal=FusedSignal(symbol=Symbol(value='ETHUSDT'), dominant_bias=<SignalType.NEUTRAL: 'NEUTRAL'>, direction=0.0, dominance_score=0.125, regime_context='stable', confidence=Percentage(value=Decimal('0.5')), timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 606271), metadata={'anomaly_score': 0.006160383032582316, 'feature_vector': [-0.001067112211422369, 0.0010782776005173024, -0.00028926003134270356, -0.0007380749054532367, 0.0], 'feature_history_length': 30, 'price_history_length': 31, 'model_fitted': False, 'last_anomaly_timestamp': None, 'anomaly_source': 'AnomalyML', 'lookback_period': 50}), metadata={'strategy_reasoning': 'Signal aligned with balanced_strategy strategy criteria', 'dominant_bias': 'NEUTRAL', 'regime_context': 'stable'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('3360.78025'), currency='USDT'), take_profit_price=Money(amount=Decimal('2436.25'), currency='USDT'))
INFO:BrokerExecutionService:🎯 EXECUTING ORDER ON MultiBroker: Order(symbol=Symbol(value='ETHUSDT'), side=<OrderSide.SELL: 'SELL'>, quantity=Decimal('0.001219954800674635'), price=Money(amount=Decimal('3278.81'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 774779), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='ETHUSDT'), strategy_name='balanced_strategy', side=<OrderSide.SELL: 'SELL'>, intent_confidence=Percentage(value=Decimal('0.40')), risk_parameters={'max_position_size': 0.04398730676857915, 'stop_loss_pct': 0.025, 'take_profit_pct': 0.0255, 'stop_loss_price': 2502.5, 'take_profit_price': 2436.25, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 0.1759492270743166, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=0.5, position_size_multiplier=1.0, stop_loss_multiplier=1.25, take_profit_multiplier=0.85)}, timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 774779), fused_signal=FusedSignal(symbol=Symbol(value='ETHUSDT'), dominant_bias=<SignalType.NEUTRAL: 'NEUTRAL'>, direction=0.0, dominance_score=0.125, regime_context='stable', confidence=Percentage(value=Decimal('0.5')), timestamp=datetime.datetime(2026, 1, 16, 18, 33, 48, 606271), metadata={'anomaly_score': 0.006160383032582316, 'feature_vector': [-0.001067112211422369, 0.0010782776005173024, -0.00028926003134270356, -0.0007380749054532367, 0.0], 'feature_history_length': 30, 'price_history_length': 31, 'model_fitted': False, 'last_anomaly_timestamp': None, 'anomaly_source': 'AnomalyML', 'lookback_period': 50}), metadata={'strategy_reasoning': 'Signal aligned with balanced_strategy strategy criteria', 'dominant_bias': 'NEUTRAL', 'regime_context': 'stable'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('3360.78025'), currency='USDT'), take_profit_price=Money(amount=Decimal('2436.25'), currency='USDT'))
2026-01-16 18:34:35,789 ℹ️INFO ConfigurableHistoricalDataProvider - ✅ Successfully fetched 30 historical data points for ZECUSDT from binance
```

### 6-Fix the below issue
```
TCUSDT
INFO:Strategy_volatility_breakout:ACCEPTED: High confidence (0.702) and non-neutral signal for LTCUSDT
2026-01-16 18:53:16,379 ℹ️INFO ArchitectureOrchestrator - Using fixed position size: $4.0 at $50000.0 = 8e-05 units
INFO:ArchitectureOrchestrator:Using fixed position size: $4.0 at $50000.0 = 8e-05 units
2026-01-16 18:53:16,379 ❌ERROR Strategy_volatility_breakout - Error calculating comprehensive risk parameters: [Errno 24] Too many open files, using basic parameters
ERROR:Strategy_volatility_breakout:Error calculating comprehensive risk parameters: [Errno 24] Too many open files, using basic parameters
2026-01-16 18:53:16,379 ℹ️INFO Strategy_volatility_breakout - Strategy volatility_breakout accepted fused signal for LTCUSDT with intent confidence 56.18%
2026-01-16 18:53:16,379 ❌ERROR ArchitectureOrchestrator - Error processing execution intent: [Errno 24] Too many open files
INFO:Strategy_volatility_breakout:Strategy volatility_breakout accepted fused signal for LTCUSDT with intent confidence 56.18%
ERROR:ArchitectureOrchestrator:Error processing execution intent: [Errno 24] Too many open files
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 119, in _perform_aggregation
    self._generate_execution_intent(fused_signal)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 240, in _generate_execution_intent
    self.logger.info(f"🎯 Generated execution intent for {execution_intent.symbol.value} "
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 131, in info
    self.logger.info(message)
Message: '🎯 Generated execution intent for LTCUSDT (SELL) with confidence 56.18%'
Arguments: ()
2026-01-16 18:53:16,380 ℹ️INFO SignalAggregator - 🎯 Generated execution intent for LTCUSDT (SELL) with confidence 56.18%
INFO:SignalAggregator:🎯 Generated execution intent for LTCUSDT (SELL) with confidence 56.18%
--- Logging error ---
2026-01-16 18:53:16,380 ❌ERROR ArchitectureOrchestrator - Traceback: Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/event_system.py", line 343, in _process_execution_intent
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/risk/advanced_risk_management.py", line 521, in __init__
    self.logger = EnhancedLogger("SLTPManager")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 98, in __init__
    self.logger = create_logger(name)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 42, in create_logger
    handler = RotatingFileHandler(log_file_path, maxBytes=1_000_000, backupCount=5)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 155, in __init__
    BaseRotatingHandler.__init__(self, filename, mode, encoding=encoding,
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 58, in __init__
    logging.FileHandler.__init__(self, filename, mode=mode,
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1152, in __init__
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/posixpath.py", line 384, in abspath
OSError: [Errno 24] Too many open files

ERROR:ArchitectureOrchestrator:Traceback: Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/event_system.py", line 343, in _process_execution_intent
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/risk/advanced_risk_management.py", line 521, in __init__
    self.logger = EnhancedLogger("SLTPManager")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 98, in __init__
    self.logger = create_logger(name)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 42, in create_logger
    handler = RotatingFileHandler(log_file_path, maxBytes=1_000_000, backupCount=5)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 155, in __init__
    BaseRotatingHandler.__init__(self, filename, mode, encoding=encoding,
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 58, in __init__
    logging.FileHandler.__init__(self, filename, mode=mode,
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1152, in __init__
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/posixpath.py", line 384, in abspath
OSError: [Errno 24] Too many open files

Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
2026-01-16 18:53:16,380 ℹ️INFO ArchitectureOrchestrator - 📥 RECEIVED EXECUTION INTENT: Processing execution intent from SignalAggregator for PAXGUSDT with confidence 56.96%
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 119, in _perform_aggregation
    self._generate_execution_intent(fused_signal)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 244, in _generate_execution_intent
    self.logger.log_decision_reason(
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 272, in log_decision_reason
    self.info(message,
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 129, in info
    self.logger.info(f"{message} | {context_str}")
Message: "DECISION REASON: SignalAggregator | Symbol: LTCUSDT | Decision: Execution Intent Generated | Reason: Signal passed strategy evaluation with confidence 56.18% | Confidence: 56.18% | component=SignalAggregator | symbol=LTCUSDT | decision=Execution Intent Generated | reason=Signal passed strategy evaluation with confidence 56.18% | confidence=0.5618271856473805 | details={'strategy': 'trend_following', 'side': 'SELL', 'regime_context': 'trending', 'dominant_bias': 'BUY', 'dominance_score': 0.4197856059020423}"
Arguments: ()
INFO:ArchitectureOrchestrator:📥 RECEIVED EXECUTION INTENT: Processing execution intent from SignalAggregator for PAXGUSDT with confidence 56.96%
```

### 7- Same issues and vital error (Too many files open error!)
```
2026-01-16 18:53:16,483 ℹ️INFO ArchitectureOrchestrator - 📥 RECEIVED EXECUTION INTENT: Processing execution intent from SignalAggregator for ZECUSDT with confidence 48.00%
INFO:ArchitectureOrchestrator:📥 RECEIVED EXECUTION INTENT: Processing execution intent from SignalAggregator for ZECUSDT with confidence 48.00%
2026-01-16 18:53:16,483 ℹ️INFO ArchitectureOrchestrator - Using execution service from architecture orchestrator for ZECUSDT
INFO:ArchitectureOrchestrator:Using execution service from architecture orchestrator for ZECUSDT
2026-01-16 18:53:16,495 ℹ️INFO ArchitectureOrchestrator - Using fixed position size: $4.0 at $50000.0 = 8e-05 units
INFO:ArchitectureOrchestrator:Using fixed position size: $4.0 at $50000.0 = 8e-05 units
2026-01-16 18:53:16,495 ❌ERROR ArchitectureOrchestrator - Error processing execution intent: [Errno 24] Too many open files
ERROR:ArchitectureOrchestrator:Error processing execution intent: [Errno 24] Too many open files
2026-01-16 18:53:16,495 ❌ERROR ArchitectureOrchestrator - Traceback: Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/event_system.py", line 343, in _process_execution_intent
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/risk/advanced_risk_management.py", line 521, in __init__
    self.logger = EnhancedLogger("SLTPManager")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 98, in __init__
    self.logger = create_logger(name)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 42, in create_logger
    handler = RotatingFileHandler(log_file_path, maxBytes=1_000_000, backupCount=5)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 155, in __init__
    BaseRotatingHandler.__init__(self, filename, mode, encoding=encoding,
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 58, in __init__
    logging.FileHandler.__init__(self, filename, mode=mode,
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1152, in __init__
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/posixpath.py", line 384, in abspath
OSError: [Errno 24] Too many open files

ERROR:ArchitectureOrchestrator:Traceback: Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/event_system.py", line 343, in _process_execution_intent
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/risk/advanced_risk_management.py", line 521, in __init__
    self.logger = EnhancedLogger("SLTPManager")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 98, in __init__
    self.logger = create_logger(name)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 42, in create_logger
    handler = RotatingFileHandler(log_file_path, maxBytes=1_000_000, backupCount=5)
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 155, in __init__
    BaseRotatingHandler.__init__(self, filename, mode, encoding=encoding,
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 58, in __init__
    logging.FileHandler.__init__(self, filename, mode=mode,
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1152, in __init__
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/posixpath.py", line 384, in abspath
OSError: [Errno 24] Too many open files

2026-01-16 18:53:16,496 ℹ️INFO AutoDetectionOrchestrator - 📥 RECEIVED EXECUTION INTENT: ZECUSDT | Side: SELL | Confidence: 48.00% | Score: 0.33 | Strategy: balanced_strategy
INFO:AutoDetectionOrchestrator:📥 RECEIVED EXECUTION INTENT: ZECUSDT | Side: SELL | Confidence: 48.00% | Score: 0.33 | Strategy: balanced_strategy
2026-01-16 18:53:16,496 ℹ️INFO AutoDetectionOrchestrator - DECISION REASON: Orchestrator | Symbol: ZECUSDT | Decision: Intent Processing Started | Reason: Received execution intent from strategy layer | Confidence: 48.00% | component=Orchestrator | symbol=ZECUSDT | decision=Intent Processing Started | reason=Received execution intent from strategy layer | confidence=0.48 | score=0.33159782608695654 | details={'strategy': 'balanced_strategy', 'side': 'SELL', 'regime_context': 'stable', 'dominant_bias': 'NEUTRAL', 'dominance_score': 0.18, 'opportunity_score': 0.33159782608695654}
INFO:AutoDetectionOrchestrator:DECISION REASON: Orchestrator | Symbol: ZECUSDT | Decision: Intent Processing Started | Reason: Received execution intent from strategy layer | Confidence: 48.00% | component=Orchestrator | symbol=ZECUSDT | decision=Intent Processing Started | reason=Received execution intent from strategy layer | confidence=0.48 | score=0.33159782608695654 | details={'strategy': 'balanced_strategy', 'side': 'SELL', 'regime_context': 'stable', 'dominant_bias': 'NEUTRAL', 'dominance_score': 0.18, 'opportunity_score': 0.33159782608695654}
202
```

8-Another and same issues
```
2026-01-16 18:53:16,532 ℹ️INFO Strategy_mean_reversion - Strategy mean_reversion accepted fused signal for IOTAUSDT with intent confidence 40.01%
INFO:Strategy_mean_reversion:Strategy mean_reversion accepted fused signal for IOTAUSDT with intent confidence 40.01%
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 109, in _perform_aggregation
    ranked_signals = self._rank_signals(signals_to_evaluate)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 126, in _rank_signals
    self.logger.debug(f"📊 Ranking {len(signals)} signals...")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 332, in debug
    self.logger.debug(message)
Message: '📊 Ranking 2 signals...'
Arguments: ()
2026-01-16 18:53:16,531 🐞DEBUG SignalAggregator - 📊 Ranking 2 signals...
DEBUG:SignalAggregator:📊 Ranking 2 signals...
--- Logging error ---
2026-01-16 18:53:16,533 ℹ️INFO Strategy_volatility_breakout - Strategy evaluation for IOTAUSDT: Confidence=0.500, Dominant Bias=SELL, Is Not Neutral=True, Dominance Score=0.125, Regime Context=weak_trend
INFO:Strategy_volatility_breakout:Strategy evaluation for IOTAUSDT: Confidence=0.500, Dominant Bias=SELL, Is Not Neutral=True, Dominance Score=0.125, Regime Context=weak_trend
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
2026-01-16 18:53:16,533 ℹ️INFO Strategy_volatility_breakout - ACCEPTED: Medium confidence (0.500) in favorable regime (weak_trend) for IOTAUSDT
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
INFO:Strategy_volatility_breakout:ACCEPTED: Medium confidence (0.500) in favorable regime (weak_trend) for IOTAUSDT
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/event_system.py", line 125, in _process_events
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/event_system.py", line 137, in _route_event
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 73, in _collect_fused_signal
    self.logger.debug(f"SignalAggregator Trigger Check: {len(self.collected_signals)}/{self.max_signals_to_evaluate} signals, {time_since_last:.2f}/{self.aggregation_window_seconds}s elapsed, should_trigger={should_trigger}")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 332, in debug
    self.logger.debug(message)
2026-01-16 18:53:16,533 ❌ERROR Strategy_volatility_breakout - Error calculating comprehensive risk parameters: [Errno 24] Too many open files, using basic parameters
Message: 'SignalAggregator Trigger Check: 1/1 signals, 0.00/1s elapsed, should_trigger=True'
Arguments: ()
2026-01-16 18:53:16,532 🐞DEBUG SignalAggregator - SignalAggregator Trigger Check: 1/1 signals, 0.00/1s elapsed, should_trigger=True
ERROR:Strategy_volatility_breakout:Error calculating comprehensive risk parameters: [Errno 24] Too many open files, using basic parameters
--- Logging error ---
DEBUG:SignalAggregator:SignalAggregator Trigger Check: 1/1 signals, 0.00/1s elapsed, should_trigger=True
2026-01-16 18:53:16,534 ℹ️INFO Strategy_volatility_breakout - Strategy volatility_breakout accepted fused signal for IOTAUSDT with intent confidence 40.01%
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
INFO:Strategy_volatility_breakout:Strategy volatility_breakout accepted fused signal for IOTAUSDT with intent confidence 40.01%
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 109, in _perform_aggregation
    ranked_signals = self._rank_signals(signals_to_evaluate)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 166, in _rank_signals
    self.logger.debug(f"📊 Signal ranking:")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 332, in debug
    self.logger.debug(message)
Message: '📊 Signal ranking:'
Arguments: ()
2026-01-16 18:53:16,533 🐞DEBUG SignalAggregator - 📊 Signal ranking:
DEBUG:SignalAggregator:📊 Signal ranking:
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/event_system.py", line 125, in _process_events
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/event_system.py", line 137, in _route_event
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 76, in _collect_fused_signal
    self.logger.info(f"🔄 Triggering aggregation: {len(self.collected_signals)} signals collected, {time_since_last:.2f}s since last aggregation")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 131, in info
    self.logger.info(message)
Message: '🔄 Triggering aggregation: 1 signals collected, 0.00s since last aggregation'
Arguments: ()
2026-01-16 18:53:16,534 ℹ️INFO SignalAggregator - 🔄 Triggering aggregation: 1 signals collected, 0.00s since last aggregation
INFO:SignalAggregator:🔄 Triggering aggregation: 1 signals collected, 0.00s since last aggregation
--- Logging error ---
Traceback (most recent call last):
2026-01-16 18:53:16,535 ℹ️INFO ArchitectureOrchestrator - Forwarding fused signal from FusionService for IOTAUSDT to aggregator
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
INFO:ArchitectureOrchestrator:Forwarding fused signal from FusionService for IOTAUSDT to aggregator
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
2026-01-16 18:53:16,535 ℹ️INFO ArchitectureOrchestrator - Forwarding fused signal from FusionService for IOTAUSDT to aggregator
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 119, in _perform_aggregation
    self._generate_execution_intent(fused_signal)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 240, in _generate_execution_intent
    self.logger.info(f"🎯 Generated execution intent for {execution_intent.symbol.value} "
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 131, in info
    self.logger.info(message)
INFO:ArchitectureOrchestrator:Forwarding fused signal from FusionService for IOTAUSDT to aggregator
Message: '🎯 Generated execution intent for IOTAUSDT (SELL) with confidence 40.01%'
Arguments: ()
2026-01-16 18:53:16,534 ℹ️INFO SignalAggregator - 🎯 Generated execution intent for IOTAUSDT (SELL) with confidence 40.01%
INFO:SignalAggregator:🎯 Generated execution intent for IOTAUSDT (SELL) with confidence 40.01%
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 109, in _perform_aggregation
    ranked_signals = self._rank_signals(signals_to_evaluate)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 169, in _rank_signals
    self.logger.debug(f"  {i+1}. {signal.symbol.value}: "
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 332, in debug
    self.logger.debug(message)
Message: '  1. IOTAUSDT: Score=0.498, Conf=50.01%, Dominance=0.13'
Arguments: ()
2026-01-16 18:53:16,534 🐞DEBUG SignalAggregator -   1. IOTAUSDT: Score=0.498, Conf=50.01%, Dominance=0.13
DEBUG:SignalAggregator:  1. IOTAUSDT: Score=0.498, Conf=50.01%, Dominance=0.13
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 90, in _perform_aggregation
    self.logger.debug(f"🔍 Starting _perform_aggregation method...")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 332, in debug
    self.logger.debug(message)
Message: '🔍 Starting _perform_aggregation method...'
Arguments: ()
2026-01-16 18:53:16,535 🐞DEBUG SignalAggregator - 🔍 Starting _perform_aggregation method...
DEBUG:SignalAggregator:🔍 Starting _perform_aggregation method...
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 95, in _perform_aggregation
    self.logger.debug(f"🔍 Inside lock: signals_to_evaluate has {len(signals_to_evaluate)} signals, collected_signals has {len(self.collected_signals)} signals")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 332, in debug
    self.logger.debug(message)
Message: '🔍 Inside lock: signals_to_evaluate has 1 signals, collected_signals has 1 signals'
Arguments: ()
2026-01-16 18:53:16,535 🐞DEBUG SignalAggregator - 🔍 Inside lock: signals_to_evaluate has 1 signals, collected_signals has 1 signals
DEBUG:SignalAggregator:🔍 Inside lock: signals_to_evaluate has 1 signals, collected_signals has 1 signals
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 119, in _perform_aggregation
    self._generate_execution_intent(fused_signal)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 244, in _generate_execution_intent
    self.logger.log_decision_reason(
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 272, in log_decision_reason
    self.info(message,
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 129, in info
    self.logger.info(f"{message} | {context_str}")
Message: "DECISION REASON: SignalAggregator | Symbol: IOTAUSDT | Decision: Execution Intent Generated | Reason: Signal passed strategy evaluation with confidence 40.01% | Confidence: 40.01% | component=SignalAggregator | symbol=IOTAUSDT | decision=Execution Intent Generated | reason=Signal passed strategy evaluation with confidence 40.01% | confidence=0.4000657318141981 | details={'strategy': 'trend_following', 'side': 'SELL', 'regime_context': 'weak_trend', 'dominant_bias': 'SELL', 'dominance_score': 0.12531121352243696}"
Arguments: ()
2026-01-16 18:53:16,536 ℹ️INFO SignalAggregator - DECISION REASON: SignalAggregator | Symbol: IOTAUSDT | Decision: Execution Intent Generated | Reason: Signal passed strategy evaluation with confidence 40.01% | Confidence: 40.01% | component=SignalAggregator | symbol=IOTAUSDT | decision=Execution Intent Generated | reason=Signal passed strategy evaluation with confidence 40.01% | confidence=0.4000657318141981 | details={'strategy': 'trend_following', 'side': 'SELL', 'regime_context': 'weak_trend', 'dominant_bias': 'SELL', 'dominance_score': 0.12531121352243696}
INFO:SignalAggregator:DECISION REASON: SignalAggregator | Symbol: IOTAUSDT | Decision: Execution Intent Generated | Reason: Signal passed strategy evaluation with confidence 40.01% | Confidence: 40.01% | component=SignalAggregator | symbol=IOTAUSDT | decision=Execution Intent Generated | reason=Signal passed strategy evaluation with confidence 40.01% | confidence=0.4000657318141981 | details={'strategy': 'trend_following', 'side': 'SELL', 'regime_context': 'weak_trend', 'dominant_bias': 'SELL', 'dominance_score': 0.12531121352243696}
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 109, in _perform_aggregation
    ranked_signals = self._rank_signals(signals_to_evaluate)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 169, in _rank_signals
    self.logger.debug(f"  {i+1}. {signal.symbol.value}: "
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 332, in debug
    self.logger.debug(message)
Message: '  2. IOTAUSDT: Score=0.498, Conf=50.01%, Dominance=0.13'
Arguments: ()
2026-01-16 18:53:16,536 🐞DEBUG SignalAggregator -   2. IOTAUSDT: Score=0.498, Conf=50.01%, Dominance=0.13
DEBUG:SignalAggregator:  2. IOTAUSDT: Score=0.498, Conf=50.01%, Dominance=0.13
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 100, in _perform_aggregation
    self.logger.debug(f"🔍 After clearing: signals_to_evaluate has {len(signals_to_evaluate)} signals, collected_signals has {len(self.collected_signals)} signals")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 332, in debug
    self.logger.debug(message)
Message: '🔍 After clearing: signals_to_evaluate has 1 signals, collected_signals has 0 signals'
Arguments: ()
2026-01-16 18:53:16,536 🐞DEBUG SignalAggregator - 🔍 After clearing: signals_to_evaluate has 1 signals, collected_signals has 0 signals
DEBUG:SignalAggregator:🔍 After clearing: signals_to_evaluate has 1 signals, collected_signals has 0 signals
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 119, in _perform_aggregation
    self._generate_execution_intent(fused_signal)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 266, in _generate_execution_intent
    self.logger.info(f"📤 Published execution intent for {execution_intent.symbol.value} "
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 131, in info
    self.logger.info(message)
Message: '📤 Published execution intent for IOTAUSDT (SELL) to event system'
Arguments: ()
2026-01-16 18:53:16,537 ℹ️INFO SignalAggregator - 📤 Published execution intent for IOTAUSDT (SELL) to event system
INFO:SignalAggregator:📤 Published execution intent for IOTAUSDT (SELL) to event system
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 1016, in _bootstrap_inner
    self.run()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 953, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 112, in _perform_aggregation
    selected_signals = self._select_best_signals(ranked_signals)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py", line 227, in _select_best_signals
    self.logger.info(f"✅ Selected {len(selected_signals)} signals for execution out of {len(ranked_signals)} evaluated")
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/logger.py", line 131, in info
    self.logger.info(message)
Message: '✅ Selected 1 signals for execution out of 2 evaluated'
Arguments: ()
2026-01-16 18:53:16,537 ℹ️INFO SignalAggregator - ✅ Selected 1 signals for execution out of 2 evaluated
INFO:SignalAggregator:✅ Selected 1 signals for execution out of 2 evaluated
--- Logging error ---
Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 73, in emit
    if self.shouldRollover(record):
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/handlers.py", line 194, in shouldRollover
    self.stream = self._open()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/logging/__init__.py", line 1201, in _open
OSError: [Errno 24] Too many open files: '/Users/mojtaba.rahbari/Sites/python/lynxion-ets/logs/system.log'
Call stack:
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/lib/python3.10/threading.py", line 973, in _bootstrap
    self._bootstrap_inner()
  File "/Users/mojtaba.rahbari/.pyenv/versions/3.10.13/l
```




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
Wrong Risk Management TP/SL:
```
INFO:Strategy_volatility_breakout:REJECTED: Neutral signal (NEUTRAL) regardless of confidence (0.600) for XRPUSDT
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1.10
2026-01-15 21:55:01,691 ℹ️INFO AdvancedRiskManagementService - Position sizing for XRPUSDT: Portfolio=$10000.00, Price=$10.00, Calculated size=15.8354, Value=$158.35, Factors: vol=1.00, corr=1.00, regime=1
```


find the reason for the below rejection:
```
, TP=$9.7360, ATR=$0.1000, SL_mult=2.40, TP_mult=2.64
INFO:AdvancedRiskManagementService:SL/TP calculation for SHORT position at $10.0000: SL=$10.1000, TP=$9.7360, ATR=$0.1000, SL_mult=2.40, TP_mult=2.64
2026-01-15 21:55:01,657 ℹ️INFO Strategy_trend_following - Calculated comprehensive risk parameters for XRPUSDT: Position size: 15.8354, SL%: 120.00%, TP%: 88.00%, Confidence: 60.00%
INFO:Strategy_trend_following:Calculated comprehensive risk parameters for XRPUSDT: Position size: 15.8354, SL%: 120.00%, TP%: 88.00%, Confidence: 60.00%
2026-01-15 21:55:01,657 ℹ️INFO Strategy_trend_following - Strategy trend_following accepted fused signal for XRPUSDT with intent confidence 48.00%
INFO:Strategy_trend_following:Strategy trend_following accepted fused signal for XRPUSDT with intent confidence 48.00%
2026-01-15 21:55:01,658 ℹ️INFO Strategy_mean_reversion - Strategy evaluation for XRPUSDT: Confidence=0.600, Dominant Bias=NEUTRAL, Is Not Neutral=False, Dominance Score=0.180, Regime Context=stable
INFO:Strategy_mean_reversion:Strategy evaluation for XRPUSDT: Confidence=0.600, Dominant Bias=NEUTRAL, Is Not Neutral=False, Dominance Score=0.180, Regime Context=stable
2026-01-15 21:55:01,658 ℹ️INFO Strategy_mean_reversion - REJECTED: Neutral signal (NEUTRAL) regardless of confidence (0.600) for XRPUSDT
```


Incorrect DUPLICATE REJECTED. which is not exists in bingx
```
2026-01-15 21:55:01,597 ℹ️INFO AutoDetectionOrchestrator - DECISION REASON: Orchestrator | Symbol: IOTAUSDT | Decision: Intent Processing Started | Reason: Received execution intent from strategy layer | Confidence: 75.94% | component=Orchestrator | symbol=IOTAUSDT | decision=Intent Processing Started | reason=Received execution intent from strategy layer | confidence=0.7593936263298837 | score=0.881654907482281 | details={'strategy': 'trend_following', 'side': 'BUY', 'regime_context': 'trending', 'dominant_bias': 'SELL', 'dominance_score': 0.8781924390437595, 'opportunity_score': 0.881654907482281}
INFO:AutoDetectionOrchestrator:DECISION REASON: Orchestrator | Symbol: IOTAUSDT | Decision: Intent Processing Started | Reason: Received execution intent from strategy layer | Confidence: 75.94% | component=Orchestrator | symbol=IOTAUSDT | decision=Intent Processing Started | reason=Received execution intent from strategy layer | confidence=0.7593936263298837 | score=0.881654907482281 | details={'strategy': 'trend_following', 'side': 'BUY', 'regime_context': 'trending', 'dominant_bias': 'SELL', 'dominance_score': 0.8781924390437595, 'opportunity_score': 0.881654907482281}
2026-01-15 21:55:01,597 ℹ️INFO AutoDetectionOrchestrator - ❌ DUPLICATE REJECTED: Pending BUY intent exists for IOTAUSDT. Preventing duplicate same-direction intent. | Intent Confidence: 75.94%
INFO:AutoDetectionOrchestrator:❌ DUPLICATE REJECTED: Pending BUY intent exists for IOTAUSDT. Preventing duplicate same-direction intent. | Intent Confidence: 75.94%
2026-01-15 21:55:01,598 ℹ️INFO AutoDetectionOrchestrator - ❌ DUPLICATE INTENT REJECTED: IOTAUSDT BUY | Intent Confidence: 75.94%
INFO:AutoDetectionOrchestrator:❌ DUPLICATE INTENT REJECTED: IOTAUSDT BUY | Intent Confidence: 75.94%
2026-01-15 21:55:01,598 ℹ️INFO AutoDetectionOrchestrator - DECISION REASON: Orchestrator | Symbol: IOTAUSDT | Decision: Intent Rejected - Duplicate Prevention | Reason: Duplicate execution intent detected | Confidence: 75.94% | component=Orchestrator | symbol=IOTAUSDT | decision=Intent Rejected - Duplicate Prevention | reason=Duplicate execution intent detected | confidence=0.7593936263298837 | score=0.881654907482281
INFO:AutoDetectionOrchestrator:DECISION REASON: Orchestrator | Symbol: IOTAUSDT | Decision: Intent Rejected - Duplicate Prevention | Reason: Duplicate execution intent detected | Confidence: 75.94% | component=Orchestrator | symbol=IOTAUSDT | decision=Intent Rejected - Duplicate Prevention | reason=Duplicate execution intent detected | confidence=0.7593936263298837 | score=0.881654907482281
2026-01-15 21:55:01,598 🐞DEBUG SignalAggregator - 📥 Collected fused signal for XRPUSDT with confidence 60.00% and dominance 0.18
```

Wrong Risk Managements
```
DEBUG:BrokerExecutionService:Take profit price: 449.42703990526115
2026-01-15 21:55:01,544 ⚠️WARNING BrokerExecutionService - TP too far from entry for BUY order: TP (449.42703990526115) vs Entry (0.0952)
2026-01-15 21:55:01,544 ⚠️WARNING BrokerExecutionService - TP too far from entry for BUY order: TP (449.42703990526115) vs Entry (0.0952)
WARNING:BrokerExecutionService:TP too far from entry for BUY order: TP (449.42703990526115) vs Entry (0.0952)
2026-01-15 21:55:01,545 ❌ERROR BrokerExecutionService - ❌ ORDER REJECTED: Order parameters are invalid or unreasonable: Order(symbol=Symbol(value='IOTAUSDT'), side=<OrderSide.BUY: 'BUY'>, quantity=Decimal('42.016806722689076'), price=Money(amount=Decimal('0.0952'), currency='USDT'), order_type='MARKET', position_side='LONG', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='trend_following', timestamp=datetime.datetime(2026, 1, 15, 21, 53, 0, 167259), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='IOTAUSDT'), strategy_name='trend_following', side=<OrderSide.BUY: 'BUY'>, intent_confidence=Percentage(value=Decimal('0.75939362632988368')), risk_parameters={'max_position_size': 1.250526306953282, 'stop_loss_pct': 0.017304547802525872, 'take_profit_pct': 0.035390904394948255, 'stop_loss_price': 429.72443317552035, 'take_profit_price': 449.42703990526115, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 28.809649819890065, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=1.3, position_size_multiplier=1.8984840658247093, stop_loss_multiplier=0.8652273901262936, take_profit_multiplier=1.179696813164942)}, timestamp=datetime.datetime(2026, 1, 15, 21, 53, 0, 167259), fused_signal=FusedSignal(symbol=Symbol(value='IOTAUSDT'), dominant_bias=<SignalType.SELL: 'SELL'>, direction=0.9492420329123546, dominance_score=0.8781924390437595, regime_context='trending', confidence=Percentage(value=Decimal('0.9492420329123546')), timestamp=datetime.datetime(2026, 1, 15, 21, 50, 13, 878570), metadata={'anomaly_score': 0.9492420329123546, 'feature_vector': [0.006322444678609097, 0.0018354439512951134, 0.004840067340067509, 0.004206098843322793, 0.0], 'feature_history_length': 30, 'price_history_length': 31, 'model_fitted': False, 'last_anomaly_timestamp': None, 'anomaly_source': 'AnomalyML', 'lookback_period': 50}), metadata={'strategy_reasoning': 'Signal aligned with trend_following strategy criteria', 'dominant_bias': 'SELL', 'regime_context': 'trending'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('0.09355260704919954'), currency='USDT'), take_profit_price=Money(amount=Decimal('449.42703990526115'), currency='USDT'))
2026-01-15 21:55:01,545 ❌ERROR BrokerExecutionService - ❌ ORDER REJECTED: Order parameters are invalid or unreasonable: Order(symbol=Symbol(value='IOTAUSDT'), side=<OrderSide.BUY: 'BUY'>, quantity=Decimal('42.016806722689076'), price=Money(amount=Decimal('0.0952'), currency='USDT'), order_type='MARKET', position_side='LONG', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='trend_following', timestamp=datetime.datetime(2026, 1, 15, 21, 53, 0, 167259), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='IOTAUSDT'), strategy_name='trend_following', side=<OrderSide.BUY: 'BUY'>, intent_confidence=Percentage(value=Decimal('0.75939362632988368')), risk_parameters={'max_position_size': 1.250526306953282, 'stop_loss_pct': 0.017304547802525872, 'take_profit_pct': 0.035390904394948255, 'stop_loss_price': 429.72443317552035, 'take_profit_price': 449.42703990526115, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 28.809649819890065, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=1.3, position_size_multiplier=1.8984840658247093, stop_loss_multiplier=0.8652273901262936, take_profit_multiplier=1.179696813164942)}, timestamp=datetime.datetime(2026, 1, 15, 21, 53, 0, 167259), fused_signal=FusedSignal(symbol=Symbol(value='IOTAUSDT'), dominant_bias=<SignalType.SELL: 'SELL'>, direction=0.9492420329123546, dominance_score=0.8781924390437595, regime_context='trending', confidence=Percentage(value=Decimal('0.9492420329123546')), timestamp=datetime.datetime(2026, 1, 15, 21, 50, 13, 878570), metadata={'anomaly_score': 0.9492420329123546, 'feature_vector': [0.006322444678609097, 0.0018354439512951134, 0.004840067340067509, 0.004206098843322793, 0.0], 'feature_history_length': 30, 'price_history_length': 31, 'model_fitted': False, 'last_anomaly_timestamp': None, 'anomaly_source': 'AnomalyML', 'lookback_period': 50}), metadata={'strategy_reasoning': 'Signal aligned with trend_following strategy criteria', 'dominant_bias': 'SELL', 'regime_context': 'trending'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('0.09355260704919954'), currency='USDT'), take_profit_price=Money(amount=Decimal('449.42703990526115'), currency='USDT'))
ERROR:BrokerExecutionService:❌ ORDER REJECTED: Order parameters are invalid or unreasonable: Order(symbol=Symbol(value='IOTAUSDT'), side=<OrderSide.BUY: 'BUY'>, quantity=Decimal('42.016806722689076'), price=Money(amount=Decimal('0.0952'), currency='USDT'), order_type='MARKET', position_side='LONG', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='trend_following', timestamp=datetime.datetime(2026, 1, 15, 21, 53, 0, 167259), parent_execution_intent=ExecutionIntent(symbol=Symbol(value='IOTAUSDT'), strategy_name='trend_following', side=<OrderSide.BUY: 'BUY'>, intent_confidence=Percentage(value=Decimal('0.75939362632988368')), risk_parameters={'max_position_size': 1.250526306953282, 'stop_loss_pct': 0.017304547802525872, 'take_profit_pct': 0.035390904394948255, 'stop_loss_price': 429.72443317552035, 'take_profit_price': 449.42703990526115, 'risk_per_trade': 200.0, 'max_position_exposure': 1000.0, 'position_quantity': 28.809649819890065, 'risk_adjustment_factors': RiskAdjustmentFactors(volatility_factor=0.9997115174677077, correlation_factor=1.0, regime_factor=1.1, market_condition_factor=1.3, position_size_multiplier=1.8984840658247093, stop_loss_multiplier=0.8652273901262936, take_profit_multiplier=1.179696813164942)}, timestamp=datetime.datetime(2026, 1, 15, 21, 53, 0, 167259), fused_signal=FusedSignal(symbol=Symbol(value='IOTAUSDT'), dominant_bias=<SignalType.SELL: 'SELL'>, direction=0.9492420329123546, dominance_score=0.8781924390437595, regime_context='trending', confidence=Percentage(value=Decimal('0.9492420329123546')), timestamp=datetime.datetime(2026, 1, 15, 21, 50, 13, 878570), metadata={'anomaly_score': 0.9492420329123546, 'feature_vector': [0.006322444678609097, 0.0018354439512951134, 0.004840067340067509, 0.004206098843322793, 0.0], 'feature_history_length': 30, 'price_history_length': 31, 'model_fitted': False, 'last_anomaly_timestamp': None, 'anomaly_source': 'AnomalyML', 'lookback_period': 50}), metadata={'strategy_reasoning': 'Signal aligned with trend_following strategy criteria', 'dominant_bias': 'SELL', 'regime_context': 'trending'}), risk_adjusted_quantity=None, stop_loss_price=Money(amount=Decimal('0.09355260704919954'), currency='USDT'), take_profit_price=Money(amount=Decimal('449.42703990526115'), currency='USDT'))
2026-01-15 21:55:01,546 ℹ️INFO ArchitectureOrchestrator - Executed order with ID: None
INFO:ArchitectureOrchestrator:Executed order with ID: None
```