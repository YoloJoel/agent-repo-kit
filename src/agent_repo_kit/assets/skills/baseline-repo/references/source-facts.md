# Build source facts before writing promises

Read this before drafting a batch of current requirements and during both source-audit passes.
Complete each batch through facts, specification, assertion review and source recheck before
starting the next batch. Persist results in existing Baseline/contract/case sections and the
behavior inventory. Reuse these records; an extra ledger or a file per claim is unnecessary.

## Establish the current fact

For each observable branch, first write this row from actual code, with the spec hidden:

| Trigger and condition | Actual outcome and side effects | Decisive source and callers | Counterexample examined | Disposition | Assertion evidence or gap |
| --- | --- | --- | --- | --- | --- |

Keep a short actual expression, table entry or branch excerpt beside its precise source anchor.
Explain how the caller reaches it, including build selection, configuration and later overrides.
Before closing a clause, compare its input domain and guarantee with every mapped behavior row.
A row restricted to one default value cannot support a clause covering all values. Trace the
remaining inputs or state the narrower precondition and explicit unreviewed gap in the clause.
Use the row to write the clause and scenario. A fact still marked unknown or defect remains in
Baseline/the existing question ledger. Describe defects and their observable consequences;
an allocation size, a validator definition or a field name does not establish a safety guarantee.
Existing accepted promises retain their authority; record source conflicts for a real disposition.

Use these concrete checks for claims that commonly look plausible while reversing the code:

| Claim | Read and record before writing it |
| --- | --- |
| Resource/command set, identity or protocol literal | Copy values from the effective registration/dispatch/formatting path, in order. Inspect additions/removals, conditional registration and the unknown-input path. Reconcile listed count with actual entries. Keep enum/constants without callers as definition-only observations. |
| Limit, allowed interval or safe rejection | Trace input parsing, actual validator call, allocation, loop/index and error path. Check below/at/above the claimed boundary. Record a missing bound or unsafe index as a defect. A buffer size alone cannot support “supports up to N” or “rejects N+1”. |
| Integrity, acknowledgement, durability or cleanup | Trace the producer's actual value/write/send, the consumer's comparison/commit/read and the failure outcome. Locate the enforcement or acknowledgement event. A reserved/zero/ignored field, asynchronous call or success return alone cannot establish the guarantee. |
| Timer, timeout, cache expiry or window | Record who wakes the work, clock/unit, threshold predicate, reset order and behavior without a subsequent event. Distinguish a scheduled timer from request-triggered or lazy processing. Inspect empty and repeated windows and the triggering input's membership. |
| Precedence or conditional update | Write the truth table from the actual ordered branches. Include both conditions true, neither true, disabled/default paths and strict versus truthy flag comparisons. Follow resulting writes/outputs. |
| Startup, shutdown, process count or shared storage | Read launch scripts and all registration/override sites in execution order. Distinguish persistent workers, wrapper and one-shot children. Resolve the final signal/callback owner. Search actual table/file writers and readers, including common helpers. |

For an important guarantee, write a concrete falsification attempt: the input/state/configuration,
the exact branch it reaches and the result that would contradict the claim. “Reviewed errors” or
“no counterexample found” without that path is unfinished analysis. Use static proof where source
is decisive; use a safe native probe when practical. Keep unsafe experiments and absent external
systems as explicit verification limits. Do not repair business code to make an observed fact fit.

For a claim about the final outcome of a selectable handler, default, or writer, start at the
actual launch/operation entry for the claimed configuration. Write down each assignment or
installation in execution order, which one remains effective, and the observable result after
control returns or transfers. Look for a second owner, later override or indirect writer even if
the first definition appears to explain the whole outcome. For an exclusivity claim, bound the
resource/key space and reconcile the other actual writers. For recovery, trace the counters,
threshold and action together. Document a reproducible failure as an observed defect if appropriate.

Choose a stimulus under which the first plausible interpretation and the final effective path
predict different outputs. Record the competing outcomes in the existing challenge and acceptance
records. Use an available safe test/probe on the in-scope sample when practical. When neither
the static path nor an observation establishes the result, leave the claim open. In the current
Spec, give the reader the deciding condition/value and local effect needed for an assertion.

## Close the discovery gaps

Before drafting the first batch, inspect executable entry points, callback/dispatch registrations,
config subscribers, publishers/consumers, worker/timer creation, storage access and launch/build
assembly. Seed the whole-scope behavior checklist from these independently of spec headings.
In each batch follow their cross-process/module peers and update the same checklist. Reconcile
unowned registrations, notifications, lifecycle events, data paths and background effects.

An excluded external implementation can still leave an in-scope boundary: document the actual
request, response/error handling and observable local effect while leaving its internals unknown.
Preserve explicit user exclusions. Give each exclusion its reason and remaining local obligation;
ordinary batches do not redefine whole-repository scope. Count unreviewed behavior separately.

## Review the test's observation

For each normative clause and meaningful scenario identify the actual test stimulus, reached
branch, observed result/state and assertion. Ask which specific wrong behavior would fail that
assertion. A generic initialization/success assertion cannot cover a command enumeration,
shutdown effect, bound or temporal rule unless its stimulus reaches and observes that behavior.
Several clauses sharing a requirement need their own evidence and explicit uncovered scenarios.

Keep `Verification: automated` as the intended method where appropriate and report missing
assertions as gaps. Do not attach unrelated passing tests or relabel manual to clear the gate.
Separate requirements, reviewed assertions, selected/executed cases, failures, timeouts and
not-run cases. Record the actual check command/filter and timeout; a hung suite leaves the
remaining cases not run. Test counts and declaration-status PASS do not measure semantic coverage.

## Recheck against the source

Audit literal/enumeration/limit/timing/precedence/lifecycle claims using the same table, rebuilt
from the effective source path. Compare every clause and concrete scenario to these facts.
Record contradictions before editing, then reopen the affected paths and adjacent branches.
Review assertions separately. Preserve unresolved issues and partial scope in the final result.

When reporting, include the facts checked, confirmed errors/omissions, unreviewed scope and
actual execution separately. Source analysis can support a current description while behavioral
verification remains pending. Fixed syntax, hashes and audit records do not close an unresolved
source contradiction or certify an unseen repository.
