# Verification: fix-local-delivery-integrity

Conclusion: PENDING

Stage: local-verification PASS; publication/final-head CI/merge PENDING.

The original 0.2.0 counterexamples were executed before implementation; its original 102 tests
passed despite those gaps. The final runtime is SHA256
`f670eee08aed8bed9188207cf7551ae07505d73b8795c1dcdd0153a1e0efed7f`.

- Source: `PYTHONPATH=src python -m unittest discover -s tests -v` — 118 PASS.
- Installed final wheel: the same suite against installed package — 118 PASS; runtime matches source.
- Integrity subset: 16 counterexample, recovery and compatibility cases PASS; actual Node ESM executed.
- `python tools/build_native.py --check` and both native Skill format checks PASS.
- Native OpenSpec 2.0.0 two-change create/validate/archive lifecycle PASS. A preserved-behavior
  mutation failed regression while targets passed; restoration returned PASS.
- Independent real model tasks: new project 28 PASS, source-only existing cachetools 434 PASS
  (416 unchanged originals + 18 targets), fresh daily native-OpenSpec task 35 PASS (28 + 7).
- Parent rechecks used the exact final runtime in isolated workspaces. Existing duplicate-key
  mutation and daily idempotency mutation both failed overall; restoring bytes returned PASS.

See `docs/repairs/local-delivery-0.2.1.md` and its linked eight evidence JSON files for actual
commands/results, task commits, content review and limits. The existing/daily original workspaces
and historical evidence were preserved. Hook configuration is not live trusted-host verification.

PR #9 exists as a draft at earlier head `23278054ee897d510954ba32ccd044c9aafec31f` with seven
successful checks. That head predates the final supplements. Automatic approval twice rejected
uploading the supplement, most recently because explicit authorization for this exact payload and
destination was missing after the prior denial. No later remote mutation was attempted.
Fresh explicit user authorization was subsequently received ("提pr并合入"). Final-head CI and merge remain pending publication; older CI is not final evidence.
