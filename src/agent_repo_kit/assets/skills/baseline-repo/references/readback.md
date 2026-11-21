# Freeze predictions before source adjudication

1. Create questions containing only `id` and concrete `stimulus`, including every recorded
   source_case and a case for each material Scenario/alternative. Write `{"questions":[...]}`.
   Run `baseline readback-open --id <round-id> --document <questions.json> --reviewer <examiner>`.
   Default mode is `same-agent-separate-pass`. Use `--mode separate-context-attested` only when
   that actually occurred; different names and files cannot establish isolated model contexts.
2. Give the reader only the returned reader.json (questions and frozen current Specs, without
   Baseline link lines). Do not show source outcomes, tests, evidence or earlier answers. Inspect
   referenced current requirements as part of the frozen input. This is a process boundary,
   not an OS sandbox. Record unavoidable context leakage in the audit/quality trial.
3. The reader writes `{"answers":[{"id":"...","status":"predicted","expected":false,
   "premises":[{"path":"openspec/specs/.../spec.md","quote":"exact deciding text"}]}]}`.
   Quote the deciding WHEN/precondition and the outcome; citing an output word is insufficient.
   If multiple outputs satisfy the Spec, use `status: ambiguous` and describe `missing` instead
   of guessing. Freeze with `baseline readback-predict --id ... --document ... --reviewer ...`.
4. Reopen source and trace the same stimulus to the actual observable endpoint. Record answers
   with id, status (entailed/ambiguous/contradicted/source-unknown), reason, observed typed output,
   and evidence anchors (path/reference/role/explains). An entailed judgment requires BOTH a
   sufficient textual rule and source agreement. A correct guess is still ambiguous. Use
   `baseline readback-judge --id ... --document ... --reviewer ...`.
5. Inspect `baseline readback-status`. A stage cannot be overwritten. If the Spec/source changes,
   open a new round after repairing it. Old rounds remain available with `--id`; the newest opened
   round is active, so old stale rounds neither disappear nor permanently block a new completed one.
   Missing source-case questions, missing predictions and unresolved judgments stay pending.

For behavior-inventory acceptance_cases, retain `premises` as exact strings in that requirement
and bind each covered Scenario with `{name, sha256}` from the complete Scenario block (trimmed,
UTF-8 SHA256). `spec_scenarios` is the reference implementation; changing WHEN/THEN/table content
invalidates the binding. These links prevent stale/omitted reviews; they do not mechanically
prove natural-language entailment. The frozen readback and actual reviewer remain necessary.

Do not treat status PASS as semantic certification or model-isolation proof. Product evaluation
separately compares actual manual/Kit runs on an independent denominator, frozen stages and costs.
