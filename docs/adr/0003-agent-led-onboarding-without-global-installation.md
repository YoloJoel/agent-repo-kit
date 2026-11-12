# 0003: Agent-led onboarding without global package installation

Status: Accepted

## Context

Requiring a clone, package installation, PATH entry, initialization flags and separate
baseline instructions makes the first-use experience needlessly manual. Generated hooks
should not depend on a global executable after the runtime has already been vendored.

## Decision

Make START_HERE.md the recommended user-facing entry and bootstrap.py its deterministic
implementation. Let the Agent obtain source, inspect the target, choose routine settings,
bootstrap and continue semantic onboarding. Import the stdlib runtime directly from source.
Generate Python hooks that locate the target's vendored runtime from cwd/parents. Migrate
existing owned global-command hooks while preserving other handlers/settings.

## Alternatives

- Retain the package-first checklist: adds user work and an unnecessary Hook dependency.
- Execute a downloaded shell installer: adds platform-specific behavior and another bootstrap layer.
- Use a hosted/MCP service: adds deployment prerequisites to local repository onboarding.

## Consequences

Python 3.11+ and access to a complete toolkit snapshot remain requirements. No pip, venv,
global command or retained source checkout is needed. Runtime trust is still environment-
owned; a different OS may need the Agent to repair its local Python Hook command. CLI
package installation remains available for users who prefer it. Inventory is still not
semantic approval; the Agent must continue the actual source-grounded workflow.
