# 0002: Reuse OpenSpec and distinguish declarations from execution

Status: Accepted

## Context

Consumers may already have specs, changes and requirement IDs. A new synchronization
engine could disagree with native OpenSpec. Some environments do not have its CLI.

## Decision

Keep native layouts and artifacts. Let the agent/native workflow synchronize behavior,
then record a review artifact with method native or reviewed. Check current IDs, retired
IDs and artifact/delta/spec freshness. Do not claim hashes prove semantic equivalence or
that reviewed file edits executed an unavailable native command.

## Alternatives

- Reimplement delta merging: creates a second behavioral specification engine.
- Require a native CLI for every operation: blocks independent deterministic checks and
  offline use even when explicit reviewed file synchronization is sufficient.
- Accept a checkbox alone: loses the actual artifact and its binding to current inputs.

## Consequences

Agents must inspect the synchronization diff. Native lifecycle hooks and remote protections
remain environment-dependent. Closure requires actual fresh local check execution and CI
independently repeats candidate verification; repository-controlled evidence is not tamperproof.
