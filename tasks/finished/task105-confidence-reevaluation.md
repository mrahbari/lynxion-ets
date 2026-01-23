- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Do the analyzed the existing implementation, identified weaknesses, and implemented all the improvements

You are acting as a senior quantitative researcher
working on an existing hedge-fund-grade trading system.

Your objective is NOT to increase signal count
and NOT to blindly improve win rate.

Your objective is to:
• Reconstruct true entry confidence
• Identify structurally weak entries
• Improve entry precision
using ONLY updates to the existing codebase.

No new strategy files should be added.
Prefer modifying and extending current modules.

Operate in a realistic, professional manner.
No exaggeration. No assumptions without evidence.

---

STEP 1 — SYSTEM & LOG REVIEW
• Review the current system architecture.
• Use existing execution and signal logs.
• Logs may be extended, but only by updating existing code files.

Required data per entry:
- Symbol
- Timeframe
- Entry timestamp and price
- Indicator and signal states at entry
- Market context if available

Do NOT rely on explicit win/loss labels.

---

STEP 2 — OUTCOME RECONSTRUCTION (MANDATORY)
Since trade outcomes are not explicitly stored:

• Reconstruct post-entry behavior using historical price data.
• For each entry, calculate:
    - Maximum Favorable Excursion (MFE)
    - Maximum Adverse Excursion (MAE)
    - Sequence: which occurred first (MFE or MAE)
    - Time to first excursion

Outcome classification must be:
- Structurally favorable
- Structurally unfavorable
- Noise-dominated / ambiguous

Binary win/loss classification is prohibited.

---

STEP 3 — MARKET STRUCTURE CONTEXT
For every entry, classify the market regime at entry:
- Trend continuation
- Pullback within trend
- Mean reversion
- Breakout
- Failed breakout / liquidity sweep

If structure is unclear, explicitly mark:
→ "Low structural clarity"

Do not force classification.

---

STEP 4 — CONFIDENCE DECOMPOSITION
Rebuild entry confidence as a composite score based on:
- Trend alignment quality
- Structural clarity
- Volatility regime suitability
- Entry timing relative to structure
- Post-entry MFE vs MAE behavior

Each component must be normalized.
Avoid indicator stacking or binary logic.

---

STEP 5 — FAILURE MODE ANALYSIS
For structurally unfavorable entries:
• Identify the dominant failure cause:
    - Early entry
    - Late entry
    - False structural signal
    - Volatility expansion against position
    - Liquidity sweep / stop-hunt behavior
    - Randomness (only if justified)

Each failure must map to a specific mechanism,
not a vague explanation.

---

STEP 6 — PRECISION IMPROVEMENT VIA CODE UPDATES
Propose ONLY minimal, surgical updates to existing code:
- Adjust weights or thresholds
- Modify entry timing logic
- Refine volatility or structure filters

Do NOT:
- Add new strategy layers
- Create new standalone modules
- Over-filter and kill trade frequency

Each modification must:
• Remove one identified failure mode
• Preserve system behavior elsewhere
• Be explainable in one sentence

---

STEP 7 — STATISTICAL VALIDATION
Across at least 20 symbols:
• Compare high-confidence vs low-confidence entries
• Measure:
    - Expectancy proxy (via MFE/MAE asymmetry)
    - Drawdown contribution
    - Consistency across symbols

The goal is asymmetry and robustness,
not cosmetic performance.

---

STEP 8 — FINAL PROFESSIONAL OUTPUT
Deliver:
1. A clear judgment on whether current entries are:
   - Structurally justified
   - Overconfident
   - Or noise-driven

2. A revised confidence logic description
   (no code unless explicitly requested)

3. One uncomfortable but necessary truth
   the system must accept to improve entry precision.

No motivational language.
No marketing tone.
Professional hedge-fund-level reasoning only.
