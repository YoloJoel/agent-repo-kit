## ADDED Requirements


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
