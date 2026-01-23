- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Do the analyzed the existing implementation, identified weaknesses, and implemented all the improvements

You are a senior hedge-fund systems engineer performing a production cleanup review.

Your task is to REVIEW and FIX the existing implementation.
NOT to praise it.
NOT to add new features.
NOT to redesign the architecture.

The goal is to REMOVE unnecessary complexity while ENSURING correctness.

--------------------------------------------------
PRIMARY OBJECTIVE
--------------------------------------------------

Reduce code, not capability.

If a piece of logic:
- Does not directly improve decision quality
- Does not directly reduce risk
- Does not directly improve execution reliability

It must be removed or simplified.

--------------------------------------------------
STEP 1 — DUPLICATION AUDIT
--------------------------------------------------

Scan the entire codebase and identify:

- Any duplicated logic across:
  - Watchers
  - Engines
  - Fusion
  - Strategy
  - Risk
  - Broker

Especially check for duplication in:
- Risk calculations
- SL / TP logic
- Confidence thresholds
- Regime detection
- Signal filtering

List each duplicated logic block and propose ONE canonical location.
Remove the rest.

--------------------------------------------------
STEP 2 — RESPONSIBILITY VIOLATIONS
--------------------------------------------------

Verify strict separation of concerns:

- Watchers:
  - Must ONLY observe raw market data
  - Must NOT infer decisions, risk, or execution intent

- Engines:
  - Must ONLY interpret observations
  - Must NOT apply strategy logic or risk logic

- Fusion:
  - Must ONLY aggregate signals and confidence
  - Must NOT modify risk, SL, TP, or sizing

- Strategy:
  - Must ONLY decide "whether to trade or not"
  - Must NOT calculate SL, TP, or position size

- Risk Module:
  - Must be the ONLY place calculating:
    - Position size
    - Stop loss distance
    - Take profit distance

- Broker:
  - Must ONLY execute validated instructions
  - Must NOT modify or reinterpret risk

Report every violation and fix it.

--------------------------------------------------
STEP 3 — FORENSIC & GOVERNANCE PRUNING
--------------------------------------------------

Review all forensic and governance code and answer:

For EACH component:
- What trading failure does this prevent?
- What measurable value does it add in production?
- What is the runtime and cognitive cost?

If the answer is unclear or theoretical → REMOVE IT.

Keep ONLY:
- Traceability (trade_id)
- Minimal decision reconstruction
- PnL attribution
- Execution diagnostics

Remove:
- Over-statistical validation
- Authority scoring
- Randomness exposure theory
- Defensibility layers without direct PnL impact

--------------------------------------------------
STEP 4 — RISK REALISM CHECK
--------------------------------------------------

Verify that:

- SL / TP are volatility-based (ATR or equivalent)
- Leverage NEVER affects SL/TP distance
- Position sizing follows:

  position_size = risk_amount / stop_distance

- No fixed % SL/TP exists anywhere
- No strategy assumes unrealistic price moves for scalping

If scalping:
- TP must be reachable under normal microstructure
- SL must survive common liquidity hunts

Fix any unrealistic assumptions.

--------------------------------------------------
STEP 5 — FINAL OUTPUT
--------------------------------------------------

Provide:

1. A concise list of code/components REMOVED
2. A concise list of code/components SIMPLIFIED
3. A list of logic that was MISSING and added
4. Confirmation that:
   - No duplicated logic exists
   - Risk is centralized
   - Governance is minimal and purposeful
   - System is suitable for high-scale deployment

Do NOT rewrite the system.
Only surgical fixes and deletions.

Clarity > Complexity
Correctness > Elegance
Execution > Theory
