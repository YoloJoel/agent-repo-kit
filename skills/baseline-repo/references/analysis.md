# Analysis contract

Map modules, processes, builds, tests, deployment, configuration and dependencies. Track
included/excluded/uninspected ranges and explain bootstrap/shutdown where applicable.

For each important module, explain purpose, input/output and collaborators. Walk an actual
operation through entry, validation, branches, transformation, persistence/messages and result.
Explain error propagation, retry/idempotency/ordering, partial success and resource release.
Identify state ownership/lifetime, transactions, locks and caches. Explain special cases,
using code locations as evidence rather than replacing explanation with symbol lists.

Separate static review, executed tests and real runtime observations. Bind evidence to
revision/worktree fingerprints. Record unknowns and contradictory documentation explicitly.
Characterization fixtures establish current behavior but do not make defects permanent promises.

Refresh affected modules/dependencies incrementally, preserve raw snapshots and mark stale
records. Historical baseline must remain historical. Current specs carry current promises.
Working safely on an established local scope does not require resolving the entire large repo.
