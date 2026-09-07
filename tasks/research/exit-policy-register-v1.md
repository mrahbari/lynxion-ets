# Exit Policy Register v1 — Prospective net-profit floor

## Status and boundary

`PREREGISTERED — OUTCOMES UNOPENED — RUNTIME DISABLED`

This protocol may activate only after the TASK-0185 execution fix is deployed into a
new empty cohort. The 98 historical BingX exits and every pre-fix lifecycle event are
excluded from membership and parameter selection.

## Paired policies

Each eligible post-boundary position is evaluated in shadow under both policies using
the same timestamped mark observations. Neither policy may place, cancel, or amend an
order during this experiment.

- **A — current reviewed policy:** +6% ROE breakeven trigger, 0.35% price buffer,
  +10% ROE trailing trigger, 0.50% price trail, monotonic stop.
- **B — candidate net-floor policy:** once observed ROE first reaches +12%, set a
  monotonic stop intended to retain at least +5.0% net ROE after the frozen cost model.
  Before +12%, behave exactly as A. After activation, B may ratchet tighter but never
  loosen below its net-floor price.

The +12%/+5% pair is frozen from the operator's stated hypothesis before prospective
outcomes. No +10/+4, +10/+5, +12/+4, symbol, side, or regime variants may be opened.

## Cost and executable-price model

- Use authoritative per-position 10x leverage; missing/malformed/mismatched leverage
  makes the position ineligible and is reported.
- Primary round-trip friction: actual recorded entry/exit fees plus 0.10% price
  slippage round trip. Stress: actual fees plus 0.20% price slippage.
- Funding is applied at every settlement strictly between entry and terminal exit with
  the correct side sign.
- Candidate floor conversion includes remaining exit friction; it may not equate gross
  ROE with net ROE.
- A shadow stop can fill only after a subsequent mark/candle observation crosses it.
  Same-observation activation and fill are forbidden. Adverse gap fills use the first
  available executable price, never the requested stop price.
- If both protective stop and TP are crossed in one same timestamp/candle, stop takes
  priority. Missing intervals invalidate that position rather than assuming no cross.

## Eligibility and frozen gates

- Minimum 100 paired completed positions, including at least 30 positions reaching
  +12% observed ROE.
- At least eight UTC weeks, five symbols, 15 LONG and 15 SHORT completions.
- Lifecycle linkage >=95%; authoritative terminal price/fee/time >=90%; zero causal,
  boundary, leverage, lookahead, or stop-chain integrity violation.
- Candidate B must beat A on paired mean net return by >0 with a position-clustered
  95% bootstrap CI lower bound >0 under primary friction.
- B net expectancy >0 and PF >1.10 in aggregate and in at least three of four forward
  chronological folds; no fold may have negative expectancy worse than A.
- Candidate improvement must remain >0 under stress friction, in both LONG and SHORT,
  and after excluding the top contributing symbol.
- Peak-to-trough equity drawdown under B may not exceed A, and worst 5% expected
  shortfall may not worsen by more than 10% relative.

Failure of any gate is `REJECT`; incomplete coverage is `COLLECTING`. Passing every
gate is `KEEP_FOR_SEPARATE_DEPLOYMENT_REVIEW`, not authorization to trade it.

## Sequential integrity

No result is inspected before the minimum coverage gate. Code/hash, activation UTC,
cost assumptions, bootstrap seed, and evaluator tests must be committed before the
first eligible observation. Repeated looks, early stopping, and parameter replacement
after outcomes are prohibited.
