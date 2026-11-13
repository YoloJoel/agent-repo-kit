"""Single-writer offline event journal; strict replay and durable append."""
import json
import os
from pathlib import Path


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.events = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                key, payload = record["id"], record["payload"]
                if key in self.events and self.events[key] != payload:
                    raise ValueError("conflicting replay")
                self.events[key] = payload

    def append(self, event_id, payload):
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("event id required")
        if event_id in self.events:
            if self.events[event_id] != payload:
                raise ValueError("conflicting event")
            return False
        encoded = json.dumps({"id": event_id, "payload": payload}, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.events[event_id] = payload
        return True
