# Fresh synthetic source-audit regression

These deliberately inconsistent spec and mapping inputs were authored for a new bounded,
read-only audit regression. They are not output from either historical onboarding task.
The reviewer received exact copies of `examples/control-hub/hub.c`, `hub.h`, `main.c`,
`Makefile` and `tests/test_hub.py`, plus the two inputs here. The fixture README and native
probe expectations were not included. All seven input hashes remained unchanged.

`task.txt` preserves the actual assignment and follow-up. `source-review.md` is the raw final
reviewer report, including its effective-path analysis, actual observations and limits.
The final candidate Skill identified the two seeded contradictions, irrelevant assertions
and the clause/evidence input-domain mismatch. The audited synthetic project remains PENDING;
its defects were intentionally left open. The report is not a semantic completion certificate.

To reconstruct the input, copy those five fixture files preserving their relative paths,
then add `spec.md` and `review-mapping.json` from here. The reviewer used the final candidate
`skills/baseline-repo/SKILL.md` and its referenced source-review instructions. This audit does
not replace an ordinary from-zero onboarding task or recover expired historical outputs.
