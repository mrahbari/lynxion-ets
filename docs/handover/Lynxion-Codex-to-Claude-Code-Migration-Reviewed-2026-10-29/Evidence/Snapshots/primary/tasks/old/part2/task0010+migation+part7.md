Before starting NGDP migration, perform a Strategy Preservation Audit.

Important:
The goal is NOT deleting legacy strategies.
The goal is preserving valuable trading hypotheses while removing obsolete implementations.

Architecture rules:
- Do not create new reports/files.
- Do not delete strategy adapters.
- Do not migrate or retire anything until classified.
- Keep repository clean.

Answer:

1. Which existing strategies represent valuable market hypotheses?
2. Which strategies failed because of timeframe/cost/implementation issues rather than invalid hypotheses?
3. Which strategies are truly obsolete and can be retired?
4. Which strategies should migrate into NGDP or other next-generation pipelines?

Review all existing strategies:

- Liquidity
- Sweep Scalper
- Mean Reversion
- VWAP Reversal
- Trend Following
- MTF Trend
- OI Footprint
- Breakout
- Donchian Breakout
- Momentum
- Volatility Breakout
- Scalping

For each provide:

- Current status:
  KEEP / MIGRATE / RETIRE
- Original hypothesis
- Why old implementation failed
- Recommended next-generation mapping
- Whether any alpha should be preserved

Do not modify code.

This is a research classification step only.

After this audit we will decide NGDP migration scope.