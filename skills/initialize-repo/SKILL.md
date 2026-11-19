---
name: initialize-repo
description: Initialize or explicitly upgrade reusable AI engineering rules, skills, templates and checks in new or existing code repositories. Use for onboarding, installation repair or requested upgrades; preserve existing AGENTS, OpenSpec, CI, IDs and dirty changes.
---

# Initialize a repository

A bare invocation authorizes whole-repository onboarding. Choose batch order yourself;
a vertical slice is an execution batch, not a reduction of scope. Read
`references/onboarding.md` before the first write for automatic specification setup.
Do not ask which slice to start with, whether to continue normal batches, or whether to
choose doc/specs versus OpenSpec. Honor an explicitly narrower user request.

1. Inspect existing instructions, Git status, source/build/test roots, CI, OpenSpec and
   design/manual documents. Follow instructions already applicable to the repository.
2. Detect new/existing/partially governed repositories. Reuse valid assets and map paths
   in `.ai/policy.json`; do not recreate specs, rename IDs or overwrite human decisions.
3. When invoked as an installed plugin/Skill, locate `scripts/initialize.py` relative to
   THIS SKILL.md and run it with an available Python 3.11+ interpreter and the target root.
   Pass `--agents claude`, `codex` or `opencode` for the runtime you actually use.
   Before the first write, pass observed native asset mappings as repeated `--path KEY=path`
   arguments, for example `--path questions=docs/baseline/open-questions.md` and
   `--path evidence=docs/agent-evidence` when the native raw-batch schema is restrictive.
   Reuse existing report/front-matter templates. Do not manufacture a parallel ledger or
   insert generic material that fails an existing native validator. The helper
   and resources are bundled inside this Skill; do not fetch a repository, ask the user to
   read a URL, install a Python package or run bootstrap.py. Installation is already complete.
   It creates project rules/checks and keeps using the installed Skills without duplicating
   them in the target. For repository-generated workflows without this helper, reuse the
   target's existing `python hack/ai/ark.py` entry. Merge managed conflicts explicitly.
Read `references/engineering-verification.md` when establishing commands, test roots and
reproducible environment evidence. Run `engineering-status`; readiness is not execution.

4. Read generated policy and observed project context. Verify project boundaries, versions and roots; fill source-backed context and explicit gaps. Reuse existing human documents. Confirm actual check commands from project configuration and
   execution before adding them to `checks`. Candidates are suggestions, not gates.
   Read `references/onboarding.md` for configuration, discovery and upgrade details.
   Read `references/project-entry.md` and curate .ai/project-entry.json from source evidence,
   then run `entry refresh`. Translate project-specific Spec/Design/ADR triggers into policy.artifact_rules using project-entry.md. Verify that the same rule reaches OpenSpec, Superpowers and a direct request. Read `references/configuration.md`; generate or reconcile
   the actual OpenSpec schema/context/rules and record source-backed configuration review.
   CLI setup or spec-file creation alone does not complete project configuration. Produce a project-specific seven-section AGENTS entrance, not
   a tool manual or build-file dump. Preserve native/human entry structure without duplicating it.
5. For existing code, continue with **baseline-repo**: explain behavior, cite evidence,
   complete the coverage/gap ledger and create/reuse source-backed current behavior specs.
   Initialization does not end at inventory or Baseline prose; follow baseline-repo through
   its specification handoff AND default source-first/post-fix semantic audit.
   Before writing the first batch, record the capability map derived from actual entries and consumers.
   Keep pending capabilities in view throughout drafting, including separate responsibilities in one source file.
   Use baseline-repo's source-facts.md: complete each behavior batch through source facts,
   clauses, Spec-only acceptance cases, same-input source comparison and actual assertion review. Report source audit, specification
   and verification gaps separately. Save checkpoints for large repositories, then continue the next pending batch
   automatically. Keep the whole inventory/capability map as the completion denominator;
   never pass the first batch as the declared whole scope. Stop only for an actual blocker,
   an execution interruption or an explicit user pause; state remaining ranges honestly.
6. For new code, keep historical baseline not applicable. Establish actual user goals
   and initial requirements/decisions; do not invent a product or architecture.
7. Run vendored `python hack/ai/ark.py doctor` and `verify --phase structure`; use the
   same local entry for later examples written as `ark`. No global ark is required.
   Diagnose live skill/hook loading when the corresponding runtime is available.
8. Report installed assets, semantic coverage, checks executed, runtime loading/trust
   and optional remote required-check configuration separately. No CI is required; enable hosted CI only when explicitly requested. Configuration-only is not live PASS.
   After final asset/navigation edits and source-audit registration, run
   `onboarding-status --record` for a fresh input-bound scope/quality result; init-report.json is a dated setup snapshot,
   not the current conclusion. Compilation does not establish business-test execution.
   Before claiming onboarding complete, use `references/completion.md` to assess actual
   content and executable checks. An initialized scaffold alone is only setup complete.

Keep initialization idempotent. Reuse relevant context on later sessions; do not repeat
whole-repository analysis at startup. Preserve existing content and accepted history.

After onboarding, use OpenSpec, another development Skill or direct conversation. Follow repository engineering requirements and run local checks; no toolkit development Skill or CI is required.
