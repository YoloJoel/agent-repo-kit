## ADDED Requirements

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

## MODIFIED Requirements

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

