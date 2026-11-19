# Agent Repo Kit behavior

## Scope

Generic repository initialization and continuing AI-assisted engineering. Skills own
semantic work; the CLI owns deterministic scaffolding, references, checks and evidence.

### Requirement: Install through native plugin or Skill distribution (REQ-NATIVE-001)

Verification: automated and native-tool checks

Claude Code SHALL receive a native plugin and marketplace manifest with two onboarding Skills.
Other hosts SHALL be able to install standard root skills/<name>/SKILL.md folders.
The initialize-repo folder SHALL contain all initialization code/resources and work when
copied alone without the repository, installed Python packages or a source bootstrap.
Project initialization SHALL preserve installer-owned Skills and avoid creating duplicates.

#### Scenario: Initialize from a copied installed Skill

- GIVEN only the complete initialize-repo folder in a host's installed Skills directory
- WHEN the Agent invokes its bundled initializer
- THEN project rules/runtime are created, existing content is preserved, and installed
  Skills remain the platform's responsibility rather than copied into every repository

### Requirement: Onboard without a global package installation (REQ-ONBOARD-001)

Verification: automated and workflow review

The recommended entry SHALL let the Agent bootstrap a complete toolkit snapshot into the
target without pip, a virtual environment or a global ark executable. Generated hooks
SHALL use the target's vendored runtime and remain usable after the toolkit source is removed.
Existing owned global-command hooks SHALL migrate without losing unrelated user handlers.

#### Scenario: Dispose of the toolkit after initialization

- GIVEN a target and a temporary complete toolkit snapshot
- WHEN the Agent bootstraps without installed packages and removes the snapshot
- THEN generated hooks work from nested target directories and semantic onboarding
  remains an explicit Agent task rather than being falsely reported complete

### Requirement: Preserve existing repository assets (REQ-INIT-001)

Verification: automated

Initialization SHALL support empty and existing repositories, merge human instructions,
preserve existing specs/IDs/settings/dirty content and reject unmanaged conflicts.

#### Scenario: Initialize and repeat on an existing repository

- GIVEN human AGENTS content, native OpenSpec artifacts and uncommitted changes
- WHEN installation runs twice with unchanged inputs
- THEN human content/IDs remain and the second installation makes no asset changes

### Requirement: Distinguish evidence inventory and understanding (REQ-BASELINE-001)

Verification: automated and workflow review

Inventory SHALL remain distinct from source-grounded static review. Review SHALL require
filled module explanations, valid scoped citations and current source/document digests.
Raw evidence SHALL be retained. Ready verification SHALL anchor pre-change evidence.

#### Scenario: Source changes after a reviewed pre-change anchor

- GIVEN reviewed source and a successful scoped ready verification
- WHEN implementation changes but historical evidence is preserved
- THEN delivery uses the anchor and current checks without rewriting old behavior

### Requirement: Require real current delivery verification (REQ-VERIFY-001)

Verification: automated

Required checks SHALL actually run/pass or have current explicit external/manual evidence.
Missing, partial, stale or unavailable required checks SHALL prevent overall PASS.
Input mutation during checks SHALL fail. Handwritten/committed PASS alone SHALL not close work.

#### Scenario: Required command is unavailable

- GIVEN a required configured check
- WHEN its executable is missing
- THEN the check is NOT_RUN and delivery is PENDING

#### Scenario: Lightweight command mutates reviewed inputs

- GIVEN a content-bound lightweight declaration and a required command
- WHEN that command passes but changes reviewed inputs or the candidate diff during execution
- THEN the same run fails input currency and retains the actual command output

### Requirement: Preserve specification synchronization through archive (REQ-ARCHIVE-001)

Verification: automated

The toolkit SHALL reuse OpenSpec layout/workflows, record reviewed synchronization and
require fresh workspace delivery evidence. Archival SHALL retain valid in-Change artifact
references, usable CI and no stale active session pointer. Hashes SHALL NOT be described
as proof of semantic equivalence.

#### Scenario: Archive a verified change with an internal review artifact

- GIVEN synchronized current specs and a review artifact inside an active Change
- WHEN delivery passes and the Change is archived
- THEN the artifact reference resolves, candidate CI rechecks successfully and context
  does not point at a missing active checkpoint

#### Scenario: File-native archive remains native

- GIVEN a verified file-native change with no toolkit metadata sidecar
- WHEN toolkit close is requested before native synchronization and archive
- THEN it reports PENDING/native-archive-required with exit 2 and preserves the active files
- AND the selected native workflow remains responsible for synchronization and archive

### Requirement: Isolate resumable work and bound hook continuation (REQ-CONTEXT-001)

Verification: automated

Session pointers SHALL be isolated by worktree/branch/session. Startup SHALL avoid full
inventory/tests. Stop continuation SHALL be bounded and permit blocked handoff.

#### Scenario: Verification cannot finish in the current environment

- GIVEN an explicitly blocked checkpoint
- WHEN a Stop hook executes
- THEN normal handoff remains possible with saved next steps

### Requirement: Check actual candidate differences (REQ-CI-001)

Verification: automated

CI SHALL cover behavior/configuration differences with related changes or exact lightweight
declarations, rerun confirmed checks, protect raw/accepted decision history and avoid trusting
committed PASS reports. Declared native adapter support SHALL distinguish configuration,
protocol validation and live-runtime verification.

#### Scenario: Source changes after a lightweight declaration

- GIVEN a declaration bound to the former contents
- WHEN a further source change changes its digest
- THEN the stale declaration no longer covers the new candidate change

### Requirement: Support tool-independent and local-only development (REQ-PORTABLE-001)

Verification: automated and native-tool checks

The toolkit SHALL read native OpenSpec or mapped ordinary change files without requiring
ark.json, a development Skill, a session activation or the toolkit archive command.
Local checks SHALL work without a remote or hosted CI. GitHub Actions generation SHALL be opt-in.
Native tools SHALL own synchronization and archive. Proposed deltas SHALL remain distinct from
current accepted specifications; synchronization SHALL be checked after native archive.

#### Scenario: Develop using ordinary native assets

- GIVEN a locally initialized repository and proposal/tasks/delta files
- WHEN the selected development tool implements and tests the scoped behavior
- THEN local verification runs real checks without a toolkit lifecycle or remote service
- AND ambiguous associations or unsynchronized archived specifications cannot pass

### Requirement: Observe project facts and preserve context (REQ-CONTEXTUAL-001)

Verification: automated and workflow review

Initialization SHALL observe languages, build manifests, declared versions and roots from
actual repository files. Unknown business architecture SHALL remain unknown. Existing human
context SHALL be preserved. Risk-appropriate templates and a local engineering standard
SHALL be available without requiring every task to produce every asset.

#### Scenario: Initialize a mixed-language repository

- GIVEN actual Java/C source, a Maven declaration and human context
- WHEN initialization observes the repository and repeats
- THEN source-backed facts are navigable, human context is preserved, and repeated setup is inert

### Requirement: Maintain source-backed knowledge and decisions (REQ-KNOWLEDGE-001)

Verification: automated and workflow review

The toolkit SHALL retain immutable static-review snapshots, source/document freshness,
separate module/contract/case coverage and explicit promotion/retirement records. Written
cases SHALL NOT be reported as executed tests. Promotion SHALL require current evidence,
real current requirements and an actual decision artifact. Existing section/ledger formats
SHALL be reusable; generated decision views SHALL have one authoritative source.

#### Scenario: Refresh explained source after a change

- GIVEN a registered source-backed explanation and immutable snapshot
- WHEN source changes and the explanation is refreshed
- THEN the old snapshot remains, freshness is explicit and a new declaration is recorded

### Requirement: Validate engineering relations without binding the development tool (REQ-RELATIONS-001)

Verification: automated

The toolkit SHALL validate applicable current/delta scenarios, identities, references, ADR and knowledge relations. Native titles/renames and foreign IDs SHALL remain usable. Format exceptions SHALL be explicit, content-bound, expiring and unable to waive required business checks. Human report content and accepted history SHALL be preserved. Specification-stage success SHALL NOT count as delivery success.

#### Scenario: Review native specifications before implementation

- WHEN valid native proposal/tasks/delta files still contain unfinished implementation tasks
- THEN specification review can pass without running business commands
- AND delivery remains pending until applicable checks and tasks are complete

#### Scenario: Complete composite dependency identity

- WHEN Depends-On names a composite REQ identity whose current owner is missing
- THEN validation reports that complete missing identity as pending
- WHEN the actual complete identity is current
- THEN that missing-owner finding is cleared

### Requirement: Execute preserved and target behavior verification (REQ-BEHAVIOR-001)

Verification: automated

Changes to established behavior SHALL have actual pre-change characterization bound to
source, plan, fixtures, command definitions and environment. Delivery SHALL rerun required
preserved regression and intended target checks separately. Missing original environments,
stale fixtures and partial required execution SHALL NOT yield delivery PASS. Initially new
repositories SHALL acquire baseline obligations as business code is committed/delivered.
JSON replay normalization SHALL be explicit and preserve visible business differences.

#### Scenario: Positive target passes while retained failure behavior breaks

- WHEN the refactor returns the intended normal result but loses a preserved error/boundary case
- THEN the actual regression command fails and delivery is FAIL
- AND the original executed evidence remains unchanged

### Requirement: Maintain daily local feedback without a required development entry (REQ-MAINTENANCE-001)

Verification: automated and native startup exercise

Context SHALL associate actual diffs with native work without requiring activation, keep
overlap ambiguous and avoid full builds/inventory on startup. Local checks SHALL persist
honest phase/command execution results and protect history against HEAD without CI. Native
paused checkpoints SHALL preserve the selected workflow. Optional Git checks SHALL preserve
custom hooks and work without hosted services. Runtime support SHALL distinguish actual
startup execution, protocol tests, native trust and unverified model-conversation behavior.

#### Scenario: Pause directly developed native work

- WHEN native work is selected by its actual diff and a paused checkpoint is saved
- THEN context can resume it without a toolkit activity pointer or sidecar
- AND Stop allows the handoff without forcing a development Skill or infinite continuation

### Requirement: Reuse native schemas and migrate owned assets safely (REQ-MIGRATION-001)

Verification: automated and real-repository qualification

First initialization SHALL support existing asset mappings before scaffold creation, preserve
native ledgers/report formats and avoid adding incompatible generic documents to established
ADR directories. Machine evidence SHALL support a mapped immutable location. Explicit legacy
upgrade SHALL retire only unmodified owned copies, preserve customization/history and restore
its own deleted/written files on failure. Release claims SHALL be bounded by actual native,
real-repository and platform evidence.

#### Scenario: Initialize a repository with a dated native raw-evidence schema

- WHEN initialization maps machine evidence and the existing native ledger before writing
- THEN original raw batches, IDs, native formats and human work remain valid
- AND mapped execution evidence is still immutable and distinct from business source

### Requirement: Reject incomplete local delivery evidence (REQ-INTEGRITY-001)

Verification: automated

Local verification SHALL conservatively include unknown non-document inputs, configuration,
build files and resources. Runtime-read document paths SHALL be configurable. All effective
requirements SHALL retain applicable test references or required delivery-check mappings,
including during changes with no delta. A mapping SHALL NOT downgrade a declared manual or
external verification type. Affected current knowledge SHALL be rechecked after source or
document changes before full delivery; explicit retirement SHALL preserve historical evidence.

#### Scenario: Modify a configuration file outside the former suffix list

- WHEN application.properties or an unknown runtime input changes without scoped work
- THEN local verification fails rather than returning document-only PASS

#### Scenario: Remove a test while unrelated tests still pass

- GIVEN a current automated requirement whose only reference is the removed test
- WHEN the remaining test suite passes
- THEN local verification remains PENDING until the effective requirement has valid coverage

#### Scenario: Deliver with a stale current explanation

- WHEN affected registered source or explanation changes
- THEN delivery stays PENDING until re-review or explicit retirement
- AND unrelated stale knowledge does not block a scoped task and original snapshots remain

### Requirement: Complete existing behavior specification handoff (REQ-BASELINE-SPEC-001)

Verification: automated

Default existing-code onboarding SHALL continue from source-backed Baseline contracts to
current observable behavior specifications at the mapped path, without an extra user prompt.
It SHALL preserve existing requirement identities, record evidence and preservation reasoning,
and keep defects, conflicts and unknowns separate from accepted promises. The handoff check
SHALL distinguish specification linkage from missing verification and actual test execution.
An explicit analysis-only scope SHALL be honored and reported as excluding specification.

#### Scenario: Ungoverned existing repository
- WHEN baseline-repo is invoked without extra parameters
- THEN it writes/reuses meaningful current specs and scenarios with Baseline/Source links
- AND does not require native OpenSpec CLI initialization for authoring files

#### Scenario: Missing specification or verification
- WHEN reviewed contracts lack current requirements or links
- THEN the handoff remains PENDING rather than claiming inventory-only completion
- WHEN the specification exists but lacks applicable tests/check mappings
- THEN specification status may PASS while verification remains PENDING

#### Scenario: Changed evidence or removed promises
- WHEN source, contract or preservation evidence changes, or a linked requirement disappears
- THEN the handoff reports stale PENDING or missing-requirement FAIL respectively

### Requirement: Reopen source after baseline generation (REQ-SOURCE-AUDIT-001)

Verification: automated

Default Baseline/spec onboarding SHALL reopen source after drafting to derive a fresh branch
and flow coverage checklist, check source-to-artifact omissions and artifact-to-source truth,
record findings, correct or dispose them with evidence, and reopen source for post-fix recheck.
Reports SHALL distinguish actual same-agent separate review from independent review, retain
first-pass finding IDs and keep new unreviewed issues open. Declared audit evidence SHALL be
bound to source/artifact/report bytes and missing/stale/open audits SHALL remain PENDING.
Structural checks SHALL NOT be represented as proof of rereading or semantic correctness.
Accepted conflicts SHALL NOT be silently overwritten and repeated unresolved work SHALL
checkpoint rather than loop indefinitely.

#### Scenario: First draft contains unsupported claims or omitted branches
- WHEN generated Baseline/spec artifacts are ready
- THEN the Agent reopens actual source/config/callers to rebuild coverage and reverse-check claims
- AND records actual issues before fixes and rechecks corrected and neighboring paths from source

#### Scenario: Incomplete review or stale audit
- WHEN one pass, scoped coverage or a first-pass disposition is missing
- THEN the audit record cannot complete
- WHEN reviewed source, artifacts or report changes after recording
- THEN audit status is PENDING until relevant source review is refreshed

#### Scenario: Unresolved conflict or second-pass discovery
- WHEN an accepted spec conflicts with source or a new unreviewed issue appears
- THEN it remains explicitly unresolved rather than being silently closed for PASS
- WHEN the Agent corrects a new issue and repeats the scoped source review
- THEN it can append another source-recheck to the same report, retaining all prior finding IDs
- AND newly discovered findings start open, and the final recheck determines outstanding findings

### Requirement: Generate usable project artifacts (REQ-ARTIFACT-QUALITY-001)

Verification: automated

Onboarding SHALL produce a project-specific entrance covering purpose/stack, actual constraints,
asset navigation, source/runtime boundaries, confirmed commands, development workflow and
authority. It SHALL preserve human/native rules and avoid a second outline or a full build
manifest dump. Major business/supporting capabilities SHALL be mapped from actual production
source/config/build scope; uninspected or excluded business scope SHALL remain partial.
Current specs SHALL state independently understandable observable input/rule/output/error and
side-effect contracts with concrete scenarios; Baseline citations SHALL be provenance rather
than substitutes for normative details. Essential delegated owners SHALL already exist.
Current quality status SHALL include entry, whole-scope coverage, specs and actual audit
declarations, and SHALL NOT infer semantic completeness or business-test execution from
counts, format PASS, compilation or a historical initialization snapshot.

#### Scenario: Many build manifests
- WHEN a repository has dozens of module build files
- THEN AGENTS remains a structured project entrance and full inventory stays in context

#### Scenario: A few lifecycle specs but major code remains unanalyzed
- WHEN selected specs have valid IDs/links but production capabilities remain unmapped or unreviewed
- THEN current onboarding reports PARTIAL/PENDING with remaining scope

#### Scenario: Reference-only spec or missing current owner
- WHEN a current promise only delegates its normative body to Baseline or an uncreated required owner
- THEN the deterministic guard reports PENDING and source review must supply real contract detail

#### Scenario: Current quality versus old setup records
- WHEN a historical setup snapshot says PENDING and later compile checks passed
- THEN reports distinguish their phase/time/scope and current quality is recalculated
- AND actual business-test execution remains a separate reported outcome

#### Scenario: Add human notes around a generated project entrance
- GIVEN an existing generated project-specific entrance with source-backed facts
- WHEN human notes are added outside its intact managed block and the entry is refreshed
- THEN both the human notes and seven project sections are preserved
- AND a later initialization keeps that entrance rather than reducing it to generic integration

### Requirement: Automatic whole-repository onboarding (REQ-ONBOARDING-DEFAULTS-001)

Verification: manual

A bare initialize-repo or baseline-repo invocation SHALL target all first-party existing
behavior in the repository, including relevant supporting configuration and build inputs.
The executing Agent SHALL choose and continue batches without asking the user to select a
vertical slice or approve routine continuation. Checkpoints SHALL preserve remaining scope;
completion of one batch SHALL NOT imply whole-repository completion. Explicit user limits
SHALL take priority; real blockers SHALL remain visible while independent work continues.

Before writing specifications, the Agent SHALL resolve existing policy and current-spec
authority from actual repository rules/content. It SHALL preserve authoritative mappings and
IDs, otherwise use the OpenSpec layout. It SHALL NOT ask a routine doc/specs-versus-OpenSpec
question or treat target designs as current promises. It SHALL automatically initialize missing
native setup with a compatible installed CLI's supported noninteractive options when doing so
preserves existing human/mapped assets. Unavailable/unsafe native setup SHALL be NOT_RUN and
SHALL NOT prevent source-backed file-based specification authoring or trigger package installation.

#### Scenario: Several business capabilities
- WHEN a bare invocation starts in an existing repository with several business capabilities
- THEN the Agent selects batch order and continues pending batches automatically
- AND retains the whole capability map as completion scope and reports genuine remaining gaps

#### Scenario: Current specification authority already exists
- GIVEN repository rules identify doc/specs as effective current specifications
- WHEN initialization runs
- THEN those paths and IDs are reused without migration or a competing OpenSpec spec tree

#### Scenario: Only target designs exist and native CLI is unavailable
- GIVEN doc/specs contains target designs and no current-spec authority is established
- WHEN bare initialization runs without an installed OpenSpec CLI
- THEN source-backed current specs are authored at openspec/specs and designs are preserved
- AND native initialization/validation is reported NOT_RUN separately from actual spec results

#### Scenario: Compatible native tool exists
- GIVEN a locally installed compatible CLI and missing native configuration
- WHEN initialization can run noninteractively without overwriting human or mapped assets
- THEN the Agent inspects installed help/version and performs native setup automatically
- AND reports actual native results without asking for a routine tooling choice

### Requirement: Complete project configuration and final onboarding evidence (REQ-ONBOARDING-CONTENT-001)

Verification: automated

When OpenSpec is applicable, onboarding SHALL generate or reconcile real schema/context/artifact
rules from source-backed project facts and established authority. It SHALL preserve native/human
schema, rules, comments and edited configuration, distinguish generation from actual content review,
and report native CLI reading/validation separately. Bounded guards and review hashes SHALL NOT
be presented as a general YAML/schema parser or semantic certification.

Current contract files, native contract declarations and current-spec contract references SHALL be
checked independently of the knowledge registry. An unregistered referenced contract SHALL block
current specification/whole-scope completion and remain in expected source-audit artifact scope.
Baseline navigation SHALL reflect actual registered/current/retired/stale knowledge and preserve
native prose; missing test mappings SHALL remain explicit non-PASS with no inferred execution.

Final onboarding SHALL re-evaluate structure and declarations after final asset/audit edits and bind
the result to actual source/configuration/test/registry/audit inputs. Later input changes SHALL make
that record stale; input changes during the check SHALL prevent a complete result. An empty-spec
structure PASS SHALL declare its limited scope and SHALL NOT claim completed semantic onboarding.

#### Scenario: Empty or framework/language-only config
- WHEN a project has no substantive context or applicable artifact rules
- THEN configuration content remains pending even if native setup or structure checks previously passed
- AND generation alone does not record an actual review or native CLI validation

#### Scenario: Native schema and human configuration
- GIVEN native configuration or an edited generated configuration
- WHEN refresh or upgrade runs
- THEN the existing content is preserved for in-place reconciliation and actual review
- AND an established non-OpenSpec mapping does not acquire a competing OpenSpec workflow

#### Scenario: Referenced contract missing from registry
- GIVEN a current specification cites a contract that was not registered
- WHEN baseline specification/onboarding status runs
- THEN the contract is discovered, completion is blocked and its artifact remains expected for source audit

#### Scenario: Navigation refresh
- WHEN knowledge is registered, promoted or retired
- THEN generated navigation reflects the declaration while retaining native front matter and prose
- WHEN source changes make knowledge stale
- THEN navigation needs refresh rather than continuing to imply fresh evidence

#### Scenario: Final snapshot and changed audit input
- WHEN a final onboarding declaration is recorded after all final artifact and audit-registration edits
- THEN its current inputs and limited verification scope are stored
- WHEN source, configuration, tests, registry or audit evidence subsequently changes
- THEN the previous final record is stale and cannot establish current completion
- WHEN only a timestamp changes without input bytes changing
- THEN timestamp ordering alone does not invalidate that record


### Requirement: REQ-BEHAVIOR-QUALITY-001 Behavior evidence and candidate review
Verification: automated
The toolkit SHALL require source-derived observable behavior review for existing-repository onboarding separately from file/capability coverage. It SHALL retain unknown/inferred/defect observations without promoting them to new current promises, check explicit source-path/branch/effect obligations and all declared normative clauses, attempted counterexamples, canonical same-condition contract conflicts and actual assertion/check mappings. Coverage SHALL be labeled as the declared discovered inventory, with runtime execution assessed separately.
The toolkit SHALL bind behavior reviews to actual source/spec/test/policy inputs, preserve immutable snapshots and verification-change/removal dispositions, expose declared transitive impact and detect new unmapped sources. It SHALL apply affected review conditions consistently to local/CI/direct delivery and toolkit close. A two-pass source/target/assertion candidate review MAY support intentional native deltas without declaring current baseline synchronized; actual tests and native archive remain separate obligations.

#### Scenario: Directory coverage and comment-only tests
- WHEN file/capability maps and REQ comments exist but observable-unit, effective-path, clause or assertion evidence is absent
- THEN existing-repository onboarding remains pending rather than being certified by structure or counts

#### Scenario: Contradiction, uncertainty and repeated contracts
- WHEN a current promise has an unresolved counterexample, inferred/unknown/defect support, or a declared same-key/same-condition contract conflict
- THEN the inconsistency prevents a successful behavior review
- WHEN a reviewed fact is intentionally not promoted or evidence is unavailable
- THEN its baseline/gap disposition and limited coverage remain explicit

#### Scenario: Source or test drift and candidate lifecycle
- WHEN affected source/test/spec evidence changes or a new unmapped production input appears
- THEN delivery/close cannot rely on stale behavior evidence, including when old impact units are empty
- WHEN an actual closed two-pass candidate audit covers all native targets, affected/new sources, current specs, inventory and actual assertion tests
- THEN candidate review may support delivery while the old current baseline remains pending refresh
- WHEN actual audit inputs or targets subsequently change
- THEN that candidate declaration is invalid until reviewed again

#### Scenario: Native readiness and meaningful regression probes
- WHEN the native toolchain or external prerequisites are unavailable
- THEN readiness/NOT_RUN is reported separately from actual build/test results
- WHEN an assertion sees original, deliberately broken and restored bounded sample behavior
- THEN actual pass/fail/pass results and logs are retained without certifying arbitrary projects

#### Scenario: Executable assertion location and native command cwd
- WHEN a claimed assertion exists only in a Python literal/docstring or supported C-family literal/comment, or only by joining disjoint selected ranges
- THEN it cannot satisfy the executable assertion-location obligation
- WHEN a configured relative executable uses the repository root or a declared subdirectory as cwd
- THEN readiness resolves it from that cwd and reports availability separately from execution

### Requirement: REQ-SOURCE-FACTS-001 Current clauses follow decisive source observations
Verification: manual

The onboarding workflow SHALL complete each behavior batch through source observations,
current clauses, assertion review and source recheck. Before drafting a new current clause,
the reviewer SHALL record trigger/condition, actual outcome/side effects and decisive effective
path evidence for the same input domain in existing Baseline/contract records. Literal sets, validation limits, safety,
timing, precedence and lifecycle claims SHALL use their actual registration, enforcement,
trigger or override path as applicable. Unknown observations and defects SHALL retain their
explicit disposition. Existing accepted source/spec conflicts SHALL retain their decision history.

The reviewer SHALL assess each clause/scenario's actual test stimulus, reached branch and
observed assertion. Missing or unrelated assertions SHALL remain verification gaps, with actual
test execution reported separately. The runtime SHALL continue to label declaration consistency
and currency within their actual scope.

The reviewer SHALL derive concrete acceptance predictions from the current Spec before comparing
them to the effective source outcomes for the same stimuli. The behavior review SHALL flag
differing declared outcomes, retain unclear or ungrounded cases as pending, and continue to
read older inventories without awarding the new review from old records.

#### Scenario: A valid reference accompanies an incorrect expected result
- GIVEN the cited requirement and source anchors exist and unrelated tests pass
- WHEN the recorded Spec prediction differs from the recorded source outcome for the same stimulus
- THEN the current behavior review fails and identifies the behavior unit

#### Scenario: A legacy inventory lacks a Spec-only case
- WHEN the existing inventory is reviewed again
- THEN the missing comparison stays pending until the Spec and source have been reviewed

The baseline workflow SHALL record its source-derived capability map before drafting batches and
reconcile it during later reviews. Re-recording SHALL require a disposition for a previously
discovered capability that disappears or changes from business to supporting.

#### Scenario: A pending alternative shares a file with a specified capability
- WHEN a later batch omits the previously recorded alternative without a disposition
- THEN recording is rejected and the previous review snapshot remains available
- AND the changed live map cannot establish current coverage

#### Scenario: A definition disagrees with an effective path
- GIVEN a declared constant, validator or callback differs from effective registration, use or final installation
- WHEN current clauses are drafted and rechecked
- THEN the source record states the effective behavior and disposition with decisive evidence
- AND a defined capacity alone cannot establish safe validation or rejection

#### Scenario: Passing tests observe a different behavior
- GIVEN a passing initialization assertion and a separate unobserved temporal or dispatch promise
- WHEN its clause/scenario mapping is reviewed
- THEN that promise retains a verification gap
- AND execution counts remain separate from assertion and source-review coverage
