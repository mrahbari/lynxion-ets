# Post-Pilot-2 execution recovery board

## 2026-10-22 10:12 UTC — pending protection visibility attribution

Primary baseline d3069c3. Three synthetic subcases falsely verified missing-symbol,
CANCELED and FILLED pending rows. Visibility now requires explicit matching symbol
and rejects existing known-terminal status set. Exact-ID NEW and legacy status-omitted
controls preserved. Actual-target 22 methods PASS; independent 22 PASS,
REVIEW_PASS_WITH_LIMITATIONS. No order parameters, risk rules or broker actions changed.
Legacy absent/unrecognized statuses still rely on pending-endpoint semantics; no strict
active-status allowlist or real current-protection proof claimed. Fresh authorized broker
evidence and supervised runtime activation remain separate gates; no runner started.

## 2026-10-22 09:16 UTC — primary exposed-entry missing-ACK recovery

Primary baseline 64e6fa3. Port main 50a8e1a without rewriting existing terminal records.
Primary B4 fixtures reproduced 11 FAIL / 22 PASS. Before fill accounting, requested
SL/TP acknowledgement gaps now preserve parent SUBMITTED and append one durable,
parent-linked PROTECTION_UNKNOWN. Repeated reconciliation remains idempotent; new-entry
admission stays closed across reopen. Marker persistence failure uses existing halt gate.
Coverage includes FILLED/PARTIALLY_FILLED/PARTIAL and UNKNOWN/CANCELED with cumulative
execution; complete acknowledged parent control remains accepted under existing semantics.
Final exact-candidate six-suite run 77 PASS, 27 warnings; independent rerun identical,
REVIEW_PASS_WITH_LIMITATIONS. Actual primary standalone harness 20 methods PASS.
Operational journal hashes unchanged. ACK evidence is not current broker protection;
already-terminalized legacy records, initial crash windows and full attribution unresolved.
No broker call, protective mutation, credential change, runner or activation this run.

## 2026-10-22 08:12 UTC — primary initial protective acknowledgement retention

Primary baseline 8733cfb; port main bd1cb91 metadata bridge only, preserving requested
leverage/client identity and broker/risk behavior. Eight new primary fake tests first
failed (24 passed). Successful initial SL/TP IDs now flow through copied Order evidence
into the durable parent SUBMITTED journal record; no fills or current-protection proof.
Stale reused-order metadata cleared before guarded send. Identity validation and durable
write failures retain recoverable entry INTENT. Existing return type remains string.
Independent review initially FAILED: field mistakenly landed on ExecutionIntent due
same-named context. Corrected BEFORE COMMIT: optional field only at end of Order;
exact ExecutionIntent constructor signature preserved and regression tested.
Synthetic fixture monkeypatch target also corrected without altering production gates.
Final independent REVIEW_PASS_WITH_LIMITATIONS; exact candidate snapshot six module
suites 65 PASS, 27 warnings. Extra stale-metadata runtime rerun 13 PASS. Actual-target
standalone 20 methods PASS. No blanket suite/readiness claim; old LIVE fixture separate.
Partial protection failure/crash before full return still lack complete per-order durable
ACK history; no legacy attribution repair. Operational journal hashes unchanged.
No broker requests, credentials changes, orders, runner activation or frozen data edits.

## 2026-10-22 07:13 UTC — unchanged activation gate and integrity check

Actual main ead5e61; primary 8733cfb with unchanged five research dirty files.
No fresh broker scope received; no request/restart or repeated finished test run.
Pilot-2 contract/collector/supervisor SHA-256 match recorded three-file baseline;
all four operational journal hashes unchanged. This is not a complete frozen-data audit.
Read-only source check confirms primary initial-entry success still discards SL/TP
acknowledgement IDs; main's prior metadata-retention port remains applicable work,
separate from the now-wired trailing-stop uncertainty guard. No new defect verdict.
Next bounded source task: primary-compatible initial acknowledgement retention/tests,
while preserving broker parameters, risk semantics and the external activation gate.

## 2026-10-22 02:09 UTC — unusable conditional acknowledgement identities

Primary baseline 336e1d5. Six fake subcases reproduced blank/bool/float IDs accepted
as protective acknowledgements. Adapter and manager now reject unusable ID types or
blank strings, retaining durable UNKNOWN/retry hold. No new exchange format policy.
Actual-target 20 test methods PASS, independently rerun REVIEW_PASS_WITH_LIMITATIONS.
Reviewer requested positive integer/string controls at both layers; added and independently
rerun before commit. Known ACKs remain accepted and are not counted as entry fills.
No broker requests, operational journal writes, risk-policy changes or activation.
AST/fake proof does not establish real exchange identity support or current protection.

## 2026-10-22 01:07 UTC — preserve protective evidence visibility in preflight

Primary baseline 294eced. Acknowledged protection is correctly excluded from entry
in-flight accounting but was absent from preflight's dedicated evidence view. Two
new synthetic tests initially errored; protection_records() now exposes copied local
records under integrity guard, inspect labels protective_orders LOCAL_JOURNAL_ONLY.
Actual-target harness 19 methods PASS, independently rerun REVIEW_PASS_WITH_LIMITATIONS.
No additional broker queries, journal writes, order actions or uncertainty clearing.
Local acknowledgements/history may be stale/terminal and are NOT active-protection proof.
Copies are shallow as with existing query APIs. This is visibility, not a completed
protective lifecycle reconciliation or rollout. Fresh broker/supervised activation gates remain.

## 2026-10-22 00:07 UTC — reject corrupt-journal reconciliation side effects

Primary baseline 00a11ef. Two synthetic actual-method tests reproduced inspect/
reconcile bypassing recover() integrity errors and consuming partial derived state.
Both now validate journal recovery before broker reads/closure handling; failure
reports explicit error and reconciliation in_sync=false, no unknown gate clearing.
Actual-target harness 17 methods PASS, independently rerun REVIEW_PASS_WITH_LIMITATIONS.
Five adjacent primary suites on exact candidate snapshot: 47 PASS / 1 unchanged
LIVE-policy FAIL, 27 warnings. No risk guard weakening or whole-suite green claim.
This only covers recognized load failures; post-load changes and complete protection
lifecycle/initial-entry crash safety remain unproven. No broker/runtime/credential writes.
Next: protective acknowledgement lifecycle and exact source/broker activation gates.

## 2026-10-21 23:05 UTC — primary protection uncertainty wired and committed

Primary 0d212ae -> 00a11ef. Actual manager method fixtures initially 6 FAIL;
pre-send durable PROTECTION_UNKNOWN now precedes mutation. Unknown response,
transport exception, missing identity and unverified visibility do not authorize retry;
same-symbol uncertainty survives journal reopen. Known identity + verified visibility
requires durable acknowledgement before reporting success. Primary priority/conflict
preservation and explicit timestamp-rejection retry retained. No old-stop cancellation added.
Protective SUBMITTED records excluded from ENTRY in-flight fill reconciliation to avoid
phantom entry accounting; identities remain in journal counts/map. Separate protective
lifecycle reconciliation remains necessary, not proven by this patch.
Actual-target fake-only harness 15 methods PASS; independent rerun and diff review:
REVIEW_PASS_WITH_LIMITATIONS. Five adjacent suites on exact committed archive:
47 PASS / 1 unchanged LIVE-risk-policy FAIL, 27 warnings. Operational journal hashes
unchanged. AST/fake constructors do not prove full broker composition or initial-entry
crash safety. No broker, secret changes, orders, runner restart or activation.

## 2026-10-21 22:01 UTC — primary durable protection-unknown prerequisite

Primary base f57e487. Minimal port of main c073e19 journal capability: durable
PROTECTION_UNKNOWN marker, optional validated local parent, recovery visibility,
new-entry hold, fsync required. Two synthetic missing-API failures reproduced;
actual-target harness now 8 methods PASS, independently rerun REVIEW_PASS_WITH_LIMITATIONS.
Journal hashes unchanged. This capability is NOT yet connected to primary manager/
broker mutation flow and does not resolve missing conditional acknowledgement IDs.
Next: preserve primary priority/conflict/stop behavior while wiring pre-send durable
uncertainty and restart admission; never blindly replace the manager from main.
Operator declines Telegram token rotation; no replacement requested/performed this run.
Previously verified HTTP401 limitation retained, separate from runner correctness.
No operational journal/credential writes, broker activity, runner or deployment activation.

## 2026-10-21 — operator Telegram credential/config verification

No secret values recorded. Primary EnvLoader explicit .env load: token and chat
match file, notifications enabled, chat matches operator destination. No process-level
Telegram overrides present in diagnostic child. Direct official Telegram getMe using
file token: HTTP401/ok=false. Separate non-echoed in-memory operator-token check:
matches file=true, HTTP401/ok=false. This is independent of runner/config security logic.
No configuration-read defect reproduced, no speculative config/security weakening.
No .env/credential writes, test message, broker request, order or runner action performed.
Current limitation: Telegram rejects the supplied/current credential; operator must
rotate the exposed token and update local secret storage, never commit/post it.

## 2026-10-21 21:02 UTC — conditional unknown-response target compatibility

Actual primary f57e487, main 0f0d416 inspected. Fake-only AST execution of actual
_BingXBroker conditional method: code=0/data.order={} gives success=True/order_id=None
after exactly one fake POST. Initial incomplete fake lacked formatting ports and made
zero requests; completed fake reproduced the defect. No real transport/construction.
Primary manager is more advanced than old main: preserves old stop before replacement,
priority/rate-limit and timestamp-specific retry classification. Do NOT replace whole
manager with main. Missing-ID correction must be paired with durable uncertainty and
manager restart admission, not simply turn success false and enable repeat submissions.
Next bounded integration: retain primary behavior while porting durable protection-unknown
association/admission and no-ID handling together. No source/runtime/state mutation this run.

## 2026-10-21 19:44 UTC — primary position snapshot conversion port

Primary base 98bac9c. Existing low positions-request and reconciliation None/exception
guards already present; not duplicated. Remaining adapter row-skip could conceal
positions. Four fake-method subcases reproduced malformed/nonfinite rows returning
partial snapshots. Minimal port of main 5620b4c rejects conversion errors and nonfinite
quantity, preserving primary leverage/isolated metadata. Actual-target offline harness:
6 methods PASS, independently rerun REVIEW_PASS_WITH_LIMITATIONS. AST executes actual
method with fake value constructors; not real adapter/transport/domain integration proof.
No risk/order policy, broker request, journal bytes, runner activation or credentials changed.
Next: protective-order unknown-response target compatibility; activation gates retained.

## 2026-10-21 — operator-authorized primary source integration completed

Primary baseline 56fef14 -> 98bac9c. Selective actual-target integration of journal
load/ref/status guards (main 9d51d3a/114cc79) and startup unknown gate (8e190e0,
primary-compatible artifact fbb8d84). No bulk merge and no protection/risk API replacement.
New scripts/verify_primary_recovery_offline.py tests actual primary source in a clean
child with fake composition, denied transports/subprocesses, blocked operational reads
and external writes. Red: 24 subcase failures. Green: four methods PASS, seven corrupt
inputs, read failure, lifecycle controls and 30 startup combinations. Independently
rerun by runtime_p0_review: REVIEW_PASS_WITH_LIMITATIONS. Post-commit direct rerun PASS.
Five adjacent suites on archive of exact 98bac9c: 47 PASS / 1 pre-existing LIVE-policy
FAIL, 27 warnings; same known baseline failure, guard not weakened. Nine operational/
research file hashes unchanged. Source integrated, NOT runtime activated or broker verified.

## 2026-10-20 23:38 UTC — loaded journal identity/status validation

Baseline bf90c6d. Missing/unknown status and invalid references reproduced
4 FAIL / 70 PASS. Load now requires nonblank string references and existing
open/terminal statuses; invalid records latch the existing fail-closed error.
Combined isolated allowlist 268 PASS, 27 warnings; independent focused 89 PASS,
REVIEW_PASS_WITH_LIMITATIONS. No journal bytes repaired or statuses cleared.
This is not full schema/transition validation or operational-history compatibility.
Primary remains 56fef14; no deployment, broker access or runner activation.

## 2026-10-20 21:35 UTC — journal load integrity guard

Baseline 8e190e0. Prior synthetic reproduction showed malformed JSON silently
reported as an empty journal. Load parse/read/record-shape failures now latch an
integrity error; recovery and appends refuse operation without altering raw history.
Missing files retain existing empty-state semantics. Three corrupt fixtures and a
missing-file control pass; focused isolated suite 70 PASS, combined allowlist
264 PASS (27 warnings). Diff check passed. Independent review is PENDING;
not deployment-ready. No operational journal, broker, credentials or runner touched.
Limits: no schema-completeness guarantee, interprocess lock or post-load disk monitoring.

## 2026-10-20 19:32 UTC — broker-connected startup recovery gate

Baseline `50a8e1a`. Configuration preflight could pass and dispatch a trading use case
despite durable INTENT/PROTECTION_UNKNOWN (**4 FAIL / 52 PASS**). Production CLI now
checks the selected journal summary before live/auto use-case dispatch; unresolved states
return exit code 2. Read exceptions and malformed summaries fail closed. Paper and known
SUBMITTED behavior remain unchanged; no statuses or safety gates are cleared.
Both CLI dispatch branches use fake lifespans/use cases in deterministic tests. Combined
isolated suite **260 PASS**, 27 warnings; independent focused **66 PASS** with
REVIEW_PASS_WITH_LIMITATIONS. Diff check passed; frozen Pilot-2 activation hashes match (3/3).
Proof limits: already-loaded singleton only, not disk-corruption validation or authoritative
broker state. Composition/lifespan construction precedes this check, so no claim of zero
initialization broker reads. Exact runtime/journal configuration and supervised activation
still require review; no actual runner, broker request, deployment or credentials change.
Next: exact selected journal integrity/launch compatibility and remaining protective recovery.

## 2026-10-20 18:33 UTC — recovery retains requested protection gaps

Baseline `bd1cb91`. An entry FILLED/PARTIALLY_FILLED response could advance the parent
without preserving missing requested protective acknowledgements (**4 FAIL / 35 PASS**).
Recovery now reports missing acknowledgement kinds before fill-accounting and appends one
durable PROTECTION_UNKNOWN child linked to the local entry reference. Original records
remain byte-preserved prefixes; repeated reconciliation adds no duplicate marker. New entry
admission remains blocked across reopen; marker persistence failure invokes the existing
halt path when enabled. No broker orders, fabricated fills or automatic gate clearing.
Initial independent REVIEW_FAIL found PARTIAL/positive cumulative execution bypasses;
six additional cases reproduced **6 FAIL / 41 PASS**, then the guard was completed for
all supported fill evidence (including UNKNOWN/CANCELED with cumulative execution).
Positive fixture expectations were corrected to existing transition-report semantics
(first pass not-in-sync, next pass in-sync), not by changing production semantics.
Combined credential-empty/network-denied suite **244 PASS**, 27 warnings; diff check passed.
Final independent REVIEW_PASS_WITH_LIMITATIONS; focused isolated rerun **62 PASS**,
27 warnings. Pilot-2 activation hashes matched (3/3); unrelated primary dirty files preserved.
Acknowledgements remain local response evidence, NOT verified active protection. This
does not close initial entry crash windows, legacy attribution or exact runtime rollout.
No authenticated access, operational journal writes or deployment occurred during this task.
Next: review runtime-source/launch compatibility and conservative protective reconciliation.

## 2026-10-20 05:53 UTC — initial protective acknowledgement retention

Baseline `c073e19`. Initial successful SL/TP acknowledgement IDs were discarded by the
low broker result, adapter and durable entry journal (**3 FAIL / 19 PASS**). Optional Order
evidence metadata now carries a copied ID mapping; the existing str broker return remains.
MultiBroker clears stale evidence before guarded send and records the mapping on the same
parent SUBMITTED record with entry order ID. Mapping validation/write failures preserve
the recoverable INTENT. No order parameter, retry, guard, routing or risk limit changed.
Known ACK chain, copy isolation, journal reopen, malformed IDs and failed durable writes
are covered. Combined credential-empty/network-denied suite **232 PASS**, 27 warnings;
independent focused **37 PASS**, REVIEW_PASS_WITH_LIMITATIONS. Pilot-2 hashes match (3/3).
No raw operational journal, credentials or runtime was modified; no broker query/order.
Proof limit: acknowledgement association is not verified active protection or a fill.
Crash before full broker return and partial protection failures still lack per-order durable
acknowledgements; reconciliation does not yet consume this association. Initial-entry
crash-safety is NOT declared complete. Next: reconcile acknowledged bindings conservatively
and retain unbound legacy history UNKNOWN; runtime-source/configuration gate remains.

## 2026-10-20 04:53 UTC — durable manager protection uncertainty

Baseline `c2a23ff`. Journal capability tests initially **3 FAIL / 8 PASS** (missing durable
protection API); manager restart/pre-action failure tests **2 FAIL / 46 PASS** reproduced
duplicate restart attempts and broker access without durable evidence. Existing append-only
journal now fsyncs PROTECTION_UNKNOWN, includes it in recovery and new-entry admission,
and validates optional local parent symbol/venue association without inventing one.
Manager writes before cancel/send, checks durable uncertainty before broker actions, and
persists acknowledged IDs as SUBMITTED (not FILLED). Lost acknowledgement persistence keeps
UNKNOWN. Fixtures use temporary journals; raw operational journals were not changed.
Known acknowledgement, immutable prefix, failed persistence, reconstructed manager/journal,
flat reconciliation and no-blanket-entry-block tests are included. Combined isolated suite
**225 PASS**, 27 warnings; independent focused **96 PASS**, REVIEW_PASS_WITH_LIMITATIONS.
Pilot-2 activation hashes match (3/3); primary dirty files preserved; diff check passed.
Limits: manager-specific only; initial entry-plus-protection crash safety is not complete.
Venue/parent may be UNKNOWN, legacy uncertainty is not backfilled, no automatic clear exists,
cancel-before-replace persists, corruption/interprocess constraints remain. Runtime NO_GO.
Next: initial protective acknowledgements and exact launch/journal compatibility, without
turning local parent metadata into broker fill proof. No broker or deployment action occurred.

## 2026-10-19 21:30 UTC — retain UNKNOWN through position-state cleanup

Baseline `347d622`. Flat/missing snapshots deleted process-local UNKNOWN protection state,
undoing the no-retry hold: **2 FAIL / 44 PASS**. Cleanup now retains UNKNOWN records;
missing None responses preserve all state through the error path. Known closed records
are still cleaned after a successful flat snapshot. Focused isolated suite **46 PASS**,
independently rerun **46 PASS**, REVIEW_PASS_WITH_LIMITATIONS. Combined isolated suite
**217 PASS**, 27 warnings; diff check passed. Pilot-2 activation hashes match (3/3).
No broker access, raw journal modification, deployment or gate release. Persistence across
restart remains unresolved; an adapter with no position-query method is not qualified.
Independent EPIC/WFO work is not suspended: its existing qualified-baseline/MTF data gates
still block economic runs, not this P0 task. No outcomes were opened to bypass those gates.
Next: durable protective-to-entry evidence and restart-safe reconciliation; keep runtime NO_GO.

## 2026-10-19 15:16 UTC — missing protective acknowledgement identity

Baseline `086a588`. Protective response code=0 with missing/empty orderId was accepted
as successful protection (**2 FAIL / 37 PASS**). Minimum adapter guard now reports
success=False and unknown_submission=True when identity is absent; it does not classify
the broker order as rejected or absent and performs no additional POST. Positive explicit
acknowledgement identity remains accepted. Initial adapter-only suite **210 PASS** did NOT
prove caller safety: independent REVIEW_FAIL caught a three-attempt manager retry hazard.
Manager regressions reproduced **2 FAIL / 47 PASS** before correction. Unknown result or
exception now records process-local UNKNOWN/request evidence and blocks loop retries AND
subsequent cancel/resubmit calls for that symbol. Missing-ID, transport-timeout and direct
exception end-to-end fixtures assert exactly one submission. Final combined isolated suite
**214 PASS**, 27 warnings. Existing entry failure/unwind policy was exercised with both
known-failure and unknown flags; one unwind plus required flat readback is retained.
No new unwind/order policy is introduced. Process-local hold is not restart-durable; base
cancel-before-replace behavior remains outside this patch's proof and must not be called safe.
Final independent review: REVIEW_PASS_WITH_LIMITATIONS; focused isolated rerun **50 PASS**,
27 warnings. An accepted unknown protective order may remain after unwind; startup must
reconcile it. No crash-durable or exchange-idempotency guarantee follows from these tests.
Pilot-2 activation contract/collector/supervisor hashes match (3/3); diff check passed.
This prerequisite does NOT complete durable protective-to-entry binding. No broker access,
historical journal change, runtime rollout or GO claim; supervised activation remains gated.

## 2026-10-19 12:21 UTC — observed position side and filled quantity

Baseline `8e3a110`. Six wrong/missing position-side, closing-side and executed-quantity
fixtures reproduced invalid attribution (**6 FAIL / 28 PASS**). Candidates now require
the previous successful snapshot's unambiguous position, matching LONG/SHORT, opposite
closing order side and finite positive executedQty/cumQty equal to observed quantity.
Duplicate symbol positions are excluded; partial fills/changed quantities stay UNKNOWN.
Prior fixtures carry explicit shape evidence, retaining original status/PnL assertions.
Focused isolated suite **34 PASS**, independently rerun **34 PASS** with
REVIEW_PASS_WITH_LIMITATIONS. Combined isolated suite **207 PASS**, 27 warnings.
Pilot-2 contract/collector/supervisor activation hashes match (3/3); diff check passed.
No deployment, journal repair, order, authenticated read or policy-threshold change.
Remaining: an older lifecycle can share this shape. Execution-time and entry/exit identity
links remain unverified; this guard alone does not establish historical exit attribution.

## 2026-10-19 10:17 UTC — trigger names do not determine result sign

Baseline `cda027e`. TP history with negative/zero reported realized PnL was classified
profitable by order type while the existing cooldown selected nonpositive handling.
Synthetic red **2 FAIL / 26 PASS**; result boolean now derives only from reported PnL>0.
Focused suite **28 PASS**, independently rerun **28 PASS**, REVIEW_PASS_WITH_LIMITATIONS.
Combined isolated suite **201 PASS**, 27 warnings. STOP-positive, finite negative/positive
and UNKNOWN/nonfinite regressions remain covered. Existing risk thresholds and order rules
are unchanged. No historical economic outcomes were opened or recomputed; tests use fakes.
Downstream strategy-result reporting differs for previously misclassified TP events and
requires runtime activation verification. Reported realized PnL is not net-after-cost proof.
Lifecycle identity/time/quantity and runtime rollout remain unresolved; no deployment occurred.

## 2026-10-19 09:20 UTC — explicit exit symbol identity

Baseline `c31418c`. Missing or mismatched history symbols could still be accepted as the
position exit: **2 FAIL / 23 PASS**. Candidate history now requires an explicit normalized
symbol match before status/PnL selection; ambiguous records stay on the UNKNOWN safety path.
Known positive/negative and existing nonfill/PnL fixtures now include symbol evidence, so
their assertions still exercise the original guards rather than passing vacuously.
Focused isolated suite **25 PASS**; combined isolated suite **198 PASS**, 27 warnings.
Independent review: REVIEW_PASS_WITH_LIMITATIONS; isolated rerun **25 PASS**, 27 warnings.
No real-exchange, full lifecycle or deployed-runtime proof is claimed.
Diff check passed. No raw historical record, runtime, broker, credentials or policy changed.
Remaining: symbol alone does not prove lifecycle side/quantity/time/order identity; do not
promote this bounded guard to complete exit attribution or runner GO.

## 2026-10-19 08:20 UTC — observed-flat UNKNOWN is not a loss

Baseline `21e770e`. Empty/failed history and missing/nonfinite PnL reproduced fabricated
strategy loss results: **4 FAIL / 19 PASS**. An early UNKNOWN branch now retains the
reviewed safety hold, emits explicit uncertainty and avoids fabricated strategy results,
journal fills or historical identity. Finite positive/negative existing paths remain tested.
Focused isolated suite **23 PASS**, independently rerun **23 PASS** with
REVIEW_PASS_WITH_LIMITATIONS. Combined isolated suite **196 PASS**, 27 warnings.
Pilot-2 contract/collector/supervisor hashes still match activation (3/3). No runtime or
broker activity. Remaining: finite PnL/FILLED alone does not establish lifecycle identity;
symbol/side/quantity/time joins and exact runtime source remain critical-path gates.

## 2026-10-19 07:14 UTC — restored first-flat provenance

Baseline `f80a790`. Restored active symbols absent at first successful snapshot must not
be joined to arbitrary history or emitted as new trade results. Three synthetic regressions
reproduced **3 FAIL / 16 PASS**, then **19 PASS** after a minimal observed-open guard.
Unverified restored exits retain a one-hour safety hold without inventing loss events;
stronger existing expiry and historical loss entries are preserved. TP behavior unchanged.
Repeated flat reconciliation does not duplicate the restored-state alert. Existing nonfill
fixtures explicitly mark observed-open state to preserve their original regression coverage.
Combined credential-empty/network-denied suite **192 PASS**, 27 warnings. Pilot-2 activation
contract/collector/supervisor hashes match (3/3); unrelated primary dirty files preserved.
Independent review: REVIEW_PASS_WITH_LIMITATIONS; isolated rerun **19 PASS**, 27 warnings.
Inherited cooldown persistence-failure behavior remains outside this patch's proof.
Observed-open UNKNOWN outcome/identity joins and runtime rollout remain separate blockers.

## Operator priority — supervised TESTNET recovery before optimization

Verified baseline `ee4cd0f`. Operator clarification supersedes the previous suspension:
continue independent authorized WFO/Hyperopt, Radar and EPIC work, while runner recovery
has first priority and must not be delayed by those tasks. Existing data/outcome gates remain.
Economic Edge is NOT a runner-start prerequisite.
Critical path, in order:
1. Correct UNKNOWN/restored-exit attribution without fabricated fills/losses or gate release.
2. Independently review the exact minimal runtime-source patch and integration regressions.
3. Select one exact runtime revision/journal; document rollback and single-runner checks.
4. Obtain fresh authorized broker exposure/protection and historical-unknown evidence.
5. Present supervised TESTNET activation decision with abort procedure; no unattended start.
Do not expand this path for optional engineering findings. Keep existing risk limits intact.
Telegram credential replacement remains external; never expose/change secrets speculatively.
This priority update is not deployment or evidence that runtime gates passed.

## 2026-10-19 06:18 UTC — non-filled protective orders are not fills

Baseline `37714be`. Four CANCELED/CANCELLED/REJECTED/EXPIRED protective-order fixtures
reproduced fabricated FILLED journal writes: **4 FAIL / 12 PASS**. Minimum one-line
closure-history predicate now requires FILLED, not arbitrary terminal status. Main focused
suite **16 PASS**, independently rerun **16 PASS** with REVIEW_PASS_WITH_LIMITATIONS.
Combined credential-empty/network-denied suite **189 PASS**, 27 warnings; diff check passed.
No historical journal corrections, broker requests, runtime activation or safety-gate release.
Remaining: FILLED alone is insufficient lifecycle attribution; causal time/identity/quantity
joins and UNKNOWN-versus-loss handling remain unresolved. RUNNER_START stays NO_GO.
Next: port reviewed UNKNOWN/restored-exit semantics minimally, without blanket branch merge.

## 2026-10-19 05:18 UTC — fail closed on partial position conversion

Baseline `85c82a1`. Eight malformed-row/prefix cases reproduced partial snapshot return
(**8 FAIL / 25 PASS**, after correcting a fixture enum reference). Conversion exceptions
now reject the whole snapshot with a sanitized error, never a partial successful list.
Independent review identified NaN/Infinity quantity as another silent-loss path; four
additional cases reproduced **4 FAIL / 33 PASS**, then finite-quantity validation was added.
Combined isolated suite **185 PASS**, 27 warnings. Valid zero rows and SHORT quantity remain
covered. Pilot-2 contract/collector/supervisor hashes match activation records (3/3).
Final independent review: REVIEW_PASS_WITH_LIMITATIONS; focused isolated rerun **49 PASS**,
27 warnings. No real-exchange or deployed-runtime proof is claimed.
No broker access, runtime deployment, journal/cooldown mutation or frozen-artifact edits.
Full runtime source compatibility, restored-exit attribution and external GO gates remain.

## 2026-10-19 04:12 UTC — BingX transport snapshot integrity

Baseline `f1d5b71`. BingX get_open_positions swallowed transport failures, API errors and
missing/malformed response data into []. Five regression failures reproduced this defect
(**5 FAIL / 19 PASS**); explicit successful list payload is now required. Transport exceptions
propagate; other failures raise generic credential-free errors; actual empty list remains valid.
Focused submission/reconciliation suite **36 PASS**; combined isolated suite **172 PASS**,
27 warnings. No broker access or deployment. Independent review: PASS_WITH_LIMITATIONS.
Residual identified by reviewer: outer adapter still skips malformed individual position rows,
which can conceal an incomplete snapshot. This remains a runner GO blocker; fix next with
synthetic tests and review. No closure attribution or historical fill claim is established.

## 2026-10-19 03:16 UTC — main position-snapshot failure guard

Baseline main `9818a04`. Main still treated failed/None position reads as an empty
snapshot and invoked closure processing. Two deterministic fake-adapter cases reproduced
**2 FAIL / 10 PASS**. Ported only the existing primary fail-closed guard: record error,
return in_sync=False before closure/journal side effects; actual [] remains valid.
Main reconciliation suite **12 PASS**, independently rerun **12 PASS** with
REVIEW_PASS_WITH_LIMITATIONS. Combined isolated allowlist **166 PASS**, 27 warnings.
Diff check passed. No broker calls, deployment, cooldown release or frozen-artifact changes.
Residual: adapters must not conceal failed reads as []; full restored-exit attribution
and runtime compatibility still need review. RUNNER_START remains NO_GO.
Next: inspect adapter failure-to-empty semantics and restored-exit causal attribution.

## 2026-10-18 local-main integration update

Actual main `edc1154` integrates the reviewed startup correction: missing open orders or a
failed pending query never establish FILLED. Existing main durable INTENT, unknown-response,
atomic unknown-admission, preflight, single-order-POST, conflict-preservation and verified
unwind-readback fixes remain. Main also removes legacy source-embedded Telegram credentials,
validates missing configuration, escapes HTML subjects, bounds requests and redacts exceptions.
Independent main-specific review: REVIEW_PASS_WITH_LIMITATIONS; main execution/notification
suite TEST_ISOLATION_PASS, **71 PASS**. No credential files or broker state were modified.
The full consolidated offline main allowlist later reported **157 PASS**; see EPIC-01.

The operator intentionally stopped the runner. This source integration is not deployment.
Telegram getMe with the primary .env token returned 401 on Oct 18; a valid external token
is still required. The primary journal currently contains local terminal FET records, but the
old startup bug could fabricate FILLED from missing identity. These are not verified fills;
preserve raw journal bytes and resolve attribution with authoritative evidence. Local active
symbols AVAXUSDT/TRXUSDT are dated observations, not current broker truth. Fresh broker
exposure/protection, historical-unknown handling, exact runtime/journal, single-runner and
supervised rollback/abort remain activation prerequisites. RUNNER_START=NO_GO.

Baseline HEAD `e5dd4db29c1477388caa64833ef1263b649ccbbd`. Isolated managed worktree: `/Users/mojtaba.rahbari/.codex/worktrees/post-pilot2-execution-recovery/lynxion-ets`. No automatic deployment. Pilot-2 stays frozen. The operator has since requested a TESTNET runner restart, but the execution-safety gate below remains NO-GO; do not start it while those defects are open.

## 2026-10-18 execution-safety gate — NO-GO for TESTNET runner

At approximately 2026-10-17 22:40 UTC, the previously authorized allowlisted **GET-only** VST audit returned zero nonzero positions and zero open orders. The permission endpoint returned an API error without a usable code; XAUT/NEAR/FET `allOrders` returned zero rows in this bounded call despite prior nonzero responses, and FET direct client-ID lookup returned `109421`. This is current-flat evidence only; historical FET submission remains UNKNOWN. The first sandboxed attempt produced only `ConnectionError`; the subsequent approved GET-only run succeeded. No broker write or order action occurred.

`main` commit `c63b8bd` fixes another reproduced startup safety defect: the production CLI previously proceeded after a TESTNET preflight with `ok=False` or after any preflight exception. Two red tests showed the use case starting; the minimal fix refuses broker-connected startup on a blocking preflight and refuses all startup when preflight itself fails. The isolated allowlisted suite is now **38 PASS / 1 expected XFAIL**. This protects only a deployed version of the CLI and does not resolve FET or protective-order uncertainty. Pilot-2 protected hashes and diff check passed.

`main` commit `3663aa8` fixes a false protective-unwind closure claim: previously a successful response to the emergency close POST made `_unwind_position` return `True` without checking whether the position was flat. Three red fixtures reproduced acceptance with an open position, a flat position without any GET, and query error. The bounded correction performs one broker position readback after an accepted close and returns success only for a valid flat symbol snapshot; otherwise the existing kill-switch path remains engaged. The existing B1 tests were adapted to distinguish accepted close from verified flatness, plus a full-flow open-position regression. The credential-empty/network-denied suite now reports **47 PASS / 1 expected XFAIL**; seven Pilot-2 protected hashes passed. This is source/fake-adapter proof only, **not deployed or independently reviewed**. It does not solve duplicate POST retries of the conditional or unwind orders, nor prove exchange-side final fills; keep `RUNNER_START=NO_GO`.

`main` commit `2dd2902` fixes the conditional-conflict cancel/replace hazard: the adapter formerly selected every pending same-type stop by symbol, canceled it without a proven position/order identity, and submitted up to two new conditional POSTs. A red fake-adapter fixture observed three submissions; the narrow fix preserves existing protection and returns failure to the existing unwind/kill-switch path. The suite is now **48 PASS / 1 expected XFAIL**; protected hashes pass. This is a conservative behavior change that still needs independent review and runtime verification. The lower-level automatic retry on lost POST response remains the XFAIL and continues to block runner activation.

`main` commit `d20b1b5` removes blind retries **only** for `POST /openApi/swap/v2/trade/order`; retry behavior for other endpoints is unchanged. Red networkless fixtures showed three physical sends on lost responses for MARKET, STOP_MARKET and TAKE_PROFIT_MARKET, while a non-order POST retry fixture remained green. After the narrow fix, the expanded isolated suite reported **52 PASS / 0 XFAIL**; protected hashes and diff check passed. Entry timeout still leaves the durable INTENT unresolved and blocks a new logical intent; conditional/close timeout still requires broker-state reconciliation. This eliminates the demonstrated local automatic-resend path, **not** all duplicate possibilities or real-exchange uncertainty. The code remains local-main only, without independent execution review or deployment. FET remains historically UNKNOWN and the current broker-flat snapshot does not clear its gate; `RUNNER_START=NO_GO`.

At approximately 2026-10-17 22:46 UTC, the allowlisted GET-only VST audit queried two documented FET order-history routes over a two-day window centered on the local INTENT. Each returned 15 rows, **zero exact `clientOrderId` matches** and **zero same-side orders within ±10 minutes by broker `time`/`updateTime`**. The current positions and open-order endpoints still returned zero; permission query remained unusable. The bounded window, clock-domain quality and historical retention are not enough to prove the INTENT was never submitted. Do not synthesize a REJECTED/CANCELLED/FILLED event or clear the global UNKNOWN admission gate. The audit script prints only counts/status classes, not raw order IDs, fills, signed URLs or credentials.

`main` commit `2b78a06` adds an atomic, process-local journal gate: a new durable INTENT is refused while any prior INTENT remains unresolved. Red tests reproduced cross-symbol and concurrent admission; after the fix, 31 allowlisted, credential-empty/network-denied tests passed. `main` commit `7f83e33` preserves a strict expected-failing diagnostic: one signed BingX STOP_MARKET POST with a lost response currently causes **three** physical POST attempts. The test suite then reported 31 PASS / 1 XFAIL. No broker adapter behavior was changed. The proposed broad POST retry removal was rejected by safety review because it could alter entry, close and protective behavior and leave positions unprotected after transient errors. A narrowly reviewed remedy with identity/reconciliation and protective-failure tests is still required.

The BingX [official swap-order reference](https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-trade/api-reference.md) currently describes `clientOrderId` for the real place-order endpoint as supported only for `MARKET` and `LIMIT`. Its test endpoint describes broader input but explicitly does not guarantee real-order validation. Therefore do **not** assume a conditional STOP_MARKET/TAKE_PROFIT_MARKET can gain exchange idempotency merely by adding `clientOrderId`. Any remedy must retain uncertain-response state, avoid blind POST retry/cancel-replace, query broker protection when authorized, and prove the partial-failure/unwind path. Real VST behavior remains UNKNOWN.

`main` commit `0990302` corrects the entry-market request key from `clientOrderID` to the officially documented `clientOrderId` in both plain and SL/TP entry paths. A red networkless fixture first showed the documented key missing; after correction the expanded allowlisted suite reported **36 PASS / 1 expected XFAIL** (the unchanged POST retry hazard). Legacy B2 tests were updated to assert local identity continuity without claiming exchange deduplication. The seven Pilot-2 hashes and diff check passed. This is code-only and behavior-affecting at the broker boundary; it needs independent review and controlled VST verification before deployment or any trading runner start. The historical FET lookup failure is not retroactively explained by this source mismatch without captured wire evidence.

Read-only local checks found no matching runner process; the primary checkout's durable journal has one unresolved FETUSDT INTENT (latest timestamp 2026-10-10 11:35:04 UTC). The previous bounded GET-only VST snapshot was flat at its observation time, not proof of this historical submission's outcome. The new gate is code-only in local `main`, not deployed to the primary runtime, and would conservatively block fresh orders while that INTENT remains. Main-specific safety diff still needs independent review. Do not delete or terminalize the INTENT, clear cooldowns, infer a fill/rejection, or start trading merely to obtain observations. Seven frozen Pilot-2 hashes rechecked PASS.

Required release evidence: exact runtime checkout/commit and journal path; authoritative resolution or explicit fail-closed treatment of FET historical submission; independently reviewed conditional-order retry/identity/reconciliation behavior; verified current broker positions and protective orders at activation time; single supervised runner, abort/rollback and smoke-check procedure. Until then: `RUNNER_START=NO_GO`, `DEPLOYED=NO`, `RUNTIME_VERIFIED=NO`.

## 2026-10-18 main-source integration (code only; runtime still stopped)

The operator directed that verified bug fixes move from isolated worktrees into the main project. The clean `main` integration checkout now contains the following controlled commits; the primary research checkout and its dirty C-11/C-35 files were not overwritten.

| Verified defect | Isolated source commit | Main commit | Main-target proof | Runtime state |
|---|---|---|---|---|
| Flat position falsely converted unknown order status to `CANCELLED` | `1d0a632` | `f39928e` | Main isolated harness self-test PASS; reconciliation suite 10 PASS | NOT DEPLOYED |
| Failed pre-send INTENT persistence could still reach broker send | `5a308e4` | `a2d3f29` | Red fsync fixture, then green; main combined suite below | NOT DEPLOYED |
| Post-send timeout/empty response falsely terminalized unknown INTENT | `6bbffa7` | `a2d3f29` | Two red failure-injection cases, then green | NOT DEPLOYED |
| Failed lifecycle append changed in-memory terminal status without durable write | `ef57be3` | `a2d3f29` | Red path-collision fixture, then green | NOT DEPLOYED |

The main-target credential-empty, network-denied allowlisted harness reported **28 PASS** across the execution truth ledger, submission-safety, durable-recovery and reconciliation suites. The seven protected Pilot-2 hashes passed and `git diff --check` passed. The reviewed source changes were adapted to main because its older test tree lacks the isolated scoped-service test file; the main-specific integration diff itself has **not** received a separate independent review. Source integration is not deployment or real-broker verification.

**Next P0 sequence, not a new epic:** independently review the exact `f39928e`/`a2d3f29`/`2b78a06` main diffs; global INTENT admission is now source-level fail-closed but not deployed or broker-validated. Resolve the conditional STOP/TAKE_PROFIT POST retry, identity and uncertain-response hazard without weakening protective behavior; prove startup reconciliation and protective-order state with networkless failure injection; then verify the intended TESTNET runtime commit, single-runner state, current broker positions/orders, rollback and supervised abort procedure. Do not silently weaken Risk/Fusion/Strategy or protective economics. The 2026-10-18 GET-only VST snapshot returned zero current positions and open orders, but FET historical submission and the key's permissions remain UNKNOWN. No runner, order, deployment or two-day trading observation window was started by this integration.

## Phase-0 gate — BOUNDED OFFLINE TEST ISOLATION VERIFIED

| Requirement | State / evidence |
|---|---|
| Separate worktree | VERIFIED: this checkout is distinct from the primary Pilot-2 data/runtime root. Worktree HEAD equals baseline. |
| Frozen hashes | Contract `d10a475166954421c49492ecc65c4aa2265d95df7d5166bb2a1ffeec2e17963a`; activation `7d1b90492af440687511dbd035fc4f8c9eb006f8a8803d6f18805d0523d5287a`; collector `2f7391e75719ae69745e39504381cadfa3e43f770eee6fe4336afe548b71d94e`; supervisor `509a410368813aa28d0e593404dc0daf7969c5db4949c96d125fe10658dee2a9`; original manifest `6cb1af4ad41191fd125c185ac2ee775892d24e2fadf80581d56111674f60594e`. All matched source report at first check. |
| Protected-artifact automation | PASS: `scripts/check_post_pilot2_protected_hashes.py` read-only check passed all five original-checkout targets. |
| Process state | `launchctl list` had no matching collector entry at check; OS `ps`/`pgrep` denied by sandbox, so VST liveness is UNKNOWN from this check. Do not infer stopped solely from that. |
| Host relationship | Same absolute laptop filesystem in Pilot-2 activation and VST local logs is consistent with shared host; exact runtime co-residency for each interval remains UNKNOWN. |
| Test isolation | `scripts/run_isolated_execution_tests.py --self-test` PASS for an explicit five-file offline test allowlist: clean re-exec environment, no worktree `.env`, dotenv loading denied, sockets/requests/urllib/process spawning denied, all four production broker adapter constructors plus BingX internal broker denied, and import-time logs redirected to temporary storage. An unreviewed e2e target was rejected. This is a bounded Python-process test guarantee, not a host-wide network sandbox or broker proof. |
| Backup | Original capture is ~4.2 GiB. No independently identified/authorized destination; `BACKUP_BLOCKED_OPERATOR`. Originals remain untouched. |

**Implementation gate: PASS for the five explicitly allowlisted networkless fake-adapter test files only; production execution remediation remains NOT APPROVED/NOT REVIEWED.** The P0 worktree is separate, protected hashes match, and normal test workflow cannot deploy into the stopped VST runtime. The harness does not authorize arbitrary test targets, authenticated broker calls, production deployment, or order actions. Any production execution diff still needs a reproduced defect, specific isolated regression tests, independent review, and a separate deployment decision.

## Queue

| Phase | Status | Next safe work |
|---|---|---|
| 1 host/execution truth | PARTIAL | Operator testimony and source evidence are consistent, but host logs/clock offset and broker truth remain unavailable; Gate A needed for account state. |
| 2 latency/churn | PARTIAL | Three 2026-10-07 local INTENT-to-result observations were 252.1–384.1 seconds; an additional Oct-10 BTCUSDT local result took 491.9 seconds. Endpoint allocation and UNI churn are NOT_MEASURED/UNKNOWN. Existing isolated timing candidate is not deployed. |
| 3 minimal remediation | ISOLATED UNKNOWN-STATUS FIX; NOT DEPLOYED | Two prior diagnostic candidates and the new flat/UNKNOWN reconciliation correction received independent `REVIEW_PASS_WITH_LIMITATIONS`; no deployment. Five allowlisted fake-adapter suites first ran 31 pass/1 fail (pre-existing LIVE-risk-policy expectation); after the correction, four relevant suites ran 25 pass. Do not weaken the guard to satisfy the old test. |
| 3 reactivation checklist | DRAFTED | See handover; stop for operator decision. |

## Checkpoint evidence and issue decisions

| Issue | Decision | Evidence / unknown |
|---|---|---|
| Laptop fault attribution | NEEDS_EVIDENCE | OPERATOR_TESTIMONY: laptop problems caused stops. Supervisor `child_start` counts starts, while collector `collector_restart` is recorded only when a pre-existing manifest is recovered; the two counters have different semantics and need not match. Exact mapping of eight starts to six restart records and each downtime mechanism is not independently established. Classification `CONSISTENT`, not proven per outage. |
| VST unresolved submission; XAUT/NEAR exits | CURRENT-OPEN INCIDENT CLOSED; HISTORICAL ATTRIBUTION NEEDS_EVIDENCE | The prior GET-only VST snapshot showed zero nonzero positions and zero open orders, so none of XAUT/NEAR/FET is represented as currently open **at that snapshot**. Exact query timestamp was not retained; result documented by commit `46b98e1` at 2026-10-13 08:50:29 UTC. `allOrders` returned 31 XAUT, 23 NEAR and 19 FET rows. XAUT/NEAR filled reduce-only STOP_MARKET rows lack a preserved exact alert-to-order/fill join. FET INTENT had no client-ID match in the bounded 19 rows; lookup `109421` does not prove non-submission. See `docs/engineering/XAUT_NEAR_FET_RECONCILIATION.md`. Cooldowns and unknown-submission gates remain; no runner restart. |
| Entry latency | NEEDS_EVIDENCE | Local ledger has total INTENT-to-result durations. Shared five-requests/60-second limiter and serialized broker admission are plausible contributors, not measured cause. Slowest endpoint `NOT_MEASURED`; no real before/after result. |
| Stale intents | NEEDS_EVIDENCE | No universal age/TTL check was established on the inspected order path. New TTL/deviation rejection would alter acceptance and is `BLOCKED_OPERATOR`. |
| UNI canceled stops | NEEDS_EVIDENCE | Screenshot display timezone, order identity, trigger, and API result are unverified here. Canceled is not equivalent to invalid request or duplicate. No AAVE lifecycle link assumed. |
| ETH SL/TP journal candidate `478acdc` | ACCEPT_WITH_LIMITATIONS | Independent reviewer: metadata precedence only, `REVIEW_PASS_WITH_LIMITATIONS`; not deployed, not broker protection proof. |
| XAUT/NEAR history diagnostic `cfa58d9` | ACCEPT_WITH_LIMITATIONS | Independent reviewer: distinguishes API error/malformed from valid empty history and preserves UNKNOWN cooldown, `REVIEW_PASS_WITH_LIMITATIONS`; not deployed, exits remain unknown. |
| Broker idempotency | NEEDS_EVIDENCE | BingX code generates/transmits <=40-character alphanumeric `clientOrderId` and has lookup by identity; durable journal stores INTENT before send. Real exchange duplicate handling after lost response and per-endpoint/order-type guarantees remain unverified. Never blind-retry UNKNOWN. |
| Protective state | OPERATOR_DECISION | Local hydrated/reconciled stop evidence is not independent current broker protection. Unprotected/unknown is not protected; automatic replacement would be order-bearing. |

Gate A was subsequently explicitly approved. An allowlisted HTTPS GET-only VST audit ran from a separate script without raw payload/credential logging. The first trade-history query's `100001` was caused by an audit-tool signing/URL-order mismatch: the corrected query returned valid history. Do **not** attribute that first error to a broker outage or absent order. The permission-query endpoint still returned an API error, so the credential's actual trading permission remains UNKNOWN. No order mutation, runner restart, new collector, V3 or strategy-policy change was made in this recovery worktree.

Research cohorts remain immutable `PARTIAL`; no new collector, Edge experiment, authenticated account query or order action.

## Research provenance dependencies (R14 Lead A; no policy expansion)

The canonical backlog's R14 `INSUFFICIENT_PROVENANCE` is **not** an exit-optimization task. Existing P0 execution-truth work can supply, where independently verified: (1) stable local intent/client order/exchange order identity; (2) authoritative entry and closing fill IDs, quantities, prices, fees and UTC/event/receipt timestamps; (3) venue/account route and symbol/contract identity; (4) time-aligned observed manager marks with source/clock quality; (5) protective-order creation, replacement, cancellation and terminal-state linkage; (6) explicit unresolved/partial-fill and history-query-error states. For XAUT/NEAR specifically, historical filled reduce-only stops are **not yet** a verified alert-to-order/PnL join. Missing fields remain `UNKNOWN`; no synthetic market path or inferred leverage repairs them.

The same P0 evidence may clarify R20 sibling-mechanism comparisons only at Lynxion's local execution boundary; it cannot supply the sibling's missing all-candidate denominator. R22 historical universe/ranks and R25 joint liquidation/OI/OBI panel are **not** P0 outputs. Do not add exit policy, stop economics, order replacement or any research outcome calculation to P0. Authenticated queries/deployment remain separately gated; this section only maps evidence already within the execution-truth mission.

## 2026-10-13 static safety continuation — no order-path modification

**FACT (source-level, not broker outcome):** `bingx_adapter.py` sends stable `clientOrderId` on the entry `execute_order` path, but `place_conditional_order` constructs STOP/TAKE_PROFIT `conditional_order_data` without one. The shared `_make_request` retries signed POST on `ConnectionError`/`Timeout` (and retryable HTTP errors). A lost response during a conditional POST can therefore cause a second physical POST without a stable client identity in that payload. The conflict branch can cancel pending same-type conditional orders and then resend. These are reachable source paths; whether BingX deduplicates them, how often this occurred, and whether a specific UNI/ETH stop was affected are **UNKNOWN**. Do not equate a cancellation with an invalid request or claim actual duplicate broker orders.

**Root-cause classification:** potential conditional-order duplicate/replace hazard is a confirmed *local mechanism*, not a proven historical incident root cause. Exact request/response identity, endpoint behavior and protective-state truth remain missing. **Unimplemented correction candidate:** stable conditional-order identity plus fail-closed unknown-submission reconciliation and identity-scoped replacement, without altering SL/TP economics. This needs specific credential/network-isolated failure-injection tests, independent execution review and operator deployment decision. The new bounded harness enables selected offline tests, not general authenticated-network proof. Protected Pilot-2 hash checker still passes in the original checkout.

The previously checked system and bundled Python runtimes lacked one or more dependencies. A separately verified existing pyenv Python has `pytest`, `pandas`, `requests` and `numpy`; no package installation was needed. Under the clean, allowlisted harness, five suites yielded **31 PASS / 1 FAIL**. The failing `test_decision_record_written_before_send` expects `ExecutionMode.LIVE`, while the current guard blocks because BingX live risk policy is not configured. This is a test-versus-current-policy conflict, not permission to weaken risk or evidence of a broker defect. The harness self-test passed and a non-allowlisted e2e target was denied. No original journal, protected artifact, broker or runner was touched. `.env.example` contains credential-shaped values of unverified validity; the test harness does not load it or any `.env` and never prints values.

### 2026-10-14 bounded UNKNOWN-status correction — isolated, NOT DEPLOYED

**FACT:** `BrokerReconciliationService.reconcile` previously converted an unrecognized/timeout broker order status to a local `CANCELLED` terminal event whenever the position snapshot was flat. A red fake-broker test reproduced `CANCELLED_UNKNOWN` from `UNKNOWN`; a flat position is not evidence of canceled order. The minimal diff now keeps the original submitted journal record, reports `recoverable status=UNKNOWN`, and sets `in_sync=false`. A second test injects status-query `TimeoutError`; repeated reconciliation stays idempotent. The new tests and four other allowlisted suites yielded **25 PASS** in the isolated harness; the separate pre-existing LIVE-policy test remains FAIL and was not silently counted green. Protected hashes passed.

**Independent review:** `REVIEW_PASS_WITH_LIMITATIONS` (separate reviewer). No order send/retry, protective-order economics, Strategy/Risk or Pilot-2 change. **Limitation:** current production reconciliation callers log recoverable drift but do not necessarily block new trading on UNKNOWN (`production_trading_orchestrator.py` and `auto_detection_orchestrator.py`); this narrow correction is not end-to-end fail-closed eligibility. The harness is process-level, not an OS-wide network denial. Keep the remaining safety gate open; no merge, deployment, runner restart or broker action. A behavior-changing global halt policy needs separate operator decision.

### 2026-10-15 pre-send INTENT durability correction — ISOLATED, NOT DEPLOYED

**FACT (original defect):** `infrastructure/brokers/multi_broker_service.py` caught every `record_intent(...)` exception and could proceed to `authorize_and_send`; more importantly, the journal's `_append` swallowed real write/flush/fsync failures and still returned an apparent INTENT. The first reviewer correctly returned `REVIEW_FAIL` because an exception-only mock missed that real failure mode. A revised red test used a real `LiveOrderJournal` with a directory/file-path collision and reproduced the path reaching `authorize_and_send`; a separate test injects `fsync` failure. The minimal correction propagates actual INTENT persistence errors, updates the INTENT in-memory index only after successful fsync, and returns before send when persistence fails. Other lifecycle journal writes retain their previous best-effort semantics. The six-file allowlisted network/credential-denied suite produced **33 PASS**. Protected Pilot-2 hashes passed.

**Independent re-review:** `REVIEW_PASS_WITH_LIMITATIONS`. The reviewed diff adds no retry, order submission path, protective economics, Strategy/Risk change or deployment. An fsync failure can leave an orphan INTENT line on disk although no send occurs; treat it as historical uncertainty, not an order fill. This is pre-send source/fake-adapter proof only; post-send UNKNOWN handling, end-to-end eligibility, broker truth and deployed runtime remain unverified. Do not merge/deploy or restart the runner without the separate operator gate.

### 2026-10-15 post-send unknown preservation — ISOLATED, NOT DEPLOYED

**FACT (original defect):** `MultiBrokerExecutionService.execute_order` recorded `FAILED` in the live order journal for any exception from `authorize_and_send`, even when `broker.place_order` had already begun. A fake-broker timeout after invocation reproduced loss of the in-flight INTENT; an empty result also followed a terminal-failure branch. A bounded correction marks when the send callback begins and retains the durable INTENT/client-order identity on timeout or empty result after that point. Guard denial and pre-send exceptions still follow their existing failed path. Two parameterized fault-injection cases plus adjacent tests passed: **35 PASS** in the clean allowlisted harness. All seven protected Pilot-2 hashes passed before commit.

**Independent review:** `REVIEW_PASS_WITH_LIMITATIONS`. This does not retry, create an order path, alter protective economics or change Strategy/Risk. An explicit broker rejection represented only as `None` may remain operationally sticky; this is conservative UNKNOWN rather than fabricated rejection. The caller can still return `None` and potentially create another logical intent; global unknown-submission admission and startup reconciliation remain unproven. No real-broker or deployed-runtime guarantee follows.

### 2026-10-15 lifecycle journal consistency — ISOLATED, NOT DEPLOYED

**FACT (original defect):** after a durable INTENT, `LiveOrderJournal._append` changed the in-memory status to terminal before attempting the non-INTENT disk write. A real directory/file-path collision made `record_failed` silently fail to write while `in_flight()` incorrectly omitted the order; restart from the original file still recovered INTENT. The red test reproduced this split. The minimum correction writes, flushes and fsyncs before changing `_orders` for every lifecycle event. INTENT failure still raises to block pre-send; subsequent write failures remain best-effort but leave prior in-memory state. The credential/network-denied relevant suite gave **36 PASS**.

**Independent review:** `REVIEW_PASS_WITH_LIMITATIONS`. This prevents one false in-memory terminal classification without changing order send, Strategy/Risk or protection economics. On fsync failure after bytes were written, a later restart may see a row not reflected in current memory; the append remains nontransactional. Later lifecycle failures still return silently, and global UNKNOWN retry admission is not proven. No broker, runner or Pilot-2 mutation; not VST-ready.

### 2026-10-15 existing fault-injection suite isolation audit

`tests/unit/test_production_failure_injection.py` was inspected but **not run or added to the broad test allowlist**: its scenario A constructs the production `BingXBrokerAdapter` with a live base URL and test-shaped credentials. The isolated harness intentionally denies that constructor, even if a test later monkeypatches its internal broker method. Other cases in that file use local fake broker state or pure sizing, but running the whole file would not be an isolated all-green proof. A future exact-node allowlist or rewrite to construct only a networkless adapter is required before counting those cases. No authenticated client, network or order action was attempted in this audit.
