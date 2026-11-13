# Source-grounded analysis guide

## Contents
- Scope and authority
- Module and flow analysis
- Contracts and behavior cases
- Coverage, decisions and promotion
- Recording and maintaining knowledge

## Scope and authority

Read real source, callers, runtime configuration, build/deployment files and tests. Manuals
are navigation and candidate evidence; architecture targets are planned behavior. If an
external legacy source is absent, identify the claim as unverified rather than endorsing
its summary. Record revision and dirty-worktree evidence. Reuse document paths and IDs.

## Module and flow analysis

Explain responsibilities, inputs/outputs and collaborators. For each important request,
event or background activity trace entry, validation, branch conditions, transformations,
state changes, side effects and output. Walk failure paths as carefully as success paths.
Describe state ownership/lifetime, concurrency and consistency assumptions, retries,
timeouts, duplication, ordering, partial failure, recovery and cleanup where applicable.
Special compatibility branches need trigger and effect, not just a function name.

A reader should understand the scoped behavior without reading source, while evidence
citations let them locate details. Headings, line references and file counts alone cannot
prove that this goal is met. Review the actual explanation and expected important branches.

## Contracts and behavior cases

Record API/message/shared-data/config/file shape, validation, errors, timing and observable
state/side effects. Identify producers/consumers and sources of compatibility obligations.
Separate observed facts from accepted promises and intended differences.

A behavior case states ID, preconditions, input/action, expected output/state/error, source
and verification method/status. Cover meaningful success, error and boundary branches.
Reuse existing tests. Derive missing characterization fixtures before altering behavior.
A written case is a plan until its actual check has run on an identified version.

## Coverage, decisions and promotion

Distinguish file inventory, explained modules, observed contracts, behavior cases, static
review and executed validation. Unread/uncertain areas remain explicit. Do not report a
whole repository understood merely because all file hashes exist.

The questions ledger is authoritative; summary/detail views derive from it. Classify facts,
behavior decisions, design tasks and validation gates. Resolve accessible facts and routine
design under accepted constraints. For material owner choices present options, impacts
and recommendation. Record the actual decision/reviewer without inventing human approval.

Promote only selected behavior backed by current evidence, an actual decision and existing
requirement declarations. Known defects need a compatibility choice. Keep raw snapshots
and decision history; retire obsolete knowledge explicitly rather than deleting history.

## Recording and maintaining knowledge

`baseline review` registers a complete module declaration; `baseline register --kind
contract/cases` records other knowledge without claiming whole-source understanding.
`baseline status` computes current/stale/historical state from source/document/decision
hashes. These are freshness checks and declarations, not semantic certification.

Default English/Chinese sections are supported. For existing manuals configure
`policy.knowledge_sections.<kind>.<role>` to point at equivalent sections, preserving prose.
Module roles: purpose, flow, state, evidence, gaps. Contract: evidence, interface, failure,
promotion. Cases: scope, cases. Mappings do not waive the underlying content requirements.

After code changes, update only related current explanations and re-record evidence; old
raw snapshots remain unchanged. Link cases, accepted requirements and actual tests without
copying entire business descriptions into every asset. Save checkpoints during long work.

Map existing decision sources with policy.paths.questions. Existing Markdown/native ledgers stay in their original format and workflow; the built-in JSON writer refuses to create a competing source. Optional decision_view/decision_details paths select generated JSON-ledger views.
