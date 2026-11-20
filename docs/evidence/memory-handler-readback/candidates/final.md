# MemoryHandler

## Purpose

A `logging.handlers.MemoryHandler` holds log records for synchronous delivery to a caller-supplied target. The caller can let record count or severity trigger delivery, request it explicitly, or choose whether closing the handler should deliver pending records.

This specification covers direct, single-threaded calls on the standard memory handler, including the inherited behavior used by those calls. In the scenarios, letters identify distinct log record objects. A *recording target* is truthy and its `handle(record)` appends the argument to its call log and returns normally unless the scenario specifies other behavior. A target call, the target's own emission, and a side effect performed by the target are distinct observations. Logger routing, global shutdown, garbage collection, concurrent calls and unrelated handlers are outside scope.

## Requirements

### Requirement: REQ-MEM-001 Initial buffer and configuration
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

`MemoryHandler(capacity, flushLevel=logging.ERROR, target=None, flushOnClose=True)` SHALL start with its own empty buffer, retain the supplied settings and start with handler level `NOTSET`, no filters and no formatter. Capacity counts records. The standard numeric levels are NOTSET 0, DEBUG 10, INFO 20, WARNING (WARN) 30, ERROR 40 and CRITICAL (FATAL) 50.

The constructor SHALL store capacity and flushLevel as supplied. It performs no positive-integer check on capacity and no conversion of a severity name to a number for flushLevel. A numeric comparison with an incompatible value raises `TypeError` when that comparison is reached.

#### Scenario: Defaults and independent pending records
- WHEN two handlers are created with capacity 2 and INFO A is emitted on the first
- THEN only the first holds A. Each has capacity 2, flushLevel 40, target None, flushOnClose True and handler level 0.

#### Scenario: String flush level
- WHEN the caller constructs a handler with capacity 3 and flushLevel `"ERROR"`, then directly emits INFO A
- THEN construction succeeds, emission raises TypeError while comparing the levels, and A remains pending.

### Requirement: REQ-MEM-002 Direct admission and effective record
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

On direct `handle(record)`, the handler SHALL apply its filters in registration order. For each filter it calls its `filter(current_record)` method if present, otherwise the filter itself. A false result stops the chain, returns the boolean False and skips emission. A truthy LogRecord result replaces the current record for every later filter and for emission. Any other truthy result keeps the current record. With no veto, the handler returns the final record object on normal completion and emits it if it tests true. Ordinary LogRecord instances test true. With no filters, the input object is the final record, so a LogRecord subclass that tests false is returned without emission. Filter mutations are visible to subsequent processing. A filter exception propagates before this call appends a record.

`addFilter(f)` SHALL append f only if it is absent. `removeFilter(f)` removes it if present. A direct `filter(record)` call uses the same chain and returns the accepted record or False without emitting. Direct `emit(record)` skips these filters, appends its argument, and returns None on normal completion. Neither direct entry tests the handler's own level. `setLevel(level)` changes that independent numeric level, accepting an integer or a registered level name. An unknown name raises ValueError and an incompatible ordinary value such as None raises TypeError. Neither case changes the previous level. `setFormatter(fmt)` SHALL store the supplied object as the handler's formatter and return None. Installation neither tests its truth nor calls its format method. Buffering and forwarding pass record objects without using the memory handler's formatter. An explicit `format(record)` tests the installed formatter and, if truthy, calls its `format(record)` once and returns the result. With None or another false-valued formatter it calls the default formatter instead.

#### Scenario: A replacement supplies the severity, identity and return value
- WHEN a handler of capacity 9 and level CRITICAL with a recording target directly handles INFO A, its first filter returns ERROR B and its next filter returns True
- THEN the next filter receives B, B triggers delivery at the default threshold, the target receives B, the buffer empties and handle returns B itself.

#### Scenario: Veto versus direct emission
- WHEN an empty handler of capacity 9 has a filter returning False, and the caller handles INFO A and then directly emits A
- THEN handle returns False without buffering A, emit returns None and precisely one entry, A, is pending.

#### Scenario: An earlier pending record survives a filter error
- WHEN INFO A is pending and the first filter raises LookupError while handling ERROR B
- THEN handle propagates LookupError, no later filter or target is called for B and only A remains pending.

#### Scenario: Observe a formatter from installation through use
- WHEN the caller installs a truthy formatter that counts calls to its format method, directly handles INFO A on a handler of capacity 1 with a recording target, then explicitly calls format(A)
- THEN the count is zero after installation and still zero after the target receives A. The explicit format call passes A to the installed formatter once and returns its result.

### Requirement: REQ-MEM-003 Count and severity triggers
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

A direct `shouldFlush(record)` query SHALL test the *current* number of buffered records against capacity. If the count is at least capacity, it returns True without inspecting record severity. Otherwise it returns the result of `record.levelno >= flushLevel`. The query itself neither appends nor delivers. In contrast, `emit` SHALL append the record object first, query with that record, and call `flush()` once if either condition is true. The triggering record belongs to the batch. Below both thresholds, the entire buffer stays pending. There is no eviction at capacity.

#### Scenario: Asking about the next record differs from emitting it
- WHEN capacity is 2, the default threshold applies, INFO A is pending and the caller queries shouldFlush(INFO B)
- THEN it returns False and only A remains pending. Emitting B now reaches count 2 and a recording target receives A then B, emptying the buffer.

#### Scenario: Severity can trigger a short batch
- WHEN capacity is 8 and WARN A is followed by ERROR B at the default threshold
- THEN A alone stays pending and B triggers delivery of A then B to a recording target. A CRITICAL record on the newly emptied handler triggers delivery by itself.

#### Scenario: A nonpositive capacity short-circuits severity
- WHEN capacity is 0, flushLevel is the string `"bad"` and DEBUG A is emitted to a recording target
- THEN the count condition is already true, the level comparison is skipped, the target receives A and the buffer empties. A negative capacity also satisfies the count test on every ordinary emission.

### Requirement: REQ-MEM-004 Target selection and retention
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

`setTarget(target)` SHALL replace the destination immediately and return None, leaving pending records untouched. It makes no delivery to the previous or new target. At entry to a flush, a missing or otherwise false-valued target causes the flush to return None with all entries retained. This applies to explicit, threshold-triggered and close-triggered flushes. Such a handler can accumulate more records than its capacity. Installing a truthy target later makes the retained records eligible for the next flush.

An ordinary `MemoryHandler` used as a target is truthy, including when its own buffer is empty or its own target is None. The sender therefore calls its inherited `handle` as described in REQ-MEM-005. On admission the receiver buffers the effective record and applies its own capacity, severity and downstream target rules. A subclass that tests false, for example through `__bool__` returning False or, in its absence, `__len__` returning zero, skips delivery at the sender's flush-entry gate.

#### Scenario: Forward to a distinct empty memory handler
- WHEN the sender has capacity 2 and targets a newly constructed MemoryHandler with capacity 1, default filters and no downstream target, and the sender emits INFO A followed by INFO B
- THEN the sender's second emission forwards A then B and clears its buffer. Each record triggers a flush on the receiver, which retains both in order because it has no downstream target.

#### Scenario: A false-valued target and a backlog
- WHEN capacity is 1, a target with a working handle method tests false, the caller emits INFO A and INFO B and explicitly flushes
- THEN the target has received no calls and both A and B remain pending in that order. Installing a recording target makes no call. The next explicit flush sends it A then B and empties the buffer.

#### Scenario: Switch before a flush
- WHEN A is pending with recording target T and the caller calls setTarget(U) for another recording target, then flushes
- THEN setTarget returns None without calling either target, T receives nothing, U receives A and the buffer empties.

### Requirement: REQ-MEM-005 Delivery through the target's handle method
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

With a truthy target, an explicit or triggered flush SHALL visit pending entries in insertion order, synchronously calling the current target's `handle(record)` with each actual buffered object. It does no sender-side level check, filtering, copying or formatting during this traversal. A later change to a buffered object is visible through the same reference. Entries stay in the live buffer while the calls run. A record appended by a callback during this traversal can itself be visited before the flush returns. When the traversal finishes normally, flush clears the existing buffer in place and returns None, irrespective of the targets' return values. Flushing an empty buffer makes no record calls. No call to the target's flush method is part of delivery.

For a target using the standard inherited `Handler.handle`, that target SHALL apply its own filters by the admission rule in REQ-MEM-002. It calls its own `emit` once with a truthy accepted record, including a replacement. A veto or a false-valued final record skips emission. The call from the memory handler does not consult the target's configured level. A target may define other behavior in its own handle or emit. The sender observes only the return or exception.

#### Scenario: A target veto is a normal return
- WHEN INFO A and INFO B are flushed to a target with inherited handle and level ERROR, its filter vetoes A and returns a replacement C for B, and its emit records arguments and returns
- THEN the target receives handle calls for A and B, its only emit argument is C, and the memory handler clears both original entries. A filter accepting an unmodified INFO record would allow the target to emit it despite its ERROR level.

#### Scenario: Identity and repeated entries
- WHEN A with message `old` is buffered twice, its message is changed to `new`, and the caller flushes to a recording target
- THEN the target receives the same A object twice in order, both calls see `new`, and a second flush makes no further calls.

#### Scenario: A callback changes destination
- WHEN A and B are pending, the current truthy target T handles A by calling setTarget(U) and returning, and U is a recording target
- THEN T receives A, U receives B and the successful flush clears the buffer. The destination is read for each entry. If U tests false but implements handle, its handle still receives B because the target truth test ran only at flush entry. If T set the target to None instead, the attempt to handle B would raise AttributeError and the original entries would remain pending.

#### Scenario: A target callback emits one more record
- WHEN the handler has capacity 10, INFO A and B are pending, and during an explicit flush the recording target handles A by directly emitting INFO C on the same memory handler once
- THEN the nested emit appends C without triggering another flush. The ongoing flush visits A, B and C in order and clears all three entries.

### Requirement: REQ-MEM-006 Interrupted delivery and retry
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

If a target call raises, the memory handler SHALL propagate that exception synchronously to the caller, stop before the next entry and skip clearing the buffer. The sender leaves the entire batch pending, including any entries whose target calls already returned and the entry whose call raised. Side effects already performed by callbacks persist. An explicit or subsequent automatic flush starts again at the front. These buffer observations assume the target did not itself edit the buffer. A truthy target lacking a handle attribute raises AttributeError on the first attempted call with a pending entry. If an emission's predicate raises after the append, the newly appended entry also remains pending.

#### Scenario: A destination fails partway
- WHEN A, B and C are pending, T returns on A and raises OSError on B, and the caller explicitly flushes
- THEN OSError reaches the caller, T has received A and B, C was not attempted and the buffer still contains A, B and C. After setTarget(U) and a successful retry, U receives A, B and C and the buffer empties.

#### Scenario: The failed record triggered the flush
- WHEN INFO A is pending, direct handle of ERROR B triggers a flush, and the target records A then raises ValueError on B
- THEN the handle call raises ValueError and leaves both A and B pending. A later successful flush offers A again even though the first call for A returned normally.

### Requirement: REQ-MEM-007 Explicit close and later calls
Verification: automated
Baseline: docs/baseline/contracts/memory-handler.md

`close()` SHALL first call flush with the current target if flushOnClose is truthy, regardless of count or severity. With a false-valued flag it skips this opportunity to deliver. In either case, including when that first flush raises, it sets target to None and performs inherited close cleanup. During that cleanup another call to the memory handler's flush runs with the target detached and preserves any remaining entries. Handler cleanup marks the memory handler closed and removes its registered name from name lookup, if present. Close does not call the target's close or flush. Close returns None on normal completion and propagates a target exception after cleanup.

Closing SHALL leave subsequent direct handle, emit, setTarget and flush calls usable. With no intervening reattachment, another close or flush cannot deliver retained records. A later target can receive retained as well as newly buffered records. The stored capacity, flushLevel, filters and flushOnClose setting still apply.

#### Scenario: Close with delivery enabled
- WHEN INFO A is below both thresholds and the caller closes the default-configured handler with a recording target twice
- THEN the first close sends A once, clears the buffer and detaches the target. The second close makes no target call. Neither close closes the target.

#### Scenario: Disable close delivery
- WHEN flushOnClose is False, INFO A is pending and the caller closes while recording target T is installed
- THEN T receives nothing, the target becomes None and A remains pending. Setting a recording target U and explicitly flushing sends U the retained A.

#### Scenario: Close fails on a later record
- WHEN the default close flush visits A then B and the target raises ValueError on B
- THEN close propagates ValueError after detaching the target and running handler close cleanup. Both A and B remain pending. A subsequent explicit flush with no target preserves both. Installing a working target and flushing offers A and B again.
