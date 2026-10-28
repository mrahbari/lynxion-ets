# Sequential Edge Research Policy v1

**Status:** FROZEN FOR C-16 AND LATER

This policy controls false discovery and candidate churn after fifteen historical candidates.
It supplements candidate-specific preregistration; it does not retroactively alter verdicts.

## Evidence Classes

1. **Exploratory clue:** discovered after opening a result. It cannot be promoted or tested by
   reslicing the same symbol-period outcomes.
2. **Independent historical confirmation:** frozen mechanics evaluated on a new symbol universe
   or time boundary whose conditional outcomes were unopened.
3. **Prospective shadow confirmation:** signals recorded after a committed time boundary, with
   no orders and no backfill.
4. **VST confirmation:** prospective broker-realistic execution with preserved risk controls.

## Candidate Admission Gate

A C-16+ candidate is admitted only if all conditions hold:

- It belongs to a mechanism family not already falsified by two independent confirmations, or
  it tests a clearly documented new causal moderator on a new outcome boundary.
- Inputs are causally available and point-in-time reconstructable.
- Expected holding-period movement is economically capable of clearing frozen costs.
- Universe, direction, signal, entry, exit, costs, folds, sample minimums, concentration ceiling,
  uncertainty method, and rejection rule are committed before outcome evaluation.
- At most one primary specification is evaluated. Diagnostic cells cannot change the verdict.
- A failed candidate is not re-run with relaxed parameters on the opened sample.

## Family-Level Multiplicity Rule

- Multiple variants within one family are treated as correlated tests, not fresh independent
  evidence.
- No family may be promoted from a nominal positive aggregate result alone.
- Historical KEEP requires a preregistered 95% lower confidence bound above zero plus all
  candidate stability gates.
- If more than one primary candidate is opened within a single future research batch, the batch
  must use Holm correction at family-wise alpha 0.05. The default remains one primary candidate.
- Prospective and VST gates remain mandatory even after historical KEEP.

## Frozen Prohibitions

- No cherry-picking symbols, sides, folds, regimes, severities, horizons, or cost assumptions
  after results.
- No production mutation from historical evidence alone.
- No weakening of risk controls to improve trade count or expectancy.
- No counting repeated tests on the same outcome panel as independent confirmation.
