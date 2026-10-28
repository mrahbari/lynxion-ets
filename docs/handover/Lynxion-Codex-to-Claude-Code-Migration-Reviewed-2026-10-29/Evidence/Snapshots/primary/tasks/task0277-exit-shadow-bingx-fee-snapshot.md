# TASK-0277 — Exit-shadow BingX public fee snapshot

## Scope

Freeze and verify the official public BingX perpetual-futures base fee schedule before creating the
replacement prospective exit-shadow cohort. Do not authenticate, query an account, start a runtime,
open outcomes, or change trading policy.

## Evidence

- Official BingX support page retrieved at `2026-09-12T16:44:38Z` states 0.05% taker and 0.02%
  maker fees for perpetual futures; VIP discounts are explicitly not assumed.
- The snapshot treats retrieval time as the earliest evidenced effective time. A cohort boundary
  must therefore be strictly later than `2026-09-12T16:44:38Z`.
- Canonical SHA-256 binds the complete supplied snapshot, including provenance and scope.
- Three focused regressions reject rate/hash drift, a pre-capture boundary, and discounted scope.

## Verdict

`KEEP — AUTHORITATIVE PUBLIC BASE FEE SNAPSHOT FROZEN; NEW LATER COHORT STILL REQUIRED`.
