---
name: deliver-change
description: Implement scoped features, fixes, refactors, upgrades or behavior-affecting configuration changes with current specifications and actual verification. Use for repository development, resuming changes or checking completion; choose a lightweight path for genuinely low-risk nonbehavior edits.
---

# Deliver a repository change

1. Inspect task, actual diff and relevant specs/ADRs/source. Read only needed context;
   distinguish observed behavior, accepted promises and planned changes.
2. Use a light path for docs/mechanical nonbehavior edits: record a hash-bound rationale
   with `ark note --scope <paths> --kind mechanical --reason <rationale> --reviewer <identity>`
   and run relevant checks. Avoid ceremonial new tests, full Change or whole-repo analysis.
3. For behavior/risky changes, reuse a native OpenSpec change or run `ark change new <id>
   --kind <kind> --scope <paths> --requirements <REQ-IDs>`. Preserve artifacts/IDs and
   declare honest scope. Explicitly activate it for the runtime session when its ID is known.
4. Fill proposal/tasks/delta and necessary design. Respect effective ADRs; record major
   long-lived choices. Use **baseline-repo** for evidence gaps. Establish necessary regression/
   characterization fixtures before altering behavior that must remain compatible.
5. Run `ark verify --phase ready --change <id>` before implementation to anchor existing
   baseline. Resolve relevant evidence gaps rather than rewriting history after implementation.
6. Implement within scope and inspect meaningful success/failure/boundary assertions.
   Update completed tasks and affected knowledge. Reuse confirmed project check commands.
7. Use the available native OpenSpec synchronization workflow and inspect the behavior diff.
   If the native tool is unavailable, explicitly synchronize current-spec files and review
   each added/modified/removed/renamed behavior. Write an honest review artifact, then run
   `ark change record-sync <id> --artifact <review.md> --reviewer <identity> --method reviewed`
   (use `--method native` only after actual native execution). See `references/verification.md`.
8. Run `ark verify --phase delivery --change <id>`. Required NOT_RUN, stale evidence,
   unfinished tasks and missing verification remain PENDING. Fix scoped problems and rerun
   when necessary. CI independently verifies the candidate revision.
9. Archive with `ark change close <id>` after fresh PASS. Otherwise checkpoint using
   `ark checkpoint --change <id> --summary <state> --next <step>`, with `--blocked` for
   real blockers. Report exact completed scope, actual checks, limitations and next step.

Reuse authorization; resolve facts/routine designs yourself. Ask only about real unresolved
product/compatibility choices or missing required permissions. Stop hooks do not replace this flow.
