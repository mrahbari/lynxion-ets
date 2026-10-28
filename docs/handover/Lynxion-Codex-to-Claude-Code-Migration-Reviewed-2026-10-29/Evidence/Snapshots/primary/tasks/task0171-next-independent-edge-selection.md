# TASK-0171 — Next Independent Edge Selection

**Status:** COMPLETE — C-34 SELECTED, OUTCOMES SEALED

Selected C-34, **cross-venue aggressive-flow divergence**, for the next preregistration. No
conditional forward return, threshold slice, trade, or outcome was calculated in this task.

## Selected mechanism

When same-asset Binance Spot and USD-M perpetual aggressive flow diverge sharply, the Spot venue may
contain less-leveraged information that the perpetual subsequently follows. The causal input is the
difference between completed-bar Spot and futures taker-buy shares, not a price underreaction ratio.

This is distinct from:

- C-21/C-22, which tested continuation from extreme **single-venue futures** taker flow;
- C-31, which required a contemporaneous **price** response gap and produced no trades;
- rejected funding, OI, basis, depth, cross-symbol, positioning, and price-sweep families.

The new causal moderator is venue-of-origin disagreement. It does not reopen C-21/C-22 by changing
their symbol, threshold, side, or horizon.

## Data feasibility facts

- Official native Spot 15-minute data contains exact `quote_volume` and
  `taker_buy_quote_volume` for the six major-symbol panel.
- Official normalized futures taker-flow data contains the corresponding quote-volume and
  taker-buy quote-volume observations.
- Existing manifests preserve exact file hashes, source gaps, and aligned timestamps. Missing exact
  pairs can be rejected without interpolation, resampling, or nearest matching.
- A multi-hour holding period can be evaluated against the existing 0.30% primary and 0.50% stress
  costs, including exact funding settlements.

## Alternatives not selected

- Volatility-compression breakout: too close to the already rejected volatility-breakout family.
- OI/funding composite: risks reslicing two repeatedly tested derivatives families.
- Intraday calendar effects: weak causal basis and high multiple-testing risk across hours/weekdays.
- C-33 variants: prohibited while the prospective liquidation cohort is collecting.

## Next unit

TASK-0172 must preregister exactly one C-34 specification before opening outcomes. It must freeze
data hashes, periods, causal alignment, divergence definition, direction, horizon, costs, funding,
folds, bootstrap, sample/breadth/concentration/drawdown gates, and a no-relaxation rejection rule.
