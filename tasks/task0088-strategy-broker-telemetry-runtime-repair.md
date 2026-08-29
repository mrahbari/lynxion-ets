# TASK-0088 — Strategy-to-Broker Telemetry Runtime Repair

**Priority:** P0 execution liveness
**Status:** IMPLEMENTED AND LOCALLY VERIFIED — runtime reload pending

## Problem Evidence

On 2026-08-29 the running VST process repeatedly rejected execution intents before broker
execution with:

`AttributeError: 'EnhancedLogger' object has no attribute 'log_strategy_to_broker_flow'`

The error originated at `AutoDetectionOrchestrator._execute_strategy_for_opportunity`. The
orchestrator has four call sites for this telemetry method, while `shared.logger.EnhancedLogger`
did not implement it. Rotated runtime logs contain 375 matching failures in one captured file.

## Root Cause

The strategy-to-broker telemetry call sites and the concrete logger API had drifted. Because
the first call occurs before `execution_service.execute_trade`, a non-critical logging API
omission prevented the execution attempt itself.

## Minimal Change

Add `EnhancedLogger.log_strategy_to_broker_flow` with the exact keyword contract already used
by the orchestrator. The method records symbol, strategy, signal, confidence, reason, and
execution status through the existing `info` path. No strategy, risk, sizing, order, or exit
logic changed.

## Validation

- Focused logger and messaging regression: 10 passed.
- Full suite: 623 passed, 1 optional layering test skipped because `import-linter` is not
  installed locally.
- `git diff --check`: passed.

## Decision

**KEEP.** The missing interface is a verified execution-liveness defect and the repair is
limited to the concrete logger contract.

## Remaining Runtime Gate

The currently running VST process must reload the corrected code before runtime recovery can
be claimed. Restarting or otherwise controlling that external process remains an operational
action; local test success is not represented as deployed evidence.
