# Verification and continuation

Confirm actual check argv in policy. Candidate commands are not promises. Configure command,
manual or external checks, marking required checks honestly. `{python}` is the active Python.
Execution creates logs/exit codes/fingerprints; handwritten PASS cannot replace it.

After performing a manual/external check or obtaining actual evidence, record it with:
`ark evidence --change <id> --check <name> --artifact <path> --reviewer <identity>
--status PASS --summary <observed-result>`. This records a declaration and freshness,
not independent truth. Keep unavailable checks NOT_RUN and overall PENDING. A partial
`--check` run cannot satisfy unselected required checks. Optional failures remain visible.

REQ references provide navigation only; inspect assertions and execute tests. Manual/external
requirements need explicit check/evidence mappings; never add a fake test to satisfy an ID.
After OpenSpec synchronization, review and record-sync, then rerun delivery against current
specs. Without a native tool, the Agent may synchronize files and review them explicitly,
recording method=reviewed; it must not assert an unavailable command ran. Use native only
for actual native execution. The runtime never implements delta merging itself. Declare
retired IDs in removed_requirements as well as affected requirements, and retain removal
verification/compatibility evidence instead of pretending retired IDs remain current.

Checkpoint during work: scope, necessary facts, preserved behavior, actual results, blockers
and next steps. A crashed process may never run an exit hook. Use explicit worktree/branch/
session change pointers. Normal pauses remain allowed even while verification is pending.
