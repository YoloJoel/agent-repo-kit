# Produce the project's engineering entrance

AGENTS.md should resemble a concise native project entrance: project/stack, architecture
constraints, asset navigation, source/module boundaries, real commands, development workflow
and rule precedence. It must not be a list of kit operations or dozens of build manifest paths.
Keep full inventory in project context/machine observations, not in the entrance. Use the
user's language. Preserve existing human/native instructions, numbering and accepted rules.

Inspect actual README/source/build/configuration, existing instructions, pipeline settings
and current manuals. Derive project purpose, runtime/component boundaries, actual contract or
architecture constraints and confirmed build/test commands. Do not invent SOLID rules, business
architecture, branch policy or release process. Where none is established say so explicitly.

Write .ai/project-entry.json with actual text for these fields:

```json
{
  "language": "zh",
  "purpose": "Actual project purpose and responsibility boundary",
  "stack": "Observed runtimes, versions, build facts; declaration versus execution distinguished",
  "boundaries": "Actual components/processes/roots and their responsibilities",
  "constraints": "Actual project constraints grounded in contracts/source/accepted decisions",
  "workflow": "Applicable project development/review/release workflow; explicit unknowns",
  "precedence": "Actual authority/conflict resolution consistent with human rules and explicit user instructions",
  "source_evidence": {"actual/file": "actual/file:L1-L20"},
  "reviewer": "Actual Agent/reviewer identity",
  "gaps": []
}
```

Use real file/line evidence, not the literal example. Empty/binary evidence uses the existing
path@sha256:<actual digest> notation. Put real unresolved facts in gaps, not an empty list to
get PASS. JSON stores renderer facts; behavior authority stays in specs and accepted decisions.
Confirm/configure actual commands in policy.checks; rendering does not execute them or infer
that compile means tests. Keep command meaning and actual execution in project context/reports.

Run `entry refresh`, then `entry status`. This safely refreshes the managed block and manifest,
preserving human text and avoiding a second outline under a native entrance. Do not hand-edit
the managed block. If a human block was edited, preserve/merge the conflict explicitly before
refresh. With a native project entrance, update its existing project sections when authorized;
do not append competing project/architecture rules or silently rewrite human requirements.

Check the rendered AGENTS itself: can a new Agent identify the project, boundaries, constraints,
assets, real commands and process without decoding the kit? Existing human sections must remain
coherent. The scaffold alone is not complete: entry status stays PENDING until declared review,
and source/config/command changes invalidate its currency. Refresh after final context/command
edits, then include the entrance/facts in baseline source audit and onboarding-status.
