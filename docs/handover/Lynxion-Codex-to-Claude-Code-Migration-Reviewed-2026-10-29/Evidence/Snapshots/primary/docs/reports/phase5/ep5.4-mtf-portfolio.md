# E-P5.4 — MTF & Portfolio Intelligence Forensics (diagnosis only)

_8355 trades (all LONGS), 90d × {BTC,ETH,SOL} × 12 strategies, frozen POST baseline. Net R = realised_R (after fees+slippage). No engine, strategy, or architecture changes — quantification only._

## Q1 — Profitability lost to MTF conflicts

Every trade is a long; `entry_regime` is the trend context at entry. B9 (MTF `compute_trend()` returns mock 0) means these contexts never gated entries → counter-trend longs were taken freely.

| entry context | trades | % | net exp R | win% |
|---|---:|---:|---:|---:|
| aligned (long in uptrend) | 2119 | 25% | -1.174 | 11% |
| neutral (long in range) | 3722 | 45% | -1.092 | 15% |
| conflict (long in DOWNtrend) | 2514 | 30% | -1.031 | 18% |

- **Counter-trend (conflict) longs: 2514 (30% of all trades)** — entry_regime = trending_down.
- Conflict net exp R **-1.031** vs aligned **-1.174** → counter-trend longs are 0.143R/trade **BETTER** than trend-aligned longs.
- **Counterfactual MTF filter** (drop all counter-trend longs): portfolio expectancy -1.094R → **-1.122R** (-0.027R/trade).
- **Profitability lost to MTF conflicts: ESSENTIALLY ZERO.** A naive HTF 'longs-only-in-uptrend' gate would *worsen* expectancy by 0.027R/trade on this sample. The data does NOT support MTF misalignment as a profitability leak (using entry_regime as the trend-context proxy) — it **refutes** the B9-impact assumption here.
- Either way, every alignment bucket is deeply negative (-1.174 / -1.092 / -1.031R) → no trend context produces positive expectancy (consistent with B14: negative gross edge). MTF gating cannot create edge that is absent.

_Caveat: entry_regime is the engine's single-timeframe regime, not a true multi-timeframe HTF score (B9 leaves the real MTF trend a mock). A genuine HTF signal could differ, but on the only trend-context available there is no evidence MTF conflict is a material leak._

### Per-strategy MTF-conflict drag

| strategy | trades | conflict% | aligned expR | conflict expR | filtered expR |
|---|---:|---:|---:|---:|---:|
| liquidity | 368 | 46% | -0.772 | -0.855 | -0.819 |
| mean_reversion | 199 | 41% | -0.974 | -0.668 | -1.004 |
| trend_following | 239 | 30% | -1.105 | -0.997 | -0.903 |
| oi_footprint | 474 | 47% | -1.084 | -0.945 | -0.953 |
| momentum | 95 | 14% | -1.003 | -0.910 | -0.988 |
| vwap_reversal | 954 | 51% | -0.853 | -1.027 | -1.056 |
| crypto_breakout | 1139 | 55% | -1.142 | -1.096 | -1.053 |
| mtf_trend | 2040 | 15% | -1.129 | -1.100 | -1.144 |
| breakout | 1281 | 0% | -1.180 | +0.000 | -1.161 |
| scalping | 1425 | 37% | -1.211 | -1.075 | -1.234 |
| volatility_breakout | 141 | 0% | -1.607 | +0.000 | -1.400 |

## Q2/Q3 — Missing portfolio intelligence & hidden correlation risk

Backtests ran one (symbol × strategy) at a time — there is no live portfolio layer (B10: correlation/heat/concentration offline-only, live sizing ignores other open positions). The risk is therefore quantified structurally from 1h-resampled returns of the traded universe.

- **Pairwise return correlation (1h):** BTC–ETH 0.85, BTC–SOL 0.81, ETH–SOL 0.84 → **avg 0.83** (high).
- **Effective independent bets** across the 3 symbols: **1.25** (of 3 nominal) — the universe behaves like ~1.3 bet(s), not 3.
- **Hidden-risk multiplier:** a strategy long in all three carries **1.60×** the volatility a naive 'independent diversification' assumption would predict (0.60% vs 0.37% hourly).

**Interpretation:** because all positions are long-only (B15) in a ~0.83-correlated universe, running the suite live would STACK correlated long exposure — concentration risk masquerading as diversification. With no live heat/correlation cap (B10) the realised portfolio drawdown would be materially larger than per-symbol backtests imply. This is hidden RISK, not hidden profit: it cannot rescue the negative per-trade expectancy (B14), it amplifies downside.

## E-P5.4 findings (6-part)

1. **Findings:** 30% of longs are counter-trend, yet counter-trend longs are the *least* unprofitable bucket (-1.031R) and trend-aligned the *worst* (-1.174R). The traded universe is 0.83-correlated (~1.3 effective bets of 3), long-only (B15), with no live portfolio risk layer (B10).
2. **Root causes:** B9 mock MTF trend → no HTF gate (but gating shows no benefit here); B10 portfolio intelligence offline-only → no correlation/heat cap live; B15/B4 long-only in a highly correlated universe.
3. **Profitability impact — MTF conflicts: ≈ ZERO (HTF gate would WORSEN expectancy by 0.027R/trade) — B9-impact assumption REFUTED here.** Portfolio/correlation: not an expectancy effect but a RISK amplifier — long-all-three carries 1.60× the volatility naive diversification implies (~1.3 effective bets).
4. **Recommended fixes (NOT executed — diagnosis only):** live correlation/heat/concentration cap (B10) to contain stacked-long drawdown; structure-aware SL/TP (B11). A real MTF/HTF gate (B9) is NOT evidenced as profit-additive here and is de-prioritised. Deferred to remediation mode.
5. **Estimated upside:** MTF gating ≈ none (this sample); portfolio cap = drawdown/risk reduction, NOT expectancy gain. Neither overcomes B14 (negative gross edge) — the binding constraint remains entry edge.
6. **Priority ranking:** B14 (entry edge) ≫ B7 (R:R geometry) > B10 (portfolio risk — real, but risk not return) > B8 (lifecycle) > B9 (MTF gate — no measured benefit). MTF/portfolio are RISK controls; they cannot manufacture the absent edge.
