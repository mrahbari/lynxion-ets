Start the NextGenTrendPipeline migration.

Important:
- Architecture is frozen.
- Do not create unnecessary files or documentation.
- Keep repository clean.
- Reuse the approved NGLS/NGMR migration pattern.

Target strategies:
- trend_following
- mtf_trend

Goal:
Replace legacy EMA/MTF signal generation with a unified multi-timeframe trend pipeline.

Target flow:

4H Macro Regime
|
v
1H Market Structure
|
v
15m Trend Setup Detection
|
v
5m Order Flow Confirmation
|
v
1m Execution Optimization
|
v
ExecutionIntent


Requirements:

1. Preserve StrategyPort and ExecutionIntent contracts.
2. StrategyAdapters become thin delegation wrappers.
3. No duplicate trend calculations remain inside adapters.
4. Backtest and live use the same pipeline.
5. OI data may be used only as a confirmation/filter feature, not as a separate strategy path.
6. Do not touch breakout strategies yet.

Before coding answer the four engineering questions.

After implementation report:
- files modified
- legacy trend logic removed
- final execution flow
- test results
- remaining migration candidates