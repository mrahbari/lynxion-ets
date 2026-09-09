# Lynxion Investor Release — Status, Decisions, and Roadmap

**Evidence date:** 2026-09-09  
**Current release status:** `VST DEMO VERIFIED — NO-TRADE ECONOMIC DEFAULT — PROFITABILITY NOT PROVEN`

Technical/agent review companion: [README_AGENT_TECHNICAL_REVIEW.md](README_AGENT_TECHNICAL_REVIEW.md)

## Executive summary

Lynxion is a functioning automated crypto-trading system with strategy, market-data,
risk-admission, broker execution, exchange-side protection, journaling, and research
components. We have verified that the system can send a bounded order through its normal
risk path to a BingX test account and create an isolated position with stop-loss and
take-profit orders visible at the exchange.

That technical result is important, but it is not evidence of a durable profitable edge.
The canonical historical journal is economically negative in aggregate and mixes several
old sizing and risk regimes. Therefore, our current professional decision is to deliver a
safe, reviewable initial VST/shadow version while retaining a **no-trade default** for
strategy admission until a strategy passes prospective, cost-adjusted, out-of-sample gates.

The initial version is intended to prove that the product, execution controls, evidence
pipeline, and research discipline are real. It does not promise profitability or authorize
real-money deployment.

## What condition the system was in

Before the current investor-release track, Lynxion already contained substantial business
and engineering functionality, but the evidence was fragmented and some operational risks
were material:

- Historical trading existed, but the journal combined different position sizes, leverage
  assumptions, code versions, and risk regimes. Comparing all trades as one clean strategy
  cohort would be misleading.
- Some earlier paths could create or manage positions without sufficiently strong central
  risk admission. This was the class of defect behind concern about unlimited or unwanted
  entries; the correct response was to harden the execution boundary, not merely blacklist
  one symbol such as XMR.
- Exchange-side protection, restart hydration, trailing-stop mutation, duplicate prevention,
  and broker routing required explicit fail-closed tests and evidence.
- Spot brokers were being queried by a position manager even though Spot accounts do not
  expose Futures positions. Phemex could also produce repeated disconnected errors. Broker
  activation was bounded so disabled or Spot-only position sources do not participate in the
  Futures trailing path.
- The existing paper demonstration read persistent runtime cooldown state. As a result, a
  nominally deterministic demo could be affected by previous runs and was not suitable for
  investor presentation.
- Long-horizon research candidates were collecting valid prospective data, but waiting many
  months for every final gate would prevent a timely initial delivery.
- No existing strategy had passed the complete standard for statistically defensible,
  cost-adjusted, out-of-sample profitability.

## The decision made today

We separated two goals that must not be confused:

1. **Initial investor release:** deliver a bounded VST/shadow product that demonstrates the
   actual execution chain, fail-closed safety controls, deterministic evidence, and technical
   reviewability.
2. **Durable edge validation:** continue research independently until positive net expectancy
   survives fees, funding, slippage, temporal folds, bootstrap uncertainty, concentration
   limits, and genuinely unopened/prospective outcomes.

This separation avoids two bad outcomes: delaying any product delivery for months, or claiming
profitability before the evidence supports it. The current release may demonstrate trades in a
test exchange account, but it does not automatically admit negative-expectancy strategies or
use real funds.

## Work completed for the initial release

### Release definition and gap assessment

- `TASK-0223` froze the bounded investor-release scope and its permitted claims.
- `TASK-0224` reconciled current source, tests, and evidence. It identified two P0 demo
  blockers: persistent-state contamination and the lack of a dedicated fail-closed launcher.

### Deterministic, broker-free demonstration

- `TASK-0225` isolated the paper demonstration from runtime cooldown/trade state.
- Repeated runs produced 87 PAPER decisions and 174 valid hash-chain records with zero
  exchange sends.
- `TASK-0226` added `python scripts/run_investor_demo.py`, a dedicated argument-free launcher
  that exposes no production or authenticated broker option and fails if an exchange send is
  observed.

### Investor-visible exchange proof

- `TASK-0227` added a separate, explicit-opt-in BingX VST proof. It checks VST mode,
  BingX-only routing, current protection coverage, duplicate position state, current configured
  leverage, and a maximum 20 USDT order size before using the normal broker risk path.
- ADAUSDT was rejected by the existing cooldown gate; the gate was not cleared or bypassed.
- One DOGEUSDT LONG was then executed on BingX VST: quantity 219, approximately 19.92 USDT,
  configured leverage 5x, isolated margin, order ID `2097618310297292800`.
- Independent exchange readback confirmed the position plus `STOP_MARKET` and
  `TAKE_PROFIT_MARKET` protection. The account-wide audit found no open VST position missing
  SL or TP at that checkpoint.
- This is proof of test-exchange execution and protection, not proof of profitable signals.

### Reproducible economic baseline

- `TASK-0228` froze the canonical journal input and generated attribution using SHA-256-bound
  artifacts.
- Source: 1,913 rows, reduced to 1,257 final trade IDs after resolving 656 duplicate state rows.
- Recorded PnL: -14,935.7042 USDT.
- Recorded signed fees: -559.710655 USDT.
- Cost-adjusted PnL: -15,495.414855 USDT.
- Expectancy: -12.32729901 USDT per trade; profit factor: 0.15008542; maximum drawdown:
  15,557.062582 USDT.

These aggregate numbers are not a forecast of the current capped version. The journal includes
56 trades above 1,000 USDT notional and averages 985.21 USDT, while the current VST order cap is
21 USDT. It also lacks regime labels for all records and lacks MFE, MAE, funding, and measured
slippage in this artifact. It is nevertheless decisive evidence that the complete historical
mixture cannot be presented as a profitable system.

There are useful descriptive leads: the historical `<=25 USDT` group, MeanReversion, and a
small OIFootprint sample are positive. They are post-result slices, not preregistered OOS tests,
so they are research inputs rather than investable claims.

### Regression status

After the controlled VST launcher was added, the full repository suite completed with
**1,049 passed and 1 skipped**. The skipped test is an optional import-layering gate whose local
dependency is not installed; it is recorded as technical-review work rather than hidden.

## What the initial investor version contains

The first deliverable targets technical credibility and controlled operation:

- deterministic one-command paper demonstration;
- a separately authorized, capped VST transaction visible in exchange history;
- central risk admission with per-order and portfolio exposure limits;
- duplicate-symbol and cooldown gates;
- isolated-margin and configured-leverage verification at the BingX entry boundary;
- mandatory exchange-side SL/TP with automatic unwind on protection failure and a kill switch
  if the unwind also fails;
- trade/evidence journaling and reproducible research artifacts;
- explicit limitations and a no-trade strategy-admission default;
- a technical-review index and architecture/evidence package, which are the next packaging tasks.

Real-money deployment, capital scaling, and a profitability claim are explicitly outside this
initial version.

## Current stage

The execution demonstration and the baseline-economics decision are complete. We are now in the
**investor evidence packaging and technical-review stage**. The immediate work is to bind the
release to exact commits, tests, risk claims, known limitations, reproducible commands, and
reviewer entry points. In parallel, prospective research continues without changing frozen
candidate rules after outcomes are visible.

The current economic policy is:

> If no strategy passes its evidence floor, the release remains a safe VST/shadow demonstration
> and does not force trades merely to look active.

## Next targets

### Initial delivery target

1. Produce a commit-bound investor evidence report and limitation statement.
2. Produce a technical-review index covering execution, risk, protection, reconciliation,
   strategy, data quality, telemetry, and their tests.
3. Add a concise architecture and data-flow diagram.
4. Verify the deterministic demo, VST evidence, full suite, and documentation from a clean
   reviewer workflow.
5. Perform a dead-code inventory; remove only individually proven unused code in isolated,
   reversible commits if it does not delay the release.
6. Freeze the initial release with an honest `DEMO_READY` or `NO_GO` verdict.

### 30-day target

- Operate the bounded VST/shadow workflow and collect clean, version-bound observations.
- Improve economic telemetry: entry/exit fees, funding, measured slippage, MFE/MAE, exit type,
  and configuration provenance.
- Preregister promising historical leads against a fresh outcome boundary before evaluation.
- Validate trailing/breakeven/profit-lock alternatives only through preregistered counterfactual
  or forward cohorts; do not tune the 5% or other thresholds from already inspected winners.

### 90-day target

- Require cost-adjusted walk-forward/OOS results, temporal breadth, bootstrap confidence bounds,
  symbol/side concentration checks, and realistic execution assumptions.
- Admit only strategies with positive net expectancy and PF above 1 across the frozen gates.
- Continue no-trade behavior for rejected or insufficiently sampled regimes.
- Prepare a bounded pilot proposal only if evidence is positive and operational controls remain
  verified.

### 180-day target

- Seek genuinely prospective confirmation across multiple market regimes.
- Reassess architecture or strategy families only if the disciplined candidate queue fails,
  preserving negative results rather than repeatedly tuning the same data.
- Consider a real-money pilot only through a separate approval gate covering capital, legal and
  compliance implications, security, monitoring, rollback, and loss limits.

## How progress will be judged

Engineering activity and trade count are not the objective. The durable target is positive,
risk-controlled **net expectancy** after realistic costs. A strategy is not admitted because it
has a high win rate, looks good in one symbol, or improves after post-hoc filtering.

The project is on the right path when every important claim is reproducible, negative results
change admission decisions, test-account execution remains protected, and future strategy
changes are evaluated against frozen prospective/OOS gates.

## Current conclusion

Lynxion is technically real and can demonstrate controlled execution on an exchange test
account. Its historical aggregate does not establish profitability, and the current team is not
hiding that fact. The chosen plan is to deliver a credible initial technical product now, prevent
avoidable loss paths, and continue disciplined edge validation rather than either waiting
indefinitely or overstating the evidence.
