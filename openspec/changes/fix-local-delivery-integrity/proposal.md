# Close the observed local delivery gaps

## Why

The 0.2.0 audit reproduced three false completion results: unrecognized configuration input,
lost current requirement coverage while remaining tests passed, and stale current explanations.
Scripted native-tool qualification did not establish full model-driven onboarding quality.

## What Changes

- Conservatively classify unknown runtime inputs; allow explicit runtime-document paths.
- Validate all effective requirements and preserve their verification type and delivery phase.
- Require affected knowledge to be rechecked or explicitly retired before delivery.
- Add counterexample/recovery tests and independently exercise installed Skills with actual tasks.

## Impact

Update `src/`, `skills/`, `tests/`, `tools/`, `docs/` and native package version metadata.
No remote service or CI becomes necessary for consumer repositories. Native OpenSpec and
other development tools retain ownership of their lifecycle.
