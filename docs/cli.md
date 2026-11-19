# CLI reference

## Project obligations and cross-tool delivery (0.4.0 RC)

A native proposal may declare `Kind:`, `Current-Requirements:` (space-separated stable IDs),
`Preserves:`, `Risks:` (space-separated project rule IDs), `Risk-Reason:` and `ADR:` (one
repo-relative Markdown path). Keep each declaration on its own line. The initializer maps
applicable project obligations in `.ai/policy.json` under `artifact_rules`; see the installed
initialize-repo project-entry reference. Path triggers apply to the actual candidate even when
an author declares no risk. Semantic triggers are reviewed declarations. Native design.md and
tasks.md may each cite their original local file on one `Workflow-Source:` line. The local
`check --base <ref>` and existing pipeline `ci --base <ref>` use the same obligations.

## Behavior evidence (0.3.0)

`ark baseline behavior-record --document <mapped behavior inventory> --reviewer <actual identity>`
binds a source-derived observable-unit inventory, actual normative clauses, branch/effect evidence,
attempted counterexamples, contract facts and assertion mappings. `ark baseline behavior-status`
rechecks these declarations, same-condition conflicts and byte currency. Missing/unknown obligations
stay PENDING; unverified current promises/contradictions/conflicts FAIL. This is NOT semantic truth
inference or test execution. See the installed baseline-repo `references/behavior-model.md` protocol.

`ark engineering-status` reports mapped C/C++/Java/Python source/test ranges and configured command
availability. It never executes commands or probes network services. Native commands use argv/cwd,
retain actual exit/signal, logs/hashes and basic environment metadata; record compiler versions,
external prerequisites and local patches with the actual run. Other stacks use the same protocol.

`ark impact` and `ark context` expose direct/transitive candidates from declared behavior dependencies.
Knowledge-only onboarding, candidate implementation delivery and native archive remain distinct.
New source/spec/test bytes require actual affected review before a fresh behavior record; re-recording
hashes alone does not review semantics. Behavior ratios describe the discovered inventory only.

Normal onboarding invokes the installed initialize-repo Skill, namespaced as
`/agent-repo-kit:initialize-repo` in Claude Code. Its bundled helper needs no checkout,
URL guide, package installation or bootstrap. It sets skill_delivery=installed and does
not duplicate host-managed Skills in the target. Source bootstrap remains compatibility.

All commands emit JSON. Examples use `ark` as shorthand for the default vendored command
`python hack/ai/ark.py`; installing a global CLI is optional. Put `--repo <path>` before the
subcommand, or run within a consumer repository/subdirectory. Python 3.11+ is required.
Deterministic commands never invoke a model automatically.

| Command | Purpose |
| --- | --- |
| `ark init [path]` | Detect new/existing code, preserve/merge assets and vendor runtime |
| `ark init . --upgrade` | Explicitly update a managed installation; conflicts are not forced |
| `ark doctor` | Diagnose assets, configured commands and runtime/discovery unknowns |
| `ark context --session <id>` | Navigation and explicit current work pointer |
| `ark baseline inventory` | Ignore-aware paths/hashes, source version and pending coverage |
| `ark baseline review --document <path> --files <paths...> --reviewer <id>` | Record a static review with actual explanations and valid source ranges |
| `ark baseline spec-status [--scope <paths...>]` | Check registered contract-to-current-spec handoff; separate specification and verification mappings; no execution claim |
| `ark baseline audit-record --report <json> --files <sources...> --artifacts <documents...> --reviewer <id>` | Record actual source-first and post-fix source recheck declarations with immutable evidence |
| `ark baseline audit-status [--report <json>]` | Detect missing, stale or unresolved audit records; not semantic certification |
| `ark entry refresh` / `ark entry status` | Render/review source-backed project entrance; preserve human/native entry; no build inventory dump |
| `ark baseline coverage-record --document <map.json> --reviewer <id>` / `ark baseline coverage-status` | Account for whole production/business capability scope and supporting exclusions; partial stays PENDING |
| `ark onboarding-status` | Current declared entrance/coverage/spec/audit quality; does not execute or certify business tests |
| `ark baseline validate` | Detect unreviewed/stale evidence, not semantic completeness |
| `ark change new <id> --kind <kind> --scope <paths...>` | Create a scoped native-layout change and draft artifacts |
| `ark change inspect [--base <ref>]` | Actual diff and behavior/configuration candidates |
| `ark change activate <id> --session <id>` | Worktree/branch/session-specific pointer |
| `ark change status <id>` | Read state without claiming completion |
| `ark verify --phase structure` | Managed assets, specifications and decision structure |
| `ark verify --phase ready --change <id>` | Check preconditions; anchor existing reviewed baseline before implementation |
| `ark change record-sync <id> --artifact <path> --reviewer <id> --method reviewed` | Record reviewed current-spec synchronization and its actual method |
| `ark verify --phase delivery --change <id>` | Actual required checks, current specs, tasks and evidence |
| `ark change close <id>` | Require fresh workspace PASS; archive legacy metadata changes, or hand native changes back to their selected archive workflow |
| `ark note --scope <paths...> --kind mechanical --reason <text> --reviewer <id>` | Hash-bound lightweight nonbehavior declaration |
| `ark evidence --change <id> --check <name> --artifact <path> --reviewer <id> --status PASS --summary <text>` | Record actual manual/external evidence, not an independent certification |
| `ark checkpoint --change <id> --summary <text> --next <text> [--blocked]` | Save recoverable progress; allow real handoff |
| `ark check [--base <ref>]` | Local candidate checks; works without a remote or CI |
| `ark ci --base <real-base-ref>` | Optional hosted invocation of the same checker |
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
they require affected observable requirements before ready. Native or mapped proposal/tasks/delta files are read directly. No ark.json, explicit activation or toolkit lifecycle is required. Legacy metadata remains supported. Concrete repository paths in proposal Impact sections provide scope; ambiguous inferred associations stay PENDING.

New IDs use `REQ-UPPERCASE-001`; existing native artifacts/IDs are preserved during install.
Use `--requirements` for affected toolkit-tracked IDs and `--remove-requirements` for its
retired subset. Record verification for removals and preserve their compatibility decision.
The toolkit checks references and freshness, while agents/native tooling inspect semantics.

Automated requirements need real test-source references or an explicit mapping to required automated checks. Native title keys use capability::title; existing IDs are preserved. For manual/external requirements,
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

For file-native changes without ark.json, close preserves the active files and reports
PENDING/native-archive-required (exit 2). Synchronize/archive using OpenSpec or the mapped
native workflow, then run the local check. No sidecar or second native archive is created.
Legacy toolkit metadata changes retain their existing archive/rebased-evidence behavior.

Lightweight checks also bind inputs before and after actual command execution. A command
that changes reviewed source, policy, a note or the candidate diff invalidates the same run;
a passing command cannot carry a PASS result onto the modified inputs.

Assertion references must identify a real contiguous statement in the selected source lines.
Python, Rust and supported C-family lexical guards reject quoted-string/comment-only matches,
including Python docstrings, Rust nested comments/raw strings, Java text blocks and C++ raw
strings. C/C++ line splicing and numeric separators retain physical-source anchors.
These are bounded guards, not complete language parsers: JavaScript regex literals and other
unsupported lexical forms still need source review. Location checks do not establish reachability
or assertion quality; review the actual stimulus/observation and run native tests.

Exit codes for doctor/validation/verification/CI: 0 PASS, 1 FAIL/input error, 2 PENDING.
Inventory uses 2 when work remains by design. Successful mutation commands return 0 even
if the resulting work item is draft/PENDING. Hook errors emit diagnostic JSON and return 0
to avoid trapping a session; local checks remain available and hosted CI is optional. The JSON status remains authoritative.

## Scope of enforcement

Current checks cannot prove complete source understanding, semantic spec equivalence,
meaningful assertions or immunity to intentionally weakened repository policy. Protect
toolkit/manifest/policy/CI edits through independent review and remote controls. No Hook
tries to intercept all shell writes. Lifecycle/adapters must be verified per runtime version.

## Knowledge and decisions

- `ark baseline register --kind contract|cases --document <path> --files <paths...> --reviewer <id>` records current scoped static evidence and immutable snapshots. Module review keeps its existing command.
- `ark baseline status` computes current/stale/historical evidence without certifying semantic completeness or case execution.
- `ark baseline promote --document <path> --requirements <IDs...> --decision <artifact> --reviewer <id>` links selected promises to real current requirements and a decision.
- `ark baseline retire --document <path> --decision <artifact> --reviewer <id>` retains obsolete history explicitly.
- `ark decision add/resolve/list` maintains one questions source and derived views. Existing native Markdown ledgers can be mapped with paths.questions; the JSON writer will not replace them.

Use knowledge_sections.<kind>.<role> to reuse existing manual sections. Case plans and static declarations are distinct from real execution evidence.

## Structural specification validation

`ark spec validate [--change <id>]` validates current/selected delta structure and relations without executing business checks. `verify --phase specification --change <id>` creates phase evidence while permitting unfinished implementation tasks; it cannot satisfy delivery/close.

Format exceptions in policy.format_exceptions are limited to requirement-wording, scenario-conditions and verification-type. Each requires code, path, sha256, owner, reason, expires (ISO date), decision and decision_sha256. Exact source/decision changes or expiry restore the blocking finding. A valid exception is WARN; actual required check failures remain FAIL. Existing assets are never silently rewritten to fit the format.

## Behavior preservation and intended changes

For existing scoped behavior, record a behavior-plan.json under the native work directory
(or policy.behavior_plans.<change> mapped path). Each case needs id, effect=preserve|target,
source, expected and required checks. Preserve cases also name real fixture paths. An
intentional replacement names replaces, before_checks, before_expected and decision. Checks
can select phases=["ready"] for old-only expectations; the default includes ready/delivery.
Ready executes only preservation/old-expectation checks. Delivery executes current required
checks. Missing applicable checks cannot pass even if check.phases mistakenly excludes them.

The original source, plan, regression fixtures, commands, environment, logs and results are
bound into immutable docs/baseline/raw/behavior evidence. A changed fixture/plan/command or
handwritten anchor cannot reuse old success. Already modified original inputs require
characterization on the original version, not a retrospective PASS. There is no permanent
mode=new exemption after real code is committed/delivered. First new behavior still needs
actual required delivery checks. External unavailable conditions remain NOT_RUN/PENDING.

`ark replay --before <recorded.json> --after <candidate.json>` compares actual JSON results.
Optional --ignore-pointer /output/timestamp requires --normalization-reason; only specific
existing output leaves can be normalized, not IDs, inputs, containers or the whole result.
It records raw digests and the normalization; fixture coverage still requires review.

## Daily local maintenance

`context` now discovers native work from real diff/scope associations without an active
pointer. Overlaps stay ambiguous; disjoint work remains independently verifiable.
`impact [--base <revision>]` records affected explanations and freshness without rewriting
history. `check` persists `.ai/runtime/last-check.json`, including stage and an explicit
business_checks_executed flag. Document-only PASS is not a business-test claim.
`checkpoint ... --paused` supports normal handoff without adding ark.json to native work.
`install-git-hook` optionally installs a real local pre-commit check, preserving custom hooks.
See local-operation.md for no-CI use, other hosts, review and runtime/trust boundaries.

## Native layout reuse and upgrade

The initializer and installed helper accept repeated `--path KEY=repository-relative-path`
for first-use mappings. For example `--path questions=docs/baseline/open-questions.md`
reuses a native ledger without creating another JSON source; `--path evidence=docs/agent-evidence`
keeps machine snapshots outside a native dated-raw-batch schema. Exact repeated mappings are
inert. Existing asset relocation requires preserving history explicitly; the flag does not
silently move established data. Current numeric ADR directories do not receive an extra README.
Plain, bulleted and common bold ADR Status headers are accepted and protected consistently.

`policy.change_associations` can map concrete path prefixes to existing native work IDs when
broad activity scopes overlap. The most specific prefix wins; an association does not expand
scope. Unknown/uncovered ownership still fails, and no global task pointer is required.

Explicit 0.1 upgrade retires only unmodified manifest-owned deliver-change copies and obsolete
asset entry points. Customized copies remain and are recorded as user-maintained in manifest
migration history. Managed runtime/entry conflicts abort before mutation; failed deletion/write
transactions restore only their own touched files. Old raw and accepted history remain.

## Local integrity in 0.2.1

Unknown non-document files are behavior candidates. This includes properties, Gradle/Go/CMake
inputs, lockfiles, protocol definitions, arbitrary formats and runtime resources. Recognized
prose stays light. Set policy.behavior_paths to additional repository paths/patterns when an
application consumes document-like inputs (for example prompts/*.md). Reviewed mechanical
changes can still use content-bound notes rather than adding broad exclusions.

The complete current-spec verification matrix is checked even if a task has no delta.
Automated promises need an exact test-source identity or an explicit required delivery-check
mapping. Manual/external promises need matching required delivery checks. Ready-only, optional
or wrong-type checks do not satisfy this relation. Test references are navigation, not proof
of assertion quality; actual commands and substantive review remain necessary.
README/prose and JSON/YAML input fixtures do not count as executable test-source references.
Use explicit required check mappings for nonstandard executable test formats. Git ignore,
attributes and editor configuration also require impact review; they are not prose exceptions.

Delivery checks gate affected registered explanations on source/document/decision freshness.
Refresh inventory and re-review current modules/contracts/cases after implementation. Use
baseline retire with --document, --decision and --reviewer for an actual historical retirement;
raw snapshots and executed pre-change anchors remain immutable. Unrelated stale documents
do not block scoped work. Empty or binary sources use file@sha256:<actual digest> in evidence
because they have no valid source line ranges; explain the reader contract and semantic gaps.
Recorded decisions participate in scope/navigation. Current knowledge is bound to verification
fingerprints, so a check cannot change its explanation or review record and reuse PASS.

Upgrade existing consumers explicitly with the updated initialize-repo helper --upgrade.
Run local checks again; previous false PASS results may now be FAIL or PENDING. This adds no
daily development Skill, remote dependency or hosted CI requirement.

## Baseline specification handoff in 0.2.2

The default baseline-repo workflow writes/reuses actual current requirements after explaining
source-backed contracts, records preservation reasoning and promotes selected promises. It
does not need an extra prompt or preinstalled OpenSpec CLI. Native CLI setup remains separate.
`baseline spec-status` checks registered contracts, freshness, current requirement declarations,
Baseline links, format and applicable test/check mappings. Use --scope for a limited module.
No contracts or unpromoted contracts are PENDING; missing linked requirements FAIL. Missing
verification mappings remain PENDING even when specification_status is PASS. A PASS means
declared linkage, not semantic completeness, owner approval or actual test execution.
Explicit analysis-only scope may stop before specs but must report that incomplete handoff.

## Source-first post-generation auditing in 0.2.3

Baseline onboarding now requires a new source-derived coverage audit, corrections/dispositions,
and separate source recheck after drafting. The report records actual review mode, every scoped
source/artifact checked in each pass, findings/evidence and retained dispositions. First-pass
findings are open; newly found second-pass issues remain open until further scoped review.
`audit-record` stores immutable snapshots and final input hashes; `audit-status` stays PENDING
for missing, changed or unresolved records. Same-agent rereading is not independent review;
checks validate declared coverage and freshness, not actual rereading or zero defects.
Accepted spec/source conflicts must be logged and not silently overwritten for a PASS.

## Project artifact quality in 0.2.4

Agent-owned .ai/project-entry.json contains actual project purpose/stack/boundaries/constraints,
workflow, precedence and source evidence, not business truth. entry refresh safely renders its
managed block after real check confirmation; human/native entry is preserved without a second
outline. Entry currency binds facts, policy and rendered content. Full manifest inventory stays
in context rather than AGENTS.

Capability maps classify actual production/build/config files as business/supporting, each
with responsibility, explicit scope status and current requirement identities. Exclusions need
reasons; business scope left uninspected stays partial. coverage-status also checks source
review currency. Mapping and counts are declarations, never semantic coverage certification.

Specs must state substantive observable contracts with concrete scenarios, provenance and
existing current owners for essential delegated rules. A narrow pointer-only statement guard
and explicit Depends-On checks catch deterministic mistakes; budget/payload/error completeness
still requires source review. They are not a general semantic proof.

onboarding-status combines current project entry, whole scope, spec/link findings, current
audit artifacts and explicit project-entry/capability-coverage/spec-self-containment reviews.
Missing, stale, unreviewed or partial scope stays PENDING. It reports verification mappings
separately and does not infer that compilation means business tests executed. Historical
initialization snapshots retain their stage/time; early empty-spec PASS is not current proof.

## Configuration and final onboarding in 0.2.6

- `ark openspec refresh`: generate owned/empty spec-driven config from current reviewed entry facts; returns PENDING until actual content review. Native/human/edited config is preserved for in-place reconciliation.
- `ark openspec record --reviewer <identity>` and `ark openspec status`: bind actual source-backed config review/current facts/authority; bounded content guards are not a YAML parser or native-execution evidence.
- `ark baseline index-refresh`: derive current knowledge/navigation while preserving native prose; registration/promotion/retirement also refresh the view.
- `ark baseline status/spec-status/validate`: discover unregistered contracts independently of the registry, including current-spec references. Referenced orphans block completion and remain expected audit artifacts.
- `ark onboarding-status --record`: recheck live structure, config, contract registry, navigation, coverage, specs and audit declarations after final edits; store final input hashes. Later source/config/test/audit/registry edits invalidate it. This does not execute business checks or native CLI.
- Mapping status and actual execution remain separate. Missing automated mappings stay PENDING and are counted by spec; absence of a test directory is not an exemption. Structure PASS explicitly states its limited scope and cannot certify onboarding.

Historical versioned sections above describe their respective releases, not the current product version.

`ark baseline behavior-change-record --change <ID> --report <two-pass report> --reviewer <identity>`
binds active candidate semantic review to actual targets/tests/source inputs. The report's
behavior_change section is specified in behavior-model.md. All native proposal/design/tasks/delta
files, affected current specs/inventory and assertion sources must be audited. Reviewed deliberate
MODIFIED/REMOVED targets do not silently rewrite current specs. Candidate declaration never replaces
actual execution or native archive; refresh current baseline after synchronization. Delivery/close
use the same scope gate, including newly added sources with no previous unit association.

When a native delta intentionally changes a requirement's verification method, keep the current
flat policy mapping and add `requirements.<ID>.targets.<change-id> = {"type": ..., "checks": [...]}`.
Only that Change's delta validation selects its target mapping; current checks retain current
authority. After native synchronization, reconcile the flat current mapping and retire the target
mapping explicitly. This never supplies manual/external execution evidence by itself.
