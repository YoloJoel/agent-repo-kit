# Verification record — 0.1.0

Date: 2026-11-12. Local execution: Linux, CPython 3.12.14. This is a concise record of
actual execution, not a claim that every runtime/operating system has been exercised.

| Validation | Actual result |
| --- | --- |
| Source workflow suite | 35 tests PASS |
| Installed-wheel workflow suite | The same 35 tests PASS using only the installed distribution |
| Wheel build | PASS; dependency-free Python wheel built from this implementation |
| Official Skill frontmatter/name validation | All 3 Skills PASS |
| Shipped JSON schemas | Both parse successfully |
| Current requirement/test navigation | All 6 current requirements referenced by meaningful workflow tests |
| Installed CLI entry point | `ark --version` returns 0.1.0 |
| Installed generated-Hook smoke | Fresh init/repeat init, nested-cwd SessionStart via `ark` on PATH, consumer CI resource: PASS |
| Existing-repository agent exercise | PASS; source-grounded baseline, actual tests, preserved assets and repeat initialization |
| New-repository agent exercise | PASS through reviewed synchronization, real tests, delivery, archive and post-archive CI |

## Existing repository exercise

An independent workflow created an actual Python stock reservation repository with normal/
error behavior and six tests, an existing human AGENTS rule, native OpenSpec configuration,
a stable STK-REQ-007 identity, existing CI and an intentionally dirty README.

Onboarding preserved all original source/spec/config/CI/README bytes. Static baseline review
covered 11 inventory files with explanations and valid evidence. A combined source/test
document was accepted without suffix citation collisions. Baseline validation, doctor and
vendored commands passed. Unchanged reinitialization returned no asset changes and a
subsequent repeat changed no bytes. Static review was kept distinct from the six executed tests.

## New repository exercise

An independent workflow initialized an empty Python repository, created a scoped bounded-clamp
feature with three requirements and 14 meaningful tests, and ran pre-implementation ready
verification. Missing synchronization initially kept delivery PENDING and prevented close.

Using explicit reviewed file synchronization (native OpenSpec was unavailable), the final
fresh worktree recorded the review artifact inside the Change and activated a named session.
Delivery executed 14 tests and passed; close passed; post-close CI against the actual base
reran the 14 tests and passed. The artifact reference was automatically rebased into archive,
and context returned no stale active Change. No manual archived metadata repair was needed
in the final fresh exercise. Earlier failure evidence remained separate in the test fixture.

## Regression coverage

The suite checks empty/legacy initialization, human CRLF/trailing-space preservation,
selected-agent preservation, existing Hook JSON merging, unmanaged conflict preflight,
partial-write rollback, path/symlink rejection, unconfirmed build candidates, standalone
vendoring, citation boundaries, current/raw baseline evidence, pre-change anchors,
real consumer assertions, absent/partial/failed/timed-out checks, input mutation,
manual requirement mappings, stale/committed evidence, retired IDs and exact identity,
archive evidence rebasing, bounded Stop feedback, normal blocked handoff, actual event JSON
subprocesses, branch/worktree isolation, candidate CI, lightweight content binding, and raw/
Accepted-ADR history protection.

## Limits and remote execution

Protocol tests do not certify live Codex/Claude instruction loading, trusted hook execution
or actual OpenCode skill loading. OpenCode lifecycle hooks are not implemented. Native
OpenSpec CLI execution was NOT_RUN in the agent fixtures; reviewed synchronization is
explicitly recorded and does not claim otherwise.

The GitHub Actions matrix covers Linux/Windows/macOS with Python 3.11/3.13. Its actual run
status is separate from the local results above. Remote branch protection is not enabled
by this implementation. Evidence/requirements links establish traceability, not complete
semantic correctness or adequate assertions by themselves.
