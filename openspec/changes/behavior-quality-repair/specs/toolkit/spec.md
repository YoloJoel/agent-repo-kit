## ADDED Requirements

### Requirement: Review complete source candidates and Scenario outcomes REQ-QUALITY-DISCOVERY-001
The toolkit SHALL expose source-only review candidates with provider limitations and keep unreviewed or stale candidates pending. It SHALL bind the full conditions and outcomes of each current Scenario to its recorded review.
#### Scenario: Initially omitted alternative
- WHEN source contains a contrasting return alternative absent from the authored case inventory
- THEN source discovery retains a candidate requiring reconciliation independently of the authored denominator
#### Scenario: Outcome changes without SHALL
- WHEN a reviewed Scenario gains or changes a WHEN, THEN, table or fenced output
- THEN its old content binding cannot satisfy current Scenario review

### Requirement: Freeze prediction and adjudication stages REQ-QUALITY-READBACK-001
The toolkit SHALL preserve frozen Spec-only reader inputs, predictions and subsequent source adjudications, retain earlier rounds and distinguish recorded review modes from proven model isolation.
#### Scenario: Source answer before prediction
- WHEN a reviewer attempts to adjudicate without a recorded prediction
- THEN the toolkit refuses closure
#### Scenario: Repair invalidates a round
- WHEN source or Spec changes after opening a round
- THEN the prior round becomes stale and a new completed active round can supersede its current status without deleting history

### Requirement: Observe required case execution REQ-QUALITY-EXECUTION-001
The toolkit SHALL distinguish command success from actual required behavior-case execution and keep missing, uncalled or skipped required cases pending.
#### Scenario: Uncalled assertion
- WHEN a command exits successfully after defining but not invoking its regression test
- THEN behavior verification remains pending and no successful pre-change anchor is created
#### Scenario: Wrong retained behavior
- WHEN the same executed assertion fails against an intentionally wrong implementation
- THEN delivery fails even if a separate target acceptance check passes

### Requirement: Explain and preserve evidence currency REQ-QUALITY-CURRENCY-001
The toolkit SHALL provide read-only evidence queries and preserve unrelated unit review counts while exposing affected, unknown, rule-source and external-snapshot changes.
#### Scenario: Independent source changes
- WHEN one independently mapped unit's source changes
- THEN that unit requires review while unaffected unit counts remain available and overall currency stays pending
#### Scenario: External contract changes
- WHEN a declared external alias's contract snapshot differs from its current local file
- THEN external currency becomes pending and delivery fingerprints change

### Requirement: Keep product evaluation distinct REQ-QUALITY-TRIAL-001
The toolkit SHALL validate frozen paired trial accounting with an independent denominator, comparable settings, separate stages and cost records without treating engineering or development-sample success as initial holdout quality.
#### Scenario: Post-repair result without initial draft
- WHEN a trial reports only audit or recheck scores
- THEN the missing initial stage prevents qualification
#### Scenario: Changed model or missing cases
- WHEN paired settings differ or either method omits denominator cases
- THEN trial accounting remains pending and product quality cannot pass
