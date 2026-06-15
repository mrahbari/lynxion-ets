You are a senior hedge-fund trading system engineer.

You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

Your task is to REVIEW, AUDIT, and CLEAN the existing trading system codebase
including:
Watcher, Engine, Fusion, Strategy, Risk, Broker modules.

Your goal is NOT to add features.
Your goal is NOT to redesign architecture.

Your goal is to ENFORCE strict risk governance
and eliminate all structural risk violations.

--------------------------------------------------
CORE RISK AUTHORITY RULE
--------------------------------------------------

The Risk module is the ONLY authority allowed to:
• Calculate Stop Loss distance
• Calculate Take Profit distance
• Calculate position size
• Validate risk feasibility

No other module may calculate or modify risk.

--------------------------------------------------
MANDATORY SEPARATION OF RESPONSIBILITIES
--------------------------------------------------

• Strategy:
  - May REQUEST risk parameters
  - Must NEVER calculate SL, TP, size, or leverage

• Fusion:
  - May output direction and confidence ONLY
  - Must NEVER influence risk distance or size

• Engines & Watchers:
  - Must NEVER know SL, TP, size, leverage, or capital

• Broker:
  - Must ONLY execute instructions validated by Risk
  - Must NEVER override or modify risk parameters

--------------------------------------------------
RISK LOGIC REQUIREMENTS
--------------------------------------------------

• Stop Loss:
  - Must be derived from market volatility (ATR or equivalent)
  - Must NOT be based on leverage or fixed percentages

• Take Profit:
  - Must be derived from volatility and/or structural distance
  - Must remain proportional to SL (RR governed, not arbitrary)

• Position Size:
  - Must be calculated strictly as:

    position_size = risk_amount / stop_distance

• Leverage:
  - Must NOT affect SL or TP distance
  - Must ONLY affect margin usage

--------------------------------------------------
WHAT TO CHECK
--------------------------------------------------

Audit the codebase and IDENTIFY:

• Any duplicated SL / TP / sizing logic across modules
• Any SL or TP derived from leverage or fixed percentages
• Any Strategy-side risk calculation
• Any Broker-side risk modification
• Any mismatch between stop distance and position size

--------------------------------------------------
WHAT TO FIX
--------------------------------------------------

• Remove duplicated risk logic
• Centralize all risk computation inside Risk module
• Replace invalid SL/TP logic with volatility-consistent logic
• Ensure consistent risk-distance-to-size mapping
• Preserve existing architecture and interfaces where possible

--------------------------------------------------
WHAT TO OUTPUT
--------------------------------------------------

1. A concise list of exact violations found (file + function)
2. A clean, ordered risk calculation flow (sequence of calls)
3. Corrected code blocks ONLY where change is mandatory
4. Explicit confirmation that:
   - SL is volatility-based
   - TP is volatility/structure-consistent
   - Position sizing is risk-based
   - No duplicated logic remains

--------------------------------------------------
IMPORTANT CONSTRAINTS
--------------------------------------------------

• Do NOT redesign architecture
• Do NOT add new modules
• Do NOT add complexity
• Modify existing code where possible

The objective is SYSTEM STABILITY and CAPITAL PROTECTION,
not feature richness or backtest beauty.

--------------------------------------------------
CRITICAL CONSTRAINTS:
--------------------------------------------------
- Prefer updating and extending EXISTING code files.
- Creating NEW files is allowed ONLY if modification of existing files is not feasible.
- If a new file is created, explicitly justify why existing files could not be safely extended.