# MemoryHandler

## Purpose

A `logging.handlers.MemoryHandler` holds log record objects in arrival order and forwards them to a caller-supplied target in batches. This Spec covers single-threaded calls to the handler, the target calls they cause, and the directly relevant behavior inherited from `BufferingHandler` and `Handler`. Global logging shutdown, garbage collection, concurrency, logger routing and unrelated handlers are outside scope.

In the scenarios, A, B and C denote distinct `LogRecord` instances unless stated otherwise. A collecting target is truthy and its `handle(record)` records the object it receives and returns normally. Each scenario uses the constructor defaults for unspecified options, an initially empty buffer before the stated setup, and collecting targets for named receivers unless a different behavior is specified. The standard methods apply unless a scenario supplies an override.

## Requirements

### Requirement: REQ-MH-001 Initial state and options
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

A new `MemoryHandler(capacity, flushLevel=logging.ERROR, target=None, flushOnClose=True)` SHALL have its own empty `buffer` list, store the supplied options, and start at handler level `NOTSET` (0) with no filters, formatter or name. `capacity` is required. The default `flushLevel` is 40. Construction stores `capacity` and `flushLevel` as supplied, without checking a minimum or converting a level name. The handler level and the severity that triggers a flush are separate settings.

#### Scenario: Independent buffers

- WHEN two handlers are constructed as `MemoryHandler(2)` and INFO A is emitted on the first
- THEN the first buffer contains just A and the second is empty. The first has capacity 2, flush level 40, target `None`, `flushOnClose=True` and level 0.

#### Scenario: An explicit level name as a flush threshold

- WHEN a caller constructs `MemoryHandler(2, flushLevel='ERROR')`
- THEN construction succeeds with `flushLevel` equal to the string `'ERROR'`. Its use in a severity comparison is covered by REQ-MH-003.

### Requirement: REQ-MH-002 Admission through handle, filter and emit
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

`handle(record)` SHALL apply the handler's filters before emission and return the filter result after a successful call. With the inherited filter chain, a veto returns `False`, and admission returns the final `LogRecord` object. Filters run in insertion order, using a filter's `.filter(record)` when present and otherwise calling the filter itself. The first falsy result ends the chain. A truthy `LogRecord` replaces the current record for all later filters and emission. Other truthy results keep the current record. With no filters the input record passes unchanged. `filter(record)` alone performs this selection without emitting. `addFilter` skips a filter already present and `removeFilter` ignores an absent filter. `handle` does not compare `record.levelno` to the handler's `level`. A direct `emit(record)` skips the handler's filters. The memory handler passes records through without formatting them.

#### Scenario: Replacement changes the flush decision

- WHEN an empty capacity-8 handler has a collecting target and the default flush level, its first filter replaces INFO A with ERROR R, and the second filter returns `True`
- THEN the second filter receives R. `handle(A)` returns R, the target receives R alone, and the buffer is empty.

#### Scenario: Veto and direct emission

- WHEN a capacity-one handler with a collecting target and handler level CRITICAL has a filter returning 0, and the caller invokes `handle(INFO A)` followed by `emit(INFO B)`
- THEN `handle` returns `False` without buffering or forwarding A. `emit` returns `None`, B reaches the target and the buffer is empty.

#### Scenario: A filter raises

- WHEN A is pending and the first filter raises `LookupError` while `handle(B)` is consulting it
- THEN the error reaches the caller. Later filters and emission of B are skipped and the buffer still contains A.

#### Scenario: Custom filter result

- WHEN a subclass overrides the handler's `filter` method to return the non-record token `'ok'` for INFO A, with room to buffer A
- THEN `handle(A)` emits A and returns `'ok'`. A falsy result from that override would be returned as supplied and skip emission.

### Requirement: REQ-MH-003 Buffering and flush decisions
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

`emit(record)` SHALL append the supplied object before calling `shouldFlush(record)` and call `flush()` once if the result is truthy. A successful `emit` returns `None`. The standard `shouldFlush` uses the current buffer length, including any just-appended record. It returns `True` when length is at least `capacity`. Otherwise it compares `record.levelno >= flushLevel`. A direct predicate query changes no state and does not count its argument as a new entry. Reaching either threshold suffices, including equality. Pending entries can accumulate beyond capacity while a target is absent. The capacity comparison runs first and a true result skips severity access. An exception from the predicate or from delivery reaches the emitter after the append. An override can inspect the appended record, suppress a normal flush, or request one early.

#### Scenario: Query before append and capacity equality

- WHEN a capacity-2 handler holds INFO A, a collecting target is attached and the caller queries `shouldFlush(INFO B)`, then emits B
- THEN the query returns `False` and leaves A pending. Emitting B delivers A then B and empties the buffer.

#### Scenario: Severity equality below capacity

- WHEN an empty capacity-8 handler with a collecting target and default flush level receives A at level 39 followed by B at level 40
- THEN A alone causes no delivery. B triggers delivery of both A and B in order, before `emit(B)` returns.

#### Scenario: Zero and negative capacities

- WHEN a handler has capacity 0, flush level `'ERROR'` and a collecting target, and the caller emits an object A with no `levelno`
- THEN A is delivered without a severity comparison. `emit` returns `None` and the buffer is empty. A negative numerical capacity has the same effect.

#### Scenario: Short-circuit and error state

- WHEN a handler with capacity 2, string flush level `'ERROR'` and a collecting target receives INFO A followed, after the caller catches any error, by INFO B
- THEN comparing A's numerical level with the string raises `TypeError` and leaves A pending. B reaches capacity, bypasses that comparison, and delivers A then B. An absent `levelno` below capacity would raise `AttributeError` after append.

#### Scenario: Custom flushing policy

- WHEN a subclass policy observes the buffer and always returns `False` from `shouldFlush`, and `emit(ERROR A)` is called at capacity 1 with a collecting target
- THEN the policy sees A already buffered. A remains pending with no target call until an explicit `flush()` delivers it.

#### Scenario: A positive query has no side effects

- WHEN a default capacity-3 handler has an empty buffer and a collecting target, and the caller queries `shouldFlush(ERROR A)` directly
- THEN the query returns `True`. A is never appended and the target receives no record.

#### Scenario: Capacity comparison fails first

- WHEN an empty handler constructed with `capacity='2'` has a collecting target, and the caller invokes `handle(ERROR A)` with no filters
- THEN the length comparison raises `TypeError` before severity is tested. The caller receives the exception and A remains in the buffer without a target call.

### Requirement: REQ-MH-004 Target selection and delivery
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

`setTarget(target)` SHALL replace the target immediately and leave all pending records in place without forwarding. It accepts the supplied object without checking for a `handle` method and returns `None`. `flush()` tests the current target for truth. With `None` or another falsy target it returns `None` and preserves all entries. With a truthy target it calls `target.handle(record)` synchronously in buffer order, starting at the first entry regardless of thresholds. It passes the actual record objects, including repeated references, and ignores every normal return value. After all calls return normally it empties the same buffer list in place and returns `None`. An empty buffer causes no target handle call. The memory handler neither tests the target handler's level nor calls its `emit`, `flush`, formatter or `close` directly. A target using the inherited `handle` applies its own filters. During delivery each call uses the then-current target and iterates the live list of pending entries.

#### Scenario: No truthy target

- WHEN capacity is 1, the supplied target's `__bool__` returns `False`, the caller emits INFO A and B and then calls `flush()`
- THEN the target receives no `handle` calls and the buffer contains A then B. It can grow beyond capacity.

#### Scenario: Retarget a backlog

- WHEN A is pending with target X, the caller sets Y then `None`, emits ERROR B, installs Z and explicitly flushes
- THEN neither X nor Y receives a record. Installing Z itself sends nothing. The explicit flush sends A then B to Z and empties the buffer.

#### Scenario: Target filter veto

- WHEN INFO A and INFO B are flushed to a target with inherited `Handler.handle`, a recording `emit` that returns normally, level CRITICAL and a filter that rejects A and permits B
- THEN the target's `handle` is called for both. Only B reaches its `emit`, and the memory handler clears both entries.

#### Scenario: Object identity and list identity

- WHEN a caller retains a reference to the buffer, emits the same INFO record twice below capacity, changes its `msg` to `'new'` and flushes
- THEN the target receives that same record twice, both times with `msg` equal to `'new'`. The original buffer list is now empty.

#### Scenario: Retarget during a callback

- WHEN a flush starts with A then B, and X handles A by calling `setTarget(Y)` before returning normally
- THEN X receives A and Y receives B. Completing the loop clears the buffer. If X instead detaches the target, the attempt to call `handle` for B raises `AttributeError` and the buffer retains A and B.

#### Scenario: Append during a callback

- WHEN a capacity-10 handler holds INFO A and B and, on receiving A during explicit flush, the target calls `emit(INFO C)` once
- THEN C remains below both thresholds on append, and that same flush offers B and then C before clearing the list.

### Requirement: REQ-MH-005 Target errors and replay
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

If obtaining or calling a target's `handle` raises, the memory handler SHALL propagate the exception, stop that drain and skip the final clear. With no callback changes to the buffer, the whole batch remains, including entries already offered and the entry whose emission triggered a flush. Earlier target side effects persist. The next flush to a truthy target starts at the first retained entry and can therefore duplicate an earlier delivery. The memory handler makes no automatic retry or rollback.

#### Scenario: Automatic flush fails on the middle entry

- WHEN capacity is 3, T records A, raises `OSError` on B before recording it, and the caller emits INFO A, B and C, then replaces T by U and calls `flush()`
- THEN `emit(C)` raises `OSError`. T has recorded A alone, C has not been offered, and the buffer still contains A, B and C. U receives all three in order and the subsequent flush clears the buffer.

#### Scenario: Invalid target on an empty and a nonempty buffer

- WHEN a truthy object with no `handle` is installed, the caller flushes an empty handler, then buffers one INFO A below capacity and calls `flush()` again
- THEN the first flush returns `None`. The second raises `AttributeError` and leaves A pending.

#### Scenario: Bare Handler as target

- WHEN a truthy, unmodified `logging.Handler()` with no filters is the target and a nonempty batch is flushed
- THEN its inherited `handle` reaches its unimplemented `emit`. `NotImplementedError` reaches the caller and the whole batch remains pending.

### Requirement: REQ-MH-006 Explicit close and subsequent use
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

`close()` SHALL call the handler's `flush()` with its current target when `flushOnClose` is truthy, even below both thresholds. It then sets `target` to `None` in cleanup, invokes `flush()` with the target detached through the base close path, and performs `Handler.close` cleanup even if flushing raised. With falsy `flushOnClose` only the detached flush runs. The standard detached flush preserves the buffer. Closing removes an existing handler-name lookup entry under this handler's nonempty name and leaves its name property as assigned. On normal completion `close()` returns `None`. The supplied target receives neither `flush()` nor `close()` from this cleanup. A closed memory handler continues accepting `handle`, `emit`, `setTarget` and `flush`. The same admission and delivery rules still apply.

#### Scenario: Successful close and repeat

- WHEN a uniquely named capacity-8 handler with default options, a collecting target T and INFO A pending is closed twice
- THEN T receives A once, with no calls to T's `flush` or `close`. The buffer is empty, the target is `None` and lookup by the old name returns `None`.

#### Scenario: Disabled close-time delivery

- WHEN capacity is 8, `flushOnClose=False`, target T is attached with INFO A pending, and the caller closes, handles INFO B, attaches U and calls `flush()`
- THEN T receives nothing, A is still pending immediately after close, `handle(B)` returns B, and U receives A then B. Disabling close-time delivery leaves threshold-triggered and explicit flushes enabled.

#### Scenario: Close-time failure

- WHEN a uniquely named handler with `flushOnClose=True` holds A and B, and T records A and raises `RuntimeError` on B during `close()`
- THEN the caller receives `RuntimeError`. The target is already `None`, lookup by name returns `None` and the complete A,B batch remains. Attaching U and calling `flush()` delivers A then B to U.

#### Scenario: Closed handler reaches its trigger again

- WHEN a capacity-one handler with no target is closed, the caller handles INFO A, sets target T, and then handles INFO B
- THEN the calls return A and B respectively. A was retained while detached, so T receives A then B when B triggers delivery.

#### Scenario: Overridden flush on close

- WHEN a subclass logs its current target in `flush()` and delegates to the standard method, with target T, A pending and `flushOnClose=True`
- THEN the override observes T then `None`, and T receives A once. With `flushOnClose=False` the override would observe only `None`.

#### Scenario: A subclass raises again during cleanup

- WHEN the first flush of an explicitly named handler raises `ValueError`, and an overridden detached flush raises `KeyError` during the same `close()`
- THEN the caller receives the later `KeyError` with the earlier exception as context. The target is detached and the handler's name lookup has been removed.

### Requirement: REQ-MH-007 Base buffering behavior
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

A plain `BufferingHandler(capacity)` SHALL start with an empty buffer and use current buffer length at least `capacity` as its sole standard flush predicate. It appends before testing and clears its existing list in place on `flush()`. Closing calls the effective `flush()` and then performs `Handler.close` cleanup even on a flush exception. `MemoryHandler` inherits the append-and-test entry and the base close call to the effective `flush()`. Its own predicate and target delivery determine the outcome of those calls.

#### Scenario: Severity alone in the base class

- WHEN a caller keeps a reference to the buffer of `BufferingHandler(2)`, emits ERROR A, queries `shouldFlush(ERROR B)`, emits B, then emits C and closes
- THEN A alone remains pending and the direct query returns `False`. B fills the buffer and clears it. C is discarded on close. The original list is empty after both clears.
