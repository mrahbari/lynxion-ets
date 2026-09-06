# TASK-0185 — Stop-admission independent review

## Scope

Review TASK-0182–0184 source and failure behavior locally. No broker call, runtime
reload, threshold change, or account mutation.

## Finding and correction

Review found one capacity-accounting defect inherited from the prior request wrapper:
rate admission occurred once outside HTTP transient retries, so up to three physical
requests could consume one token. Admission now occurs inside the retry callback and
queue timing accumulates across every physical attempt.

## Verification gates

- Every transient HTTP retry reacquires the same priority/capacity contract.
- Terminal stale/ambiguous stop responses do not multiply outer retries.
- Timestamp gets at most one outer retry.
- Stop mutation admission remains bounded to 15 seconds per physical request.
- Accepted replacement still requires exact pending identity/attributes before state
  commit.
- Global capacity and all exit thresholds remain unchanged.

## Verdict

`REPOSITORY_READY — DEPLOYMENT_GATED`. Focused and full regression suites pass. The
active runtime still executes the old code. Reloading would change the commit bound to
the active prospective exit cohort and therefore requires a new empty cohort root and
explicit runtime approval; historical events must not be mixed across the boundary.

## Next

After operator approval: record the current cohort audit, create a new empty activation
root bound to the reviewed commit, perform controlled VST-only reload, and verify one
runner plus broker-visible protective stops read-only. Otherwise keep the current
runtime and cohort untouched.
