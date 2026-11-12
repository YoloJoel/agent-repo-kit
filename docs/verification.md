# Verification record — 0.1.0

Date: 2026-11-12. Local execution: Linux, CPython 3.12.14. This is a concise record of
actual execution, not a claim that every runtime/operating system has been exercised.

| Validation | Actual result |
| --- | --- |
| Source workflow suite | 47 tests PASS, including native installed-folder workflows |
| Installed-wheel workflow suite | The same 47 tests PASS using the installed runtime and repository native artifacts |
| Wheel build | PASS; dependency-free Python wheel built from this implementation |
| Official Skill frontmatter/name validation | All 3 Skills PASS |
| Shipped JSON schemas | Both parse successfully |
| Current requirement/test navigation | All 8 current requirements referenced by meaningful workflow tests |
| Installed CLI entry point | `ark --version` returns 0.1.0 |
| Installed generated-Hook smoke | Fresh init/repeat init, nested-cwd SessionStart via `ark` on PATH, consumer CI resource: PASS |
| Existing-repository agent exercise | PASS; source-grounded baseline, actual tests, preserved assets and repeat initialization |
| New-repository agent exercise | PASS through reviewed synchronization, real tests, delivery, archive and post-archive CI |
| Native Claude manifests | Claude Code 2.1.322 strict runtime validation: plugin and marketplace PASS |
| Standard Skills installation | Skills CLI 1.8.1 discovers and installs exactly 3 Skills into an isolated Codex project |
| Remote Git-ref Skills installation | Actual GitHub `owner/repo#branch` installation and installed-helper initialization PASS |
| Installed-Skill agent exercise | PASS; all 11 inventory files reviewed, 8 actual tests PASS, installer and user content preserved |

## Native distribution

The recommended release is a native Claude plugin/custom marketplace plus standard root
Skill folders. Actual `claude plugin validate` strict checks passed for both manifest
files. Actual Skills CLI discovery found exactly three Skills, and a project-scope copy
installation preserved bundled scripts/resources. No user-level plugin or Skill setting
was changed by these isolated checks.

The actual published GitHub branch was also installed into a separate empty project with
Skills CLI 1.8.1 using `YoloJoel/agent-repo-kit#codex/bootstrap-agent-repo-kit`. All three
Skills were copied; the installed helper ran under `python -I -S` and returned PASS, mode
new and skill_delivery installed. README pins this verified CLI and uses Git-ref syntax
because a tree URL parses slash-containing branch names incorrectly in this version.

Native tests copy only the complete initialize-repo folder, disable site-package loading,
initialize without a source checkout and then delete the installed source before checking
the vendored runtime. They also verify no duplicate project Skill copies, installer-owned
folder preservation, empty-repo classification with a skills lock, checksum/traversal
failure before target mutation and deterministic native-artifact drift detection.

An independent Agent used the actual project-scope installed Skills on a Python retry
utility, without accessing toolkit source or installing a Python package. It explained all
11 inventory files in three source-cited module documents, recorded gaps, confirmed the
real test command and ran eight behavior tests. Baseline validation, doctor, structural
verification and both generated hook commands from a nested directory passed. Repeat
initialization returned no changes and kept the review current; all 13 installer-owned
file hashes, the dirty README bytes and the original AGENTS prefix were preserved.

Runtime manifest validation is distinct from submission to Anthropic's official directory;
the supported route is the repository's custom marketplace. Live model invocation and
host trust remain separately unverified: the fixture's live Codex process could not start
because the host state directory was read-only. Hook smoke checks do not claim live loading.

## No-install Agent entry exercise

A fresh independent Agent followed START_HERE.md on an existing Python fixture, without
pip, a virtual environment or a global ark command. It bootstrapped with the source entry,
preserved human instructions/dirty README/source/tests, documented actual behavior and
contracts, reviewed all eight inventory files and ran six real tests. Baseline validation,
doctor and structural verification passed. The exact generated SessionStart command worked
from a nested directory with PYTHONPATH empty. No user installation steps were needed.

Automated bootstrap tests additionally run with Python `-I -S` to disable installed-package
loading, delete the toolkit checkout before invoking generated hooks, migrate legacy owned
hooks while preserving user settings, detect GitHub CI automatically and distinguish failed
diagnostics from successful scaffolding. Live host loading/trust remain separately unverified.

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
at commit 1f237da79db5d11afdc875ebb64e2acdbbc5d754 passed all seven jobs, including native
manifest/installer checks. Later commit status is reported separately. Remote branch protection is not enabled
by this implementation. Evidence/requirements links establish traceability, not complete
semantic correctness or adequate assertions by themselves.
