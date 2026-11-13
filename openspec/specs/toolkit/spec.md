# Agent Repo Kit behavior

## Scope

Generic repository initialization and continuing AI-assisted engineering. Skills own
semantic work; the CLI owns deterministic scaffolding, references, checks and evidence.

### Requirement: Install through native plugin or Skill distribution (REQ-NATIVE-001)

Verification: automated and native-tool checks

Claude Code SHALL receive a native plugin and marketplace manifest with two onboarding Skills.
Other hosts SHALL be able to install standard root skills/<name>/SKILL.md folders.
The initialize-repo folder SHALL contain all initialization code/resources and work when
copied alone without the repository, installed Python packages or a source bootstrap.
Project initialization SHALL preserve installer-owned Skills and avoid creating duplicates.

#### Scenario: Initialize from a copied installed Skill

- GIVEN only the complete initialize-repo folder in a host's installed Skills directory
- WHEN the Agent invokes its bundled initializer
- THEN project rules/runtime are created, existing content is preserved, and installed
  Skills remain the platform's responsibility rather than copied into every repository

### Requirement: Onboard without a global package installation (REQ-ONBOARD-001)

Verification: automated and workflow review

The recommended entry SHALL let the Agent bootstrap a complete toolkit snapshot into the
target without pip, a virtual environment or a global ark executable. Generated hooks
SHALL use the target's vendored runtime and remain usable after the toolkit source is removed.
Existing owned global-command hooks SHALL migrate without losing unrelated user handlers.

#### Scenario: Dispose of the toolkit after initialization

- GIVEN a target and a temporary complete toolkit snapshot
- WHEN the Agent bootstraps without installed packages and removes the snapshot
- THEN generated hooks work from nested target directories and semantic onboarding
  remains an explicit Agent task rather than being falsely reported complete

### Requirement: Preserve existing repository assets (REQ-INIT-001)

Verification: automated

Initialization SHALL support empty and existing repositories, merge human instructions,
preserve existing specs/IDs/settings/dirty content and reject unmanaged conflicts.

#### Scenario: Initialize and repeat on an existing repository

- GIVEN human AGENTS content, native OpenSpec artifacts and uncommitted changes
- WHEN installation runs twice with unchanged inputs
- THEN human content/IDs remain and the second installation makes no asset changes

### Requirement: Distinguish evidence inventory and understanding (REQ-BASELINE-001)

Verification: automated and workflow review

Inventory SHALL remain distinct from source-grounded static review. Review SHALL require
filled module explanations, valid scoped citations and current source/document digests.
Raw evidence SHALL be retained. Ready verification SHALL anchor pre-change evidence.

#### Scenario: Source changes after a reviewed pre-change anchor

- GIVEN reviewed source and a successful scoped ready verification
- WHEN implementation changes but historical evidence is preserved
- THEN delivery uses the anchor and current checks without rewriting old behavior

### Requirement: Require real current delivery verification (REQ-VERIFY-001)

Verification: automated

Required checks SHALL actually run/pass or have current explicit external/manual evidence.
Missing, partial, stale or unavailable required checks SHALL prevent overall PASS.
Input mutation during checks SHALL fail. Handwritten/committed PASS alone SHALL not close work.

#### Scenario: Required command is unavailable

- GIVEN a required configured check
- WHEN its executable is missing
- THEN the check is NOT_RUN and delivery is PENDING

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

### Requirement: Isolate resumable work and bound hook continuation (REQ-CONTEXT-001)

Verification: automated

Session pointers SHALL be isolated by worktree/branch/session. Startup SHALL avoid full
inventory/tests. Stop continuation SHALL be bounded and permit blocked handoff.

#### Scenario: Verification cannot finish in the current environment

- GIVEN an explicitly blocked checkpoint
- WHEN a Stop hook executes
- THEN normal handoff remains possible with saved next steps

### Requirement: Check actual candidate differences (REQ-CI-001)

Verification: automated

CI SHALL cover behavior/configuration differences with related changes or exact lightweight
declarations, rerun confirmed checks, protect raw/accepted decision history and avoid trusting
committed PASS reports. Declared native adapter support SHALL distinguish configuration,
protocol validation and live-runtime verification.

#### Scenario: Source changes after a lightweight declaration

- GIVEN a declaration bound to the former contents
- WHEN a further source change changes its digest
- THEN the stale declaration no longer covers the new candidate change

### Requirement: Support tool-independent and local-only development (REQ-PORTABLE-001)

Verification: automated and native-tool checks

The toolkit SHALL read native OpenSpec or mapped ordinary change files without requiring
ark.json, a development Skill, a session activation or the toolkit archive command.
Local checks SHALL work without a remote or hosted CI. GitHub Actions generation SHALL be opt-in.
Native tools SHALL own synchronization and archive. Proposed deltas SHALL remain distinct from
current accepted specifications; synchronization SHALL be checked after native archive.

#### Scenario: Develop using ordinary native assets

- GIVEN a locally initialized repository and proposal/tasks/delta files
- WHEN the selected development tool implements and tests the scoped behavior
- THEN local verification runs real checks without a toolkit lifecycle or remote service
- AND ambiguous associations or unsynchronized archived specifications cannot pass

### Requirement: Observe project facts and preserve context (REQ-CONTEXTUAL-001)

Verification: automated and workflow review

Initialization SHALL observe languages, build manifests, declared versions and roots from
actual repository files. Unknown business architecture SHALL remain unknown. Existing human
context SHALL be preserved. Risk-appropriate templates and a local engineering standard
SHALL be available without requiring every task to produce every asset.

#### Scenario: Initialize a mixed-language repository

- GIVEN actual Java/C source, a Maven declaration and human context
- WHEN initialization observes the repository and repeats
- THEN source-backed facts are navigable, human context is preserved, and repeated setup is inert
