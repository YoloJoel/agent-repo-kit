# Architecture

The product is a native Claude plugin plus standard standalone Skill folders, with an
optional Python developer distribution. Project initialization vendors the same runtime/
resources into a consumer, so agent rules, direct CLI and CI share behavior.
The single self-contained runtime is deliberate for a dependency-free consumer installation;
tests exercise boundaries through disposable repositories and actual subprocesses.

| Layer | Owns | Does not establish |
| --- | --- | --- |
| Skills | Semantic inspection, design, meaningful tests, decisions and file synchronization | Deterministic automatic truth |
| AGENTS/engineering standard | Persistent task routing and completion protocol | Universal model compliance |
| Policy/templates | Machine configuration and delivery structure | Correctness merely by filling headings |
| Runtime | Inventory, references, scope, freshness, real check execution and archive conditions | Complete semantic equivalence |
| Hook adapters | Runtime-specific event JSON and bounded feedback | Every shell write or a security boundary |
| Local checks / optional CI | Execution on a candidate diff | Remote branch protection merely by existing |

## Installation

The host installs the plugin or two Skill folders once. The installed initialize-repo
Skill resolves its own scripts/initialize.py and uses its bundled engine/resources, without
another checkout, URL guide, package installation or bootstrap. It initializes the target
and leaves Skill lifecycle to the host rather than copying duplicates into each project.
Generated hooks use the target's vendored runtime. Source bootstrap is compatibility only.

Root skills/ artifacts are generated from canonical WORKFLOW.md sources, the runtime and
assets. One initialized Skill folder is self-contained; its checksum-bound text resource
bundle avoids external relative paths and hidden nested SKILL discovery. CI checks drift.

Preflight managed targets; merge a tagged AGENTS block and structured Hook JSON, retain
unmanaged documents. Record owned digests in manifest and preserve human content exactly
outside managed blocks. Roll back only writes performed by the failed transaction. Version
differences require explicit upgrade; manual edits to generated content produce conflicts.

## Baseline

Ignore-aware inventory records hashes and unreviewed/stale state. Agent-authored module
documents explain full behavior with path/line evidence. Static-review declarations are
separate from executed checks. A ready verification anchors scoped reviewed pre-change
evidence; delivery keeps the anchor while source changes. Historical raw batches persist.

## Change and verification

Native OpenSpec and mapped ordinary document layouts are read directly. Legacy ark.json remains readable, but is not required. Verification, evidence and checkpoints are generated results rather than a development entry. There is no second delta-merging implementation. Prefer the
native workflow; reviewed file synchronization is supported and named honestly when no
native tool exists. Sync hashes establish freshness, not semantic equivalence.

Verification records code/config/spec fingerprints, real argv/cwd/exit/log, failed/unrun
checks and environment. Required checks aggregate conservatively; optional failures stay
visible. Input mutation invalidates a run. Closure requires fresh workspace execution and
valid completion conditions. Local check re-executes rather than trusting committed PASS JSON. Optional CI can run the same checker independently.

## Context and runtime adapters

Local pointers use root/worktree, branch and session identity; checkpoints travel with the
change. Startup supplies bounded navigation without a full scan. Stop defaults to advisory;
enforce permits one continuation per session/turn and respects existing continuation and
blocked checkpoints. Model or runtime changes do not rewrite repository knowledge.

The ADR directory records lasting choices. Compatibility documentation separates shipped
configuration, protocol validation, installed-runtime loading and remote enforcement.
