## Agent Repo Kit workflow

Use the user's language for explanations and documents. Work from the repository root;
use `python hack/ai/ark.py` if the global `ark` command is unavailable.

- Read `docs/engineering-standard.md` and `.ai/policy.json` when workflow details matter.
- For onboarding or an explicit toolkit upgrade, use **initialize-repo**.
- For current behavior, consult `{{BASELINE}}` and verify relevant source/configuration;
  use **baseline-repo** when evidence is missing or stale.
- For promised behavior, read relevant specs under `{{SPECS}}`; for planned changes,
  read the related change under `{{CHANGES}}`. Use **deliver-change** for implementation.
- Consult effective ADRs for consequential architecture choices. Record discrepancies
  between observed behavior and specs; do not silently rewrite either side.
- Read only task-relevant context. A typo/mechanical edit needs neither a full Change,
  whole-repository Baseline nor new tests that merely mirror implementation.
- For behavior changes and risky refactors, declare scope and acceptance scenarios.
  Establish necessary characterization tests before changing behavior that must stay.
- Use confirmed commands in policy. Candidate commands are unverified suggestions.
  Never report NOT_RUN as PASS or an inventory as an approved semantic baseline.
- Update affected specs, decisions, evidence and tasks. Preserve original evidence and
  accepted history; link superseding records. Do not renumber existing requirement IDs.
- Before declaring delivery complete, run fresh delivery verification. During work and
  interruption, save a checkpoint and next step; genuine blockers can remain PENDING.
- Reuse authorization. Resolve facts and routine design choices yourself; ask only about
  material scope/compatibility decisions or required permissions not already resolved.

Commands: `ark doctor`, `ark context`, `ark baseline inventory`, `ark change inspect`,
`ark verify --phase structure`, `ark verify --phase delivery --change <id>`.
