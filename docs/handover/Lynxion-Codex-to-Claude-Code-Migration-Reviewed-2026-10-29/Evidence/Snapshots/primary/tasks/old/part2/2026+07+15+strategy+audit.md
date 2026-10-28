### Strategy Preservation Audit
──────
### Part 1: Answers to Audit Questions

#### 1. Which existing strategies represent valuable market hypotheses?

• Liquidity / Sweep Scalper: The hypothesis that price hunts stop-losses at established swing highs/lows and then
rejects back into the range is highly valid.
• Mean Reversion / VWAP Reversal: Reverting back to the Point of Control (POC) after price reaches extreme boundaries
(VAL/VAH or VWAP standard deviation bands) under low momentum.
• Trend Following / MTF Trend: Following macro trend direction backed by multi-timeframe alignment.
• Breakout / Donchian Breakout: Capitalizing on structural breakouts of range boundaries accompanied by high
volume/order-flow momentum.
• OI Footprint: Using Open Interest (OI) divergence to predict short squeezes or long liquidations.

#### 2. Which strategies failed because of timeframe/cost/implementation issues rather than invalid hypotheses?

• VWAP Reversal: Failed because the legacy reset interval was simulated via  current_bar_index % 24  (24 minutes on 1m
chart), causing the VWAP to hug price and prevent any deviation breakout.
• Mean Reversion: Failed due to demanding 3 prior failed range breaks on the 1m timeframe (an arbitrary threshold that
never co-occurred).
• Liquidity (Sweep): Contained a bug that omitted the  type  tag for swing-lows, preventing BUY signals from ever
generating.
• General: All legacy strategies suffered from taker fee drag and a lack of microstructural order flow (OBI/CVD)
confirmation.

#### 3. Which strategies are truly obsolete and can be retired?

• Momentum: Obsolete. Pure low-timeframe momentum chasing is dominated by execution costs and noise.
• Scalping: Obsolete. Attempting high-frequency taker trades on sub-5m timeframes leads to negative expectancy after
commissions.

#### 4. Which strategies should migrate into NGDP or other next-generation pipelines?

• OI Footprint should migrate its alpha into the ExecutionConfirmationEngine as a microstructural filter.
• Trend Following / Breakout should migrate to use the unified engines ( MarketStructureEngine ,  SetupEngine ,
ExecutionConfirmationEngine ,  ExecutionOptimizer ).
• NGDP (Next Gen Dynamic Position) will serve as the position sizing, scaling, and risk exposure engine for all of
these pipelines, dynamically sizing trades based on microstructural volatility and current portfolio risk.
──────
### Part 2: Strategy Classification & Recommended Mapping

| Strategy Name     | Current Sta…       | Original Hypothes… | Why Old Implement… | Recommended Next-… | Alpha to Preserve  |
|-------------------|--------------------|--------------------|--------------------|--------------------|--------------------|
| Liquidity         | MIGRATED           | Stop-sweep         | Swing low bug, no  | NGLS Pipeline      | Swing-point        |
|                   | reaction.          | OBI/CVD            |                    | sweeps.            |                    |
|                   |                    | confirmation,      |                    |                    |                    |
|                   |                    | taker order fee    |                    |                    |                    |
|                   |                    | drag.              |                    |                    |                    |
| Sweep Scalper     | MIGRATED           | Stop-sweep         | Lookback           | NGLS Pipeline      | Sweep detection.   |
|                   | reaction.          | miscalculations,   |                    |                    |                    |
|                   |                    | taker fee drag.    |                    |                    |                    |
| Mean Reversion    | MIGRATED           | Range-bound        | Restrictive        | NGMR Pipeline      | Reversion to POC.  |
|                   | reversion to mean. | failed-break       |                    |                    |                    |
|                   |                    | count, no OBI/CVD. |                    |                    |                    |
| VWAP Reversal     | MIGRATED           | Deviation from     | 24-minute session  | NGMR Pipeline      | Reversion to POC   |
|                   | session VWAP.      | reset bug.         |                    | from VAL/VAH.      |                    |
| Trend Following   | MIGRATE            | Riding macro trend | EMA lag, no order- | NGMR / Trend       | Trend direction    |
|                   | direction.         | flow validation,   | Pipeline           | bias.              |                    |
|                   |                    | taker slippage.    |                    |                    |                    |
| MTF Trend         | MIGRATE            | Multi-timeframe    | Timeframe          | NGMR / Trend       | Timeframe          |
|                   | trend alignment.   | synchronization    | Pipeline           | confluence.        |                    |
|                   |                    | lag.               |                    |                    |                    |
| OI Footprint      | MIGRATE            | Position building  | Isolated           | ExecutionConfirmat | OI Squeeze filter. |
|                   | via OI/CVD.        | execution, no      | ionEngine          |                    |                    |
|                   |                    | limit-maker        |                    |                    |                    |
|                   |                    | routing.           |                    |                    |                    |
| Breakout          | MIGRATE            | Range breakout     | High false         | Next-Gen Breakout  | Volume expansion.  |
|                   | entry.             | breakouts          | Pipeline           |                    |                    |
|                   |                    | (whipsaws) on 1m   |                    |                    |                    |
|                   |                    | charts.            |                    |                    |                    |
| Donchian Breakout | MIGRATE            | Channel breakout   | No volume or OBI   | Next-Gen Breakout  | Channel            |
|                   | entry.             | verification.      | Pipeline           | boundaries.        |                    |
| Momentum          | RETIRE             | Chasing short-term | Dominated by       | Retired (Absorbed  | None.              |
|                   | moves.             | execution          | by NGMR)           |                    |                    |
|                   |                    | costs/noise.       |                    |                    |                    |
| Scalping          | RETIRE             | High frequency     | Dominated by       | Retired (Absorbed  | None.              |
|                   | price flips.       | exchange fees.     | by NGLS)           |                    |                    |
