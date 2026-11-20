# Reopen source after generation

Read `source-facts.md` and rebuild its factual rows from effective code during each pass.
Audit every literal/enum, validation/limit, safety, timer/expiry, precedence and lifecycle claim
using the applicable checks there. Check each clause/scenario's actual test stimulus and
observation; a generic passing assertion is not coverage for unrelated behavior.

This is mandatory after baseline/spec drafting by default; a format check is not a substitute.
Honor limited scope and report uninspected dependencies. Reuse existing native audit formats
for prose if present; the JSON record below is a verification attachment, not a second issue
or decision authority. Reference existing issue IDs and the single decision ledger.

## First pass: derive coverage again from source

Set aside the generated outline. Reopen actual entry points, callers, configuration, branch
conditions, validation order, state ownership, success/failure returns, side effects, retries,
ordering/concurrency, cleanup and recovery. Follow reachable helpers and cross-module paths;
do not stop at entry signatures or trust earlier summaries. Inventory meaningful branches and
record concrete file/line evidence and what was checked, not just filenames/hashes.

Check both directions:
- Source to artifacts: which observable behaviors, exception paths or constraints are missing
  from module explanations/contracts/cases/current specs? Is an exclusion justified?
- Artifacts to source: can each important claim, scenario, diagram and expected result be
  substantiated? Check unsupported guarantees, reversed conditions, incorrect defaults,
  lost side effects and planned behavior passed off as current behavior. Review test assertions
  where available; test counts and Requirement IDs do not prove coverage.

Write actual findings with stable IDs, source evidence, affected artifacts and impact BEFORE
editing. If none are found, explicitly record an empty list and actual inspected coverage;
never manufacture a problem to satisfy the report. Persist the first pass before proceeding.

## Fix, then recheck from source

Correct generated statements/omissions, cases and mappings when source evidence is clear.
For rejected findings record why with evidence. For a conflict with accepted specs/decisions,
record the discrepancy and actual owner decision needed; do not silently rewrite accepted
promises or business code. Refresh only affected knowledge declarations/promotions afterward.

Reopen source again in a separate post-fix pass. Rebuild the relevant branch checklist and
check every first-pass issue, affected assertions, neighboring error/side-effect paths and
cross-module effects. Do not merely reread the edited prose or rerun the checker. Retain
every first-pass ID as fixed/rejected/open with evidence-backed reasoning; add newly found
issues. Execute applicable checks and distinguish them from static analysis. Two meaningful
passes are the default. If a recheck discovers a correctable issue, persist it as open, make
the correction, then append another `source-recheck` to the same batch report. Reopen the
batch's declared sources and artifacts, trace the correction and neighboring cases, and carry
every prior finding ID forward. A new finding always starts open. Repeat only while there
is evidence-backed progress. If a recurring issue, missing evidence or a decision prevents
closure, retain it as open and checkpoint the remaining work.

Use an independent fresh reviewer if the environment supports one: provide raw source, task
scope and artifacts without the author's diagnosis. Otherwise perform the separate reread in
the same agent and state that mode. Do not demand user approval merely to run routine review.
Do not describe same-agent review or structural validation as independent semantic auditing.

## Record the actual passes

Write a JSON attachment under the mapped Baseline scope (for example source-audit.json):

```json
{
  "review_mode": "same-agent-separate-pass",
  "passes": [
    {
      "kind": "source-first",
      "sources": [{"path": "src/service.py", "evidence": "src/service.py:L1-L30", "checked": "Actual branch/flow details inspected"}],
      "artifacts": [{"path": "openspec/specs/service/spec.md", "checked": "Actual claims, omitted behaviors and scenarios checked"}],
      "findings": [{"id": "AUD-001", "issue": "Actual discrepancy", "evidence": "src/service.py:L12-L18", "status": "open"}]
    },
    {
      "kind": "source-recheck",
      "sources": [{"path": "src/service.py", "evidence": "src/service.py:L1-L30", "checked": "Post-fix branch/neighboring path reread details"}],
      "artifacts": [{"path": "openspec/specs/service/spec.md", "checked": "Fixed claim and adjacent scenarios rechecked"}],
      "findings": [{"id": "AUD-001", "issue": "Actual discrepancy", "evidence": "src/service.py:L12-L18", "status": "fixed", "resolution": "Actual correction and source-based recheck reasoning"}]
    }
  ]
}
```

Replace examples with real scope/observations. Every pass must include every selected source
and artifact. Include module explanations, contracts, cases, specs and relevant diagrams/decision
records; do not audit a token subset and claim all artifacts reviewed. Use [] when no findings.
Empty/binary inputs use path@sha256:<actual digest> and explicit limits. A new second-pass
finding that is not yet rechecked remains open, even if a later edit seems straightforward.
Use the actual review mode; record reviewer identity without inventing human approval.

Then run:

```text
ark baseline audit-record --report <audit.json> --files <actual source/config paths...> --artifacts <reviewed document/spec paths...> --reviewer <actual identity>
ark baseline audit-status --report <audit.json>
```

The record preserves an immutable report snapshot and binds final source/artifact/report hashes.
Missing records, open issues or subsequent byte changes stay PENDING. This checks declarations,
coverage and freshness, not that rereading really occurred or semantics are flawless. Run status,
validate, spec-status and actual project checks separately. Report audit scope/mode/findings,
specification state and actual execution independently before claiming onboarding complete.

## Required onboarding quality topics

Use artifact-quality.md for the acceptance criteria. Rebuild the capability map independently
from source directories/call paths and compare to current specs. Read each spec with Baseline
hidden: can concrete inputs/assertions/error and side-effect checks be written from the spec
alone? Open the source afterward to prove those details, not to excuse their omission from spec.
For each disputed prediction, identify the clauses and supplied inputs that determine it.
Check whether a different ordering, default or owner consistent with those clauses would
change the observation. If so, record the missing premise even when the prediction matches
execution. Distinguish assumptions made by an external test observer from rules owned by
the capability. Apply this check across clauses when one actor hands work or state to another.
Also review AGENTS as a project-specific entrance rather than a tool operation list. Include
AGENTS, .ai/project-entry.json, applicable OpenSpec config, current Baseline README, the capability
map and all claimed artifacts in audit scope. Discover contract files/references from disk, not
just the registry; an unregistered referenced contract cannot disappear from expected audit scope.
Record these actual checks in report.quality_checks, using one object per topic:
`{"topic":"project-entry|capability-coverage|spec-self-containment","status":"PASS|PENDING","checked":"Actual inspected scope, evidence and result"}`.
Each object uses one actual topic/status value, not the pipe-separated example. Mark quality
PENDING and record findings for omissions or unverifiable details. These are review declarations,
not machine semantic certification. After final audit registration and all edits run onboarding-status --record; do not equate a
selected spec's format/link PASS or an initial empty-spec run with whole-repository completion.

## Behavior-level closure

Use behavior-model.md for a source-derived denominator, every normative clause, effective
branch/use/effect chains, unresolved evidence, attempted counterexamples and canonical contract
consistency across specs. Verify tests at actual assertions, not REQ comments. Audit the final
behavior inventory in both passes. Call baseline behavior-status separately; audit records
and strict format validation cannot replace this semantic work. A new source/spec conflict
takes priority over adding IDs or polishing format. Preserve actual reviewer independence.
