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

## Automatic scope and specification setup

Default existing-code scope is the whole repository: all first-party observable behavior,
plus supporting build/configuration and relevant tests/callers. Record generated/vendor and
external exclusions with reasons. Do not equate file count with semantic understanding.
Derive the capability map before choosing execution order. Select dependency-first batches
or an end-to-end vertical slice yourself, then continue all remaining batches. Keep a durable
checkpoint of completed/pending capabilities, inspected revision and next batch. No routine
"which slice?" or "continue?" question is needed. A real missing dependency or authority conflict
may block affected scope; preserve PENDING and continue independent work.

Resolve specification setup before the helper's first write, without offering a routine
"doc/specs or OpenSpec?" choice:

- Existing policy mappings are authoritative; upgrades preserve them. Existing native OpenSpec
  configuration/rules/IDs are preserved, not regenerated merely because onboarding ran.
- Without policy, inspect repository rules and actual documents. Reuse an established current
  specification root (including doc/specs) and its lifecycle through --path specs/changes.
  A directory name alone is not authority: design targets/manuals are not effective current specs.
  Do not migrate, duplicate or relabel them as accepted current behavior.
- With no established current-spec authority, use openspec/specs/<capability>/spec.md and
  openspec/changes. Write real current specs during baseline handoff; no empty placeholder
  directory or fabricated Change is needed. doc/specs containing only target designs stays intact.
- Inspect local OpenSpec configuration and CLI availability. When native setup is missing and
  an installed CLI supports noninteractive initialization compatible with these paths and the
  current runtime, inspect its installed --help/version, then run that native initialization
  automatically with supported options. Inspect generated diffs; preserve human instructions,
  settings, Skills and mapped authority. Do not run initialization blindly over existing assets.
  Do not switch a mapped native lifecycle to a parallel default tree just to run a CLI.
- If the CLI is absent, incompatible, interactive-only, or cannot initialize without overwriting
  human assets, record native setup/validation NOT_RUN with the actual reason and continue
  file-based baseline/spec authoring at the selected authoritative path. Do not install packages
  or run a network package runner merely to probe for the CLI. Toolkit scaffolding, spec files,
  native CLI setup and native validation are separate results; never call them all "initialized"
  based only on the existence of openspec/specs.

Ask only when inspecting accessible rules cannot resolve conflicting authoritative roots or
another material owner decision. State the concrete conflict; a missing CLI, first batch order,
or recoverable checkpoint alone is not such a decision. Explicit user requests to install a
native tool or migrate authority are separate authorization and take priority.

## Project facts and local operation

Read .ai/project.json and the context document mapped by policy.paths.context (default docs/project-context.md). Verify observed languages, build manifests, declared versions and test roots against actual files. Fill real project boundaries and command knowledge; retain explicit unknowns. Existing human context is preserved. The engineering standard defines risk-appropriate assets and stage completion.

All checks operate locally. Hosted CI generation is opt-in with --ci github, including for GitHub origins. No CI or remote is required. Report asset setup, semantic coverage, real check execution, runtime trust and optional remote settings separately.

## Existing native schemas

Inspect authority documents before initialization. The bundled helper accepts repeated --path KEY=repository-relative-path for baseline/specs/changes/adr/templates/context/standard/questions/decision_view/decision_details/evidence. Set first-use mappings before scaffold creation. Exact repeated mappings are inert; relocating an already initialized asset requires preserving its history explicitly. Use paths.evidence for machine snapshots when a native raw directory requires dated batches/front matter. Preserve the native verification report sections and append managed runtime evidence to the existing report.
