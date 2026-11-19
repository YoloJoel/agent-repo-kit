# Can a reader derive a correct acceptance case from the Spec?

Start with two separate copies of the same source revision and the same requested scope.
Generate each candidate from source without giving its author another candidate, answers, or
the evaluator's observations. Keep the index and cross-cutting constraints in scope.
Freeze the candidates. Assign anonymous labels and use the same model/settings and budget
for both readings where possible. Record any difference.

## Unprompted case design

Before showing any test questions, give a reader only one candidate's current Spec, including
referenced current requirements. For each important rule, have the reader produce the initial
state, input and falsifiable expected output or state change, quoting the supporting clause.
Freeze those cases. A reader missing an input, boundary or observable result marks the gap.
Use a fresh context for the other candidate. Have a source reviewer check both sets against
effective code, then map actual assertions and any executed cases separately. Keep the source
fact denominator independent of both candidates. Split complete, partial and omitted facts;
report correct, partial, contradictory and unresolved claims separately.

## Fixed public sample

The following diagnostic uses the public control-hub example on Linux with make, cc and
Python. Give the reader only the candidate Spec and the output of the first command. Withhold
source, tests, probe code, example answers and scoring output until the answers are frozen.
For every ID return either a predicted JSON value and an exact supporting quote, or
`{"status":"unclear","missing":"which detail the Spec leaves open"}`.
Use `{"status":"predicted","value":42,"quote":"exact supporting text"}` for a prediction.

```sh
python tools/score_spec_readback.py --questions
python tools/score_spec_readback.py --spec candidate.md --answers frozen-answers.json --output run-a
```

Keep the full rows and native logs. Check that each quote really entails the predicted answer;
the scorer checks text presence and compares values with actual sample output. The question
already supplies the stimulus, so this measures prediction given an input. It does not measure
spontaneous case design or general source coverage. The reader should mark an ambiguity even
if they happen to know the expected result.

The deliberately flawed public example makes the scoring procedure reproducible:

```sh
python tools/score_spec_readback.py --spec docs/evidence/source-facts-review/spec.md --answers docs/evidence/source-facts-review/example-answers.json --output run-seeded
```

Its eight supplied example answers should produce one match, two contradictions and five unclear
results. They are authored controls. Generating a candidate with an installed plugin and scoring
a fresh reader's answers is a separate experiment. Do not tune prompts against private answers or
report the controls as generated Spec quality.
