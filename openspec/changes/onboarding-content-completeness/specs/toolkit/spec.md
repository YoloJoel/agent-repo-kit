## ADDED Requirements

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
