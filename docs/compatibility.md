# Compatibility and deployment status

Documentation checked: 2026-11-12. Product version: 0.1.0. A declared API shape,
generated config, a protocol test and a live trusted runtime are different claims.

| Surface | Shipped behavior | Local validation | Environment-specific follow-through |
| --- | --- | --- | --- |
| Python package/CLI | Python 3.11+, stdlib runtime, packaged resources and console entry | Unit/consumer tests and installed-wheel exercise | Python on each developer/CI machine |
| Codex instructions/skills | AGENTS plus `.agents/skills` copies | Asset and managed-file checks | Confirm actual instruction/skill loading in selected runtime |
| Codex Hooks | `.codex/hooks.json`, SessionStart and bounded Stop | Real JSON stdin/stdout subprocess protocol | Project/config trust; Python interpreter; live runtime behavior |
| Claude instructions/skills | CLAUDE import and `.claude/skills` copies | Merge/import/asset checks | Confirm loading mode and avoid competing instruction copies |
| Claude Hooks | Merge `.claude/settings.json`, SessionStart/Stop | Settings-preservation and subprocess protocol tests | Actual runtime/config permission and Python interpreter |
| OpenCode | AGENTS and `.opencode/skills` | Native discovery layout generated | Confirm live skill discovery; lifecycle plugin not implemented |
| GitHub Actions | Consumer workflow plus toolkit OS/Python matrix | Local check/CI command exercises | Remote Actions execution and separately required check rules |
| Other runtimes | Human-readable rules and vendored CLI | No native adapter claim | Implement and validate a thin adapter before declaring support |

Local development executes on Linux/Python 3.12. The toolkit CI is configured for Linux,
Windows and macOS with Python 3.11/3.13; inspect actual workflow runs for their result.
A configured matrix is not a claim that it has already passed remotely.

The recommended Agent entry is START_HERE.md with bootstrap.py; no package or global
command installation is required. Generated hooks find the vendored runtime from their
working directory/parents and use Python. The source checkout is disposable. On another
OS, an Agent can rerun bootstrap to repair the Python command without repeating semantic
analysis. Initialization does not modify global instructions, silently authorize hooks
or configure branch protection. A global CLI remains an optional convenience.

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
