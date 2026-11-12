---
name: baseline-repo
description: Establish or refresh a source-grounded explanation of an existing repository or affected module. Use for legacy onboarding, missing or stale evidence, refactor preparation, contract discovery or validating manuals against actual code; explain behavior and track coverage and gaps.
---

# Explain and verify current behavior

1. Read policy, baseline index and relevant manuals as navigation/candidate evidence.
   Inspect actual source/config/tests for important claims and contradictory information.
2. Run `ark baseline inventory`. Inspect coverage.json and classify source, generated/
   vendor code, build/deployment/config and exclusions. Path/hash counts are not approval.
3. Read `references/analysis.md`. Trace implementations and callers. Explain full normal
   and failure flows, branches, state, transformations, side effects and compatibility.
   Function names and signatures alone do not fulfill the analysis.
4. Write module documents with Purpose, Flow, State and failure, Evidence and Gaps headings.
   Cite valid `path:L1-LN` source locations. Replace scaffolding before removing ARK:FILL.
5. Record static review with `ark baseline review --document <module.md> --files <paths>
   --reviewer <identity>`. Identify the actual reviewer; do not imply a nonexistent human review.
6. Extract observed external contracts and distinguish implementation details/defects from
   intended promises. Resolve compatibility questions before promoting behavior into specs.
7. Maintain questions.json: fact, behavior-decision, design-task or validation-gate. Resolve
   accessible facts independently and continue work around unrelated real blockers.
8. Run `ark baseline validate`. Report scope, revision/worktree evidence, unreviewed/stale
   ranges, actual runtime checks and gaps. Preserve raw snapshots and accepted IDs.

Before risky implementation, run ready verification on the scoped Change to anchor reviewed
pre-change evidence. Keep this as history instead of rewriting it to match the new behavior.
