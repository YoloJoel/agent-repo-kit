# Compatibility and deployment status

Documentation checked: 2026-11-13. Product version: 0.2.0. A declared API shape,
generated config, a protocol test and a live trusted runtime are different claims.

| Surface | Shipped behavior | Local validation | Environment-specific follow-through |
| --- | --- | --- | --- |
| Python package/CLI | Python 3.11+, stdlib runtime, packaged resources and console entry | Unit/consumer tests and installed-wheel exercise | Python on each developer/CI machine |
| Standalone Skills | Standard root `skills/<name>/SKILL.md`; self-contained initialize helper | Actual Skills CLI discovery/installation and copied-folder execution | Host controls installation scope/loading; invoke initialize-repo per repository |
| Codex instructions/skills | Installed Skills plus generated project AGENTS | Native source/assets and project runtime checks | Confirm actual instruction/skill loading in selected runtime |
| Codex Hooks | `.codex/hooks.json`, SessionStart and bounded Stop | Real JSON stdin/stdout subprocess protocol | Project/config trust; Python interpreter; live runtime behavior |
| Claude plugin | Native plugin/marketplace metadata plus root skills/ | Actual Claude CLI strict manifest validation | Install through native marketplace; live model invocation is separate |
| Claude instructions/skills | Plugin Skills plus project CLAUDE/AGENTS | Merge/import/asset checks | Avoid duplicate project Skill copies after platform installation |
| Claude Hooks | Merge `.claude/settings.json`, SessionStart/Stop | Claude Code 2.1.322 native --init-only SessionStart executed; Stop subprocess/bounds tested | Full model conversation/live Stop remains unverified; host permissions and Python apply |
| OpenCode | AGENTS and `.opencode/skills` | Native discovery layout generated | Confirm live skill discovery; lifecycle plugin not implemented |
| Local Git check | Optional pre-commit command, custom-hook preservation | Actual rejecting commit exercise; no remote required | Opt-in, bypassable local check; no server protection claim |
| Other pipelines | Same CLI with actual comparison base | Generic documented command protocol | Native runner/toolchain/artifact setup remains project-owned |
| GitHub Actions | Consumer workflow plus toolkit OS/Python matrix | Local check/CI command exercises | Remote Actions execution and separately required check rules |
| Other runtimes | Human-readable rules and vendored CLI | No native adapter claim | Implement and validate a thin adapter before declaring support |

Local development executes on Linux/Python 3.12. The toolkit CI is configured for Linux,
Windows and macOS with Python 3.11/3.13; inspect actual workflow runs for their result.
A configured matrix is not a claim that it has already passed remotely.

Install once through Claude plugin or a Skills installer, then invoke initialize-repo per
repository. Its code/resources are inside the Skill folder; no source bootstrap, additional
checkout, URL instructions or global CLI is needed. Generated hooks use the vendored project
runtime. Skill loading and runtime trust remain host-owned. The source bootstrap/package
are developer compatibility entries, not normal user setup. Initialization does not modify
global instructions, silently authorize hooks or configure branch protection.

## Primary documentation

- [Codex project customization](https://learn.chatgpt.com/docs/customization/overview)
- [Codex AGENTS discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex Hooks and trust](https://learn.chatgpt.com/docs/hooks)
- [Claude project instructions/imports](https://code.claude.com/docs/en/memory)
- [Claude Skills](https://code.claude.com/docs/en/skills)
- [Claude Hook event/output reference](https://code.claude.com/docs/en/hooks)
- [OpenCode instructions](https://opencode.ai/docs/instructions/)
- [OpenCode Skill discovery](https://opencode.ai/docs/skills/)
- [OpenCode plugin configuration](https://opencode.ai/docs/plugins/)

Adapters use the shared runtime; the toolkit does not assume that matching event names
across products imply identical trust, configuration, loading or blocking behavior.
