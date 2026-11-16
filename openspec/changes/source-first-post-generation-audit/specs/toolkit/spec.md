## ADDED Requirements

### Requirement: Reopen source after baseline generation (REQ-SOURCE-AUDIT-001)

Verification: automated

Default Baseline/spec onboarding SHALL reopen source after drafting to derive a fresh branch
and flow coverage checklist, check source-to-artifact omissions and artifact-to-source truth,
record findings, correct or dispose them with evidence, and reopen source for post-fix recheck.
Reports SHALL distinguish actual same-agent separate review from independent review, retain
first-pass finding IDs and keep new unreviewed issues open. Declared audit evidence SHALL be
bound to source/artifact/report bytes and missing/stale/open audits SHALL remain PENDING.
Structural checks SHALL NOT be represented as proof of rereading or semantic correctness.
Accepted conflicts SHALL NOT be silently overwritten and repeated unresolved work SHALL
checkpoint rather than loop indefinitely.

#### Scenario: First draft contains unsupported claims or omitted branches
- WHEN generated Baseline/spec artifacts are ready
- THEN the Agent reopens actual source/config/callers to rebuild coverage and reverse-check claims
- AND records actual issues before fixes and rechecks corrected and neighboring paths from source

#### Scenario: Incomplete review or stale audit
- WHEN one pass, scoped coverage or a first-pass disposition is missing
- THEN the audit record cannot complete
- WHEN reviewed source, artifacts or report changes after recording
- THEN audit status is PENDING until relevant source review is refreshed

#### Scenario: Unresolved conflict or second-pass discovery
- WHEN an accepted spec conflicts with source or a new unreviewed issue appears
- THEN it remains explicitly unresolved rather than being silently closed for PASS
