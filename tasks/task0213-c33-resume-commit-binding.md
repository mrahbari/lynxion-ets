# TASK-0213 — C-33 resume commit binding

## Status

`COMPLETE — STATIC RESUME BLOCKER FIXED; RUNTIME STILL PROHIBITED`

## Finding

The active C-33 manifest is pinned to commit
`1c46d42ff4b76cfdf7914fde346e4d1163bcc854`, while repository HEAD has advanced.
The TASK-0209 command would therefore fail before collection because `activate()` used
HEAD as the expected collector commit.

The collector blob at the pinned commit and current HEAD is exactly identical
(`abdaf68dc24cbc29dc8dd33897a190fff015fd13`). The mismatch is repository history, not
collector-code drift.

## Minimal correction

The dedicated resume launcher resolves the existing manifest's pinned commit and retains it only when Git proves
that the current executable collector file has the exact same blob identity at HEAD and
at the pinned commit. Any missing commit, unreadable manifest, Git failure, or collector
blob difference fails closed. The original collector remains byte-identical and new
activations continue to bind current HEAD. The reviewed resume command is
`python scripts/resume_c33_liquidation_collector.py --enable-network`.

## Acceptance

Synthetic tests prove identical-blob resume, changed-blob rejection, and current-HEAD
binding for new activation. No collector or runtime was started, no network was used,
and no ledger, manifest, broker, account, strategy, risk, or outcome was changed.
