# Baseline specification handoff verification

Conclusion: PENDING
Stage: local-verification PASS; final PR checks pending.

- Source `PYTHONPATH=src python -m unittest discover -s tests -v`: 123 PASS.
- Actual built/installed 0.2.2 wheel, same suite via installed package: 123 PASS.
- `python tools/build_native.py --check`: PASS; both native Skill quick validations PASS.
- Five handoff tests cover inventory/contract-only incompletion, mapped spec authoring,
  absent verification and its recovery, missing links/deleted requirements, source/decision
  freshness, and the actual vendored CLI. Existing 118 tests remain passing.
- Fresh model invocation on source-only catalog produced four current requirements/eight
  scenarios, contract/cases/preservation reasoning, with unchanged business source.
- Parent reviewed actual prose and reran spec-status on the exact source/wheel/vendored
  runtime: specification PASS, verification PENDING for four unmapped requirements.
- Ten actual one-off behavior probes passed, without being passed off as persistent tests.

Actual artifacts, hashes and outputs: docs/evidence/baseline-spec-use.json.
No claim of universal semantic completeness, native OpenSpec CLI setup or live Hook trust.
