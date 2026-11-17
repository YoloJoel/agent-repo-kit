# Native engineering verification and reproducibility

Read when establishing commands or interpreting test failures. Use `engineering-status` for
read-only source/test stack ranges and mapped command availability. It does not test external
services, install tools or prove runtime readiness. Configure actual roots, including nonstandard
C/C++ test directories and separate Java modules. Unknown stacks use the same argv/evidence
protocol; do not guess support from a file extension.

| Stack | Inspect before confirming commands | Typical native execution (adapt, do not copy blindly) |
| --- | --- | --- |
| C/C++ | CMake/Make targets, toolchain, features, ABI, native libraries, gtest/CTest setup, mocks | Configure/build existing targets; run ctest or actual test binary with recorded filters |
| Java | Wrapper/Maven/Gradle versions, modules, profiles, JDK, test plugins, skipped tests | Existing wrapper verify/test command; distinguish package/compile from tests |
| Python | Environment, source import roots, unittest/pytest conventions and dependencies | Actual project's native test command |

Persist reproduction evidence with each actual run: source commit AND dirty-source hashes,
exact argv/cwd, compiler/JDK/build-tool versions, OS/architecture, flags/features, selected modules,
dependency conditions, generated reports and exit/log results. Avoid dumping secrets/environment
credentials. If a local WSL/toolchain patch is needed, save its exact diff/hash and reason outside
immutable source snapshots; say whether the tested inputs include it. A clean-repo success cannot
be claimed from a patched worktree. Repository portability changes are a separate scoped change.

Distinguish PASS, actual test FAIL, crash/signal, NOT_RUN/unavailable service and filtered/skipped
scope. Do not relabel SIGILL as harmless because the test existed previously; investigate compiler,
architecture, mock framework and actual implementation, retaining uncertainty. Redis/DB absence
blocks dependent cases; it is neither a business pass nor evidence all remaining failures are
environmental. A filtered rerun is a different scope, not the full suite.

Tie assertions to actual checks with behavior-model.md. If interception fails, inspect a lower
boundary, adapter seam, transport harness or integration replay. Never weaken production behavior,
remove meaningful assertions or switch to manual merely to turn the result green. A justified
method change must retain history, alternatives, unverified scope and actual review. Manual tests
still need reproducible steps/expected output and actual execution evidence before verification.

Do not require all historical defects/tests to be repaired for a knowledge-only onboarding.
Report knowledge review, behavior evidence, build, selected tests, full-suite result and outstanding
debt independently. For later development, execute original affected behavior before risky changes,
then preserved regression and intended acceptance using the existing behavior-plan workflow.

Use the same AGENTS/standard/policy/checker through Claude, Codex, OpenCode or direct conversation.
Initialization and later upgrades preserve mappings/history and merge manual conflicts explicitly.
Hook trust/loading is host-owned; no native OpenCode lifecycle plugin is asserted. A manual Agent
can read the installed Skill and repository instructions and run the vendored Python entry.
