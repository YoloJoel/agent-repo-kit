# Design

The Agent owns semantic extraction, existing-spec reconciliation and routine preservation
reasoning. The runtime only checks registered contract evidence, promotions, current spec
identity/link/format and verification mappings. New spec-status is an onboarding completion
entry, not a global mandatory rebaseline on every change. It honors mapped paths/scoped
checks, preserves raw history and separates specification PASS from verification PENDING.
Existing check/validate behavior remains compatible; native CLI initialization is separate.
