

First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Why we need to check .csv file for order placements and many issues like this! 
- why system needs to check it for production! it's not backtest!!!!!
- Check my observations that I shared below as a sample of logs!


There are lots of strange issues which i confused! so track a symbol like  NEOUSDT and find out what happened?
- check the ./logs/* deeply as well
- remember, we still have problem with order placement!
- New Resource Issue: The system is now creating too many resources (threads, file handles) which causes "Too many open files" error.
- make sure The system properly handles execution intents without generating multiple duplicate rejections.
- The "Too many open files" error is a resource exhaustion issue. The system is creating multiple broker instances and data providers, which is consuming too
  many file descriptors.

  
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