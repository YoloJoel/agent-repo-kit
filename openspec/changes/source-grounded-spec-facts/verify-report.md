# Verification

Stage: final local implementation/distribution qualification
Conclusion: PASS for executed local checks and all eight implementation-head CI jobs. Final PR-head checks remain a merge condition.

- Final source suite: 189 tests PASS.
- Built and installed 0.3.1 wheel: 189 tests PASS; packaged source-facts resource matches source.
- Generated native assets: `python tools/build_native.py --check` PASS; `git diff --check` PASS.
- Installed 0.3.0 initializer upgraded the consumer to 0.3.1, preserving its human AGENTS text.
  A repeated upgrade reported no changed files; the consumer resource matches the release source.
- Linux C probes: original five tests, effective facts, changed-rule/original-test counterexample
  and restored tests PASS. Interrupted-command regressions retain failure/partial observations.

The before/after isolated onboarding tasks produced mostly correct source facts in both versions.
The revised candidate still had a clause/evidence input-domain mismatch, prompting an explicit
alignment rule in the final resource. Raw task artifacts expired, so their surviving summaries
are historical context and cannot establish reproducible comparative improvement.
The final fresh source-audit regression is recorded separately with its actual inputs and report.

See `docs/evidence/source-facts-use.json` and `docs/repairs/source-facts-0.3.1.md`.
These checks do not certify private-project behavior, the user's DeepSeek runner, complete
production dependencies or universal semantic correctness. Workflow review and actual execution
remain distinct from runtime declaration consistency checks.

Published implementation head `d3fd0bf300de7f69fbe84a192ee733262e472da7`: all eight
[CI jobs passed](https://github.com/YoloJoel/agent-repo-kit/actions/runs/44293329166), including
Linux/Windows/macOS on Python 3.11/3.13, native installers/OpenSpec and actual native probes.
This final evidence-only commit does not change the tested runtime or Skill resources.
The final PR and main-branch reruns report their own actual revisions and outcomes.
