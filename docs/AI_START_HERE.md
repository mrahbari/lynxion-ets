# Lynxion ETS — AI Start Here

**Purpose:** Canonical handoff packet for a new senior AI agent or technical reviewer

**Prepared:** 2026-09-14

**Source checkpoint:** `5c591a6` (this document is committed after that checkpoint)

**Branch at preparation:** `task-00-ground-truth-audit`

**Current economic verdict:** `COLLECTING — PROFITABILITY NOT PROVEN`

## 1. Instructions to the receiving AI

Treat repository source, tests, frozen research manifests, and reproducible artifacts as evidence.
Treat prose, previous-agent statements, logs, and dated exchange observations as claims that may be
stale. Never infer profitability from implementation quality, green tests, win rate, leverage, or a
small positive sample.

Before proposing or making a change:

1. read `AGENTS.md` and `tasks/00-right-path.md` completely;
2. inspect `docs/ROADMAP_INDEX.md` and the header plus latest entries of
   `docs/LYNXION_PROGRESS_LEDGER.md`;
3. inspect the current task and the relevant frozen candidate preregistration;
4. run `git status --short` and `git log -1 --oneline`;
5. classify material claims as `FACT`, `INFERENCE`, `HYPOTHESIS`, or `UNKNOWN`;
6. preserve task boundaries and make the smallest justified change;
7. test behavioral changes and preserve reproducible evidence;
8. do not weaken a frozen gate after outcomes become visible.

Do not treat this snapshot as live truth indefinitely. Refresh changing counts, runtime state,
exchange state, test totals, process ownership, and Git state from their primary sources.

## 2. Mission and success definition

The mission is to determine whether Lynxion has a statistically defensible, risk-controlled trading
edge and, if current strategies do not, test bounded causal alternatives until either:

- a candidate demonstrates positive net expectancy after realistic fees, funding, and slippage,
  survives chronological OOS/WFO and uncertainty tests, has acceptable drawdown and concentration,
  and replicates prospectively across the frozen breadth gates; or
- the bounded hypothesis cycle demonstrates that the current strategy family or information set is
  insufficient, triggering an explicit new-data, new-strategy-family, or architecture hypothesis.

More trades, higher win rate, 10x leverage, a profitable slice found after inspection, and a working
broker path are not substitutes for edge.

## 3. Two separate project tracks

### Track A — Investor technical release

The initial package is frozen as:

`INVESTOR_REVIEW_READY — TECHNICAL VST/SHADOW ONLY`

Evidence boundary: `1f07520`, frozen by TASK-0234.

This means the repository has a reviewable deterministic broker-free demo, bounded BingX VST
evidence, risk/protection controls, evidence classification, and reviewer documentation. It does
not mean profitable, break-even, pilot-ready, production-ready, or approved for real money.

Canonical release evidence:

- `docs/INVESTOR_RELEASE_EVIDENCE_INDEX.md`
- `docs/README_INVESTOR_RELEASE.md`
- `docs/README_AGENT_TECHNICAL_REVIEW.md`
- `docs/INVESTOR_RELEASE_ROADMAP.md`

### Track B — Economic edge validation

This track remains active and must not borrow credibility from Track A. Economic admission retains
`NO_TRADE_DEFAULT` until every applicable frozen gate passes.

Current dated snapshot:

| Candidate | State | Current evidence | Correct interpretation |
|---|---|---|---|
| C-35 compression release | `COLLECTING` | 90 decisions; two completed positive cost-adjusted outcomes; both SHORT, two symbols, one UTC week | Encouraging individual outcomes, statistically insufficient; aggregate economics sealed |
| C-11 severe funding | `COLLECTING` | Two completed outcomes and one pending ETHUSDT candidate | Insufficient sample; only settlements strictly after epoch `1788082349` count |
| C-33 liquidation exhaustion | `COLLECTING` | Liveness restored; 741 eligible buckets in one resumed public session | Below next frozen 1,000-bucket checkpoint; no edge verdict |
| +12%/+5% exit shadow | `NOT ACTIVATED` | Repository prerequisites and public BingX fee snapshot prepared | Still requires fresh read-only single-runner proof of zero missing stops and applicable runtime/authenticated approval |

The C-35 governing preregistration is `tasks/research/edge-candidate-register-v34.md`. C-11 is
governed by `tasks/research/edge-candidate-register-v10.md`. Do not import historical records into
either prospective cohort.

## 4. Why the current method can discover edge

The active acceleration constraint is `docs/EDGE_ACCELERATION_WITHOUT_PLATFORM_EXPANSION.md`.
Its current ranked decision artifact is `docs/EDGE_ACCELERATION_DECISION_2026-09-14.md`.

The research loop is deliberately adversarial:

```text
historical attribution
    -> causal hypothesis
    -> preregistration before outcomes
    -> data-integrity and provenance gate
    -> cost-adjusted historical/OOS evaluation where admissible
    -> forward prospective collection
    -> frozen aggregate and breadth gates
    -> KEEP / REJECT / INSUFFICIENT verdict
    -> minimal production proposal only after promotion
```

Each hypothesis must freeze its universe, timeframe, side, regime, signal, entry, exit, costs,
sample size, folds, uncertainty method, concentration, drawdown, stress assumptions, and rejection
criteria before opening outcomes. Parameter variants on the same inspected panel are not independent
hypotheses.

If a candidate fails, preserve the negative result and move to the next preregistered causal
mechanism. If the bounded cycle fails, explicitly assess whether better information is required;
do not endlessly tune thresholds on opened data.

## 5. Economic validation standard

No candidate is admitted without all applicable evidence:

- correct deduplication and entry/outcome identity;
- no lookahead, lag mismatch, incomplete candle, survivorship, or MTF alignment error;
- candle high/low handling for SL/TP, with conservative intrabar ambiguity;
- realistic execution price, fees, funding, slippage, and partial-fill treatment;
- positive net expectancy and profit factor above 1;
- chronological OOS or walk-forward survival;
- clustered bootstrap confidence assessment;
- temporal, symbol, and side breadth;
- bounded concentration and peak-to-trough equity drawdown;
- positive stress-cost behavior;
- genuinely unopened prospective confirmation.

Failure or insufficient evidence keeps the candidate out of production admission.

## 6. System orientation

Lynxion is a Python event-driven crypto-perpetual trading and research system. BingX VST is the
preferred broker integration target. Its major layers are:

```text
market data -> watchers/engines -> fusion/strategies -> execution intent
            -> risk enforcement -> execution guard -> broker adapter
            -> exchange acknowledgement/protection -> reconciliation/journals
```

Useful entry points:

| Area | Entry point |
|---|---|
| Main runtime | `run_trading_system.py` and `./lynxion` |
| Deterministic broker-free investor demo | `scripts/run_investor_demo.py` |
| Explicit controlled BingX VST demo | `scripts/run_investor_vst_demo.py` |
| BingX execution boundary | `infrastructure/brokers/adapters/bingx_adapter.py` |
| Central risk enforcement | `infrastructure/risk/risk_enforcement.py` |
| Active protection/trailing | `infrastructure/risk/active_position_manager.py` |
| C-35 hourly research | `scripts/run_c35_hourly.py` |
| C-11 prospective funding | `scripts/update_c11_prospective_funding.py` |
| C-33 checkpoint | `scripts/check_c33_checkpoint.py` |

Do not assume that the high-level architecture is the actual call path. Trace constructors,
dependency injection, event subscriptions, and adapter dispatch in the current source before making
a behavioral claim.

## 7. Safety and authorization boundary

Repository-safe analysis, tests, public-data research collection, documentation, and minimal
evidence-supported source fixes may proceed within the active task policy. The following remain
separate approval gates even if an operator previously authorized ordinary autonomous work:

- real funds or live-account exposure;
- starting or reloading a trading runtime;
- authenticated broker queries or order/position/account mutation;
- secrets or security-boundary changes;
- destructive/data-loss actions;
- paid services;
- legal/compliance decisions;
- merges or materially different architecture.

Never place an order merely to generate evidence. Investor technical-demo identities must remain
excluded from edge metrics.

## 8. Known ground truth and unresolved risks

### Supported technical conclusions

- The investor demo P0 isolation and fail-closed launcher gaps were closed by TASK-0225/0226.
- TASK-0234 froze a technical-only investor package; its claims are tied to a dated evidence
  boundary, not permanently current runtime state.
- Central risk, broker protection, routing, leverage/margin admission, trailing monotonicity,
  restart hydration, and evidence integrity have focused regression coverage.
- The C-35 pipeline deadlock discovered after its first prospective signal was fixed in `fda57ea`;
  this enabled correct outcome-before-next-signal progression but did not create market edge.

### Not proven or still open

- Durable positive expectancy is not proven.
- Current mutable BingX position/protection state is not established by old readbacks.
- The exit-shadow activation lacks its final fresh single-runner stop-visibility evidence.
- C-35 signal frequency is low; it cannot be the only schedule for investor delivery.
- Historical journals mix different code, sizing, and configuration eras and lack complete MFE,
  MAE, measured slippage, funding, regime, and configuration provenance.
- Optional cleanup is subordinate to correctness and edge work; do not delete code without proven
  reachability and regression evidence.

## 9. Historical evidence warning

Superseded comprehensive strategy roadmaps and old project-context snapshots were removed in
TASK-0326 because their Alpha/edge labels, exact runtime counts, exchange-state assertions, and
strategy recommendations were no longer admissible current evidence. Tracked versions remain in
Git history for forensic use. Do not revive their conclusions without reproducing them from current
source and evidence. The dated `docs/INVESTOR_RELEASE_GAP_ASSESSMENT.md` remains only as a valid
record of the pre-fix gap state, not as the current release verdict.

## 10. Recommended first-pass commands

These are read-only or local verification commands. Network, broker, runtime, and mutation commands
still require the applicable task authority.

```bash
git status --short
git log -1 --oneline
sed -n '1,220p' AGENTS.md
sed -n '1,240p' tasks/00-right-path.md
sed -n '1,240p' docs/ROADMAP_INDEX.md
sed -n '1,100p' docs/LYNXION_PROGRESS_LEDGER.md
tail -220 docs/LYNXION_PROGRESS_LEDGER.md
python scripts/verify_c35_candle_ledger.py
python scripts/verify_c35_funding_ledger.py
python scripts/verify_c35_signal_ledger.py
python scripts/check_c35_signal_throughput.py
python scripts/check_c33_checkpoint.py
```

Do not run `./lynxion`, `run_trading_system.py`, authenticated broker scripts, or order demos solely
because they appear in this handoff.

## 11. What the receiving AI should deliver

For reviews, return:

1. verified current Git/worktree state;
2. current Track A and Track B verdicts without mixing them;
3. contradictions between docs and source/evidence;
4. the first unfinished bounded roadmap unit;
5. its acceptance criteria and required evidence;
6. any genuine blocker or approval gate;
7. explicit uncertainty and negative findings.

For implementation work, continue from the first unfinished task, preserve preregistration and
evidence boundaries, make minimal changes, run proportionate tests, document results, and commit one
reviewable unit at a time.

## 12. Copy-paste prompt for another AI

```text
You are reviewing and continuing the Lynxion ETS repository. Begin by reading AGENTS.md,
docs/AI_START_HERE.md, tasks/00-right-path.md, docs/ROADMAP_INDEX.md, the header and latest entries
of docs/LYNXION_PROGRESS_LEDGER.md, and the current task plus its relevant frozen preregistration.
Verify Git and data state before relying on dated counts. Treat source/tests/frozen artifacts as
evidence and prose as potentially stale. Separate the technical investor-release verdict from the
economic edge verdict. Do not claim profitability, pilot readiness, runtime health, or broker state
without current reproducible evidence. Preserve NO_TRADE_DEFAULT and all preregistered gates. Do not
place orders, start/reload runtime, call authenticated broker paths, mutate accounts, expose secrets,
merge, delete data, or change production policy without the applicable explicit approval. Identify
the first unfinished bounded roadmap unit and proceed with minimal evidence-supported work.
```
