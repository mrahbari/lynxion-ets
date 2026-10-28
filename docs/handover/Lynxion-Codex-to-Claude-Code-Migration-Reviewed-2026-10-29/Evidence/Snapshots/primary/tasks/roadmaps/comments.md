  2. Future Migration Roadmap: We can schedule a systematic migration from V2 to V3 endpoints to take advantage of V3's
  native SL/TP parameters and higher API rate limits.



---------------





Act as a Senior Python Algorithmic Trading Engineer and Quant Systems Auditor.

You are reviewing a live crypto futures trading system (Lynxion) running on BingX with real micro-capital.

IMPORTANT:

Do NOT modify code immediately.

This phase is a forensic investigation only.

The goal is to identify the exact root causes behind observed live trading inconsistencies before implementing any fix.

Do not redesign the architecture.
Do not introduce new managers, frameworks, databases, or abstractions.

Respect the existing architecture:

Watchers → Event System → Fusion → Strategy → Risk → Execution → Broker

The current system has already passed production safety validation:

- Exchange execution path verified.
- Risk limits active.
- Journal integrity verified.
- SL placement infrastructure verified.
- 396/396 tests passing.

Therefore, focus only on correctness issues observed during live trading.

---

# Live Trading Observations Requiring Investigation

## 1. Trading Activity Stops After Initial Startup Trades

Observed behavior:

After system startup:

- Several trades are opened successfully.
- System continues running for hours.
- No additional trades are executed.
- After full shutdown and restart:
    - Several trades are opened again.

This indicates a possible lifecycle/state problem.

Investigate:

- Watcher state persistence.
- Signal cooldown state.
- Cached symbols.
- Event queue state.
- Strategy adapter state.
- Fusion state.
- Risk manager state.
- Duplicate signal suppression.
- Position tracking state.

Questions:

- Is there any state that never expires?
- Is there any in-memory cache surviving incorrectly?
- Is a startup initialization event required to reset something?
- Are symbols becoming permanently blocked after first evaluation?

Provide evidence from logs and code paths.

---

# 2. Multiple Strategies Are Now Generating Trades

Observation:

This is a positive change.

Previously only one strategy generated trades.

Now:

Examples:

- TrendFollow
- VWAPReversal
- MTFTrend

are producing executions.

Do NOT remove this behavior.

Validate:

- Are strategy identities correctly preserved?
- Is strategy attribution in execution logs accurate?
- Is strategy performance tracking isolated?

---

# 3. Confidence Calculation Audit

Critical issue:

Almost every trade shows:

Confidence: 80.0%

Example:


Strategy: TrendFollow
Confidence: 80.0%

Strategy: VWAPReversal
Confidence: 80.0%

Strategy: MTFTrend
Confidence: 80.0%


This is statistically suspicious.

Investigate:

- Where confidence is generated.
- Where confidence is transformed.
- Any hardcoded multipliers.
- Any default fallback values.
- Any clamping logic.
- Any cached confidence values.
- Whether watcher confidence reaches strategy layer correctly.

Required:

Trace:

Watcher confidence
↓
Fusion confidence
↓
Strategy confidence
↓
Execution confidence
↓
Telegram notification confidence

Identify where the value becomes 80%.

Do not assume.

Provide exact source.

---

# 4. Timestamp Integrity Audit

Critical issue:

Different trades show identical timestamps.

Example:

Multiple trades:


Timestamp: 2026-07-21 22:23:04


even when execution happened hours apart.

Investigate:

- Cached order metadata.
- Shared object mutation.
- Default timestamp generation.
- Event reuse.
- Dataclass default values.
- Strategy signal object reuse.
- Serialization problems.

Required:

Trace:

Signal creation time
→ Execution intent time
→ Order submission time
→ Broker response time
→ Telegram notification time

The final order record must represent the real execution lifecycle.

---

# 5. Stop Loss / Take Profit Calculation Audit

Observed issue:

Some trades have incorrect risk/reward.

Examples:

AVAX:

Entry:
6.588

SL:
6.6503

TP:
6.52212

This is a SHORT trade:

SL distance:
0.0623

TP distance:
0.06588

This one is acceptable.

But other trades show cases where:

- SL distance > TP distance.
- Risk/reward is not aligned.
- Targets appear too close.
- Positions remain open too long.

Investigate:

- Who calculates SL?
- Who calculates TP?
- Which timeframe is used?
- Is ATR involved?
- Is strategy SL overwritten later?
- Is risk module modifying values?
- Does execution use the same values shown in Telegram?

Required:

Create a full trace:

Strategy output SL/TP

↓

Risk Manager SL/TP

↓

Execution Order SL/TP

↓

Exchange attached SL/TP

Identify any mismatch.

---

# 6. Entry Price Mismatch Investigation

Observed:

Telegram entry price does not always match broker execution price.

Example:

Telegram:


Price: 0.1921


Broker:

different fill price.

Investigate:

Determine whether the difference is caused by:

- Market order slippage.
- Wrong price source.
- Last candle close usage.
- Signal price instead of fill price.
- Notification generated before execution confirmation.

Required:

Clearly separate:

Signal Price

vs

Requested Order Price

vs

Exchange Fill Price

vs

Notification Price

---

# 7. Trade Performance Investigation

Current observation:

Approximately:

10 trades:

2 winners

8 losers

Do NOT conclude strategy failure yet.

Investigate:

- Market regime during trades.
- Holding duration.
- Entry timing.
- Trend alignment.
- Exit reasons.

Important observation:

Entries appear better than before.

Possible issue:

The market does not continue the expected move.

Trades stay open too long and eventually hit SL.

Investigate:

- Time-based exit possibility.
- Momentum exhaustion.
- Lack of volatility continuation.
- Missing momentum confirmation.
- Missing liquidity confirmation.

Do not modify strategy yet.




---
---
---
---
---
---
---

# Provided Live Trades For Analysis

Analyze these examples:

[Insert trade logs]

For each trade provide:

- Strategy
- Entry quality
- SL placement quality
- TP placement quality
- Market condition
- Exit reason
- Possible failure category

---

# Expected Deliverable

Before any code change provide:

## 1. Root Cause Classification

For each issue:

Category:

A) Confirmed bug

B) Configuration problem

C) Logic problem

D) Strategy limitation

E) Expected market behavior


## 2. Evidence

For each finding:

- File name
- Function name
- Runtime evidence
- Log evidence

## 3. Priority Ranking

Rank fixes:

P0:
Production risk / capital loss

P1:
Incorrect execution behavior

P2:
Performance improvement

P3:
Optimization


## 4. Minimal Fix Proposal

Only after identifying the root cause:

Suggest:

- Exact files to modify.
- Why modification is needed.
- Expected impact.
- Regression risks.

No architectural redesign.

---

The objective:

Make the existing production system behave correctly and transparently before attempting strategy improvements.

Preserve the current architecture and existing strategy edge.