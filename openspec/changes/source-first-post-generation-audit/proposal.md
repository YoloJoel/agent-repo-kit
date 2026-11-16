# Source-first post-generation audit

## Why
Generated Baseline/spec artifacts need a fresh source review, not just format validation.

## What Changes
Require source-first coverage/claim review, persisted findings and fixes/dispositions, then
post-fix source reread. Bind actual two-pass declarations to reviewed inputs without semantic
certification. Preserve accepted conflicts and report unresolved scope honestly.

## Impact
Update `src/`, `skills/`, `tests/`, `docs/` and version metadata to 0.2.3. No business code
changes, mandatory hosted platform or global daily rebaseline.
