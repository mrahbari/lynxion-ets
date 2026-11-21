# TASK-0253 — C-35 funding activation preflight

## Scope

Freeze a separate integrity boundary before the first C-35 public funding query.

## Evidence

- Manifest binds the candidate protocol, funding collector, outcome resolver, boundary, universe,
  public-only network contract, and source commit `e41d9b4fd6481f94ed56fe69f5b8fa7b634d5374`.
- Preflight rejects identity, boundary, universe, network, hash, and commit-ancestry drift.
- Three focused tests pass; the real manifest verifies successfully.
- Manifest remains `PREPARED_NOT_ACTIVATED`; no funding query or outcome occurs in this task.

## Verdict

`KEEP — FUNDING PREFLIGHT COMMIT-BOUND; CONTROLLED FIRST PUBLIC QUERY NEXT`.
