## ADDED Requirements

### Requirement: Complete existing behavior specification handoff (REQ-BASELINE-SPEC-001)

Verification: automated

Default existing-code onboarding SHALL continue from source-backed Baseline contracts to
current observable behavior specifications at the mapped path, without an extra user prompt.
It SHALL preserve existing requirement identities, record evidence and preservation reasoning,
and keep defects, conflicts and unknowns separate from accepted promises. The handoff check
SHALL distinguish specification linkage from missing verification and actual test execution.
An explicit analysis-only scope SHALL be honored and reported as excluding specification.

#### Scenario: Ungoverned existing repository
- WHEN baseline-repo is invoked without extra parameters
- THEN it writes/reuses meaningful current specs and scenarios with Baseline/Source links
- AND does not require native OpenSpec CLI initialization for authoring files

#### Scenario: Missing specification or verification
- WHEN reviewed contracts lack current requirements or links
- THEN the handoff remains PENDING rather than claiming inventory-only completion
- WHEN the specification exists but lacks applicable tests/check mappings
- THEN specification status may PASS while verification remains PENDING

#### Scenario: Changed evidence or removed promises
- WHEN source, contract or preservation evidence changes, or a linked requirement disappears
- THEN the handoff reports stale PENDING or missing-requirement FAIL respectively
