# Edge Candidate Register v21 — C-22 Independent Taker-Flow Confirmation

**Status:** FROZEN — OUTCOMES UNOPENED

C-22 is the one permitted independent confirmation of C-21 under the sequential research policy.
It uses DOGEUSDT, LINKUSDT, LTCUSDT, DOTUSDT, and AVAXUSDT, whose taker-flow-conditioned outcomes
are unopened. The universe is disjoint from C-21.

All signal and execution mechanics are frozen unchanged from
`tasks/research/edge-candidate-register-v20.md`: exact completed 16-bar four-hour taker quote-flow
score, causal prior-180 p90 threshold, positive LONG/negative SHORT, next-open entry, prior-bar
24-hour close, overlap rejection, actual funding, and 0.20/0.30/0.50% costs.

KEEP requires primary N>=600, expectancy>0, PF>1, bootstrap lower bound>0; >=3/4 positive folds
with N>=120; both sides positive with N>=150; >=4/5 symbols positive with N>=80; positive-PnL
concentration<=35%; reverse N>=250 with expectancy>0 and PF>1; and primary positive at 0.50% cost.

Failure closes the taker-flow continuation family. No reversal, threshold/horizon change, symbol
slice, or production mutation is authorized.
