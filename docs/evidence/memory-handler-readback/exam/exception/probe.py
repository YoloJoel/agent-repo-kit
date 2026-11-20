#!/usr/bin/python3
"""Replay the targeted exception confirmation with checked, independent fixtures."""

import argparse
import hashlib
import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = [
    (logging, "/usr/lib/python3.13/logging/__init__.py",
     "dc42e5cf19a2dd03bd95ed3600803effa9c5f107927ab5f66cacf3eebcfd9a47"),
    (logging.handlers, "/usr/lib/python3.13/logging/handlers.py",
     "464980a72ce4c0ca1e6a6724a9760f5e101475a4e347329272ba6d2c4b39dffd"),
]


def verify():
    if (sys.implementation.name != "cpython" or sys.version_info[:3] != (3, 13, 5)
            or not os.path.samefile(sys.executable, "/usr/bin/python3")):
        raise RuntimeError("Incorrect reference runtime")
    for module, filename, digest in SOURCES:
        source = Path(filename)
        if Path(module.__file__).resolve() != source:
            raise RuntimeError("Unexpected imported source " + str(module.__file__))
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise RuntimeError("Changed source " + filename)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("ids", nargs="*", help="Optional individual question IDs")
    selected = args.parse_args().ids
    verify()
    packet = json.loads((ROOT / "questions-E.json").read_text())
    result = {}
    for question in packet["questions"]:
        qid = question["id"]
        if selected and qid not in selected:
            continue
        scope = {}
        exec(compile(packet["shared_fixture_python"], qid + "-fixture", "exec"), scope)
        exec(compile(question["stimulus_python"], qid + "-stimulus", "exec"), scope)
        values = scope["observations"]
        if list(values) != question["observation_fields"]:
            raise RuntimeError("Unexpected fields in " + qid)
        result[qid] = json.loads(json.dumps(values, allow_nan=False))
    unknown = sorted(set(selected) - set(result))
    if unknown:
        raise ValueError("Unknown question identifiers: " + ", ".join(unknown))
    print(json.dumps(result, indent=2), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
