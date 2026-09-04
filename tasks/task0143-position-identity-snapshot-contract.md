# TASK-0143 — Position Identity Snapshot Contract

**Status:** READY — DISCONNECTED SPECIFICATION

## Objective

Define the smallest restart-safe identity record needed to join an authoritative terminal order to
the exact forward-observed position without changing execution or broker reconciliation.

## Required Contract

- Schema version and deterministic record ID.
- Manager `position_key`, normalized symbol, position side, entry price, quantity, authoritative
  leverage, first/last observed UTC times, and observer run ID.
- Optional exchange position/order identifiers only when genuinely present.
- Atomic replacement, corruption detection, deterministic validation, and secret/account-field
  rejection.
- Explicit lifecycle states for open, closure-observed, and terminal-evidence-complete; no deletion
  is required for the initial disconnected implementation.
- Ambiguous symbol/side matches fail closed and cannot emit an exit-fill event.

## Sealed Boundary

The first implementation must be disconnected from ActivePositionManager, reconciliation,
composition roots, and broker adapters. It may only implement validation/storage and tests under a
temporary directory. Runtime wiring and terminal-fill emission remain later gates.

## Non-Goals

- No broker query, order, runtime deployment, historical backfill, threshold/strategy change,
  prospective boundary, or profitability conclusion.
