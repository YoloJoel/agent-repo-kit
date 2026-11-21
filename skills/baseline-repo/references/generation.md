# Generate from observable decisions

Apply this to the active capability slice, then continue `baseline next`. Its purpose is to
change what gets discovered and written, not merely add declarations after drafting.

1. Run `baseline discover` before reading the generated Spec outline. Review executable roots
   (launch, registration, scheduling, configuration consumption) and work backwards from each
   external response, durable write, message consumer or state reader. Reconcile the two views.
   Python discovery supplies branch alternatives and import candidates; C/C++/Java/JS scans are
   lexical prompts only. An empty candidate list never waives this traversal.
2. For each candidate, find the active registration/caller and final implementation. Inspect later
   assignments, inherited overrides, handler replacement, build selection and disabled code.
   Keep an unreachable implementation as baseline/excluded with evidence, never a current promise.
   For every branch affecting an observable result, choose the closest input taking the opposite
   branch; include equality at thresholds and overlapping conditions for precedence. Add those
   stimuli as source_cases before choosing Spec clauses. One sampled failure does not cover success.
3. Record the actual configuration/build/deployment combination in the unit condition and source
   evidence. Group equivalent variants only after reading the consumers. A value declared in a
   header is not its effective value. Configuration, registration and consumer files belong in
   the unit's evidence so their edits invalidate it. Unavailable variants stay unknown.
4. Follow producer → state owner → final consumer for an end-to-end promise. Name the observer
   and the last proven event in the outcome: local enqueue, write completion, remote acknowledgment
   or durable state visible after restart. Stop at the available evidence boundary. A transport
   success alone cannot establish delivery or persistence. Record external sources using explicit
   aliases with `external record` when local snapshots are available; otherwise retain the gap.
5. Select current promises, observed baseline facts and defects separately. Preserve accepted
   requirements and report implementation conflicts. Never promote a defect to make current
   source consistent, and never drop the whole capability because one variant is uncertain.
6. Choose a Spec boundary around one cohesive caller-visible contract. Keep shared error/status/
   configuration rules in one current requirement and reference it from related requirements.
   Avoid a directory/function catalog and avoid combining alternatives with different outputs into
   a vague requirement. A reader should be able to derive each expected result without Baseline.
7. Maintain `contract_catalog` in the behavior inventory for genuinely shared facts. Keys identify
   the same protocol/state/field, aliases map actual existing terms, and condition mappings identify
   equivalent applicability. Do not equate legitimately different modes. Example:

   ```json
   {"contract_catalog":{"delivery.retries":{"aliases":["publish.retries"],
     "conditions":{"send current synchronous path":"sync","synchronous send":"sync"}}}}
   ```

   The checker compares declared aliases and conditions; the reviewer must discover missing aliases
   and semantic conflicts. A catalog is not automatic synonym inference.
8. Write deciding conditions, default/effective values, units, order, error outcomes and relevant
   side effects in the current Spec. Keep source locations and findings in evidence. Derive indexes
   and navigation from that evidence (`explain`, `baseline next`, `index-refresh`), rather than copying
   every fact into every document. Existing useful prose and authoritative assets remain intact.
9. Independently re-open source and attempt a counterexample for each high-risk promise. Include
   unregistered/overridden handlers, ignored configuration, producer success with consumer failure,
   restart/replay and branch complements. Fix drafts, retain accepted conflicts and preserve the
   original findings. The same author's self-check is not an independent evaluation.

Discovery reconciliation document: `schema_version: 1`, `candidates` with scanner `id`,
`source_sha256`, `disposition` (specified/baseline/excluded), and a concrete `reason`.
Specified rows also name current `requirements` and registered `source_cases` IDs. For each
scanner limitation, `source_reviews[path]` records `source_sha256`, actual `checked` work,
remaining `limitations`, and `reviewer`. Missing or stale rows stay pending. Status counts measure
candidate reconciliation, not exhaustive behavior coverage.
