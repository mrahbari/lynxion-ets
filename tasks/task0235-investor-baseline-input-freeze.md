# TASK-0235 — Investor baseline input freeze

## Scope

Repair reproducibility of the investor economic baseline without changing its cohort, rows,
metrics, verdict, or the append-only runtime journal.

## Defect

The manifest pinned the original journal SHA-256, but its reproduction command referenced the
mutable runtime journal. New completed trades changed that file, so the documented command could
no longer reproduce the frozen artifact.

## Minimal repair

- Recover exactly the first 1,913 data rows plus header from the append-only journal.
- Require that recovered bytes match the already frozen input SHA-256 before writing a snapshot.
- Point the manifest reproduction command and input path to the immutable snapshot.
- Reproduce identical economic metrics. The artifact hash may change only because its embedded
  `journal_path` now names the immutable snapshot; the new artifact hash is then frozen.

## Boundary

No historical record is edited or inferred. No current journal row is removed. No strategy,
runtime, broker, risk, candidate, or economic verdict changes.

## Evidence

- The recovered 1,913-row snapshot matches the original frozen input SHA-256
  `96765d50515cf8a48e3b2c556401649357ec946231388084e2957087153126c9`.
- Reproduction retained N=1,257, cost-adjusted PnL -15,495.414855 USDT, expectancy
  -12.32729901 USDT, PF 0.15008542 and max drawdown 15,557.062582 USDT.
- The new artifact SHA-256 is
  `b3822a9bf1193f9b76274e3b4be53924971e85ff201a825a2ed7542436ef9e06`;
  its economic content is unchanged and its source path now names the immutable snapshot.
- Materialization regressions: 2 passed.

## Verdict

`KEEP — BASELINE INPUT IS NOW IMMUTABLE AND REPRODUCIBLE`.
