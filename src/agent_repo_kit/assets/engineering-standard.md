# Repository engineering standard

## Authority and project context

Read AGENTS and docs/project-context.md. Source/configuration and runtime evidence describe
actual behavior. Baseline explains current and historical facts. Current Spec describes
accepted promises, active deltas describe proposed changes, Design explains implementation,
and ADR records consequential long-lived choices. Resolve disagreements explicitly.
Facts that can be established from source should be investigated. Ask owners about unresolved
material product/compatibility choices; reuse authorization and accepted decisions.

## Development entry and risk

Use OpenSpec, another Skill/tool, or direct conversation. Native tools own their lifecycle;
no toolkit development Skill, ark.json, explicit activation or secondary archive is required.
Preserve existing asset paths and identifiers. Do not rename valid IDs to fit a template.

| Work | Minimum applicable assets and checks |
| --- | --- |
| Read-only analysis | Relevant source/evidence and honest findings; no artificial Change |
| Wording/format/mechanical nonbehavior edits | Impact rationale and relevant checks; no ceremonial tests or complete Change |
| Observable fix or new behavior | Scope, proposal, behavior/scenarios, tasks and meaningful verification |
| Risky refactor or concurrency/state change | Preserved behavior, pre-change fixtures, design, scenarios and regression evidence |
| Protocol/data compatibility or migration | Explicit contract difference, compatibility decision, design, migration/recovery and validation |
| Framework/dependency model/module boundary | Impact/design; ADR when consequential or long-lived; native build and compatibility checks |

Use native artifacts or mapped equivalents. Design is required for new concurrency, data
models, external dependencies/interfaces and significant cross-module work. ADR is for
long-lived choices; local implementation detail stays in Design. Not-applicable dimensions
need a concrete reason, not invented content. A configuration diff can change behavior.

## Specifications and traceability

Describe observable behavior in Spec; keep class names/algorithms/thread choices in Design.
Identify requirements consistently with the repository's existing scheme. Give observable
scenarios with conditions/inputs and expected outcomes. Identify automated, manual or
external verification. Keep references from affected requirements to actual tests/evidence.
For a high-impact rule, derive a concrete input and predicted output, error or state change
from the Spec alone. For current behavior compare that prediction with the reachable source
branch for the same input. Preserve missing or conflicting evidence. For a proposed change
use the accepted target as the expectation and verify it against the candidate implementation.
Keep the assertion location and the actual test run as separate evidence.
Check the complete effective-spec verification matrix even when this change has no delta;
removing a test must not leave a current promise without a test reference or an explicit
required delivery-check mapping. Proposed deltas can precede tests; current promises retain
their obligations. Manual/external promises need their own required delivery check mappings.
Only executable test-source formats count as source references; a README, input fixture or
coverage table under the test directory cannot replace a deleted test. Map other executable
test systems to their actual required command explicitly.
Native OpenSpec validation/synchronization should be reused, not reimplemented as a merger.

## Baseline and knowledge

Explain responsibilities, full normal and failure flows, branches, state ownership, side
effects, compatibility and source/config/test evidence. Function lists are not explanation.
Record uninspected/uncertain dimensions and unavailable runtime conditions. Inventory does
not prove understanding. Distinguish facts, inferences, accepted choices and planned design.
Promote only selected behavior promises; defects and implementation details are not
implicitly permanent contracts. Preserve raw evidence and accepted history.
Recheck affected current explanations after implementation. Stale registered module,
contract or case descriptions keep delivery PENDING until refreshed or explicitly retired
with a decision. Original snapshots remain immutable; unrelated stale knowledge does not
block a scoped task. An edited explanation itself also needs its review declaration refreshed.
Changes to its recorded decision are also an impact. Verification binds current knowledge
and checks its final state; a command that changes its own verification inputs cannot pass.
Maintain one question/decision source; link product choices, design work, validation gates
and ADR to their implementation/specification outcome. Do not duplicate competing statuses.

## Implementation and verification

1. Establish actual scope, accepted contracts, target scenarios and unresolved facts.
2. Before risky changes, review affected behavior and establish necessary characterization
   or contract fixtures on the original version. New projects acquire existing behavior as
   code lands; they are not permanently exempt from regression requirements.
3. Implement using the selected workflow and update affected knowledge, tests and tasks.
4. Run confirmed native project commands; build candidates are not automatically approved.
5. Inspect implementation/design/spec consistency and meaningful failure/boundary assertions.
6. Run `python hack/ai/ark.py check --base <revision>` locally. Active deltas are proposed
   behavior; native archive owns synchronization, followed by current-spec verification.
7. Keep actual results, risk, missing conditions and next steps in the repository.
   On onboarding, complete actual project configuration, discover unregistered contract files,
   refresh Baseline navigation, audit all final artifacts and run onboarding-status --record.
   This final snapshot checks current declarations/structure and their input currency, not
   execution of business tests. Structure PASS can legitimately have an empty spec tree; it
   cannot establish semantic onboarding or behavior verification. A phase
   such as specification review is distinct from implementation delivery or archive.

A required missing/unrun/partial check is PENDING; failures are FAIL. PASS requires actual
applicable evidence. Bind reports to the source/workspace, policy and tool environment.
No handwritten PASS, stale run or placeholder command can substitute for real verification.
Manual/external checks need an actual artifact and reviewer; a declaration is not independent
certification. Review core policy/checker changes as well as business changes.

## Architecture and decisions

System overview describes roles, boundaries, dependencies and end-to-end flows. Baseline
explains current facts; target architecture names intended changes and migration differences.
ADR states context, decision, alternatives and consequences. Preserve Accepted ADR body and
raw/archive history; use superseding or supplemental records to correct accepted history.

## Local operation, exceptions and continuation

All core checks operate locally without GitHub, a remote or CI. Optional Git hooks and CI
reuse the same checker; their presence or configuration is not proof of effective execution.
Diagnose hosted required checks only when applicable. Preserve existing pipelines/settings.
Unknown non-document files are treated as behavior candidates, including configuration,
build inputs, lockfiles and resources. Add runtime-consumed Markdown/document paths or
patterns to policy.behavior_paths. Content-bound lightweight declarations remain available
for reviewed nonbehavior changes; do not globally exclude runtime inputs to avoid a gate.

Record existing debt separately from new/worsened problems. Exceptions need scope, reason,
owner, review/expiry condition and alternative evidence, under an applicable accepted policy.
Do not invent an exception or weaken a check simply to make a failure pass.

Keep AGENTS concise and load task-relevant context. Startup does not run full scans/builds.
Save scope, completed work, actual results, blockers and next steps during work; exit hooks
may never run. Isolate worktree/branch/session state. Normal pause and external blockers
allow recoverable handoff. Limit stop retries. Upgrade explicitly and preserve human content.

## Executed behavior evidence

For changes to established behavior, maintain a scoped behavior-plan.json alongside native
work artifacts, or map its existing path using policy.behavior_plans.<change>. The plan is a
verification matrix, not a development lifecycle. Preserve entries identify original source,
observable outcome, real checks and stable fixture/test files. Target entries identify intended
outcomes and checks. Replacements also name the old expectation/checks and a compatibility
decision. Use check.phases=["ready"] for old expectations that intentionally stop applying.
Run ready verification on original inputs before implementation. It executes the applicable
old checks and stores immutable source/plan/fixture/command/environment/log evidence. Delivery
reruns required regression and target checks and reports them separately. Do not weaken a
preserved fixture after anchoring; re-characterize the original version when evidence needs
correction. A once-empty repository acquires the same obligations when behavior is committed
or delivered. A missing old runtime remains PENDING; do not invent before-change success.

Optional JSON replay comparison uses exact JSON equality by default. Any ignored output leaf
needs an explicit pointer and nonbusiness reason. Keep the raw hashes and normalization visible;
never normalize away a true business difference. Native project test commands remain primary.

## Native asset formats

Reuse native report and knowledge front-matter formats as well as paths and IDs. Map machine
evidence with paths.evidence when native raw-batch directories have their own schema. Those
snapshots remain immutable and excluded from source inventory. Use path-scoped
change_associations only to clarify genuinely overlapping work; this does not expand a
change scope or create a global active-task pointer.

## Existing repository specification handoff

Existing-code onboarding includes source-backed current specs, not only Baseline prose.
Extract observable preserved behavior with scenarios and Baseline/Source references; reuse
existing IDs and native paths. Record routine preservation analysis without inventing owner
approval. Keep defects, contradictions and unknowns in the single ledger. Use baseline
spec-status to check declared handoff; specification and actual verification are separate.
Absent tests/check mappings remain PENDING. Explicit analysis-only scope may omit specs but
must report this limitation. Native OpenSpec CLI initialization is separate and optional: specs
can be written without it, but do not claim native commands are installed or validated.

## Source-first review after generation

Baseline/spec generation must be followed by a new source-derived coverage audit, findings
record, fixes or reasoned dispositions, and a separate post-fix source recheck. Cover both
source-to-document omissions and document-to-source truth, not just headings/IDs/hashes.
Use baseline audit-record/audit-status to bind the declared passes to source/artifact/report
bytes. Missing, stale or unresolved audits remain PENDING. Such records cannot prove actual
rereading, reviewer independence or semantic correctness. Declare actual review mode; preserve
accepted decisions and history. Stop with explicit remaining work rather than loop indefinitely.

## Behavior evidence and incremental semantic review

Discover observable behavior independently from directories/spec outlines, including cross-module
messages/configuration/lifecycle/calculation/upgrade paths. Current normative clauses require
verified effective branch/use/effect evidence; inferred/unknown/defect observations remain explicit
gaps or baseline facts. Attempt counterexamples and reconcile canonical contract facts across
related specs. Use the baseline-repo behavior-model protocol and baseline behavior-status.
REQ comments/test filenames are navigation; inspect actual stimulus/assertion/expected result
and map native checks. Test-method downgrades retain reasons, alternatives and unverified scope.
Source/spec/test changes require affected dependency/caller/contract review, not just fresh hashes.
Coverage is over a declared behavior inventory and is never proof of exhaustive discovery.
Record local build patches/toolchains and distinguish selected tests, full regression failures
and unavailable external services. Do not fix all existing business defects merely for onboarding.

An active delta may intentionally differ from current promises until native synchronization.
After actual two-pass source/target/assertion review, baseline behavior-change-record can bind
candidate evidence without certifying the stale current inventory. Audit all native targets,
affected/new sources and assertion tests. Actual ready/regression/target execution is still
mandatory; delivery and close share the gate. Refresh current behavior after native archive.

## One change across development tools

Read the actual current spec, applicable accepted decisions and this repository's engineering
standard before editing. Use the same scoped Change ID across OpenSpec, Superpowers and direct
requests, including in a new conversation. Keep accepted behaviors in the mapped current specs.
Use the Change delta for proposed behavior. A design draft or implementation plan is not a current
spec. The user can describe only the desired behavior; the working agent maintains these records.

- OpenSpec uses the native proposal, delta, design, tasks, synchronization and archive.
- With Superpowers, write the design and implementation plan directly to the Change's design.md
  and tasks.md when convenient. To reuse an existing local draft, put `Workflow-Source: <repo-relative.md>`
  on a line in its matching native document. The local check follows one reference, includes the
  source content in its fingerprint and reads unchecked tasks from the real plan. Keep the source
  present through archival. Use the project's effective spec and ADR conventions throughout.
- A direct request uses those same documents and local commands, with ordinary file edits.
  For a change of entry or session, inspect the diff and active Change before creating a new one.
- For a feature, give the delta a verifiable requirement and scenario. For a fix restoring a current
  contract, cite its stable IDs in `Current-Requirements: ID1 ID2`. A production maintenance change
  without a delta explains its preserved observable behavior on a `Preserves:` line. Write an explicit
  `Kind:` when intent is ambiguous. The existing content-bound lightweight route applies to small edits.
- Resolve the project's conditional obligations in policy.artifact_rules. Use `Risks: rule-id` in the
  proposal for semantic triggers. For a reviewed exclusion use `Risks: none` and a concrete
  `Risk-Reason:`. The actual candidate paths can still trigger rules. Reference an applicable decision
  with `ADR: docs/adr/NNNN-name.md` using the actual mapped path. The decision can be Proposed during
  specification and must be Accepted for implementation phases that require it.
