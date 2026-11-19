# Accept project artifacts by usefulness, not file or reference counts

## 1. Source-derived capability coverage

Before deep module work, inspect all production/build/config roots and actual entry/call paths.
Map stable observable business capabilities, not just startup/heartbeat/shutdown or the first
few files. In a protocol system include the actual protocol/connector groups and upstream,
downstream, state and integration responsibilities present in source. Do not import a remembered
classification from another project. In a library include its actual public behaviors/policies.

Write a coverage map at an existing native location or a scoped Baseline document, for example:

```json
{"capabilities":[
  {"id":"actual-capability","kind":"business","purpose":"Actual observable responsibility","sources":["actual/source.py"],"status":"pending","requirements":[]},
  {"id":"build-support","kind":"supporting","purpose":"Actual build-only support","sources":["actual/build/file"],"status":"excluded","requirements":[],"reason":"Source-reviewed build support, not a runtime behavior contract"}
]}
```

Use actual current inventory files (baseline coverage.json), including behavior-bearing config
and build/resource inputs. Map files explicitly; do not expand source_paths/exclude to hide
uninspected business code. Supporting/vendor/generated exclusions need concrete reasons. A
business capability outside current scope stays pending/excluded and must be reported partial.
For an inspected business capability with actual current requirements set specified and list
the existing IDs/titles; support-only files need no invented product requirements.

Run `baseline coverage-record --document <map.json> --reviewer <actual identity>` before selecting
the first batch. A pending row is an expected discovery result. Within the requested scope,
walk entry/registration/caller paths forward, then trace externally visible effects, writers and
build-selected components back to their owners. Record anything found by just one walk. One source
file can implement several capabilities. For a scoped review keep other existing rows intact and
report the requested slice and remaining repository coverage separately.

Reread this recorded list after each batch and fill its pending rows. For a genuine retirement,
merge or reclassification, set `capability_dispositions.<previous ID>` on the same map to the
specific reason, surviving ID/evidence as applicable. A batch boundary alone leaves a row pending.
The checker reconciles IDs and business-to-supporting changes against the last recorded map.
It cannot discover an entry neither walk found. Run `baseline coverage-status` to inspect remaining gaps.
These are declared coverage, not proof of semantics. Independently reconstruct the capability
checklist from source during audit; do not just approve the author's map. Report total production
inputs, mapped/reviewed scope, excluded reasons and each unfinished capability. Large scopes
proceed by module with checkpoints, automatically continuing the remaining batches. A bare
invocation retains whole-repository scope; do not ask the user which slice to start or whether
to continue normal work. Never say full onboarding is done after a small partial pass.

## 2. Specs stand on their own

Baseline explains observed code, provenance, internals, defects and gaps. Spec is the current
observable promise. A Baseline/Source line cites evidence; it does not replace requirement text.
Do not remove useful references, but do not reduce a spec to a directory of links either.

Give each capability its own Purpose explaining that capability's actual observable responsibility;
do not paste the same generic source-snapshot/scope paragraph into all specs.

For each real capability write enough normative detail to design meaningful acceptance tests
without opening Baseline/source. Cover applicable dimensions:
- Preconditions, input/message/config shape, fields/types/required/optional/default rules.
- Validation/dispatch rules, branch ordering, transformations and actual output/error behavior.
  Where source fixes an observable exception type/error code, name it; “rejects” alone is not
  sufficient to distinguish a compatible failure from a different one. Do not invent codes.
- Observable state/side effects and order, duplicate/conflict/partial failure semantics.
- Timing/thresholds with units, actual constants or configurable parameters/defaults/ranges;
  “within budget” without a defined budget/configuration contract is not sufficient.
- Retry/backoff/confirmation/commit/recovery boundaries where source actually has them.
- Normal, error, boundary and interaction scenarios with concrete expected results/assertions.

Do not invent details or copy private function/class implementation into normative behavior.
If a dimension does not apply, explain why briefly. If source/evidence is unavailable, keep the
gap explicit and do not certify that capability complete. A small simple capability may have a
small spec; there is no minimum word/Requirement count and no rule that every private helper
needs a spec. Depth follows actual observable complexity.

Examples: “SHALL follow Baseline contract” is insufficient. A sufficient promise states which
input is accepted/rejected, which output/error/state follows, and includes concrete scenarios.
Keep source references alongside that content. Cross-spec reuse is valid only when the owning
requirement already exists at a current, precise reference. Use Depends-On: <actual REQ IDs> for
essential delegated contract ownership. An uncreated future capability or an external Baseline
payload definition cannot stand in for current normative payload/error/confirmation semantics.
If a native human-approved current spec is underspecified, clarify evidence-backed details
without silently changing its accepted meaning; conflicts remain in the single decision ledger.

## 3. Project entrance and independent quality review

Ensure AGENTS is a project entrance; use initialize-repo's project-entry guidance/entry refresh
instead of dumping tooling rules or all manifests into it. Confirm real project commands and
distinguish compile, static checks, business tests and outside evidence. Do not call compile-only
validation “business tests passed”. No Change directory is required just to inspect source and
author current Baseline; do not create empty directories as proof of progress.

During source-first review, hide Baseline and read each spec alone. Try to write specific
assertions from it; record missing payload/error/threshold/side-effect details as findings. Then
reopen source to verify/fill those details. Independently map the major source responsibilities
to specs and audit the complete claimed artifact scope, including project entrance and map.
Record report.quality_checks for project-entry, capability-coverage, spec-self-containment with
actual checked scope/evidence and PASS/PENDING. Existing audit-record still checks declarations,
not cognition; never describe its PASS as proof that semantics are complete.

## 4. Report current quality and phase honestly

Run `onboarding-status` after final entry/map/spec/audit updates. It combines current declared
entry, whole production coverage, spec/link findings, audited artifacts and explicit quality
topics. Missing coverage or audit topics stays PARTIAL/PENDING, even if selected specs validate.
Business verification must still cite actual commands/assertions/results; this quality command
does not execute them. Missing test mappings remains PENDING, not permission to relabel manual.

init-report.json is a dated setup snapshot. An earlier PENDING there and a later compile PASS
can both be true; distinguish phase/run/time/scope rather than overwrite history or call them
the same conclusion. A structure PASS before specs existed says nothing about current specs.
Use current quality status and current actual run reports, with remaining work/checkpoint.
