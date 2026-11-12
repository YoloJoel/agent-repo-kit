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

Hook commands require installed `ark` on PATH once per environment. Vendored commands
work without global installation. Codex/Claude Hook JSON is merged and trust is runtime-owned.
OpenCode gets native skills; lifecycle hooks are not implemented. Explicit upgrades use
`ark init --upgrade`; edited managed files cause conflicts. Keep custom AGENTS content
outside managed blocks. Inspect the recorded PID before removing a stale runtime lock.
