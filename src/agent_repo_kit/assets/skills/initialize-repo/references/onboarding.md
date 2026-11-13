# Onboarding details

`ark init` is deterministic scaffolding. Semantic onboarding is agent-owned. The command
vendors the Python 3.11+ stdlib runtime to `hack/ai`, copies selected skill discovery files,
and appends a managed AGENTS block. It does not approve a baseline or enable branch protection.

Map existing baseline/spec/changes/ADR/template roots in policy. Leave native OpenSpec
configuration intact. Read native or mapped proposal/tasks/delta artifacts directly; do not add ark.json or introduce a second lifecycle.

Configure confirmed checks using argv arrays, for example:
`{"name":"unit","argv":["{python}","-m","unittest","discover","-s","tests"],"required":true}`.
`{python}` is the current interpreter. Use manual/external check types for outside evidence.
Commands never run via a shell; unavailable commands remain NOT_RUN.

The normal entry is the installed initialize-repo Skill (Claude plugin or standalone).
Resolve scripts/initialize.py relative to its SKILL.md; the entire helper/runtime/resource
bundle is included in that folder. Do not require a toolkit checkout, URL instructions,
bootstrap.py or a global CLI. Initialization keeps using platform-installed Skills and
records skill_delivery=installed; it does not copy duplicate Skills into the target.
bootstrap.py remains a source-development compatibility entry only.

Hook commands find the target's vendored runtime from cwd/parents and use Python,
so neither a global ark nor the original toolkit checkout is required. Codex/Claude Hook
JSON is merged and trust is runtime-owned. Existing global-ark hook entries are migrated
without deleting user hooks. On another OS/environment, the Agent can rerun the installed initialization helper to
repair its Python command; this does not require repeating semantic analysis.
OpenCode uses its installed Skills; lifecycle hooks are not implemented. Update through the
same plugin/Skills installer, then invoke initialize-repo for an explicit upgrade using
its bundled helper with --upgrade. An updated source/global CLI is optional for developers.
Edited managed files cause conflicts. Keep custom AGENTS content
outside managed blocks. Inspect the recorded PID before removing a stale runtime lock.

## Project facts and local operation

Read .ai/project.json and the context document mapped by policy.paths.context (default docs/project-context.md). Verify observed languages, build manifests, declared versions and test roots against actual files. Fill real project boundaries and command knowledge; retain explicit unknowns. Existing human context is preserved. The engineering standard defines risk-appropriate assets and stage completion.

All checks operate locally. Hosted CI generation is opt-in with --ci github, including for GitHub origins. No CI or remote is required. Report asset setup, semantic coverage, real check execution, runtime trust and optional remote settings separately.

## Existing native schemas

Inspect authority documents before initialization. The bundled helper accepts repeated --path KEY=repository-relative-path for baseline/specs/changes/adr/templates/context/standard/questions/decision_view/decision_details/evidence. Set first-use mappings before scaffold creation. Exact repeated mappings are inert; relocating an already initialized asset requires preserving its history explicitly. Use paths.evidence for machine snapshots when a native raw directory requires dated batches/front matter. Preserve the native verification report sections and append managed runtime evidence to the existing report.
