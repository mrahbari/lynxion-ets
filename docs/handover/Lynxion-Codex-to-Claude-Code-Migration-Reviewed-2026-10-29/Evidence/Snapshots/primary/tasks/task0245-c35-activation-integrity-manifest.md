# TASK-0245 — C-35 activation integrity manifest

## Scope

Freeze and verify the exact prospective protocol, collector, evaluator, boundary, universe, public
network contract, and source commit before any C-35 observation.

## Evidence

- Manifest binds the three source SHA-256 hashes and source commit `56e07138e7d1c580611d2fda28191e4742fac2b7`.
- Verifier fails closed on identity, boundary, universe, network-contract, file-hash, or commit-
  ancestry drift.
- Three focused tests pass for exact acceptance plus hash and boundary rejection.
- Manifest remains `PREPARED_NOT_ACTIVATED`; no candle, signal, or outcome exists.

## Verdict

`KEEP — COMMIT-BOUND C-35 PREFLIGHT READY; CONTROLLED FIRST PUBLIC RUN NEXT`.
