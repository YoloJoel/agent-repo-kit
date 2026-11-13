---
name: initialize-repo
description: Initialize or explicitly upgrade reusable AI engineering rules, skills, templates and checks in new or existing code repositories. Use for onboarding, installation repair or requested upgrades; preserve existing AGENTS, OpenSpec, CI, IDs and dirty changes.
---

# Initialize a repository

1. Inspect existing instructions, Git status, source/build/test roots, CI, OpenSpec and
   design/manual documents. Follow instructions already applicable to the repository.
2. Detect new/existing/partially governed repositories. Reuse valid assets and map paths
   in `.ai/policy.json`; do not recreate specs, rename IDs or overwrite human decisions.
3. When invoked as an installed plugin/Skill, locate `scripts/initialize.py` relative to
   THIS SKILL.md and run it with an available Python 3.11+ interpreter and the target root.
   Pass `--agents claude`, `codex` or `opencode` for the runtime you actually use. The helper
   and resources are bundled inside this Skill; do not fetch a repository, ask the user to
   read a URL, install a Python package or run bootstrap.py. Installation is already complete.
   It creates project rules/checks and keeps using the installed Skills without duplicating
   them in the target. For repository-generated workflows without this helper, reuse the
   target's existing `python hack/ai/ark.py` entry. Merge managed conflicts explicitly.
4. Read generated policy. Confirm actual check commands from project configuration and
   execution before adding them to `checks`. Candidates are suggestions, not gates.
   Read `references/onboarding.md` for configuration, discovery and upgrade details.
5. For existing code, continue with **baseline-repo**: explain behavior, cite evidence,
   complete the coverage/gap ledger. Initialization does not end at inventory. Work by
   module and save checkpoints for large repositories; state incomplete ranges honestly.
6. For new code, keep historical baseline not applicable. Establish actual user goals
   and initial requirements/decisions; do not invent a product or architecture.
7. Run vendored `python hack/ai/ark.py doctor` and `verify --phase structure`; use the
   same local entry for later examples written as `ark`. No global ark is required.
   Diagnose live skill/hook loading when the corresponding runtime is available.
8. Report installed assets, semantic coverage, checks executed, runtime loading/trust
   and remote required-check configuration separately. Configuration-only is not live PASS.

Keep initialization idempotent. Reuse relevant context on later sessions; do not repeat
whole-repository analysis at startup. Preserve existing content and accepted history.

After onboarding, use OpenSpec, another development Skill or direct conversation. Follow repository engineering requirements and run local checks; no toolkit development Skill or CI is required.
