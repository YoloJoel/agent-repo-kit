# Runtime interfaces

## Purpose
Describe runtime registration, configuration and frame results.

## Requirements

### Requirement: REQ-HUB-001 Registered resources
Verification: automated
The hub SHALL register stream, probe and archive resources.
#### Scenario: Resource listing
- WHEN resources are listed after initialization
- THEN all three names are returned

### Requirement: REQ-HUB-002 Period updates
Verification: automated
The hub SHALL reject period updates outside the interval 1 through 600.
#### Scenario: Above maximum
- WHEN the period update interface receives 700
- THEN it returns an error without storing the value

### Requirement: REQ-HUB-003 Frame values
Verification: automated
The receiver SHALL return the input Frame value.
#### Scenario: Frame reception
- WHEN the receiver is given a Frame
- THEN its value is returned
