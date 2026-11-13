# ADR-0005: Tool-independent, local repository engineering

Status: Accepted

## Context

A required deliver-change workflow and ark.json duplicate the lifecycle already owned by
OpenSpec or another development tool. Consumer repositories may have no GitHub or CI.

## Decision

Expose two onboarding Skills. Persist development requirements in repository rules and
run tool-independent checks locally. Read ordinary/native proposal, tasks and deltas;
legacy metadata stays compatible. Native tools own synchronization and archive. Active
deltas describe proposed behavior; archived deltas must agree with current specifications.
Generate hosted CI only when explicitly requested. Local verification is the common base.

## Alternatives

Automatically invoking the old development Skill preserves the unwanted coupling.
Making CI mandatory excludes local/private repositories. Neither is adopted.

## Consequences

No dedicated lifecycle or pointer is required. Unclear associations remain pending.
Document readers establish structural relations, not semantic correctness. Live host
loading and optional remote enforcement continue to require separate evidence.
