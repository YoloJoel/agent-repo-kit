# Repository engineering standard

## Evidence and authority

Source/config/runtime evidence describes a version's actual behavior. Baseline explains
observations and gaps. Current specs describe accepted behavior; active deltas describe
planned changes; accepted ADRs explain architecture decisions. Resolve discrepancies
explicitly instead of silently rewriting one side.

## Task routing

Read-only work, documentation corrections and demonstrably mechanical edits use a light
path: record impact/results and run relevant checks. Do not create ceremonial tests or
duplicate documents. Small configuration/dependency diffs can still affect behavior.
Features, observable fixes, compatibility changes and risky refactors need scoped changes.
Reuse existing OpenSpec or other mapped artifacts and IDs. No ark.json, toolkit lifecycle or development Skill is required. Native tools retain ownership of synchronization and archive.

## Delivery

1. Identify scope, current contracts, target scenarios and unresolved facts.
2. Establish source-grounded baseline and necessary characterization fixtures.
3. Fill proposal/tasks/delta/design; explain genuinely not-applicable sections.
4. Run ready verification before implementation to anchor reviewed existing behavior.
5. Implement, inspect meaningful assertions and confirm actual check commands.
6. Use the available OpenSpec synchronization workflow; inspect the result and record a
   spec-sync review artifact. If no native tool is available, the Agent can explicitly
   synchronize files and review the behavior diff, recording method=reviewed rather than
   claiming the CLI ran. The toolkit does not implement delta merging.
7. Complete tasks and run fresh delivery verification. Required checks must actually run
   and pass; manual/external checks need current evidence. Partial runs remain PENDING.
8. Archive only with fresh local execution evidence and synchronized current specs.
   Run `python hack/ai/ark.py check --base <revision>` locally before delivery. CI may run the same checker, but is optional and never a prerequisite for using the toolkit.

## Baseline and decisions

Inventory paths/hashes do not prove semantic understanding. Explain full normal/failure
flows, state, side effects and compatibility details before recording static review.
Cite valid `path:L1-LN` locations. Preserve raw snapshots and record uninspected ranges.
Promote only reviewed behavior promises, not every implementation quirk or defect.
Classify questions as fact, behavior decision, design task or validation gate. Look up
facts and complete routine designs. Ask an owner only about real unresolved tradeoffs.
Use ADRs for consequential long-lived choices; preserve accepted decision history.

## Verification and continuation

Individual statuses: PASS, FAIL, NOT_RUN or NOT_APPLICABLE with a reason. Overall:
PASS, FAIL or PENDING. Requirement references are navigation, not assertion coverage.
Evidence for another tree cannot establish completion. Remote required checks and branch
protection are separately configured; a workflow file alone does not enable protection.

Keep AGENTS concise and context task-specific. Initialize explicitly; diagnose lightly
on startup. Avoid whole scans/builds on every tool call. Stop feedback must be bounded
and allow ordinary pause/blocker handoff. Save checkpoints during work because exit hooks
may never run. Keep local pointers isolated by worktree/branch/session. Upgrade explicitly
and preserve human content and dirty changes.
