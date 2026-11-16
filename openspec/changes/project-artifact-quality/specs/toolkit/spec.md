## ADDED Requirements

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
