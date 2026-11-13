---
name: baseline-repo
description: Establish or refresh source-grounded repository knowledge, contracts, behavior cases and evidence gaps. Use for existing-code onboarding, stale knowledge, refactor preparation or checking manuals against actual source; preserve existing documents, identifiers and history.
---

# Explain current behavior with evidence

Use the supplied initialize-repo helper if project rules/runtime are absent. Run the target's
`python hack/ai/ark.py` for command examples written as `ark`. No package or global CLI is needed.

1. Read applicable repository rules and path/section mappings. Reuse current manuals,
   contracts, decisions and tests as navigation; verify important claims against actual
   source/configuration/callers. Do not silently treat design targets as current facts.
2. Run `ark baseline inventory`. Establish included modules, generated/vendor exclusions,
   unavailable external sources and actual revision/workspace. Inventory is not understanding.
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
7. Promote selected promises only after an actual compatibility decision and current Spec
   exist: `ark baseline promote --document <path> --requirements <IDs> --decision <artifact>
   --reviewer <identity>`. Do not promote every implementation detail or defect. Retire
   obsolete knowledge explicitly with --decision; retain immutable raw snapshots.
8. Run `ark baseline status` and `ark baseline validate`; execute real project checks.
   Report source/module/contract/case coverage separately from executed tests. Explain
   uninspected, uncertain and unavailable ranges. Save progress for large scopes.

During later development, refresh affected knowledge only. New repositories acquire existing
behavior as code lands; later changes also need evidence and regression safeguards. Native
OpenSpec/other tools remain free to organize development. No daily toolkit Skill or CI is required.
