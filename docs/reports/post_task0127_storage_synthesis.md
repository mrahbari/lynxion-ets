# Post-TASK-0127 Storage Synthesis

## Decision

The full 2023–2026 BTC+ETH aggregate-trade corpus remains NO_GO. Its 49.18 GB compressed footprint
cannot coexist with the frozen 20 GiB reserve. The reserve will not be weakened and external storage
will not be introduced without an operator gate.

A bounded, preregistration-safe panel is feasible using **BTCUSDT only, 2024-01-01 through
2026-08-29**:

- 2024 compressed bytes: 6,819,713,454
- 2025 compressed bytes: 6,703,338,120
- 2026 through August 29: 4,824,990,812
- total: 18,348,042,386 bytes (~17.1 GiB)

This leaves more than the 20 GiB reserve on current storage while allowing a resumable compressed
raw cache and one-archive-at-a-time normalization. The bounded dates are fixed for storage reasons
before feature or outcome inspection: 2024 can serve as temporal reverse and 2025–2026 as primary.

## Acquisition Boundary

The next task is acquisition only. Stream each checksum-verified daily ZIP into deterministic native
15-minute aggregate-trade summaries, retaining the compressed raw cache and never expanding the
corpus in full. Census at minimum signed aggressive quote volume, trade count, quote-volume moments,
maximum trade size, and upper-tail concentration. Do not define thresholds, signals, trades, or PnL.

The normalized data gate must enforce exact timestamp units, maker-side semantics, numeric validity,
monotonic aggregate-trade IDs/times within archives, duplicate/conflict detection, complete archive
coverage, explicit gaps, reproducible hashes, and the 20 GiB free-space reserve.
