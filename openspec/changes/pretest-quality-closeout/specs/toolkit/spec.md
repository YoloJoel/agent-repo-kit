## MODIFIED Requirements

### Requirement: Require real current delivery verification (REQ-VERIFY-001)

Verification: automated

Required checks SHALL actually run/pass or have current explicit external/manual evidence.
Missing, partial, stale or unavailable required checks SHALL prevent overall PASS.
Input mutation during checks SHALL fail. Handwritten/committed PASS alone SHALL not close work.

#### Scenario: Required command is unavailable

- GIVEN a required configured check
- WHEN its executable is missing
- THEN the check is NOT_RUN and delivery is PENDING

#### Scenario: Lightweight command mutates reviewed inputs

- GIVEN a content-bound lightweight declaration and a required command
- WHEN that command passes but changes reviewed inputs or the candidate diff during execution
- THEN the same run fails input currency and retains the actual command output


### Requirement: Preserve specification synchronization through archive (REQ-ARCHIVE-001)

Verification: automated

The toolkit SHALL reuse OpenSpec layout/workflows, record reviewed synchronization and
require fresh workspace delivery evidence. Archival SHALL retain valid in-Change artifact
references, usable CI and no stale active session pointer. Hashes SHALL NOT be described
as proof of semantic equivalence.

#### Scenario: Archive a verified change with an internal review artifact

- GIVEN synchronized current specs and a review artifact inside an active Change
- WHEN delivery passes and the Change is archived
- THEN the artifact reference resolves, candidate CI rechecks successfully and context
  does not point at a missing active checkpoint

#### Scenario: File-native archive remains native

- GIVEN a verified file-native change with no toolkit metadata sidecar
- WHEN toolkit close is requested before native synchronization and archive
- THEN it reports PENDING/native-archive-required with exit 2 and preserves the active files
- AND the selected native workflow remains responsible for synchronization and archive


### Requirement: Validate engineering relations without binding the development tool (REQ-RELATIONS-001)

Verification: automated

The toolkit SHALL validate applicable current/delta scenarios, identities, references, ADR and knowledge relations. Native titles/renames and foreign IDs SHALL remain usable. Format exceptions SHALL be explicit, content-bound, expiring and unable to waive required business checks. Human report content and accepted history SHALL be preserved. Specification-stage success SHALL NOT count as delivery success.

#### Scenario: Review native specifications before implementation

- WHEN valid native proposal/tasks/delta files still contain unfinished implementation tasks
- THEN specification review can pass without running business commands
- AND delivery remains pending until applicable checks and tasks are complete

#### Scenario: Complete composite dependency identity

- WHEN Depends-On names a composite REQ identity whose current owner is missing
- THEN validation reports that complete missing identity as pending
- WHEN the actual complete identity is current
- THEN that missing-owner finding is cleared


### Requirement: REQ-BEHAVIOR-QUALITY-001 Behavior evidence and candidate review
Verification: automated
The toolkit SHALL require source-derived observable behavior review for existing-repository onboarding separately from file/capability coverage. It SHALL retain unknown/inferred/defect observations without promoting them to new current promises, check explicit source-path/branch/effect obligations and all declared normative clauses, attempted counterexamples, canonical same-condition contract conflicts and actual assertion/check mappings. Coverage SHALL be labeled as the declared discovered inventory, with runtime execution assessed separately.
The toolkit SHALL bind behavior reviews to actual source/spec/test/policy inputs, preserve immutable snapshots and verification-change/removal dispositions, expose declared transitive impact and detect new unmapped sources. It SHALL apply affected review conditions consistently to local/CI/direct delivery and toolkit close. A two-pass source/target/assertion candidate review MAY support intentional native deltas without declaring current baseline synchronized; actual tests and native archive remain separate obligations.

#### Scenario: Directory coverage and comment-only tests
- WHEN file/capability maps and REQ comments exist but observable-unit, effective-path, clause or assertion evidence is absent
- THEN existing-repository onboarding remains pending rather than being certified by structure or counts

#### Scenario: Contradiction, uncertainty and repeated contracts
- WHEN a current promise has an unresolved counterexample, inferred/unknown/defect support, or a declared same-key/same-condition contract conflict
- THEN the inconsistency prevents a successful behavior review
- WHEN a reviewed fact is intentionally not promoted or evidence is unavailable
- THEN its baseline/gap disposition and limited coverage remain explicit

#### Scenario: Source or test drift and candidate lifecycle
- WHEN affected source/test/spec evidence changes or a new unmapped production input appears
- THEN delivery/close cannot rely on stale behavior evidence, including when old impact units are empty
- WHEN an actual closed two-pass candidate audit covers all native targets, affected/new sources, current specs, inventory and actual assertion tests
- THEN candidate review may support delivery while the old current baseline remains pending refresh
- WHEN actual audit inputs or targets subsequently change
- THEN that candidate declaration is invalid until reviewed again

#### Scenario: Native readiness and meaningful regression probes
- WHEN the native toolchain or external prerequisites are unavailable
- THEN readiness/NOT_RUN is reported separately from actual build/test results
- WHEN an assertion sees original, deliberately broken and restored bounded sample behavior
- THEN actual pass/fail/pass results and logs are retained without certifying arbitrary projects

#### Scenario: Executable assertion location and native command cwd
- WHEN a claimed assertion exists only in a Python literal/docstring or supported C-family literal/comment, or only by joining disjoint selected ranges
- THEN it cannot satisfy the executable assertion-location obligation
- WHEN a configured relative executable uses the repository root or a declared subdirectory as cwd
- THEN readiness resolves it from that cwd and reports availability separately from execution

