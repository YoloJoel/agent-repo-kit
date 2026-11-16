# Automatic whole-repository onboarding

## Why
Bare initialization could stop after scaffolding and ask for the first vertical slice or a
specification tool/path choice. The default whole-repository goal and automatic continuation
were not explicit; the usage guide also told users to initialize native tools separately.

## What Changes
Make default scope and batch continuation explicit in both installed workflows. Resolve existing
spec authority before writes, use the OpenSpec layout when absent, and automatically initialize
compatible installed native tooling without overwriting human assets. An unavailable CLI is a
separate NOT_RUN result and does not block file-based specs.

## Impact
Version 0.2.5; workflow/reference sources, regenerated native bundles and usage documentation.
Forward testing also reproduced generated project sections disappearing after an outside note;
preserve the existing generated layout on refresh and cover this with a focused regression.
Preserve explicit limited tasks, existing mappings/IDs, human content and actual pending gaps.
No new mandatory dependency, package installation, hosted CI or delivery Change for Baseline.
