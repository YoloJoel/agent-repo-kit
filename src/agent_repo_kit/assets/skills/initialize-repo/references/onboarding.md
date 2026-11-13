# Onboarding details

`ark init` is deterministic scaffolding. Semantic onboarding is agent-owned. The command
vendors the Python 3.11+ stdlib runtime to `hack/ai`, copies selected skill discovery files,
and appends a managed AGENTS block. It does not approve a baseline or enable branch protection.

Map existing baseline/spec/changes/ADR/template roots in policy. Leave native OpenSpec
configuration intact. Adopt existing changes by adding schema-compatible ark.json metadata
without overwriting their artifacts.

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
without deleting user hooks. On another OS/environment, the Agent can rerun bootstrap to
repair its Python command; this does not require repeating semantic analysis.
OpenCode uses its installed Skills; lifecycle hooks are not implemented. Update through the
same plugin/Skills installer, then invoke initialize-repo for an explicit upgrade using
its bundled helper with --upgrade. An updated source/global CLI is optional for developers.
Edited managed files cause conflicts. Keep custom AGENTS content
outside managed blocks. Inspect the recorded PID before removing a stale runtime lock.
