# TASK-0244 — C-35 public append-only candle collector

## Scope

Implement the isolated public-data input required by C-35 without activating it or opening a signal
or outcome.

## Contract

- Fixed unauthenticated Binance USD-M kline endpoint, frozen six-symbol universe, 15-minute bars.
- Stores only completed candles with raw-response SHA-256 and exact decimal strings.
- Tags candles at/before the boundary `WARMUP_ONLY` and later candles `PROSPECTIVE`.
- Append-only JSONL with deterministic symbol/open-time deduplication; malformed existing evidence
  fails closed.
- No API keys, broker adapters, account state, order methods, strategy runtime, or production path.

## Evidence

Four focused regressions verify strict boundary roles, unclosed-candle exclusion, idempotent append
with provenance hash, and frozen-universe rejection.

## Verdict

`KEEP — PUBLIC COLLECTOR READY BUT NOT ACTIVATED; NO SIGNAL OR OUTCOME OPENED`.

Activation requires a separate integrity manifest and controlled first run after this commit.
