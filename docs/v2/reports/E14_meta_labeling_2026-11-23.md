# E14 — meta-labeling as the standard form of Fusion/Engine (2026-11-23)

## 1. Literature review (what the standard is)
- **Meta-labeling** (Lopez de Prado, *Advances in Financial Machine Learning* 2018, ch. 3; Joubert, "Meta-Labeling:
  Theory and Framework", JFDS 4(3) 2022; Meyer, Barziy & Joubert on calibration and position sizing, JFDS 2023):
  a primary model sets the side; a secondary binary classifier, trained on "did this primary signal win",
  decides take / skip and the size. Its job is to raise precision of a high-recall primary.
- **This is what Fusion + Engine are meant to be**: strategies = primary model, Fusion/Engine = secondary model
  over watcher states. The standard version learns the weights from data, validates them with purged CV and
  calibrates the probability before using it for sizing. The current implementation uses hand-set weights and
  thresholds and is called with one signal at a time (E12), so it never fuses anything.
- **Validation**: purged k-fold with embargo (drop training labels that overlap the test span, then a buffer);
  combinatorial purged CV for a distribution of paths; Deflated Sharpe / PBO for multiple testing.
- **Calibration**: needed when probability drives size. Platt (logistic) is safer with little data, isotonic
  needs more data and can overfit.
- **Known limitation** (practitioner reports, e.g. QuantConnect forum): meta-labeling filters and sizes an
  existing edge; it rarely creates one from a primary model with none. If the secondary features carry no
  information about the primary's outcomes, the out-of-fold AUC is ~0.5 and nothing improves.

Sources: Wikipedia "Meta-Labeling" and "Purged cross-validation"; Hudson & Thames meta-labeling notes and code
(hudson-and-thames/meta-labeling); GARP whitepaper on AFML; IBKR Campus / QuantInsti on purging and embargo;
MQL5 article on probability calibration; arXiv 2509.23665 and 2605.01796 on Platt vs isotonic.

## 2. Test (pre-registered, script committed before running: a54c372)
Script `research/v2/experiments/e14_meta_labeling.py` (rules in docstring). E9 trades: 28,561 DEV,
12,588 holdout. Features: all watcher states at entry (volatility ratio, 1h/4h trend t-stat, funding, 24h
return, BTC 24h return, all signed by side), stop distance, hour, strategy. Label: R > 0.
Models: logistic regression; gradient boosting + isotonic calibration. Purged 5-fold CV, 24 h embargo.

| model | DEV OOF AUC | best q | DEV filtered mean R / PF | HOLD AUC | HOLD base R | HOLD filtered R / PF | lift |
|---|---|---|---|---|---|---|---|
| logistic | 0.471 | 0.5 | -0.151 / 0.78 | 0.502 | -0.092 | -0.100 / 0.85 | -0.008 |
| GBM + isotonic | 0.502 | 0.5 | -0.100 / 0.85 | 0.498 | -0.092 | -0.094 / 0.86 | -0.002 |

**Verdict: FAIL** (both models, DEV and holdout). AUC is 0.47-0.50: the watcher states, fused properly with
learned weights, carry no information about which strategy trades win. Logistic OOF AUC below 0.5 means the
fitted patterns reverse between folds (non-stationary noise). Bet sizing 2p - 1 gives no trade a positive size
(calibrated p never exceeds 0.5 at a 39 % base win rate). Per-strategy detail: `E14_meta_labeling_per_strategy.csv`.

## 3. Decision (E7-4)
The architecture (primary strategy + secondary filter) is the standard one; the inputs are the problem, not
the implementation. A refactor of Fusion/Engine into a learned filter would not change PnL today.
- Fusion/Engine stay in place with their interfaces; no live change (they already do not affect PnL, E12).
- Re-open only when a new input exists with standalone information (out-of-fold AUC >= 0.55 on strategy
  outcomes), e.g. order-flow or OI features. The E14 script is the ready harness: add the feature, rerun.
- Fusion/Engine remain excluded from the cleanup inventory (E10).
