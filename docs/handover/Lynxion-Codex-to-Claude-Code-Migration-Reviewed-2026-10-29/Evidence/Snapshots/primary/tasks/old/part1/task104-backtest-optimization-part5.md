You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.


## 🔑 Clear answer (no ambiguity)

Yes — **now it is both allowed and necessary to take care of the strategies as well**.

Why?

* You **already fixed execution correctness**
* You **proved strategies are actually driving trades**
* The massive trade counts and drawdowns are **not a backtest bug anymore**
* They are a **strategy intent-quality problem**

⚠️ If you *don’t* touch strategies at this stage and jump to Hyperopt, you will:

* Optimize noise
* Reward overtrading
* Destroy generalization
* Waste compute and time

So the next step **must include strategy-side changes**, but in a **very controlled and minimal way**.

---

## 🎯 What kind of strategy changes are allowed now?

✅ Allowed:

* Intent emission discipline
* Cooldowns
* Position exclusivity
* Signal confirmation
* Regime / volatility gating
* Debouncing repeated signals

❌ Still NOT allowed:

* Complex new indicators
* Curve fitting
* Parameter optimization
* Hyperopt
* Profit chasing

This step is about **making strategies sane**, not profitable.

---

## ✅ NEXT PROMPT — STRATEGY INTENT DISCIPLINE & EXECUTION SANITY

Use **only this prompt next** 👇

---

## ✅ STRATEGY INTENT HARDENING PROMPT (POST-EXECUTION FIX)

> **System Context**
>
> I am working with a production-grade quantitative trading system built on a strict **Hexagonal Architecture**.
>
> The execution layer has already been corrected using a formal `ExecutionIntent` contract.
>
> Backtests now execute **all strategy-emitted intents correctly**, revealing:
>
> * excessive trade counts
> * extreme drawdowns
> * bar-by-bar intent emission
>
> This confirms that **execution is correct**, but **strategy intent quality is not yet controlled**.
>
> ---
>
> ## 🎯 Objective (This Step Only)
>
> Harden **strategy-side intent emission** so that:
>
> 1. Strategies emit ExecutionIntent **only when a meaningful edge exists**
> 2. Bar-by-bar signal spam is eliminated
> 3. Trade frequency becomes realistic and bounded
>
> This step focuses on **behavioral discipline**, not profitability.
>
> ---
>
> ## 🔒 Non-Negotiable Constraints
>
> * Do NOT change execution, backtester, or broker logic
> * Do NOT introduce Hyperopt
> * Do NOT add new strategies
> * Do NOT refactor architecture
>
> Strategy logic may be **extended**, not rewritten.
>
> ---
>
> ## 🔍 Step 1 — Intent Emission Discipline
>
> For each strategy:
>
> * Prevent repeated intent emission in the same direction
> * Enforce **minimum bars between entries**
> * Block intent emission when:
>
>   * a position is already open
>   * market conditions are unchanged from the last signal
>
> All blocked intents must be logged with explicit reasons.
>
> ---
>
> ## 🧭 Step 2 — Market Condition Validation
>
> Before emitting an ExecutionIntent, strategies must confirm:
>
> * sufficient volatility (ATR / range-based)
> * non-flat market conditions
> * alignment with the strategy’s intended regime
>
> These checks must:
>
> * be lightweight
> * reuse existing indicators if possible
> * avoid introducing new heavy computations
>
> ---
>
> ## 📉 Step 3 — Safety Guards (Not Optimization)
>
> Add hard safety rules:
>
> * maximum trades per day
> * maximum consecutive losses
> * optional time-based cooldown after exit
>
> These rules exist to:
>
> * prevent pathological behavior
> * stabilize metrics
> * protect future Hyperopt runs
>
> ---
>
> ## 🚫 Explicit Non-Goals
>
> * Do NOT improve returns directly
> * Do NOT tune parameters aggressively
> * Do NOT remove losing strategies
> * Do NOT introduce curve fitting
>
> This step is about **signal quality**, not performance.
>
> ---
>
> ## ✅ Expected Outcome
>
> * Trade counts drop to realistic levels
> * Drawdowns become interpretable
> * Strategies behave consistently across runs
> * Backtest metrics become suitable for:
>
>   * comparison
>   * selection
>   * Hyperparameter optimization
>
> If any strategy cannot be disciplined without violating architectural constraints, it must be explicitly reported.

---






---

## 3️⃣ The correct next step (conceptually)

You now need to answer one precise question in code:

> “What is the single function / method where an ExecutionIntent is born?”

And then ensure:

* **all discipline checks happen *before* that return**
* not after
* not in helpers that are never called
* not in adapters that strategies bypass

This is a **wiring & enforcement problem**, not a design problem.

---

## 4️⃣ ✅ NEXT PROMPT — STRATEGY INTENT ENFORCEMENT AUDIT & FIX

This is the **only correct next prompt** for your current state.

Use this **alone**, do not combine it with anything else.

---

## ✅ STRATEGY INTENT ENFORCEMENT PROMPT (WIRING & ACTIVATION)

> **System Context**
>
> The trading system uses a strict Hexagonal Architecture and a formal `ExecutionIntent` contract.
>
> Execution correctness has been verified.
>
> Strategy intent discipline rules (cooldowns, exclusivity, regime checks) were recently added, but backtest results show:
>
> * `Generated == Entries`
> * `Filtered == 0`
> * No reduction in trade count
>
> This proves that **intent discipline logic is not being enforced at the point of intent emission**.
>
> ---
>
> ## 🎯 Objective (This Step Only)
>
> Ensure that **all strategy intent discipline rules are actually enforced** at the **exact point where an `ExecutionIntent` is created and returned**.
>
> The goal is to make discipline **effective**, not to add new rules.
>
> ---
>
> ## 🔒 Non-Negotiable Constraints
>
> * Do NOT modify backtester or execution logic
> * Do NOT add new discipline rules
> * Do NOT change strategy semantics
> * Do NOT refactor architecture
>
> This is strictly a **wiring / enforcement audit**.
>
> ---
>
> ## 🔍 Step 1 — Identify the Intent Birth Point
>
> For each strategy:
>
> * Identify the **single method** that returns or constructs `ExecutionIntent`
> * Trace the full call stack that leads to that return
>
> Explicitly document:
>
> * where discipline checks are currently implemented
> * whether they are guaranteed to run before intent creation
>
> ---
>
> ## 🔧 Step 2 — Enforce Discipline Before Intent Creation
>
> Modify the code so that:
>
> * No `ExecutionIntent` can be created unless:
>
>   * cooldown checks pass
>   * position exclusivity passes
>   * regime / volatility checks pass
>
> These checks must:
>
> * execute synchronously
> * block intent creation (not just log warnings)
>
> If a check fails:
>
> * no intent is returned
> * a rejection reason is logged
>
> ---
>
> ## 🧪 Step 3 — Verification
>
> Re-run a 360-day BTCUSDT backtest and verify:
>
> * `Filtered > 0`
> * `Entries < Generated`
> * Trade count drops materially
>
> If this does not happen, the implementation must be considered incomplete.
>
> ---
>
> ## 🚫 Explicit Non-Goals
>
> * Do NOT optimize profitability
> * Do NOT tune parameters
> * Do NOT remove strategies
> * Do NOT introduce Hyperopt
>
> This step is purely about **making existing discipline rules actually take effect**.
>
> ---
>
> ## ✅ Expected Outcome
>
> * Intent discipline visibly reduces intent emission
> * Trade counts become realistic
> * Logs clearly explain why intents are blocked
> * System becomes genuinely ready for:
>
>   * metric stabilization
>   * Hyperopt preparation
>
> If discipline logic cannot be enforced without violating architecture, this must be explicitly stated and justified.

---

## 5️⃣ Why this prompt is the right one (and why nothing else is)

* You already **designed** the rules
* You already **implemented** the rules
* You just haven’t **activated them at the choke point**

This prompt fixes **exactly that**, nothing more.


