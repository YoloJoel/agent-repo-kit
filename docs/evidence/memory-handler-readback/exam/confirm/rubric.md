# Sealed readback scoring rubric

Each set has six questions, with three named observation fields apiece. Mark each field independently against the matching key. Encode the answer as a prediction from the supplied candidate specification. Evidence about how the implementation works belongs in the key. A reader must not run the stimuli, browse the source, look at the keys or consult the other candidate.

## Observation field decisions

Apply the following precedence separately to each field.

1. **Contradicted (C).** A definite predicted value or behavior conflicts with an expected component, including a wrong exception, destination, record identity, count, order, or state. A definite sequence presented as complete contradicts the key if it omits a required element or includes an extra one. This takes precedence over any other correct component within the field.
2. **Full (F).** The answer unambiguously predicts every requested component of the field. Exact semantic equivalents earn full credit. Object labels stand for identity only where the code itself uses an identity observation. Count a logically entailed prediction even if the answer words it differently.
3. **Partial (P).** The answer predicts at least one correct, testable component but explicitly leaves or plainly does not address another component. There are no contradicted components. For example, naming a delivery recipient can determine one component even when the final buffer is unresolved. An explicitly incomplete sequence can earn partial credit when its stated portion is correct and given the right ordering qualification.
4. **Unspecified (U).** No requested component is determined. This includes a bare “unknown,” mutually exclusive possibilities with no definite common component, or a restatement of the setup alone. Inapplicable invented details are ignored unless they contradict a requested observation.

A qualifying conditional prediction earns credit for the components shared by all alternatives it asserts. Merely listing permutations as alternatives does not determine an order. Boolean false, the integer zero and a null return are distinct as observable types. Object field order in JSON is immaterial. Sequence order and repetitions matter. An unambiguous prediction in prose can answer multiple fields. Assign a shared sentence to each field it actually answers.

## Report

The primary result is the per-field F/P/C/U tally out of 18. A secondary field score is (F + 0.5 × P) / 18. Do not merge unspecified with contradicted when reporting counts. Also assign a whole-question status with this fixed order: any C field makes the question C, three F fields make it F, three U fields make it U, and every remaining mix makes it P. Preserve the component marks when a mixed question receives C. Missing questions get U on all fields. Do not change weights according to perceived question difficulty or family.

Keys provide the exact observed mapping, decisive original-source anchors and an explanation of each field. Those explanations are for checking equivocal prose, not additional required answers. Score only the requested public observations. No credit is added for knowledge of implementation details absent from the observations. When auditing a specification-only reading, flag an asserted result unsupported by its cited text separately; do not silently reclassify an unsupported assertion as textually entailed. Keep behavior accuracy and support in the specification distinguishable.

## Reproduction and integrity

Run all questions with `/usr/bin/python3 -I -B probe.py`. Pass individual IDs as arguments to run them independently. Each starts with a new fixture namespace. The probe checks interpreter identity, version, loaded module paths and both module source digests before evaluating stimuli. It serializes the requested results before interpreter teardown. Run `sha256sum -c SHA256SUMS` from this directory to verify the sealed inputs, keys, runner and rubric. The manifest excludes itself.
