Before writing ANY implementation code, perform a Senior Quant + Principal Software Engineer design review of the proposed Derivatives Data Layer.

IMPORTANT CONSTRAINTS

- Architecture is frozen.
- Do NOT redesign the system.
- Do NOT introduce new architectural patterns.
- Do NOT move responsibilities between layers.
- Collector must remain a pure ingestion component.
- FeatureEngine must remain a pure computation layer.
- Watchers/Fusion/Strategies remain consumers only.

Your task is NOT to improve the architecture.

Your task is to find hidden engineering risks before implementation.

Review the specification from the following perspectives:

--------------------------------------------------
1. Domain Model Review
--------------------------------------------------

Verify that every raw entity is sufficient.

FundingRate
OpenInterest

Check:

- missing fields
- timestamp correctness
- exchange identifiers
- symbol normalization
- decimal precision
- future compatibility

Do NOT invent unnecessary fields.

--------------------------------------------------
2. Feature Contract Review
--------------------------------------------------

Review every feature individually.

For each feature answer:

- mathematically correct?
- point-in-time safe?
- leakage free?
- deterministic?
- computational complexity acceptable?
- streaming compatible?
- backtest compatible?
- suitable for production?
- suitable for research?

If not,
explain why.

--------------------------------------------------
3. Dependency Review
--------------------------------------------------

Verify whether any feature secretly depends on data that is NOT guaranteed to exist.

Example:

price_oi_divergence

requires synchronized OHLCV.

Verify every dependency.

--------------------------------------------------
4. Time Alignment Audit
--------------------------------------------------

This is critical.

Verify that

Funding = every 8h

Open Interest = every 1h

OHLCV = 1m

can all be aligned WITHOUT introducing look-ahead bias.

Explain exactly how timestamps should be aligned.

Identify every possible hidden leakage.

--------------------------------------------------
5. Storage Review
--------------------------------------------------

Review whether raw storage is sufficient.

Should derived features be stored?

Or always recomputed?

Explain tradeoffs.

--------------------------------------------------
6. Performance Review
--------------------------------------------------

Estimate computational complexity.

Can this run on

11 symbols

7 years

hourly

without bottlenecks?

Identify expensive calculations.

--------------------------------------------------
7. API Review
--------------------------------------------------

Review the DTO.

Is anything missing?

Is anything redundant?

Should any field be immutable?

Should nullable values exist?

--------------------------------------------------
8. Future Extensibility
--------------------------------------------------

Can this same FeatureEngine later support

Liquidations

L2

OrderBook

Tick Tape

without breaking API compatibility?

If not,
identify the issue.

--------------------------------------------------
9. Hidden Failure Modes
--------------------------------------------------

Think like a production reviewer.

List every hidden risk such as

missing funding snapshots

exchange downtime

duplicate timestamps

clock skew

REST gaps

missing OI windows

partial downloads

NaN propagation

misaligned history

out-of-order records

and explain how they should be handled.

--------------------------------------------------
10. Final Verdict
--------------------------------------------------

Return only one of:

APPROVED

APPROVED WITH MINOR CHANGES

REQUIRES CHANGES

If changes are required:

rank them by impact

Critical

High

Medium

Low

Do NOT write code.

Do NOT refactor architecture.

Do NOT implement anything.

Perform a design audit only.