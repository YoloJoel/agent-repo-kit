# Offline event journal qualification example

A concrete new-project task: durable single-writer event append, idempotent retry, conflict
rejection and explicit corrupt replay. Six tests cover replay/Unicode, duplicate no-write,
conflict preservation, invalid IDs, unserializable input, torn records and conflicting replay.
The native OpenSpec qualification adds ordered immutable ID listing as a second change and
proves that breaking the original duplicate return value fails regression while the new
listing acceptance still passes.

Run `python tools/qualify_openspec.py --output <report.json>` from the toolkit root. It creates
an isolated local Git repository, invokes the bundled initializer and actual OpenSpec 2.0.0,
executes old/new checks, native validation/synchronization/archive and local candidate checks.
No consumer remote, CI, development Skill or toolkit activity pointer is used.

This is not a production WAL: multi-writer locking, parent-directory fsync, crash/power-loss
fault injection, malicious replay schemas, caller mutation of payloads and throughput are
outside its qualified scope. Do not infer production guarantees from the small example.
