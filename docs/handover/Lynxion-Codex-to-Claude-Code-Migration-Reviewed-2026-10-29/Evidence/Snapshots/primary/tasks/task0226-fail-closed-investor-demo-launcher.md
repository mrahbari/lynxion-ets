# TASK-0226 — Fail-closed investor demo launcher

## Scope

Add one explicit broker-free investor-demo entry point over the isolated TASK-0225
scenario. Do not expose production, testnet, broker, network, strategy, or tuning options.

## Implementation

- `python scripts/run_investor_demo.py` accepts no operational arguments.
- It forces paper mode, removes the live-trading opt-in, and emits a machine-readable
  banner stating that network, broker execution, and profitability claims are disabled.
- The underlying scenario emits the same contract in its JSON result.
- The scenario exits non-zero unless all 87 decisions route to PAPER, the hash-chained
  ledger verifies, and exchange-send count is exactly zero.
- Production-style arguments such as `--mode production` are rejected by the parser.

## Evidence

- Focused launcher/guard/risk suite: 35 passed.
- Direct launcher run: 87 PAPER decisions, 174 verified ledger records, and zero
  exchange sends.
- Full suite: 1,042 passed, one optional import-layering test skipped.

## Decision

`KEEP — P0-IR2 CLOSED`. The investor demo now has a dedicated structurally broker-free
command. This demonstrates execution-safety mechanics using deterministic assumptions;
it is not a backtest, market simulation, or profitability result.

## Next

TASK-0227: freeze the current reproducible cost-adjusted economic baseline and investor
no-trade admission verdict without reopening rejected candidate outcomes.
