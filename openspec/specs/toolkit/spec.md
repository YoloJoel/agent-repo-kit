# Agent Repo Kit behavior

## Scope

Generic repository initialization and continuing AI-assisted engineering. Skills own
semantic work; the CLI owns deterministic scaffolding, references, checks and evidence.

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
