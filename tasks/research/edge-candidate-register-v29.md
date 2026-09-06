# Edge Candidate Register v29 — C-30 Independent Positioning-Divergence Confirmation

**Status:** OPENED — C-30 REJECTED; FAMILY CLOSED

C-30 is the one permitted independent confirmation of C-29's top-trader/crowd positioning-
divergence mechanism. It preserves the signal and economic specification exactly but moves to five
disjoint symbols whose conditional positioning outcomes were not opened by C-29. If C-30 fails,
the positioning-divergence family closes under the sequential research policy.

## Frozen Independent Boundary

- Symbols: AVAXUSDT, DOGEUSDT, DOTUSDT, LINKUSDT, and LTCUSDT. None appeared in C-29.
- Primary native futures prices: `data/research/c15/binance_futures_15m`; reverse prices:
  `data/research/c17/reverse_price`; positioning metrics and funding are under `data/research/c17`.
- Primary price SHA-256: AVAX `1e78a738069199357586350b5653c4cef75150666416e00cd7254167cf6e1034`,
  DOGE `f3170d93bd2f2e08c8b011d286220ee97de09e465f044fdd764a837fe461d4fd`, DOT
  `fe919ae304f7eab4e0daa224efc657d39af45ca3dd0a8a6b955bd6000cea315c`, LINK
  `5828638c2ed38d1c23addd106551efbfadd3f5bbb7c912699b910c25e72b8d62`, LTC
  `fd6922e8488c1b37b1f666418f681b9edc8da6062e7cbf0b32451b01c68c28e8`.
- Reverse price SHA-256: AVAX `30820954f5937d01a6bef8f8ee28ea740b9d633430412a2abb53b1c97f0a8787`,
  DOGE `bc89f4f41f39dbeb0a5cb9f1eb263e7c93a287acaf64d791ff9fdd7b86b0b013`, DOT
  `5c3e4ef533a989d97f48914cdb79c3f49ae5ab12f88b2ff034c9956d79e63d1c`, LINK
  `c4bbc2b19187f216987ff27af600330d05a01be5e1a323568caba2dac1692ae1`, LTC
  `543a4c6fbc94450f8f77f0c5b8a090a33c12363e317bd0eec3d4f513972be7f9`.
- Metrics SHA-256: AVAX `4594a6b040654047d1b5d7a0628b4366d9081746e7ac0d17555030d2c4053d71`,
  DOGE `5d2982ad761a01504237b2b3129b00209a21f1d2eeadecc3e27d4863c5032100`, DOT
  `21e65f486869c6010c882fbcd620a1bc8564c531f97cd988407ed598123e8aa8`, LINK
  `f46dddfa3c910748755902f2950efd37d969f2cba57b558e75676b7c3ac32982`, LTC
  `682458983b6c6a133241b8189b3f0b250f3cd4757eb680c43d7d510068f4a57d`.
- Funding SHA-256: AVAX `2aacfffc05219a440ba7e87766eea26af692a7399ef10f5be3b5d1d640ae591f`,
  DOGE `00132b8cc6ad3ff733ae382a385569e080fd016b62f65f7a8cbb4689eacd341b`, DOT
  `6a6ff1fed52b61201f1d63463d902a2e690338667ebfd57f1902dc5668702bb8`, LINK
  `c2dcd51c6c1b7b5e744d4de7b95a231cdbb200d05718a40d85c832b7d69d86a9`, LTC
  `b36acf3bee53ff5e5a4017503b80cd5ec7d8b0d1bb9d496b5809fe2d19e8bc9b`.
- The evaluator must enforce every full hash before calculating an outcome.
- Primary: 2023-01-01 through 2026-08-29. Reverse: 2021-12-01 through 2022-12-31.

## Frozen Signal and Execution

- Use C-29 unchanged: exact four-hour UTC decisions; exact five-minute-prior metrics observation;
  finite positive `count_long_short_ratio` and `sum_toptrader_long_short_ratio`; log transforms;
  causal p90 thresholds from the prior 180 valid decisions for absolute crowd positioning and
  absolute top/crowd divergence; require opposite signs and strict exceedance of both thresholds;
  trade LONG when top positioning is above one and SHORT when below one.
- Enter at the exact decision-time 15-minute open and exit exactly 96 bars/24 hours later. Require
  all 97 native timestamps; one position per symbol; earliest signal wins; no overlap.
- Funding settlements strictly after entry and at or before exit are included with correct side.
- Frozen cost is 0.30% round trip, with 0.20% and 0.50% sensitivities.
- No price, OI, taker, funding-level, regime, volume, rank, time, or diagnostic filter is allowed.

## Frozen Reporting and Gate

- Four global chronological primary folds; positions crossing folds are excluded. Cluster-bootstrap
  10,000 samples by UTC entry day with seed 300030.
- Report all C-29 census, economics, uncertainty, side, symbol, fold, year, cost, funding, drawdown,
  and concentration fields.
- KEEP requires every condition: primary N>=300; expectancy>0; PF>1; clustered lower bound>0;
  >=3/4 positive folds with N>=50; both sides positive with N>=75; >=4/5 symbols positive with
  N>=40; every primary year positive with N>=50; maximum positive-PnL symbol concentration<=35%;
  reverse N>=150 with expectancy>0 and PF>1; and positive primary expectancy at 0.50% cost.
- Any failure is REJECT. A pass is only `KEEP_FOR_PROSPECTIVE_VALIDATION`.

## Frozen Prohibitions

No C-29 parameter or gate is relaxed. No post-result slice or variant is permitted. No order or
production strategy/risk/trailing/symbol/leverage change is authorized.

## Frozen Result

C-30 produced only 56 primary trades. Net expectancy was +0.3617% and PF 1.5219 at 0.30% cost,
and remained positive at 0.50%, but the daily-clustered interval crossed zero
[-0.2196%, +0.9953%]. Two folds were negative; only two LONG trades occurred; 52/56 trades were
DOT; concentration was 75.74%; and only 2023 had observations. The positive reverse result had
only 13 all-SHORT trades. Every minimum sample, breadth, side, year, reverse, uncertainty, and
concentration gate failed. Verdict **REJECT**. Together with C-29, this closes the exact
positioning-divergence family without threshold/symbol/direction variants. Machine report:
`docs/reports/edge_candidate_c30.json`.
The report reproduced byte-for-byte; ten focused tests and the full suite pass with 886 passed and
one optional import-linter skip.
