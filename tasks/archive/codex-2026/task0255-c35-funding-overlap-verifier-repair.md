# TASK-0255 — C-35 funding overlap verifier repair

## Defect

The hourly public refresh correctly appends a new coverage receipt even when its response contains
the same already-recorded settlements. Because the raw response body and SHA-256 can be identical,
one funding record may legitimately be covered by multiple overlapping successful requests. The
verifier incorrectly required exactly one matching receipt and failed closed on valid evidence.

## Minimal repair

Require at least one same-symbol, same-source-hash request range covering the settlement. Preserve
receipt deduplication, settlement deduplication, request-range validation, and all boundary checks.
Do not weaken source binding: a missing or different response hash still fails.

## Evidence

Added a regression for repeated overlapping coverage with the same response body. Five funding-
ledger tests pass, and the live ledger verifies after the repair.

## Verdict

`KEEP — VALID REPEATED PUBLIC COVERAGE NO LONGER FAILS; SOURCE BINDING PRESERVED`.
