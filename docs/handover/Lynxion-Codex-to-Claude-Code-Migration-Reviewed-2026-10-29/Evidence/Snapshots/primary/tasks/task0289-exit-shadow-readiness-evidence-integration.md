# TASK-0289 — Exit-shadow readiness evidence integration

## Scope

Make the repository-only readiness checker consume the already-frozen fee snapshot and replacement
empty cohort instead of permanently reporting their original absence. Do not access a broker,
start a runtime, activate the candidate, or change policy.

## Defect

The checker hard-coded all three original blockers. After TASK-0277 and TASK-0278 supplied and
verified two of them, it continued to report both as missing, creating stale operational guidance.

## Fix and evidence

- The checker now independently parses and verifies the exact replacement cohort and fee snapshot.
- Missing, malformed, hash-drifted, nonempty, or commit-invalid evidence still fails closed.
- The real repository now reports exactly one remaining blocker: fresh read-only evidence of one
  VST runner with zero positions missing stop loss.
- Focused readiness, cohort, and fee regressions pass.

## Verdict

`KEEP — STALE READINESS BLOCKERS FIXED; VST SAFETY EVIDENCE STILL REQUIRED`.
