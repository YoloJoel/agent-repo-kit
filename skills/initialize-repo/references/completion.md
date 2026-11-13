# Check the actual onboarding result

Assess artifacts in the target repository before claiming completion. Work only within the
real requested scope. Do not substitute directory counts or checker success for content review.

- Verify project identity, module boundaries, build/test commands and external assumptions
  against source/configuration. Include build scripts, lockfiles, resources and runtime-read
  documents; map the last group using policy.behavior_paths when their extensions look like prose.
- For new repositories, record actual goals and observable acceptance criteria, then implement
  using the user's chosen tool. Create necessary design/ADR only when the work warrants it.
- For existing repositories, read the selected code, callers and tests. Produce explanations
  of normal/error/boundary flows, observable contracts, state/concurrency/recovery and gaps.
  A source index is navigation, not a completed explanation. Provide an architectural overview
  for a scope spanning components/processes, with useful diagrams and evidence-backed boundaries.
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
