# Behavior evidence and quality

Kind: feature

Directory/capability maps, source line references and REQ comments could be mistaken for sufficiently reviewed behavior. Generated specs could miss cross-module effects, promote guesses or retain contradictory clauses. Add an evidence protocol, source-first behavior denominator, assertion-level review and consistent candidate gates while preserving native lifecycle and existing assets.

Scope: `src/agent_repo_kit`, `skills`, `tests`, `tools`, `examples/config-relay`, `docs`, `README.md`, `CHANGELOG.md`, `pyproject.toml`, `.claude-plugin`, `.github`

Requirements: REQ-BEHAVIOR-QUALITY-001

Existing 0.2.x assets are retained; explicit upgrade introduces pending behavior-review obligations. Runtime checks declaration consistency and freshness, never arbitrary semantics. No business code or private source is changed. No required daily Skill/CI/remote is introduced.
