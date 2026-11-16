# Complete the existing-behavior specification handoff

Do this during ordinary baseline-repo onboarding without asking for an extra prompt.
Honor an explicit analysis-only or limited module scope and report the omitted scope.

1. Read policy.paths.specs/changes and existing requirements before writing. For an
   ungoverned repository, create real capability spec files at the mapped specs path
   (default openspec/specs/<capability>/spec.md). Do not create empty directories or
   assume OpenSpec CLI is installed. Native commands require its own initialization;
   use it when available/requested, preserve its files, and report unavailable validation.
2. Extract public observable behavior from traced source/config/callers and tests:
   normal results, validation/errors, state/side effects, ordering/idempotency, recovery
   and compatibility where actually present. Keep algorithms and class names in Baseline
   or design, not normative requirements. Cover meaningful branches rather than cloning
   source statements into specs. Record inspected revision and unresolved ranges.
3. Reuse current requirement IDs/titles for the same promise. Add evidence links instead
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
   and source evidence with `Source: <path>:Lx-Ly`. Link actual cases/checks. Example shape:

   ```markdown
   ### Requirement: REQ-LOOKUP-001 Existing lookup
   Verification: automated
   Baseline: docs/baseline/contracts/lookup.md
   Source: src/lookup.py:L12-L28
   The service SHALL return the stored value for an existing key.
   #### Scenario: Known key
   - WHEN a stored key is queried
   - THEN its stored value is returned without modifying the record
   ```

   Replace the example with observed behavior; no fabricated source ranges or test results.
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
