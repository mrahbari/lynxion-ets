# E8b — Watchers after the layer-1 fixes, fresh period (2026-11-22)

Fixes under test (commit 27f0296): closed bars fed once (no repeated 30-bar window), `candle` payload for
market_pulse/historical_candle, BingX funding for funding_rate, realistic funding thresholds, Engine rules for
candle/funding, Fusion regime extreme-first ordering.

Data: 8 liquid perps, 1m bars, DEV 2026-07..08 and VALIDATION 2026-09..10 — neither used in E8.
Gross returns per signal (round-trip cost ~10 bp), non-overlapping samples. `E8b_watcher_retest.csv`.

| Watcher (rule) | Horizon | DEV bp (t) | VALIDATION bp (t) | Verdict |
|---|---|---|---|---|
| market_pulse (Fusion) | 4h | +5.1 (1.8), 5/8 sym | +10.4 (3.3), 7/8 sym | only signal positive in both windows; at/below cost alone |
| market_pulse (Fusion) | 1h | +1.9 (2.8) | +0.7 (0.9) | weak |
| historical_candle | 1h / 4h | +1.2 / +2.2 | −0.3 / −1.4 | **E8 promise (+20 bp) did not replicate** |
| anomaly_ml | 15m–4h | ~0 | sign flips between windows | no edge |
| volatility (Engine, long-only) | 1h / 4h | +2.5 / +19.6 | +5.9 / −7.7 | long bias, unstable |
| trend_mtf | all | 100 samples in 2 months | unstable | fires almost never on 1m bars |
| funding_rate | — | no reading beyond 0.05%/period on these majors | — | rare by construction; needs alts |

## Conclusion for layer 1
- The plumbing defects are fixed and verified live (all watchers now produce observations, no tracebacks).
- Individually no watcher has a tradable edge at 15m–4h; only market_pulse (4h, Fusion rule) is consistently
  positive and is a candidate *filter*, not a stand-alone signal.
- Live Fusion still emits no direction because every observation fails the confidence filter (watchers report
  ~0.25–0.4 against thresholds 0.55–0.70). Calibrating that scale is layer-2 work (E8c).
