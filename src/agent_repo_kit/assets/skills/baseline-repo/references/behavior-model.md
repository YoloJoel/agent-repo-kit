# Behavior-first discovery, evidence and review

Read this BEFORE selecting spec boundaries or drafting requirements. Source code is the
starting point; an existing spec tree, directory list or generated capability map is not
the discovery checklist. The runtime records/checks obligations; the Agent must do the analysis.

## Discover observable units

1. Identify externally or internally observable triggers: API/CLI, message topics and handlers,
   timers, configuration changes, process/device lifecycle, calculations and callbacks,
   upgrade/migration, persistence/replay and background work. Inspect registration AND actual
   callers, routing tables, configuration consumers and deployment switches. Trace cross-module
   flows; a transport, business handler and response encoder can belong to one contract.
2. Make one row per observable promise/meaningful alternative, not per source file or function.
   Group specs around behavior/cohesive contracts; modules remain source navigation. Enumerate
   cross-cutting units explicitly and name an owner. Reconcile orphan triggers, unowned effects,
   untraced consumers and unmapped callers before declaring complete discovery.
3. For each unit inspect normal, negative, boundary, recovery, concurrency, resource and
   compatibility dimensions. Say not-applicable only with actual reasoning. Trace reject paths,
   partial success, retry/ack ordering, timeout fallbacks, cleanup, crash/restart and cancellation
   where present. Best-effort publishing is not durable or acknowledged delivery.
4. Track `verified`, `inferred`, `unknown`, `defect` separately from `current`, `baseline`, `gap`.
   A guess or known bug must not become a new SHALL/MUST. Existing accepted source/spec conflicts
   remain explicit discrepancies. Retain unknown/gap rows in the denominator; do not fill in
   plausible defaults. Preserve the repository's single question/decision ledger.

## Trace evidence to an effective path

Record trigger + effective conditions + caller/registration + decisive branch + outcome/side
effect, using separate precise source anchors. Distinguish `definition` from `config-use`,
`entry`, `call`, `branch`, `effect`. A constant needs actual consumers/overrides, units, defaults,
and limits; a same-name symbol needs actual linkage/build/registration. Trace both sides of
external contracts where accessible; unavailable code remains a gap, never invented evidence.
Explain what each anchor establishes and what it cannot establish. Inspect runtime enablement,
value transformations and error propagation before writing capacity/timeout/resource claims.

For EVERY normative assertion attempt to falsify it: seek an input/state/configuration/path
that violates it, and consider a competing interpretation. Write the attempted counterexample,
alternative and outcome before closing the claim. Compare repeated messages/fields/units/ranges,
error codes, retry/ack/state names across ALL related specs. Assign canonical contract keys and
explicit applicability conditions; identical keys/conditions cannot carry contradictory values.
Different spellings/conditions require human/Agent reconciliation; the checker cannot infer synonyms.

## Durable protocol

Write `<mapped baseline>/behavior-inventory.json` (or preserve an equivalent existing file and
record its actual path). This is evidence/traceability, not a competing normative spec or question
ledger. Keep existing IDs; new behavior IDs only identify discovery rows. Schema 1:

- `scope`: whole or limited; `scope_reason`; `sources`: actual production/build/config paths.
- `discovery`: method, source_first, independence (describe actual mode, not claimed independence).
- `surfaces`: api, messages, configuration, lifecycle, computation, upgrade, storage, background.
  Each has status applicable/not-applicable/unknown, reason, evidence anchors and units (IDs).
- `units`: id, capability, owner, trigger, condition, outcome, confidence, disposition, reason,
  depends_on (other behavior IDs), evidence, dimensions, challenge, contract_facts, verification, tests.
- Every evidence anchor: path, reference (`path:Lx-Ly`), role, explains. Cite each chain component.
- Every dimension: status reviewed/not-applicable/unknown and concrete reason. Split significant
  alternatives into rows/scenarios rather than labeling a whole module reviewed.
- Current unit: requirement (existing authoritative ID/title), spec_path, normative_quote (actual
  clause verbatim). Baseline/gap units have no current requirement. Map ALL normative clauses.
- `challenge`: counterexample, alternative, result supported/contradicted/unknown, reason.
- `contract_facts`: optional list of key, condition, typed value. Normalize names, units, enum and
  payload fields deliberately; do not alter conditions merely to suppress a real conflict.
- `verification`: automated/manual/external/unverified. For automated, each tests entry is an
  anchor with role assertion plus input, expected, assertion (actual executable snippet), detects
  (why incorrect behavior fails), checks (required native command names from policy).
- Manual/external: verification_reason and checks. A missing mock/interceptor is a blocker to
  that method; investigate transport/adapter/integration alternatives. Record procedures and
  actual external evidence via the existing evidence workflow. Unexecuted is still PENDING.
- An automated-to-other downgrade additionally needs verification_change: reason, alternatives,
  remaining_gap, reviewer. Removed rows need removed_units mapping IDs to explicit dispositions.

Run `baseline behavior-record --document <actual file> --reviewer <actual reviewer>` after real
review, then `baseline behavior-status`. Recording never runs tests. Snapshots bind inputs and
retain old rows/modes; file changes invalidate currency. Whole onboarding requires this review;
upgrading 0.2.x does not silently certify old inventory. Do not regenerate old specs wholesale.

## Assertion and execution quality

For each promise locate the actual stimulus, reachable test target, assertion and expected result.
REQ comments and matching test filenames are navigation only. Inspect assertions against both
normal and failure outcomes. Run native checks; where practical mutate one meaningful behavior
and confirm the SAME test fails, then restore. Mutation is a scoped experiment, not universal proof.
Do not invent tests solely for implementation mirrors or broaden initialization into fixing all
historical business defects. Count discovered/reviewed/gap behavior units separately from files,
current requirements, mapped assertions, actual executed cases and external/environment blockers.

After changes, inspect `impact` behavior direct/transitive candidates, relevant callers, canonical
contract peers, tests and all affected docs. New/unmapped triggers require discovery updates.
Re-read affected code, reconcile real claims/assertions and refresh the record; re-hashing alone
is not semantic review. Audit behavior inventory alongside final specs in both source passes.

PASS means explicit declaration consistency/currency only. Neither this protocol, a ratio of 1,
two review records nor a native strict validator proves discovery completeness or semantic truth.

## Active changes and synchronization

Do not rewrite a current promise merely because an active delta proposes different behavior.
Use existing behavior-plan/ready evidence on original code before risky work. After implementation,
review the actual candidate against current promises AND intended targets. Keep original snapshots.
When current inventory is stale, record a current two-pass candidate audit for delivery:

1. Use the normal source-audit report with both real passes, covering affected/new production
   inputs, transitive units and actual assertion test sources. Audit the behavior inventory,
   affected current specs and ALL existing native proposal/design/tasks/delta files.
2. Add `behavior_change`: targets (all actual native target paths), contract_consistency (actual
   reviewed current/target field/range/term differences), units. Each unit needs id, outcome
   preserved/intentional-change/new/removed/unresolved, reason, counterexample, assertion_review,
   evidence anchors and tests entries using the actual assertion schema above. Retain affected IDs
   and discover new source behavior. Intentional changes/removals of promises need actual native
   MODIFIED/REMOVED delta entries. An unchanged current spec is not automatically the target.
3. Register the actual two-pass report with baseline audit-record, then run
   `baseline behavior-change-record --change <ID> --report <report> --reviewer <identity>`.
   It binds actual candidate bytes, target files, test assertions and source audit. Missing,
   unresolved or stale review blocks delivery/close through the same gate. Actual original,
   regression and target execution still use the existing verification workflow.
4. Manual/external units need verification, verification_reason, checks and verification_artifacts
   included in the source audit. Actual execution/evidence remains mandatory in delivery. An
   automated downgrade also needs verification_change fields defined above. Do not weaken a
   promise or remove an assertion to force PASS. Unresolved units remain PENDING.
5. Let the native tool synchronize/archive. Reconcile current behavior inventory/specs from the
   resulting source, review affected contracts/assertions, then re-record current evidence.
   Candidate approval is not current-baseline approval or native synchronization/archive proof.

Unrelated known gaps do not require fixing all history for a scoped task. New/unmapped production
sources remain discovery obligations even when the old impact set is empty. No extra task pointer,
second archive or mandatory daily Skill is introduced.

If a target intentionally changes Verification mode before archive, retain the current flat
policy.requirements.<ID> mapping and add targets.<change-id> with its actual type/checks. Current
checks use current mapping; delta delivery uses that named target. After native synchronization,
reconcile the current mapping. The target mapping is neither downgrade approval nor execution.
