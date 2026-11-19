# Verify report — workflow contract pilot

Stage: local pilot candidate. Scope is the repository runtime, generated resources and synthetic
consumer exercises. The actual model's behavior on private projects remains to be evaluated.

| Observation | Result |
| --- | --- |
| Source unit tests; installed wheel unit tests (Python 3.12, Linux) | 208 passed in each suite. Seven focused cases exercise the new Change contract. |
| Source vs native resources | build_native.py --check passed. |
| Published helper layouts (0.3.1, 0.3.2) upgraded to 0.4.0-rc.1 in separate consumer copies | Both kept human entry text and uncommitted source bytes. Repeat upgrades reported zero changed assets. Vendored runtime matched installed Skill engine bytes. |
| New-repository delivery, one SQLite feature | Code alone and external draft layout alone both failed ownership checks. Proposal and tasks alone stayed PENDING. A scoped persistence rule kept delivery PENDING with a delta but missing design and decision. Positive accepted-decision and regression cases passed. |
| Native OpenSpec 2.0.0 in a synthetic consumer | Two actual validations and archives; an unfinished referenced plan was rejected by the vendored CLI, the completed plan passed. Deliberately breaking established behavior failed the regression check while the new acceptance check passed; restored implementation passed. |
| Native C source-fact probe | PASS within the fixture's observed paths. |
| Live developer sessions with Superpowers, direct prompts and a private repository | Awaiting local feedback. The external-plan fixture exercises its layout, content and archive handoff. |

The version is a pre-release. Inspect the candidate PR for the current remote OS/installer jobs.
Production dependency checks and protected-branch configuration are outside these local results.
