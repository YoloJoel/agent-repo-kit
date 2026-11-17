# Complete the OpenSpec project configuration

Toolkit scaffolding, actual spec files, project configuration content, native CLI setup and
native CLI validation are separate results. CLI absence does not exempt configuration content.

Inspect the actual policy/authority, installed schema and existing config before writing.
A mapped non-OpenSpec workflow without OpenSpec config stays with that workflow. Otherwise:

1. Curate source-backed project-entry facts and run entry refresh. Read actual engineering
   rules, architecture/contract constraints, native schema and template requirements.
2. For a toolkit-generated/empty config, run `ark openspec refresh`. It writes supported
   spec-driven YAML from reviewed facts and explicit observable-behavior/workflow rules.
   Inspect the output: project identity, stack/versions, boundaries, authority paths,
   compatibility, IDs/scenarios, design triggers, testing/report/sync tasks. Refine facts
   and regenerate owned config, or reconcile actual native configuration in place.
3. Existing native/human schema, context, rules, comments and unknown keys are preserved;
   refresh refuses overwriting edited/unowned config. Read and supplement that existing YAML
   yourself, retaining schema-specific artifact names and accepted instructions. This is a
   normal authorized edit, not a reason to ask which tool/root/slice the user wants.
   Do not rename a custom schema or append duplicate context/rules keys to satisfy a checker.
4. Actually review YAML syntax with an available parser/native tooling, or explicitly state
   the unavailable validation. Verify context facts and rules against authority/templates;
   reject empty/schema-only/language-only placeholders or copied example business settings.
   The stdlib content guard is deliberately bounded; it is not a general YAML/schema parser.
5. After real content review run `ark openspec record --reviewer <actual reviewer>`, then
   `ark openspec status`. The record binds config, AGENTS, facts, authority/policy and evidence.
   Generation alone does not record a review or assert native CLI read/validation execution.
   Keep native execution/compatibility evidence and actual gaps separately. Custom schema
   semantics still require the actual reviewer/native tooling; a content record cannot prove them.
6. Include config and the real Baseline navigation page in the two-pass source-audit scope.
   After final audit registration and all artifact edits, `ark onboarding-status --record`
   rechecks live structure/content declarations and saves a final input-bound result.
   Subsequent source/config/test/registry/audit changes invalidate it. It does not run business
   tests and never converts missing tests/native environment into PASS.

Do not overwrite an existing valid config through package/template replacement. Reconcile
conflicts from actual authority; ask only for a genuine unresolved owner decision.
