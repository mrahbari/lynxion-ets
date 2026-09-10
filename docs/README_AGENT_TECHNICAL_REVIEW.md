# Lynxion — Agent and Technical Reviewer Brief

**Snapshot date:** 2026-09-09

**Repository branch at snapshot:** `task-00-ground-truth-audit`

**Evidence code boundary:** `1f07520 fix: restore execution stablecoin guard config`

Investor-facing companion: [README_INVESTOR_RELEASE.md](README_INVESTOR_RELEASE.md)

## Review objective

Determine whether the current roadmap and investor-release claims are supported by reproducible
evidence. Review the system as two separate tracks:

1. a bounded VST/shadow technical release; and
2. continuing research toward statistically defensible positive net expectancy.

Do not infer that execution capability, green unit tests, or a successful VST order proves edge.

## Canonical verdicts

| Question | Current verdict | Evidence class |
|---|---|---|
| Can the repository run a deterministic broker-free demo? | Yes | Reproduced local test/demo evidence |
| Can the guarded path create a protected position on BingX VST? | Yes | Authenticated VST observation on 2026-09-09 |
| Was the demonstrated position isolated with SL and TP? | Yes at postflight checkpoint | Authenticated VST readback |
| Is current exchange state permanently guaranteed by that checkpoint? | No | Exchange state is time-varying |
| Does the historical aggregate show positive economics? | No | Hash-bound descriptive baseline |
| Does any positive slice currently qualify as edge? | No | Post-hoc or under-sampled; no qualifying OOS gate |
| Is real-money deployment approved or justified? | No | Outside release scope and evidence gate |
| Release policy when edge is unproven | No-trade strategy admission | Frozen decision |

## State before the investor-release track

- The codebase already implemented data ingestion, strategy selection, order entities, broker
  adapters, risk enforcement, position management, trailing/profit locks, journaling, and research.
- Historical observations were not one clean experimental cohort: sizing, risk, configuration,
  and code eras differed materially.
- Risk hardening was required at the broker boundary so symbol blacklisting could not be treated
  as the fix for a general unlimited-entry/bypass class.
- Prior work added or verified bounded VST exposure, authoritative leverage/margin checks,
  duplicate admission, mandatory protection, protection-failure unwind, kill-switch escalation,
  restart hydration, monotonic trailing mutation, and disabled-broker routing.
- Long-horizon C-11/C-33 and forward-exit work retained prospective boundaries, but their
  collection cadence did not fit the initial investor-delivery deadline.
- The pre-existing paper harness was coupled to persistent cooldown state, making presentation
  output depend on previous runtime activity.

## Decision record

`TASK-0223` separated delivery readiness from profitability validation. The release does not wait
for months of C-33 data, but it also does not lower edge gates. If no strategy qualifies, the
release demonstrates product behavior in PAPER/VST while strategy admission remains no-trade.

The following claims are intentionally distinct:

- **DEMO_READY:** safe and reproducible VST/shadow demonstration, no profitability claim.
- **INVESTOR_REVIEW_READY:** demo plus technical-review package and no open in-scope P0.
- **PILOT_REVIEW_READY:** future prospective-economic and operator-approval gate.
- **NO_GO:** any open in-scope P0, irreproducible economics, or misleading edge claim.

## Completed release units

| Task | Commit | Result |
|---|---:|---|
| TASK-0223 release-track freeze | `a9cd1a2` | Scope, claims, boundaries, and roadmap frozen |
| TASK-0224 gap assessment | `721bac1` | Two demo P0s identified; profitability unproven |
| TASK-0225 demo state isolation | `10fa173` | 87 PAPER decisions, 174 valid records, zero sends, repeatable |
| TASK-0226 fail-closed demo launcher | `a0bc14c` | Dedicated broker-free investor command; P0-IR1/2 closed |
| TASK-0227 controlled VST proof | `63b1229` | One capped isolated DOGEUSDT VST position with SL/TP verified |
| TASK-0228 economic baseline | `034bcbf` | Hash-bound negative aggregate; no-trade default retained |
| TASK-0229 reviewer READMEs | `ee56979` | Investor and technical review narratives |
| TASK-0230 demo/research separation | `86e6f0d` | Technical-demo identities excluded from edge metrics |
| TASK-0231 current VST activation | `7704c0e` | Commit-bound empty forward cohort and protected VST runtime |
| TASK-0232 10x VST launcher | `95ea6e0`, `cd338f2` | Launcher-scoped 10x plus exact ROE-boundary regression |
| TASK-0233 execution liveness | `1f07520` | Missing stablecoin-guard configuration restored |

## Safety/execution evidence to inspect

- `scripts/run_investor_demo.py`: deterministic broker-free launcher.
- `scripts/run_investor_vst_demo.py`: explicit-opt-in, one-order VST proof with pre/postflight.
- `infrastructure/brokers/adapters/bingx_adapter.py`: serialized broker admission, margin/leverage
  verification, main order, conditional protection, unwind, and kill-switch behavior.
- `scripts/audit_vst_protection.py`: read-only exchange-side protection coverage.
- `tests/unit/test_investor_demo_isolation.py`: paper-demo state isolation.
- `tests/unit/test_investor_vst_demo.py`: VST launcher preflight and cap behavior.
- `tests/unit/test_task0185_bingx_retry_admission.py`: stop-mutation admission evidence.
- `docs/INVESTOR_RELEASE_GAP_ASSESSMENT.md`: dated classifications and known gaps.

The dated TASK-0227 VST proof used the then-current configured 5x leverage. TASK-0232 later scoped
10x to new entries launched specifically through `./lynxion`; it did not mutate existing positions
or global loader defaults. The launcher requires BingX testnet and pins both leverage ceilings;
the broker boundary must establish isolated 10x and read it back before admitting a new entry.
The 21 USDT hard order-notional cap and 1,000 USDT portfolio-notional cap remain unchanged.

VST evidence at execution time:

- ADAUSDT was rejected by cooldown; no bypass or state reset occurred.
- DOGEUSDT LONG, quantity 219, reference notional about 19.92 USDT.
- BingX VST order ID `2097618310297292800`.
- Readback: leverage 5, `isolated=true`, one `STOP_MARKET`, one `TAKE_PROFIT_MARKET`.
- Account-wide postflight: three open positions, zero missing SL, zero missing TP.

This is a dated checkpoint, not a perpetual exchange-state assertion.

## Economic baseline and provenance

Reproduction command:

```bash
python scripts/performance_attribution.py \
  --journal data/research/investor_release/trade_journal_baseline_v1.csv \
  --output data/research/investor_release/cost_adjusted_baseline_v1.json
```

Frozen hashes:

```text
trade_journal.csv SHA-256:
96765d50515cf8a48e3b2c556401649357ec946231388084e2957087153126c9

cost_adjusted_baseline_v1.json SHA-256:
b3822a9bf1193f9b76274e3b4be53924971e85ff201a825a2ed7542436ef9e06
```

Canonical results:

| Metric | Value |
|---|---:|
| Source rows | 1,913 |
| Final deduplicated trade IDs | 1,257 |
| Duplicate state rows resolved | 656 |
| Recorded PnL | -14,935.7042 USDT |
| Signed fees | -559.710655 USDT |
| Cost-adjusted PnL | -15,495.414855 USDT |
| Expectancy | -12.32729901 USDT/trade |
| Profit factor | 0.15008542 |
| Max drawdown | 15,557.062582 USDT |

Interpretation constraints:

- The journal mixes incompatible eras; 56 trades exceed 1,000 USDT notional while the current
  VST per-order cap is 21 USDT.
- Every record lacks regime classification; 747 lack confidence and initial SL/TP.
- This artifact has no MFE, MAE, measured slippage, or funding attribution.
- The `<=25 USDT` slice is positive (N=719, expectancy +0.26955 USDT, PF 2.442), but it is
  post-hoc, not preregistered, not OOS, and lacks temporal/uncertainty gates.
- MeanReversion is descriptively positive at N=106; OIFootprint at N=14 is too small. Neither is
  admitted as edge.

## Validation standard for future edge claims

A credible candidate must be preregistered before its outcome boundary is opened and evaluated
with, at minimum:

- no lookahead, lag misalignment, or future-informed universe selection;
- correct multi-timeframe downsample/forward-fill/shift/alignment;
- high/low-based SL/TP path handling with conservative ambiguity rules;
- fees, funding, slippage, and realistic execution pricing;
- deduplicated causal entries/exits and partial-fill treatment;
- chronological walk-forward/OOS folds;
- clustered bootstrap confidence interval;
- positive net expectancy and profit factor above 1;
- temporal, symbol, and side breadth plus concentration limits;
- equity peak-to-trough drawdown;
- positive stress-cost result and a genuinely unopened prospective confirmation.

High win rate, a positive in-sample slice, more trades, or leverage scaling is insufficient.

## Immediate roadmap

1. Create a commit-bound release evidence report and limitation statement.
2. Create a reviewer index mapping each critical claim to source, tests, and evidence.
3. Add a concise architecture/data-flow diagram.
4. Run clean deterministic-demo and regression verification.
5. Inventory dead code using static references plus dynamic/config/plugin reachability; cleanup is
   optional, isolated, and subordinate to evidence work.
6. Freeze the initial release verdict.

## 30/90/180-day roadmap

### 30 days

- Collect version-bound VST/shadow outcomes under current caps.
- Complete fee, funding, slippage, MFE/MAE, exit-reason, and configuration provenance.
- Preregister eligible MeanReversion/small-notional/flow leads against fresh boundaries.
- Keep C-11/C-33 rules frozen and preserve negative outcomes.
- Evaluate exit-policy alternatives prospectively; do not tune breakeven/profit-lock thresholds
  after observing the same trades.

### 90 days

- Require complete cost-adjusted OOS, temporal breadth, bootstrap, concentration, and stress-cost
  gates before strategy admission.
- Retain no-trade for unsupported symbols/regimes.
- Propose a bounded pilot only if both economics and operational controls pass.

### 180 days

- Seek prospective multi-regime replication.
- If all disciplined candidates fail, reassess strategy family, data sources, or architecture as
  explicit new hypotheses rather than repeatedly optimizing opened data.
- Real-money pilot remains a separate capital/security/legal/monitoring approval decision.

## Questions an independent reviewer should answer

1. Can any documented claim be reproduced from the pinned input, commit, and command?
2. Are PAPER and VST launchers structurally separated from live execution?
3. Can any entry bypass the serialized broker-backed risk admission?
4. Does every accepted position obtain valid exchange-side protection or guaranteed unwind?
5. Are current runtime/exchange statements clearly distinguished from dated observations?
6. Does any proposed edge use a boundary selected before outcomes were inspected?
7. Are costs, folds, uncertainty, concentration, and drawdown complete?
8. Is no-trade preserved when evidence is negative or insufficient?
9. Is cleanup isolated from behavioral changes and protected against dynamic-discovery breakage?

## Reviewer conclusion supported by current evidence

The project is following a defensible direction: it has stopped treating implementation activity
as proof of profitability, has demonstrated bounded exchange-test execution, has preserved
fail-closed risk behavior, and has converted negative economics into a no-trade admission
decision. It is not yet valid to conclude that Lynxion has durable edge or is ready for real
capital. The next correct milestone is an auditable investor technical package, followed by clean
prospective/OOS economic evidence—not broader optimization of the already-opened journal.

## Frozen release verdict

`INVESTOR_REVIEW_READY — TECHNICAL VST/SHADOW ONLY` at evidence code boundary `1f07520`.
The independent evidence index is `docs/INVESTOR_RELEASE_EVIDENCE_INDEX.md`. This verdict does
not mean profitable, break-even, pilot-ready, production-ready, or approved for real funds.
