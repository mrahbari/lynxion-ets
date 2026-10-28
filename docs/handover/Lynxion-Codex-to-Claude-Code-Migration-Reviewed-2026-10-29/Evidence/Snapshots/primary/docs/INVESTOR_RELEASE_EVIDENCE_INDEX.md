# Lynxion Investor Release Evidence Index

**Frozen:** 2026-09-09  
**Evidence code boundary:** `1f07520`  
**Verdict:** `INVESTOR_REVIEW_READY — TECHNICAL VST/SHADOW ONLY`

This index classifies the claims allowed in the initial investor release. It does not claim
profitability, break-even operation, pilot readiness, production readiness, or approval for real
capital.

## PROVEN TECHNICAL CAPABILITY

| Claim | Evidence | Reproduction or review entry point |
|---|---|---|
| Deterministic broker-free demo | 87 PAPER decisions, 174 verified records, zero exchange sends | `python scripts/run_investor_demo.py`; `tests/unit/test_investor_demo_isolation.py` |
| Bounded BingX VST execution | TASK-0227 dated one-order proof | `scripts/run_investor_vst_demo.py`; `tasks/task0227-controlled-investor-vst-order.md` |
| Exchange-side SL/TP protection | Dated BingX VST readback with no unprotected position at checkpoints | `scripts/audit_vst_protection.py`; BingX adapter protection tests |
| Central VST exposure caps | 21 USDT per order and 1,000 USDT aggregate notional | `infrastructure/risk/risk_enforcement.py`; risk-enforcement tests |
| Isolated authoritative leverage admission | Broker rejects missing, stale, malformed, cross, or mismatched leverage state | `tests/unit/test_task0135_leverage_contract.py` |
| 10x exit arithmetic | 6% ROE breakeven and 10% ROE trailing boundaries tested with float-safe equality | `tests/unit/test_task0232_lynxion_vst_leverage.py` |
| Demo/research separation | Canonical demo identity excluded from attribution and prospective edge monitoring | TASK-0230 tests and demo-order registry |
| Current repository regression | 1,056 passed, one optional layering test skipped | `pytest -q` at code boundary `1f07520` |

Technical observations are dated. They prove that the tested path worked at its checkpoint, not
that mutable exchange state is permanently healthy.

## PROSPECTIVE RESEARCH IN PROGRESS

| Candidate or stream | Current state | Constraint |
|---|---|---|
| C-11 severe funding | `COLLECTING`; one completed negative record at the latest due update | Only settlements strictly after epoch 1788082349; all frozen gates remain binding |
| C-33 liquidation/order-flow | `COLLECTING`; public append-only ledger | No historical import; gaps and interrupted sessions remain ineligible |
| Forward exit observation | Fresh commit-bound cohorts | No historical event may be imported into a new activation boundary |
| Bounded causal hypothesis cycle | Not yet promoted | At most five independent preregistered mechanisms; costs, OOS/WFO, bootstrap and prospective gates required |

## NOT YET PROVEN ECONOMICALLY

- No strategy has demonstrated durable positive net expectancy after fees, funding, slippage,
  chronological OOS/WFO, bootstrap uncertainty, drawdown, concentration and prospective gates.
- The frozen historical mixture is negative: 1,257 final trades, -15,495.414855 USDT
  cost-adjusted PnL, -12.32729901 USDT expectancy, and profit factor 0.15008542.
- Positive small-notional, MeanReversion and OIFootprint slices are post-hoc or under-sampled leads,
  not admissible edge evidence.
- 10x leverage changes margin, liquidation headroom and ROE trigger timing; it does not create edge
  or improve dollar expectancy for an unchanged capped notional and price path.
- The investor release therefore retains a no-trade economic admission default.

## Release limitations

- The TASK-0227 exchange proof was a dated 5x position. New `./lynxion` entries request isolated
  10x, but the first new-entry exchange readback remains a separate runtime observation.
- Historical attribution lacks complete regime, MFE, MAE, measured slippage and funding fields.
- CCUSDT and HYPEUSDT are excluded when their data exceeds the missing-data threshold; XMR remains
  blacklisted. These are safety exclusions, not edge improvements.
- The local optional architecture-layering test requires `import-linter` and was skipped.
- Real-money use remains an explicit future approval gate.

## Verdict rationale

The bounded demonstration and reviewer package are reproducible, the known investor-scope P0 demo
defects are closed, negative economics are disclosed, and no profitability claim is made. That is
sufficient for `INVESTOR_REVIEW_READY` as a technical VST/shadow release. It is insufficient for
`PILOT_REVIEW_READY`, strategy admission, capital scaling, or live deployment.
