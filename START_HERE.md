# Agent entry: onboard the current repository

This page is an executable workflow for the Coding Agent. The user has requested this
toolkit for their current repository. Complete the setup and relevant semantic work;
do not turn the steps below into a manual installation checklist for the user.

## 1. Resolve source and target

Read the target's applicable instructions and Git status. The current business repository
is the target; the agent-repo-kit checkout is only a tool source. Never initialize the
temporary toolkit checkout in place of the target.

Reuse a supplied local toolkit checkout. Otherwise obtain this repository into a temporary
directory using an available connector or Git/download capability. Preserve the branch or
commit selected in the URL used to read this page. For a branch URL, resolve its current
commit and record it; do not silently switch to main or another version. Read its
initialize-repo Skill at `src/agent_repo_kit/assets/skills/initialize-repo/SKILL.md`.

## 2. Run one local bootstrap

Find an existing Python 3.11+ interpreter (`python`, `python3`, or `py -3` on Windows).
Use it to run the complete checkout's entry point:

```text
<python> <toolkit-checkout>/bootstrap.py <target-repository>
```

No pip, global CLI installation, virtual environment or PATH change is needed. Choose
`--agents` for the runtime you actually use when known; this is an Agent choice rather
than a question for the user. Defaults install common skill entries. The bootstrap
detects new/existing code, merges existing assets, enables repo-local Codex/Claude hook
configuration and adds the consumer CI template when origin is hosted on GitHub.

Keep existing rules, requirements, OpenSpec/config, tests and dirty changes. A managed
conflict is a concrete merge task, not permission to overwrite. If a required interpreter
or source access is genuinely missing, report that specific blocker after completing
independent inspection; do not pretend initialization or checks ran.

## 3. Continue automatically

Read the newly installed target AGENTS.md and initialize-repo instructions directly,
even if this live session has not yet refreshed its Skill discovery. Use the target's
`python hack/ai/ark.py` for every later example written as `ark`.

- Existing repository: inspect actual code/config/tests, reuse manuals as candidates,
  explain modules/flows/contracts, record evidence and gaps, confirm real commands and
  continue baseline-repo. Save checkpoints for large scopes and actual blockers.
- New repository: keep historical baseline not applicable; install the workflow without
  inventing product requirements. Use actual goals if the task already supplies them.
- Partly governed repository: retain existing IDs and assets, map paths and fill gaps.

Run the vendored doctor and relevant structure/behavior checks. Check instructions/Skill
loading and hook execution when the runtime permits. Runtime trust and remote branch
protection remain separately verified states. Do not claim them active from config alone.

## 4. Leave a simple result

Report what is connected, actual source-review scope, actual checks, and real remaining
decisions/blockers. Do not ask the user to rerun bootstrap, select routine options, invoke
baseline commands, install a global ark command or repeat already authorized steps.

After onboarding, the user can describe normal development goals. Use deliver-change,
the current repository's rules/specs and the vendored runtime automatically. The temporary
toolkit source may be deleted; ongoing commands and hooks must not depend on it.
