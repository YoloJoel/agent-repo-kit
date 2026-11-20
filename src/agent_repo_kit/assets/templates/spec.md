# Capability

<!-- ARK:FILL -->

## Purpose
Describe the observable capability and accepted scope.

## Requirements

### Requirement: REQ-CAPABILITY-001 Observable behavior
Verification: automated

The system SHALL describe an observable promise, not an implementation algorithm.

#### Scenario: Named condition
- WHEN a concrete input/action occurs under stated conditions
- THEN a concrete observable output/state/error follows

For source-backed promises, link the registered Baseline contract. Keep implementation/test line locations in the evidence record. Reuse existing repository IDs.
