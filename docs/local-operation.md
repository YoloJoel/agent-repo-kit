# Local operation and optional integration

Install the plugin/Skills, initialize once, then describe work normally. OpenSpec, another
workflow or direct conversation can produce native/mapped artifacts. No daily toolkit Skill,
activity pointer, hosted Git service or CI is required. The agent reads the persistent rules,
maintains applicable assets, and runs local checks before claiming delivery.

`python hack/ai/ark.py context` reads actual Git differences and native work assets for
navigation. It does not run a build, inventory the whole repository, or infer task ownership
from timestamps. Multiple work items may have disjoint scopes; overlapping matches remain
ambiguous. Without Git, navigation cannot invent an actual diff; local check conservatively
inspects the available inventory and explicit scope instead.

`impact [--base <revision>]` lists changed paths and affected knowledge with actual freshness.
A path association is a review candidate, not proof of semantic impact. Keep raw evidence;
refresh current explanations or explicitly retire obsolete knowledge when appropriate.

`check [--base <revision>]` stores `.ai/runtime/last-check.json`. Its stage and
business_checks_executed distinguish document/structure checks from executed business
commands. Missing mandatory checks remain pending. Each change report preserves original,
regression and intended target evidence. Required checks are re-executed, not trusted from
committed PASS files. A local comparison defaults to HEAD for history protection.

`checkpoint --change <id> --summary ... --next ... --paused` saves normal handoff;
--blocked names an external blocker. Native work gains a checkpoint, not an ark.json
lifecycle. Stop feedback is advisory for inferred work; an explicitly activated legacy task
may use bounded enforcement. A normal pause/blocked checkpoint and stop_hook_active permit
handoff. No hook performs a full build on every tool call.

## Optional local Git check

`python hack/ai/ark.py install-git-hook` installs a pre-commit check when the repository has
no conflicting hook. It works with local Git, GitLab, Gitea, private servers or no remote.
Custom hooks and external/global hook managers are preserved; integrate the same command
through their existing reachable path. The hook includes staged, unstaged and untracked
candidate work, so keep unrelated work in another worktree or provide scoped declarations.
It can be bypassed with Git options and is not remote/server enforcement.

## Optional pipelines and review

In Jenkins, GitLab CI, Gitea or another runner, provide Python 3.11+, the native project
build tools, the candidate checkout and its actual comparison history, then run:

```sh
python hack/ai/ark.py ci --base "$ACTUAL_TARGET_COMMIT"
```

Use the actual target/merge base, fetch enough history and keep `.ai/runtime/runs` plus
`.ai/runtime/last-check.json` as appropriate artifacts. A missing/invalid base fails; a CI
configuration file is not proof of a required server gate. Keep existing pipelines and their
credential/build setup. GitHub workflow generation remains an explicit optional initializer
flag; other hosts do not receive a fake GitHub setup.

Review policy/checker/manifest/pipeline modifications independently of business changes.
Check case completeness and assertion quality, design/contract consistency, original evidence,
expected target differences, native synchronization, remaining risks and actual execution.
Use the project's existing review mechanism; no PR platform is required.

## Native loading

Claude Code 2.1.322 actually ran the generated SessionStart command using --init-only and
returned navigation context in a clean local consumer. Stop subprocess/bounded feedback and
local Git blocking are tested separately. This does not certify a full model-driven Claude
conversation. Codex 0.167.0-alpha.4 is present; trusted native hook loading remains unverified
in this environment. Project hook definitions need host-owned review/trust. OpenCode has
instruction/Skill layout support; no native lifecycle plugin is shipped. See compatibility.md
for exact tiers. Initial setup cannot silently authorize host-owned trust decisions.
