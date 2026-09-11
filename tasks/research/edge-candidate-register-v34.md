# Edge Candidate Register v34 — C-35 Compression-Release Continuation

**Status:** PRE-REGISTERED — PROSPECTIVE SHADOW ONLY

**Prospective boundary:** `2026-09-11T00:40:44Z` (`1789087244` epoch seconds).

## Admission rationale

C-35 is the only new primary candidate admitted after TASK-0240. Registering five variants would
inflate false discovery. It tests a volatility-state transition distinct from rejected raw
momentum, acceleration, funding, positioning, basis, and microstructure families: a directional
break immediately after symbol-specific volatility compression.

## Frozen source and universe

- Public unauthenticated Binance USD-M 15-minute klines for BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT,
  XRPUSDT, and ADAUSDT.
- Prospective observations only. Candles opening at or before the boundary may enter the fixed
  30-day/96-bar/16-bar rolling warmup only; they cannot serve as a decision bar, signal, virtual
  entry, virtual exit, or counted outcome. Every decision-bar open, entry open, and exit open must
  be strictly after the boundary.
- A decision occurs on each exact UTC hour after its just-closed 15-minute candle is final.
- Missing, duplicate, non-monotonic, or non-contiguous candles invalidate that symbol/decision.

## Frozen signal

All calculations use completed candles only.

- Normalized true range is true range divided by close.
- True range is the maximum of high-low, absolute high-minus-previous-close, and absolute
  low-minus-previous-close. The 20th percentile uses sorted values with linear interpolation at
  zero-based rank `(N - 1) * 0.20`; no library-default percentile variant may be substituted.
- Compression requires the median normalized true range of the 16 bars immediately preceding the
  decision bar to be strictly below the 20th percentile of the preceding 2,880 completed bars
  (30 days), excluding those 16 bars and the decision bar.
- LONG breakout: decision-bar close is strictly above the maximum high of the preceding 16 bars.
  SHORT breakout: strictly below their minimum low.
- Decision-bar normalized true range must be at least 0.45%, and decision-bar volume must be at
  least 1.5 times the median volume of the preceding 96 bars, excluding the decision bar.
- Rank simultaneous candidates by decision-bar normalized true range descending, then symbol
  ascending. Admit only the first, with at most one unresolved virtual position portfolio-wide.

## Frozen virtual execution and costs

- Enter at the next exact 15-minute open after the decision bar and exit at the open eight bars
  later (two hours). Require all intervening timestamps and both fill opens.
- LONG return is exit/entry minus one; SHORT return is entry/exit minus one.
- Primary round-trip friction is 0.30%; sensitivities are 0.20% and 0.50%. Missing funding makes
  the outcome incomplete if a settlement occurs strictly after entry and at or before exit;
  otherwise apply public funding with the correct side sign.
- No leverage, sizing, stop, take-profit, trailing, intra-candle fill, or capital scaling is modeled.

## Frozen prospective gate

- Do not inspect aggregate outcomes before both eight UTC weeks and 240 completed positions exist,
  including at least 80 per side and at least 30 in four of six symbols.
- Four chronological folds, with positions forbidden to cross fold boundaries. Require at least
  three positive folds with at least 40 positions each.
- KEEP requires primary net expectancy >0, PF >1, daily-clustered 10,000-sample bootstrap 95%
  lower bound >0 with seed `350035`, both sides positive, at least four symbols non-negative,
  maximum positive-PnL symbol concentration <=35%, equity max drawdown <=20%, and positive
  expectancy under 0.50% friction.
- Any failed completed gate is `REJECT`. Until every gate is evaluable, verdict is `COLLECTING`.
  A pass is only `KEEP_FOR_SEPARATE_VST_REVIEW`, never deployment authorization.

## Frozen prohibitions

No threshold, percentile, window, universe, direction, ranking, horizon, cost, sample gate, fold,
bootstrap, or concentration rule may change after the first prospective observation. No historical
outcome import, broker/authenticated call, order, production integration, or account/risk change.
