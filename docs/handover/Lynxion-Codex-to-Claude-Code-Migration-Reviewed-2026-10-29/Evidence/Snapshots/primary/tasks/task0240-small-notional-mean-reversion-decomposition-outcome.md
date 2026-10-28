# TASK-0240 — Small-notional and MeanReversion decomposition outcome

## Scope

Execute TASK-0239 once against its frozen baseline and interpretation contract.

## Results

- The 2x2 partition covers all 1,257 final trades.
- Small/not-MeanReversion: N=615, +191.448262 USDT, mean normalized return +9.0413%,
  bootstrap 95% interval [-0.4130%, +27.7003%].
- Small/MeanReversion: N=104, +2.356567 USDT, mean normalized return +0.0218%, interval
  [-0.3784%, +0.4119%].
- Larger/not-MeanReversion: N=536, -15,691.201877 USDT, mean normalized return -1.8551%,
  interval [-2.2048%, -1.5928%].
- Larger/MeanReversion has only two observations and cannot establish independence from the
  small-notional era.
- The small-versus-larger normalized-return direction agrees in all four eligible UTC weeks and
  within both eligible strategies, but uncertainty still includes zero in both small-notional
  2x2 cells.
- One symbol supplies 85.91% and the top three symbols 89.80% of the small-notional slice's
  positive PnL, exceeding both frozen concentration limits. MeanReversion does not exceed them.

## Verdict

`REJECT_AS_CAUSAL_EDGE — SIZE_ALIAS, STRATEGY_ALIAS, AND CONCENTRATED`.

The small-notional pattern is directionally persistent but statistically uncertain and extremely
PnL-concentrated. MeanReversion is almost entirely contained inside the small-notional band and
its relevant interval includes zero. Neither label is an independently defensible entry edge.

## Boundary and next

No production or research admission changes. Do not promote notional size or the MeanReversion
label. The next step is to preregister at most five independent hypotheses composed only of
predictors observable at entry and not defined by position size, realized outcome, or post-entry
excursion.

Artifact SHA-256:
`3aaa3a1cb080e5aa7b04d74855e912c4fda471a66c01fee0652538f9013ba265`.

Focused regressions: 3 passed.
