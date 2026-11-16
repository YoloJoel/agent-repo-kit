---
name: baseline-repo
description: Establish or refresh source-grounded repository knowledge, contracts, current behavior specifications, behavior cases and evidence gaps. Use for existing-code onboarding, stale knowledge, refactor preparation or checking manuals against actual source; preserve existing documents, identifiers and history.
---

# Explain current behavior with evidence

A bare invocation covers the whole repository. Select the first capability/vertical slice
and subsequent batches yourself; do not ask the user to choose ordering or approve normal
continuation. Explicit user limits take priority. Checkpoints preserve progress while work
continues; they do not shrink the completion scope or end the task after one slice.

Use the supplied initialize-repo helper if project rules/runtime are absent. Run the target's
`python hack/ai/ark.py` for command examples written as `ark`. No package or global CLI is needed.

1. Read applicable repository rules and path/section mappings. Reuse current manuals,
   contracts, decisions and tests as navigation; verify important claims against actual
   source/configuration/callers. Do not silently treat design targets as current facts.
2. Run `ark baseline inventory`. Establish included modules, generated/vendor exclusions,
   unavailable external sources and actual revision/workspace. Inventory is not understanding. Read `references/artifact-quality.md` before planning batches. Keep the whole repository
   inventory/capability map as the denominator unless the user explicitly limited scope.
   Derive a complete business/supporting capability map from actual production/build/config
   sources, not from already generated specs. Record it with baseline coverage-record;
   uninspected capabilities remain pending. Do not present lifecycle-only or a partial module
   pass as whole-repository completion. Preserve explicit exclusions and their reasons.
3. Read `references/analysis.md`. Trace full normal/error paths, branch conditions, state,
   side effects, concurrency/recovery and compatibility. Explain what happens and why;
   function signatures alone are insufficient. Preserve useful existing prose and IDs.
4. Write or supplement module explanations with purpose, flows, state/failure, evidence
   and gaps. Existing localized/manual sections can be reused through policy mappings.
   Record with `ark baseline review --document <path> --files <paths> --reviewer <identity>`.
5. Extract observable contracts and precondition/input/expected-output/error cases into
   existing or scoped documents. Record them using `ark baseline register --kind contract`
   or `--kind cases`, with --document, --files and --reviewer. Case plans are not executed
   tests. Contract review does not claim every source behavior has been understood.
6. Separate facts, inferences, known defects, intended behavior and material choices.
   Resolve accessible facts yourself. Keep questions in the single ledger with
   `ark decision add/resolve/list` for its JSON format, or preserve/update an existing mapped native ledger through its original workflow; generated views are not separately maintained truth.
   Prepare concrete options/recommendations only for real unresolved owner decisions.
7. By default, continue from Baseline to current behavior specifications; do not stop at
   explanations, inventory or contract documents. Read `references/specification.md`.
   Write/reuse current specs under policy.paths.specs for verified observable behavior,
   with scenarios, Baseline/Source links and actual verification gaps. This is part of a
   bare baseline-repo invocation, not an optional user prompt. Preserve existing specs/IDs;
   record conflicts, defects and unknowns separately without endorsing or silently fixing them.
   Document routine preservation reasoning as the actual Agent analysis, not invented owner approval.
   Promote selected promises only after that compatibility record and current Spec exist: `ark baseline promote --document <path> --requirements <IDs> --decision <artifact>
   --reviewer <identity>`. Do not promote every implementation detail or defect. Retire
   obsolete knowledge explicitly with --decision; retain immutable raw snapshots.
8. After drafting, perform a NEW source-first semantic audit using `references/source-audit.md`.
   Reopen actual source/configuration/callers and build a coverage checklist from code, not
   from the generated documents. Check both source-to-artifact omissions and artifact-to-source
   truth, including errors, boundaries, state and side effects. Record findings before fixing.
   Correct generated claims or give evidence-backed dispositions; preserve accepted conflicts.
   Then reopen source again for a separate post-fix pass and check affected/cross-cutting flows.
   Default to these two real passes, not two runs of a structural validator. Use a fresh reviewer
   when available; otherwise use an explicitly same-agent separate pass. Never claim independence
   if unavailable. Keep unresolved/recurrent issues PENDING and save a checkpoint; no infinite loop.
   Record the actual report with `ark baseline audit-record`, then run `ark baseline audit-status`.
9. Recheck project-specific AGENTS facts/commands and use initialize-repo project-entry guidance
   with `entry refresh` if necessary. Explicitly audit the three quality topics from
   references/artifact-quality.md: project-entry, capability-coverage, spec-self-containment.
   Include AGENTS, .ai/project-entry.json, the capability map, module/contract/case artifacts
   and current specs in the actual source-audit scope. After these edits refresh audit records;
   do not use an old audit on changed artifacts.
10. Run `ark baseline status`, `ark baseline validate` and `ark baseline spec-status`
   (use --scope <source/document paths> for an explicitly limited task). Execute real project checks.
   Report specification creation separately from verification: missing tests/check mappings
   keep verification PENDING, never relabel them manual merely to pass. A planned or empty
   specs directory is not a completed baseline. Respect an explicit analysis-only user scope
   and report that specification is not performed rather than claiming full onboarding.
   Run `ark baseline coverage-status` and `ark onboarding-status`. Report uncovered production
   scope and pending capabilities even if the selected specs validate. A few cross-cutting
   capabilities or valid links cannot establish full project coverage.
   Report source/module/contract/case coverage separately from executed tests. Explain
   uninspected, uncertain and unavailable ranges. Save progress for large scopes and
   continue the next available pending batch automatically. Genuine blockers remain PENDING;
   work on independent unblocked modules. Do not stop solely because a batch finished.

During later development, refresh affected knowledge only. New repositories acquire existing
behavior as code lands; later changes also need evidence and regression safeguards. Native
OpenSpec/other tools remain free to organize development. No daily toolkit Skill or CI is required.
