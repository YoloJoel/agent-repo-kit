# agent-repo-kit contributor instructions

This repository builds a generic toolkit; keep business domains, programming languages,
model providers and runtime adapters separate. The user's requested scope takes priority.

- Runtime implementation: `src/agent_repo_kit/core.py`, Python 3.11+ standard library only.
- Distribution assets: `src/agent_repo_kit/assets/`. Skills are shipped into consumer repos;
  editing these does not install a personal ChatGPT skill or authorize changing global settings.
- Behavioral promises: `openspec/specs/toolkit/spec.md`. Architecture choices: `docs/adr/`.
- Reuse current source, specifications and actual execution results; distinguish planned
  adapter support from implemented configuration/protocol/live-runtime verification.
- Preserve consumer human instructions, native OpenSpec artifacts/IDs, settings and dirty files.
- Do not report scaffolding as semantic baseline approval, textual REQ matches as assertion
  quality, unavailable checks as PASS, or Hook config as trusted/live runtime integration.
- Confirm changes with `python -m unittest discover -s tests -v` after installing the package,
  or `PYTHONPATH=src python -m unittest discover -s tests -v` during development.
- Validate built-wheel assets and the vendored consumer path when packaging or initialization
  changes. Keep tests focused on observable workflow guarantees rather than implementation mirrors.
- Save recoverable progress before interruptions. Use independent scoped changes for larger
  follow-up work; no workflow or Hook should force an infinite stop/continue cycle.
