"""Compare frozen readbacks with source observations. Run from any directory."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def typed(value):
    return json.dumps(value, allow_nan=False, sort_keys=True)


def exam_dir(suite):
    return ROOT / "exam" / {"A": "", "B": "", "C": "confirm", "D": "final", "E": "exception"}[suite]


def index_questions(rows):
    entries = {row["id"]: row for row in rows}
    if len(entries) != len(rows):
        raise ValueError("Duplicate question identifier")
    return entries


def check_scores(run, execute):
    suite = run["suite"]
    folder = exam_dir(suite)
    keys = index_questions(load(folder / f"key-{suite}.json")["questions"])
    answers = index_questions(load(ROOT / run["answers"]))
    reviews = index_questions(load(ROOT / run["review"]))
    spec_bytes = (ROOT / run["spec"]).read_bytes()
    if hashlib.sha256(spec_bytes).hexdigest() != run["spec_sha256"]:
        raise ValueError(f"Candidate changed for {run['candidate']}")
    if keys.keys() != answers.keys():
        raise ValueError(f"Reader question set differs for {suite}")
    if execute:
        output = subprocess.check_output(
            ["/usr/bin/python3", "-I", "-B", str(folder / "probe.py"), *keys], text=True
        )
        observed = json.loads(output)
    field_counts = Counter()
    question_counts = Counter()
    support_counts = Counter()
    for question_id, key in keys.items():
        expected = key["actual_observations"]
        if execute and typed(observed[question_id]) != typed(expected):
            raise ValueError(f"Runtime observation differs for {question_id}")
        fields = answers[question_id]["fields"]
        review = reviews[question_id]["fields"]
        if fields.keys() != expected.keys() or review.keys() != fields.keys():
            raise ValueError(f"Field names differ for {question_id}")
        marks = []
        for field, predicted in fields.items():
            mark = review[field]["accuracy"]
            if mark not in ("F", "P", "C", "U"):
                raise ValueError(f"Invalid field grade {question_id}.{field}: {mark}")
            if predicted["status"] in ("full", "predicted"):
                expected_mark = "F" if typed(predicted["value"]) == typed(expected[field]) else "C"
                if mark != expected_mark:
                    raise ValueError(f"Typed comparison and recorded grade differ at {question_id}.{field}")
            marks.append(mark)
            field_counts[mark] += 1
            support_counts[review[field]["contract_support"]] += 1
        question_mark = ("C" if "C" in marks else "F" if set(marks) == {"F"}
                         else "U" if set(marks) == {"U"} else "P")
        question_counts[question_mark] += 1
    return {"candidate": run["candidate"], "suite": suite, "fields": dict(field_counts),
            "questions": dict(question_counts), "contract_support": dict(support_counts)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="Replay the public probes on the pinned Debian interpreter")
    args = parser.parse_args()
    manifest = load(ROOT / "runs.json")
    for run in manifest:
        print(json.dumps(check_scores(run, args.execute), sort_keys=True))


if __name__ == "__main__":
    main()
