# Edge Candidate Register v24 — C-25 Independent Basis-Convergence Confirmation

**Status:** OPENED — C-25 REJECTED; FAMILY CLOSED

C-25 is the one permitted independent historical confirmation of C-24. It uses the disjoint
DOGEUSDT, LINKUSDT, LTCUSDT, DOTUSDT, and AVAXUSDT panel whose spot/perpetual basis-conditioned
outcomes remain unopened.

All signal, execution, and economic mechanics are frozen unchanged from
`tasks/research/edge-candidate-register-v23.md`:

- exact native 15-minute spot/perpetual intersection;
- completed close basis `perpetual_close / spot_close - 1`;
- causal prior-2,880 p99 excluding current and strict positive basis >0.40%;
- equal-notional next-open LONG spot/SHORT perpetual;
- next-open exit after completed basis <=0.05%, otherwise exact 96-bar timeout;
- per-symbol overlap rejection and actual SHORT funding cashflows;
- two-unit capital normalization and 0.20% primary cost, with 0.15/0.30/0.50% sensitivities;
- primary 2024-01-01–2026-08-29, reverse 2023, four global folds, UTC-date clustered bootstrap
  with 10,000 samples and seed 240024.

KEEP requires primary N>=150, expectancy>0, PF>1, bootstrap lower bound>0; >=3/4 positive folds
with N>=20; >=3/5 positive symbols with N>=20; concentration<=45%; reverse N>=50 with expectancy>0
and PF>1; timeout share<=50%; and positive primary expectancy at 0.30% cost.

Failure is REJECT and closes direct basis convergence at family level. No threshold, horizon, exit,
cost, direction, or symbol slice may change. No production or order action is authorized.

## Frozen Result

C-25 produced only two primary pairs, both DOGEUSDT, with +0.3117% expectancy and no losses; the
reverse period produced zero pairs. Primary N, PF definition, folds, symbols, concentration, and
reverse gates failed. The frozen verdict is **REJECT**, and together with C-24 this closes direct
basis convergence at family level. Sparse positive events cannot authorize threshold relaxation or
production action. Machine report: `docs/reports/edge_candidate_c25.json`.
