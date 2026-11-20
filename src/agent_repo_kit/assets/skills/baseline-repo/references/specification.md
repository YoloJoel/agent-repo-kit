# Complete the existing-behavior specification handoff

Do this during ordinary baseline-repo onboarding without asking for an extra prompt.
Honor an explicit analysis-only or limited module scope and report the omitted scope.
Otherwise the scope is the whole repository, with automatically ordered batches; checkpoints
are recoverable progress, not a reason to ask for continuation or deliver one slice as complete.

Read `source-facts.md` and `behavior-model.md` first. Draft by observable capability and cross-module contract,
not by directories. Every normative clause needs a discovered behavior unit, actual path
conditions, an attempted counterexample and explicit verification gaps.
Before writing a clause, persist its actual trigger/condition/outcome and decisive source
expression in the batch's existing Baseline/contract table. Resolve literal lists, effective
validation and event/timer/override behavior there. Review each scenario's real test observation.

1. Read policy.paths.specs/changes and existing requirements before writing. For an
   ungoverned repository, create real capability spec files at the mapped specs path
   (default openspec/specs/<capability>/spec.md). Do not create empty directories or
   assume OpenSpec CLI is installed. Preserve an existing authoritative mapping (including
   doc/specs); do not ask the user to choose a directory. Without established current specs,
   use the default OpenSpec layout. Target design documents alone do not establish current
   authority. With a compatible installed CLI, inspect its --help/version and initialize missing
   native setup noninteractively for the current runtime when it preserves mapped assets.
   Preserve existing native config/rules; do not overwrite human instructions or introduce a
   second spec tree. If native setup is unavailable/unsafe, record NOT_RUN and continue file-based
   authoring. Never auto-install packages just to probe availability. Native CLI setup and actual
   specs are separate results; neither a directory nor an unavailable CLI ends the baseline.
Read `artifact-quality.md`: specs must be independently understandable and testable;
Use the registered Baseline contract as the stable provenance link. State the input, rule and outcome in the Spec itself.

2. Extract public observable behavior from traced source/config/callers and tests:
   normal results, validation/errors, state/side effects, ordering/idempotency, recovery
   and compatibility where actually present. Keep algorithms and class names in Baseline
   or design, not normative requirements. Cover meaningful branches rather than cloning
   source statements into specs. Record inspected revision and unresolved ranges.
3. Reuse current requirement IDs/titles for the same promise. Add stable Baseline contract links instead
   of generating duplicates or overwriting accepted semantics. A source/spec conflict is
   an open discrepancy, not permission to rewrite either. Do not import target designs
   as current behavior. Known defects/ambiguous choices remain in the single ledger;
   retain any existing explicit compatibility decision and do not silently repair code.
4. Record preservation reasoning: which verified behavior is retained, why, and which
   defect/unknown/implementation details are excluded. Routine analysis under the user's
   preservation goal needs no additional approval. Identify the actual Agent reviewer;
   do not describe this as a human-approved ADR. Ask only for genuinely material choices.
5. Write substantive requirements/scenarios using the existing format or bundled spec
   template. Each new requirement cites its registered contract with `Baseline: <path>`
   or its stable section. Keep exact implementation and test line references in the registered
   contract, behavior inventory, assertion mapping or audit report. Apply this to the entire Spec
   and to change deltas, including tables, footnotes and Markdown link targets. When updating an
   older Spec, first preserve each locator and its Requirement ID in the corresponding Baseline
   evidence record, then remove the inline citation without changing the promise or scenario.
   For newly proposed behavior, use the applicable decision or change rationale. Example:

   ```markdown
   ### Requirement: REQ-LOOKUP-001 Existing lookup
   Verification: automated
   Baseline: docs/baseline/contracts/lookup.md
   The service SHALL return the stored value for an existing key.
   #### Scenario: Known key
   - WHEN a stored key is queried
   - THEN its stored value is returned without modifying the record
   ```

   For each high-impact alternative, try to write one discriminating case from the Spec alone.
   For example, “uses the configured limit” leaves acceptance at equality undecided. Specify the
   observable result at equality and just across it when the effective path establishes both.
   If callers supply named values, trace their effective definitions as well as the comparison.
   State the ordering, mapping or unit a reader needs to decide the outcome. Include only
   distinctions that affect the contract. Preserve an unknown when the owning source is unavailable.
   Put the rule in this Spec. Keep source anchors and branch analysis in the evidence record.
   Follow the acceptance_cases comparison in behavior-model.md before completing this batch.
6. Register contract/case evidence, then `baseline promote --document <contract> --requirements <IDs> --decision <preservation-record> --reviewer <actual identity>`.
   A promotion records selected promises, not every detail in a contract. Document
   exclusions and unresolved decisions so linked IDs cannot imply total semantic coverage.
7. Run `baseline spec-status` (or --scope for a limited task), `baseline validate` and
   structure checks. Fix missing specs, scenarios, evidence and links. Missing automation
   must remain an explicit verification gap; do not switch Verification types to get PASS.
   Reuse/run existing checks; add characterization before later behavior changes, rather
   than claiming all onboarding needs a complete new test suite. `spec-status` checks
   declarations/mappings, not test execution or assertion quality. Report actual command
   outcomes independently. Save module checkpoints for unfinished work.

After drafting and before final onboarding claims, perform the default two source passes in
`source-audit.md`: omissions/claims audit, fixes/dispositions, then a fresh source recheck.
Re-register changed knowledge and selected promotions after document fixes, preserving raw
snapshots. Record the audit only after final artifacts and their evidence are consistent.
