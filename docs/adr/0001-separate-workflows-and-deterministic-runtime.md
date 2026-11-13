# 0001: Separate semantic workflows from deterministic checks

Status: Superseded by ADR-0005

## Context

The toolkit must initialize different repositories and work with multiple Coding Agents.
Scaffolding cannot explain source behavior, while model instructions alone cannot reliably
record execution or repeat structural checks.

## Decision

Ship three semantic Skills and one stdlib-only Python runtime. Vendor the same runtime and
assets into consumers. Keep policy explicit, commands as argument arrays, initialization
idempotent, and local evidence distinct from CI re-execution. Use JSON for configuration
and schemas to avoid a required YAML parser dependency in the vendored runtime.

## Alternatives

- One giant prompt: cannot provide deterministic checks or repeatable installation.
- A required hosted service/MCP: increases deployment and availability dependencies.
- Separate implementations for every runtime/CI: creates policy and behavior drift.

## Consequences

Python 3.11+ is required. Semantic correctness still requires source review and meaningful
behavioral tests. Runtime adapters remain thin. Public flow changes are explicit upgrades;
the initial self-contained module can later be refactored behind the same consumer interface.
