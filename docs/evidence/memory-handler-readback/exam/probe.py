#!/usr/bin/python3
"""Run sealed observations against the identified CPython installation."""

import argparse
import hashlib
import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULES = [
    (logging, "/usr/lib/python3.13/logging/__init__.py",
     "dc42e5cf19a2dd03bd95ed3600803effa9c5f107927ab5f66cacf3eebcfd9a47"),
    (logging.handlers, "/usr/lib/python3.13/logging/handlers.py",
     "464980a72ce4c0ca1e6a6724a9760f5e101475a4e347329272ba6d2c4b39dffd"),
]


def verify_runtime():
    if (sys.implementation.name != "cpython" or sys.version_info[:3] != (3, 13, 5)
            or not os.path.samefile(sys.executable, "/usr/bin/python3")):
        raise RuntimeError("Use the specified /usr/bin/python3 CPython 3.13.5")
    for module, filename, expected in MODULES:
        path = Path(filename)
        if Path(module.__file__).resolve() != path:
            raise RuntimeError("Unexpected module path: " + str(module.__file__))
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Source bytes changed: " + str(path))


def run(ids):
    samples = {}
    for letter in ("A", "B"):
        question_path = HERE / f"questions-{letter}.json"
        packet = json.loads(question_path.read_text())
        for question in packet["questions"]:
            qid = question["id"]
            if ids and qid not in ids:
                continue
            scope = {}
            exec(compile(packet["shared_fixture_python"], f"{qid}-fixture", "exec"), scope)
            exec(compile(question["stimulus_python"], f"{qid}-stimulus", "exec"), scope)
            obs = scope["observations"]
            if list(obs) != question["observation_fields"]:
                raise RuntimeError("Observation fields changed: " + qid)
            # Freeze the observation before dropping the fresh scenario namespace.
            samples[qid] = json.loads(json.dumps(obs, allow_nan=False))
    bad = sorted(set(ids) - set(samples))
    if bad:
        raise ValueError("Unknown question identifiers: " + ", ".join(bad))
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*", help="Question IDs. Omit to run all.")
    arguments = parser.parse_args()
    verify_runtime()
    print(json.dumps(run(arguments.ids), ensure_ascii=False, indent=2), flush=True)
    # Stop after the measured public calls, without logging.shutdown at exit.
    os._exit(0)


if __name__ == "__main__":
    main()
