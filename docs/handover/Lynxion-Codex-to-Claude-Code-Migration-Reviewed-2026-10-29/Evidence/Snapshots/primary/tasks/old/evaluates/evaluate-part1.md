Act as an expert Python Algorithmic Trading Developer specializing in Crypto Futures, Price Action Systems, SMC/ICT concepts, Fibonacci-based strategies, and Advanced Risk Management.

I have an existing Python crypto futures trading bot.

The current entry strategy is based on Price Action (SMC/ICT) and Fibonacci levels.

IMPORTANT:
Do NOT rewrite, replace, or fundamentally alter the existing entry signal generation logic.

The goal is NOT to create a new strategy.

The goal is to add a professional Trade Management and Execution Safety Layer around the existing strategy to improve trade quality, reduce avoidable losses, and manage positions professionally.

Before implementing anything:
1. Audit the current architecture.
2. Identify the correct integration points.
3. Explain what should be changed and what should remain untouched.
4. Avoid unnecessary new files, abstractions, managers, or architectural redesign.
5. Prefer minimal, clean modifications following the existing project structure.

---

# Observed Problems From Live Trading Analysis

After manually comparing successful trades (for example ZAMA) and stopped-out trades (ONDO, WLD, XLM) using TradingView charts, the conclusion is:

The core entry logic is generally detecting meaningful Fibonacci and price-action zones.

The main weaknesses are in trade filtering, execution timing, and position management.

The system currently suffers from:

---

## 1. Missing Higher-Timeframe Context

Problem:

The bot sometimes opens LONG positions:

- Directly below strong HTF resistance.
- Against a strong bearish trend.
- Near major downward trendlines.
- During unfavorable market structure.

Required improvement:

Add an HTF safety filter before execution.

Requirements:

- Detect higher timeframe trend direction.
- Detect major resistance/support zones.
- Detect strong bearish or bullish market structure.
- Suppress low-quality counter-trend entries.

Example:

Do not execute LONG if:

- HTF structure is strongly bearish.
- Price is directly below significant resistance.
- Risk/reward is poor because upside liquidity is limited.

Do not modify the original signal generation.
Only add a pre-execution validation layer.

---

# 2. Falling Knife Protection

Problem:

The system sometimes enters immediately when price touches a Fibonacci level during a strong liquidation move.

Example:

Price drops aggressively:

- Candle touches Fib zone.
- Strategy immediately enters LONG.
- Selling pressure continues.
- Stop loss gets hit.

Required improvement:

Add momentum and volatility protection.

Requirements:

Before entering:

- Check candle body size relative to ATR.
- Detect abnormal price acceleration.
- Avoid entering during extreme momentum spikes.

Example:

If:

current candle body > 2.0 * ATR

then:

Do not immediately enter.
Wait for market stabilization.

---

# 3. Momentum Confirmation

Problem:

The system ignores strong opposing momentum.

Example:

LONG entry occurs while:

- MACD histogram strongly negative.
- Selling momentum increasing.
- No reversal confirmation exists.

Required improvement:

Add momentum validation.

Requirements:

Before execution:

Check:

- MACD histogram.
- Momentum direction.
- Momentum exhaustion.

The filter should not reject every counter-trend trade.

It should only block extreme situations where momentum strongly conflicts with the trade direction.

---

# 4. Candle Confirmation Before Entry

Problem:

Current behavior:

Touch Fibonacci level → Immediate entry.

Required improvement:

Require confirmation.

Examples:

For LONG:

Wait for:

- Bullish engulfing.
- Pin bar rejection.
- Strong close above Fibonacci level.
- Liquidity sweep followed by recovery.

For SHORT:

Opposite confirmation.

The system should avoid entering during an unresolved price reaction.

---

# 5. Dynamic ATR-Based Stop Loss Management

Current problem:

Static SL placement can be too tight or placed inside liquidity zones.

Required improvement:

Improve SL calculation without changing entry logic.

Requirements:

Stop loss should:

- Respect liquidity sweep areas.
- Avoid obvious stop hunting zones.
- Include ATR-based protection.

Rules:

Minimum distance:

1.0 * ATR

Maximum distance:

2.5 * ATR

The final SL should balance:

- Market structure.
- Volatility.
- Risk limits.

---

# 6. Multi-Stage Take Profit Management

Add professional position management.

## TP1 - Partial Profit Taking

Requirements:

TP1 should be based on:

- Nearest structural resistance/support.
- Fibonacci 0.382 / 0.5 levels.
- Minimum Risk/Reward of 1:1.5.

When TP1 is reached:

- Close approximately 50% of the position.
- Move remaining position stop loss to Break-Even.
- Include exchange fee buffer.

Example:

Entry:
100

Break-even SL:

Entry + trading fees + small safety buffer.

---

## TP2 - Main Objective + Trailing Stop

Remaining position:

Target:

- Fibonacci 0.786 / 1.0 extension.
- Or minimum R:R 1:3.

After TP1:

Activate:

- ATR trailing stop.

Suggested:

Trailing distance:

1.5 * ATR

Alternative:

Step trailing:

- Move SL to TP1 when price reaches halfway to TP2.

---

# 7. Exchange-Aware Execution Safety for Partial TP Management

The execution module must correctly handle exchange limitations during partial closing.

This is mandatory for production safety.

Requirements:

## Quantity Validation

Before sending TP1 partial close:

- Respect exchange minimum order quantity.
- Respect minimum notional requirements.
- Validate that partial close size is executable.

Never submit invalid exchange orders.

---

## Precision Handling

Do NOT use floating point calculations for order quantities.

Use:

- Decimal arithmetic.
- Exchange metadata.
- Quantity step size.
- Price tick size.
- Quantity precision.

Example:

Normalize:

- order quantity.
- limit price.
- stop price.

according to exchange rules.

Compatible with exchanges such as:

- BingX Futures.
- Binance Futures.

---

## Partial Fill Handling

The execution module must handle:

- Partial TP fills.
- Cancelled partial orders.
- Remaining position size changes.

After TP1:

Do not assume 50% was closed.

Confirm:

- Actual filled quantity.
- Remaining exchange position size.

All TP2 and trailing stop calculations must use:

REAL remaining exchange position size.

Not the original position size.

---

# 8. Risk Management Integration Rules

The implementation must respect existing architecture.

Requirements:

- Do not duplicate risk engines.
- Do not create parallel execution paths.
- Do not bypass existing broker/exchange validation.
- Keep one authoritative position state.
- Keep exchange reality as the final source of truth.

---

# 9. Expected Deliverable

Before coding:

Provide:

1. Current architecture analysis.
2. Recommended integration point.
3. List of files that need modification.
4. Explanation of why each file changes.
5. Confirmation that entry strategy remains untouched.

After approval:

Implement:

- Clean modular code.
- Minimal changes.
- Production-safe logic.
- Unit tests.

Do not introduce unnecessary complexity.

The objective:

Improve trade quality and execution safety while preserving the existing strategy edge.