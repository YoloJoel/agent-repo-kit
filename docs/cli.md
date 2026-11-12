# CLI reference

All commands emit JSON. Put `--repo <path>` before the subcommand, or run within a
consumer repository/subdirectory. The vendored equivalent is `python hack/ai/ark.py`.
Python 3.11+ is required. Commands never invoke a model automatically.

| Command | Purpose |
| --- | --- |
| `ark init [path]` | Detect new/existing code, preserve/merge assets and vendor runtime |
| `ark init . --upgrade` | Explicitly update a managed installation; conflicts are not forced |
| `ark doctor` | Diagnose assets, configured commands and runtime/discovery unknowns |
| `ark context --session <id>` | Navigation and explicit current work pointer |
| `ark baseline inventory` | Ignore-aware paths/hashes, source version and pending coverage |
| `ark baseline review --document <path> --files <paths...> --reviewer <id>` | Record a static review with actual explanations and valid source ranges |
| `ark baseline validate` | Detect unreviewed/stale evidence, not semantic completeness |
| `ark change new <id> --kind <kind> --scope <paths...>` | Create a scoped native-layout change and draft artifacts |
| `ark change inspect [--base <ref>]` | Actual diff and behavior/configuration candidates |
| `ark change activate <id> --session <id>` | Worktree/branch/session-specific pointer |
| `ark change status <id>` | Read state without claiming completion |
| `ark verify --phase structure` | Managed assets, specifications and decision structure |
| `ark verify --phase ready --change <id>` | Check preconditions; anchor existing reviewed baseline before implementation |
| `ark change record-sync <id> --artifact <path> --reviewer <id> --method reviewed` | Record reviewed current-spec synchronization and its actual method |
| `ark verify --phase delivery --change <id>` | Actual required checks, current specs, tasks and evidence |
| `ark change close <id>` | Require fresh workspace PASS, rebase in-Change evidence and archive |
| `ark note --scope <paths...> --kind mechanical --reason <text> --reviewer <id>` | Hash-bound lightweight nonbehavior declaration |
| `ark evidence --change <id> --check <name> --artifact <path> --reviewer <id> --status PASS --summary <text>` | Record actual manual/external evidence, not an independent certification |
| `ark checkpoint --change <id> --summary <text> --next <text> [--blocked]` | Save recoverable progress; allow real handoff |
| `ark ci --base <real-base-ref>` | Candidate-diff coverage and independent check execution |
| `ark hook session/stop --agent codex/claude` | Consume runtime event JSON on stdin |

## Initialization

Flags: `--mode auto/new/existing`, `--agents codex,claude,opencode`, `--hooks`,
`--ci github`, `--upgrade`. Default agents are all three on a fresh install; a repeat
without `--agents` preserves the existing selection. New explicit agents are added.
Hook and CI enablement are optional. Existing native OpenSpec configuration is untouched.

`changed` lists installation/configuration asset changes, excluding the generated report,
baseline observations and runtime records. A first repeat report can differ because its
change list becomes empty; subsequent unchanged runs are byte-stable outside runtime.
Baseline status STATIC_REVIEW_CURRENT means static references are current, not that a
runtime/production verification or semantic completeness certification has occurred.

## Change metadata and requirements

Kinds: feature, fix, refactor, maintenance, docs. Use feature/fix/refactor for behavior work;
they require declared affected REQ IDs before ready. Adopt an existing native change by
adding ark.json conforming to the shipped change schema, retaining its existing artifacts.

New IDs use `REQ-UPPERCASE-001`; existing native artifacts/IDs are preserved during install.
Use `--requirements` for affected toolkit-tracked IDs and `--remove-requirements` for its
retired subset. Record verification for removals and preserve their compatibility decision.
The toolkit checks references and freshness, while agents/native tooling inspect semantics.

Automated requirements need real test-source references. For manual/external requirements,
configure explicit policy mapping instead:

```json
{
  "requirements": {
    "REQ-OPS-001": {"type": "manual", "checks": ["recovery-inspection"]}
  },
  "checks": [
    {"name": "recovery-inspection", "type": "manual", "required": true}
  ]
}
```

## Verification

`--check <name>` selects partial execution, but unselected required checks remain NOT_RUN.
`--base <ref>` checks scope against a real Git comparison. No command is invented or run
merely because a build marker exists. Review candidate commands and configure actual argv.

Artifacts include source/config/spec/policy/runtime-manifest fingerprints, actual argv/cwd,
exit codes, logs and environment. The fingerprint excludes self-referential reports and uses
canonical Change paths so archival alone does not invalidate behavioral evidence. Archive
rebases in-Change artifact references and clears completed session pointers. Local close
requires local execution; CI re-executes against the candidate rather than trusting the report.

Exit codes for doctor/validation/verification/CI: 0 PASS, 1 FAIL/input error, 2 PENDING.
Inventory uses 2 when work remains by design. Successful mutation commands return 0 even
if the resulting work item is draft/PENDING. Hook errors emit diagnostic JSON and return 0
to avoid trapping a session; required CI is independent. The JSON status remains authoritative.

## Scope of enforcement

Current checks cannot prove complete source understanding, semantic spec equivalence,
meaningful assertions or immunity to intentionally weakened repository policy. Protect
toolkit/manifest/policy/CI edits through independent review and remote controls. No Hook
tries to intercept all shell writes. Lifecycle/adapters must be verified per runtime version.
