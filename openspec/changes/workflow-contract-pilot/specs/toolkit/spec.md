## ADDED Requirements

### Requirement: REQ-WORKFLOW-001 Shared project obligations at delivery
The toolkit SHALL evaluate a scoped native Change against project-defined artifact obligations
for direct requests, OpenSpec artifacts and linked third-party design or plan documents.

#### Scenario: Unclassified production work
- WHEN production files are delivered with a native proposal and checked tasks, without an identified intent or observable delta
- THEN delivery stays pending with the missing intent, while an explicitly documented fix can cite an existing effective requirement.

#### Scenario: Persistence policy
- WHEN the real scoped candidate intersects a registered persistence rule requiring spec, design and ADR
- THEN delivery lists missing artifacts and requires the referenced decision to be Accepted before implementation delivery.

#### Scenario: Reuse a native plan and design
- WHEN the Change references a local design and a plan produced by another entry
- THEN verification follows the addressed documents, detects outstanding tasks, and leaves native synchronization and archival to the selected workflow.
