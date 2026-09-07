# TASK-0201 — State, funding, and paired-outcome binding

## Scope

Bind one disconnected candidate state-machine path to its causal exit time, exact
funding window, and per-position economics. Do not aggregate or inspect cohort outcomes.

## Result

- Entry fill time is preserved through costed position grouping and must precede the
  first prospective manager observation.
- A candidate shadow fill maps its sequence to the exact observation UTC; a candidate
  without an earlier fill shares the authoritative terminal time and price.
- Baseline and candidate funding are independently admitted over their exact windows.
- Missing coverage fails closed before per-position economics.

## Boundary

Only synthetic fixtures were evaluated. No aggregate, bootstrap, gate, candidate
verdict, active cohort, runtime, or broker path was opened.

## Next

TASK-0202 freezes the coverage-gate counter so aggregate results cannot be exposed before
100 pairs, 30 activations, eight weeks, five symbols, and both-side minima are met.
