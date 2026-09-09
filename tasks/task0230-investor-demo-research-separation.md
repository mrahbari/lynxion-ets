# TASK-0230 — Investor-demo and research-data separation

## Scope

Adopt the investor-delivery/edge-acceleration directive and close the verified contamination risk
where a controlled VST demo could later be reconstructed as a normal strategy trade.

## Root cause

The controlled demo order carried `investor_vst_demo` on the in-memory `Order`, but the direct
adapter proof did not write the multi-broker intent journal. Exchange-history reconstruction could
therefore fall back to `trend_following` when the position eventually closes. Attribution and the
prospective monitor also lacked an explicit technical-demo exclusion.

## Minimal change

- Canonical purpose: `INVESTOR_TECHNICAL_DEMO`.
- Append-only registry records client order ID before future demo sends and exchange order ID after
  acknowledgement.
- The already executed TASK-0227 order ID is registered explicitly.
- Exchange-history reconstruction applies the canonical label from the registry.
- Descriptive attribution and prospective edge monitoring exclude canonical/legacy demo labels.
- The frozen TASK-0228 artifact remains byte-reproducible when no demo row is present.

## Evidence

- Focused suite: 21 passed.
- Tests prove registry identity loading and exclusion from both attribution paths.
- TASK-0228 artifact regeneration remains SHA-256
  `ab26707481a250fbded6ac40112aca012a2b5439fce9957433679b746ac82adb`.
- No order, broker request, runtime/config change, cohort mutation, or historical rewrite occurred.

## Verdict

`KEEP — DEMO/RESEARCH SEPARATION ENFORCED`.

