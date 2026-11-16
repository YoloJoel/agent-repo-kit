# Source-first audit verification

Conclusion: PENDING
Stage: local-verification PASS; final-head CI pending.

Source and actual built/installed 0.2.3 wheel: 130 tests each PASS. Seven new tests reject
missing reread passes, dropped findings/scoped artifacts, invalid evidence or dispositions,
newly discovered issues falsely closed, and stale source/artifact/report inputs; legitimate
rechecks preserve immutable snapshots. Actual vendored CLI also executed.
Native generated assets match and both Skill format checks PASS.

A fresh model received existing source plus generated artifacts containing three syntactically
valid semantic contradictions, without the diagnosis/expected answer. It reopened source,
recorded the first findings before correction and performed a separate post-fix source pass.
All three were detected: two fact errors corrected; accepted sorting-spec/source conflict
retained as open, not silently rewritten. Ten actual probes passed, explicitly without
standing automated mappings. Business source and prior raw history stayed unchanged.
Parent reviewed actual source/report/artifacts and revalidated the original two-pass report
with the exact final source/wheel runtime in an isolated copy: PENDING only for the open
conflict. Source mutation additionally produced stale PENDING; restoration removed staleness
without hiding the open conflict. Extra delivery/checkpoint calls without a Change ID were
invalid, honestly recorded and not described as business checks.

Evidence: docs/evidence/source-first-audit-use.json. This small Linux/Python example is not
proof of full-project semantic completeness or independent review; actual review mode was
same-agent-separate-pass. No zero-defect/actual-cognition certification is claimed.
