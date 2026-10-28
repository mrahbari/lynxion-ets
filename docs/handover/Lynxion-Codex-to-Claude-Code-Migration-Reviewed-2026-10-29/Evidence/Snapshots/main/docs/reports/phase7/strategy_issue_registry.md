# Phase 7 — Strategy Issue Registry

**Date:** 2026-06-12. Every identified issue across the 12 strategies, classified
Type-A (implementation defect) / Type-B (calibration) / Type-C (market/data limitation),
with status and disposition. Type-A → fixed immediately; Type-B → evidence + only fixed
if clearly a correctness issue (not optimization); Type-C → documented & quantified.

## Type-A (implementation defects) — ALL FIXED
| id | strategy | issue | fix | status |
|---|---|---|---|---|
| A1 | liquidity | swing levels stored without `'type'` → all treated as highs → SELL-only (0 BUY) | tag highs `'high'`/lows `'low'` | FIXED (0→61 BUY) |
| A2 | vwap_reversal | regime gate compared raw $/bar slope to a fractional threshold → regime fired 14/19941 | normalize slope (fractional) | FIXED |
| A3 | vwap_reversal | `_should_reset_session` used `bar_index%24` → 24-min "session" → deviation gate unreachable | anchor to real UTC-day timestamp | FIXED |
| A4 | mean_reversion | range bounds included the tested bars → rejection/expansion impossible | exclude tested bars from window | FIXED |
| A5 | breakout | consolidation range recomputed each bar → a true break collapsed `is_defined` | latched-range state machine; exclude current bar | FIXED |
| A6 | trend_following | `trend_extreme_threshold=0.99` ≈ always-true on 1m → blocked entries | 0.99→0.999 | FIXED |
| A7 | scalping | absolute `min_volume_threshold=100` vs ~6/bar → failed every bar pre-gate | relative liquidity floor | FIXED |

_(Operational Type-A from the stabilization phase — resample aliases, `_detect_missing_candles`,
CMC list/string, empty-CSV guard, pkg_resources — are logged in `../stabilization-fixes.md`.)_

## Type-B (calibration) — DOCUMENTED, NOT changed (remediation = threshold/redesign = disallowed)
| id | strategy | issue | evidence | impact if "fixed" | why not changed |
|---|---|---|---|---|---|
| B1 | breakout / crypto_breakout | confidence formula `(compression_ratio/10+|mom|)/2` (≤~0.2) can never reach own `min_confidence=0.35` → **0 trades at every TF** | 0 trades in all 324 matrix cells | would make breakout *tradeable* (then likely still no edge per Type-C) | rescaling formula or lowering threshold = calibration/optimization; needs human correctness ruling |
| B2 | vwap_reversal | `_check_rejection_pattern` requires close on opposite VWAP side from entry → rejection path dead; only failure-swings confirm | dead code path; lower fire rate | higher signal frequency | reinterpreting rejection geometry borders on redesign |

## Type-C (market / data / structural limitations) — DOCUMENTED & QUANTIFIED
| id | scope | limitation | quantified evidence |
|---|---|---|---|
| C1 | ALL | no gross/stable edge on OHLCV after realistic costs | 324 matrix cells: win 19–24% vs ~40% breakeven; **WFO: 0 temporally-stable (strategy,symbol) pairs**, best 2/4 (coin-flip) |
| C2 | ALL | SOL is a universal failure | 0 positive WFO segments for every strategy on SOL; aggregate SOL PnL deeply negative |
| C3 | 1m timeframe | structural cost-incompatibility | TP=2.25×ATR≈0.10% ≪ 0.30% round-trip cost; breakeven ≈15m |
| C4 | scalping | thesis (move>cost at scalp frequency) unmet at any tradeable frequency | negative on every TF AND symbol; sumPnL −8317 |
| C5 | mtf_trend | "MTF" = 3 EMAs on a single timeframe, not true multi-TF data | single-TF proxy by design |
| C6 | oi_footprint | no real open-interest feed; uses volume×1.5 proxy | named OI edge unproven; best cell ETH +405 rests on proxy |
| C7 | mean_reversion / vwap_reversal | intrinsic low frequency from multi-condition conjunction | 6 and 12 trades respectively across all higher-TF cells |

## Redundancy
| id | strategy | issue | disposition |
|---|---|---|---|
| R1 | crypto_breakout | explicit code alias of `BreakoutStrategyAdapter` (identical logic/config/results) | **RETIRE** as a separate entry |

## Tally
Type-A: 7 (all fixed) · Type-B: 2 (documented) · Type-C: 7 (documented/quantified) ·
Redundancy: 1. **No remaining in-scope Type-A or correctness-clear Type-B defect.**
