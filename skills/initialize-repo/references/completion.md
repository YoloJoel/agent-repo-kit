# Check the actual onboarding result

Assess artifacts in the target repository before claiming completion. Work only within the
real requested scope (whole repository for a bare invocation). A batch/vertical slice does
not redefine completion scope; continue remaining batches without routine approval. Do not substitute directory counts or checker success for content review.

- Verify project identity, module boundaries, build/test commands and external assumptions
  against source/configuration. Include build scripts, lockfiles, resources and runtime-read
  documents; map the last group using policy.behavior_paths when their extensions look like prose.
- For new repositories, record actual goals and observable acceptance criteria, then implement
  using the user's chosen tool. Create necessary design/ADR only when the work warrants it.
- For existing repositories, read the selected code, callers and tests. Produce explanations
  of normal/error/boundary flows, observable contracts, state/concurrency/recovery and gaps.
  A source index is navigation, not a completed explanation. Provide an architectural overview
  for a scope spanning components/processes, with useful diagrams and evidence-backed boundaries.
- For existing code, create/reuse current behavior specs at policy.paths.specs, with
  observable requirements/scenarios and Baseline/Source links. Invoke baseline spec-status
  for the requested scope. Baseline prose without the spec handoff is incomplete onboarding;
  distinguish specification PASS from missing verification PENDING. Respect analysis-only scope.
- Require the default generation-aftercare source audit: reopen source independently of the
  generated outline, inspect omissions and reverse-check claims, record findings, fix/dispose,
  and reopen source for post-fix recheck. Run baseline audit-status for the relevant report.
  Structural PASS cannot replace this; a same-agent pass is not an independent reviewer.
- Maintain one question/decision source. Separate source facts, owner choices, accepted promises
  and validation conditions. Record accepted compatibility differences and their consequences;
  do not approve unknown semantics or invent owner decisions.
- Run confirmed checks. With established behavior, execute original characterization before
  changing it, then regression and target acceptance. Keep missing conditions PENDING and
  report specification-only checks separately from business test execution.
- After a change, recheck affected current knowledge and effective-spec verification links.
  Preserve immutable baseline snapshots and explicitly retire historical explanations when
  appropriate. Complete native synchronization/archive with the selected tool.
- Save scope, actual results, remaining work and a usable next step. Completion can be partial:
  distinguish setup, explained modules/contracts/cases, executed tests and runtime trust.

The desired result is usable source-backed engineering knowledge and repeatable local
verification. It does not depend on hosted CI, a particular daily Skill, or identical filenames.

## Project artifact quality

Run onboarding-status, not just doctor/structure. Require a curated project-specific entrance,
full declared production capability coverage with explicit supporting/excluded scope, current
specs and source audit of all claimed artifacts. Explicitly review spec-self-containment with
Baseline hidden. Requirement/scenario counts alone are not acceptance. Compilation-only
checks do not count as business tests. init-report.json is a historical initialization snapshot;
current summaries cite the actual phase/run/time/scope and PENDING gaps. An absent Change
directory during source-baseline authoring is not itself an error; do not create empty artifacts.
