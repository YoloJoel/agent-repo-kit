from pathlib import Path
import logging
from logging import handlers

root = Path.cwd().resolve()
assert Path(logging.__file__).resolve() == root / "logging/__init__.py"
assert Path(handlers.__file__).resolve() == root / "logging/handlers.py"


def record(name):
    return logging.LogRecord("probe", logging.INFO, "", 0, name, (), None)


def raises_original(call, target):
    try:
        call()
    except LookupError as exc:
        assert exc is target.error
    else:
        raise AssertionError("expected the original exception")


class Gate:
    def __init__(self):
        self.error = LookupError("target truth")
        self.events = []
        self.fail = True

    def __bool__(self):
        self.events.append("truth")
        if self.fail:
            self.fail = False
            raise self.error
        return True

    def handle(self, record):
        self.events.append(record.msg)


a, b = record("A"), record("B")
t = Gate()
h = handlers.MemoryHandler(2)
assert h.handle(a) is a
pending = h.buffer
assert h.setTarget(t) is None and h.target is t and t.events == []
raises_original(lambda: h.handle(b), t)
assert h.buffer is pending and h.buffer == [a, b] and h.target is t
assert t.events == ["truth"]
assert h.flush() is None and t.events == ["truth", "truth", "A", "B"]
assert h.buffer is pending and not pending
h.close()
print("threshold handle: set [], failed [truth], retained [A,B], retry [truth,A,B], cleared")

t = Gate()
h = handlers.MemoryHandler(2, target=t)
assert h.target is t and t.events == []
raises_original(h.flush, t)
assert t.events == ["truth"] and h.buffer == [] and h.target is t
h.setTarget(None)
h.close()
print("explicit empty flush: constructor [], raised original error at truth, no handle call")

t = Gate()
h = handlers.MemoryHandler(3, target=t)
h.name = "round4-gate-probe"
h.emit(a)
raises_original(h.close, t)
assert t.events == ["truth"] and h.target is None and h.buffer == [a]
assert h._closed and logging.getHandlerByName(h.name) is None
assert h.flush() is None and h.buffer == [a]
h.setTarget(t)
h.flush()
assert t.events == ["truth", "truth", "A"] and not h.buffer
h.close()
print("close: [truth], detached, removed registered name, retained [A], reattached retry delivered A")


class SwitchingGate(Gate):
    def __bool__(self):
        self.events.append("truth")
        h.setTarget(replacement)
        a.msg = "changed"
        raise self.error


t, replacement = SwitchingGate(), Gate()
replacement.fail = False
h = handlers.MemoryHandler(4, target=t)
h.emit(a)
raises_original(h.flush, t)
assert t.events == ["truth"] and replacement.events == [] and h.target is replacement
assert h.buffer == [a] and a.msg == "changed"
h.flush()
assert replacement.events == ["truth", "changed"] and not h.buffer
h.close()
print("hook retargets and mutates A before raising: both effects persist; retry uses replacement")


class LengthGate:
    def __init__(self):
        self.error = LookupError("length")
        self.events = []

    def __len__(self):
        self.events.append("length")
        raise self.error

    def handle(self, record):
        self.events.append(record.msg)


t = LengthGate()
h = handlers.MemoryHandler(1, target=t)
raises_original(lambda: h.emit(b), t)
assert t.events == ["length"] and h.buffer == [b] and h.target is t
h.setTarget(None)
h.close()
print("length fallback: emit propagated original error, retained triggering B, no handle call")
