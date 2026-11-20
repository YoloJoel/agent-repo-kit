# Can a reader predict a buffered handoff from the current Spec?

The specimen is the single-threaded behavior of CPython 3.13.5 logging.handlers.MemoryHandler, its directly relevant inherited methods and its caller-provided target. Independent readers received the stimulus, the observer definitions and one frozen current Spec. An examiner executed each probe on a pinned Debian interpreter before scoring. The study excludes global shutdown, garbage collection, concurrency, and unrelated handlers.

## Read the evidence

- `exam/` contains sets A and B, question-wise observations, the scoring rubric, source anchors and a probe. `exam/confirm/`, `exam/final/` and `exam/exception/` contain sets C, D and E. Their SHA256SUMS files were frozen independently of the candidates.
- `candidates/` holds each English current Spec. `answers/` holds the readers’ frozen values, partial predictions, requirement IDs and quotes. `audits/` contains source discovery, source rechecks and separate adjudication of answer accuracy and textual support. Candidate confidence and a correct guess do not establish entailment.
- `runs.json` maps the actual candidate/suite pairs to their evidence. A field marked F agrees completely with the observed behavior, P is partially determined, C contradicts the observation and U is unspecified. Per-question scoring and handling of partial answers follow the sealed rubric. The field-level contract_support column grants the fixture’s ordinary observer conventions. The stricter support column preserves missing premises in the question itself.

Run from this directory:

```sh
python3 verify.py
python3 verify.py --execute
```

The first command reconstructs the results from the frozen records. The second repeats the instrumented calls using /usr/bin/python3 CPython 3.13.5 and verifies the byte hashes and module locations checked by the probe. The public source hashes are dc42e5cf19a2dd03bd95ed3600803effa9c5f107927ab5f66cacf3eebcfd9a47 for logging/__init__.py and 464980a72ce4c0ca1e6a6724a9760f5e101475a4e347329272ba6d2c4b39dffd for logging/handlers.py.

## Recorded outcomes

Each compared cell gives full field matches / fields, followed by fields entailed under the observer conventions. The other predicted fields in C and D are partial or unspecified; their frozen decisions remain in the per-field records.

| Suite | Base | Regenerated | Composition recheck | Exception recheck |
|---|---|---|---|---|
| A | 18/18, 14/18 | 18/18, 17/18 | 18/18, 18/18 | 18/18, 18/18 |
| B | 18/18, 11/18 | 18/18, 18/18 | 18/18, 18/18 | 18/18, 18/18 |
| C | 12/18, 12/18 | 16/18, 16/18 | 18/18, 18/18 | 18/18, 18/18 |
| D | Not tested | 3/9, 3/9 | 6/9, 6/9 | 9/9, 9/9 |
| E | Not tested | Not tested | Not tested | 3/3, 3/3 |

On the last frozen Spec the 22 questions yielded 66 complete, type-correct matches. C–E specify their own observer semantics and account for 30 fields. The 36 legacy A/B fields retain the strict fixture qualifications in their audit. All 349 final reader quote occurrences occur in the candidate. Some local field citations omit a supporting clause available elsewhere in the Spec, including the level table for B1.

## Comparison design

The base author used the native Skill from PR #25, 7873ae931b53f83569411e15991a9e0eb2a55663. The revised author used the same source and task in a newly initialized project with the named-input change, tree c05dbdb18b495e994ceaa71621fd650278965eac. Each recorded a source-derived map before drafting. Later post-fix source rechecks extended the revised Spec without replacing its requirement IDs. Separate role contexts used scoped directories on a shared filesystem. No hosted plugin session was attested.

| Candidate | How it was produced | Suites read |
|---|---|---|
| base | Independent source-to-Spec generation on PR #25 | A, B, C |
| revised | Independent generation with named inputs grounded in their effective order | A, B, C, D |
| final | Scoped post-fix source recheck for an ordinary component as a receiver and effects during configuration | A, B, C, D |
| closure | Scoped follow-up for exceptions in caller-provided admission checks, before delivery starts | A, B, C, D, E |

A/B and their source keys preceded the first readings. C, D and E are distinct, targeted holdouts produced after identifying an ambiguity in the preceding round. Authors had no access to any questions or keys. Post-fix reviewers received a description of the issue class. Later readers in this run did not browse the evidence tree. Once published, these cases can serve as regression fixtures. New blind studies require new undisclosed samples.

The A/B readers' 36 original predictions all matched execution. With fixture observer conventions, only 25 followed fully from the base Spec. Ten fields depended on missing named-level order and one depended on whether installing a formatter could invoke it. A/B use imported helpers for LogRecords and labels. The strict literal adjudications preserve those assumptions separately. C, D and E supply their observer semantics. Follow-ups distinguish a receiving MemoryHandler’s truth value, a callback during setup or use, and exceptions before the first delivery versus after a receiver has already performed an effect.

The negative control removed REQ-MH-002 and inserted an immediate-forwarding promise under REQ-MH-003 that contradicted REQ-MH-004. A separate reader located both the missing filter behavior (A3) and the conflicting retarget rules (A2). It also spotted the conflict at A5 although an immediately following flush makes the final states converge. The patch, frozen predictions and predeclared criteria are preserved separately from candidate scores.

The probes check their stated cases. The ordinary Kit source and clean-wheel suites passed 221 tests each, and the generated native resources passed parity checking. The consumer’s automated assertion mappings for its seven requirements remain pending. This trial contains only public source behavior and cannot establish coverage of an entire repository or performance on a different model or real business module.
