"""Score frozen Spec-only answers on the public control-hub sample using native observations."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from qualify_source_facts import qualify


QUESTIONS = {
    "Q1": "List registered resource names after initialization, sorted alphabetically (JSON array of strings).",
    "Q2": "Does a period update with 700 return the accepted value 700 (boolean)?",
    "Q3": "What integer does the receiver return for a frame with token 999 and value 42?",
    "Q4": "Which route string results when both the global and local flags are enabled?",
    "Q5": "Reset at time 0, tick at 99 with no ingestion. How many reports have been emitted (integer)?",
    "Q6": "Reset at 0, ingest at 20 with zero fields. How many reports have been emitted (integer)?",
    "Q7": "Continue Q6 by ingesting at 21 with zero fields. What is the total report count (integer)?",
    "Q8": "What integer does configuring five filters return?",
}


def score(spec_text, answers, observations):
    actual = {
        "Q1": sorted(observations["registered_resources"]),
        "Q2": observations["update_period_700"] == 700,
        "Q3": observations["received_arbitrary_token_value"],
        "Q4": observations["both_rules_enabled_route"],
        "Q5": observations["reports_after_timer_tick"],
        "Q6": observations["reports_at_boundary"],
        "Q7": observations["reports_after_next_event"],
        "Q8": observations["filter_count_5"],
    }
    if not isinstance(answers, dict) or set(answers) != set(QUESTIONS):
        raise ValueError("Supply one answer for every question, including unclear answers.")
    rows = []
    for key, observed in actual.items():
        answer = answers[key]
        if not isinstance(answer, dict) or answer.get("status") not in ("predicted", "unclear"):
            raise ValueError(f"{key}: use predicted or unclear")
        if answer["status"] == "unclear":
            if not isinstance(answer.get("missing"), str) or not answer["missing"].strip():
                raise ValueError(f"{key}: describe what the Spec leaves open")
            rows.append({"id": key, "result": "unclear", "missing": answer["missing"]})
            continue
        quote = answer.get("quote")
        if not isinstance(quote, str) or not quote.strip() or quote not in spec_text or "value" not in answer:
            raise ValueError(f"{key}: prediction needs a value and a verbatim supporting passage")
        predicted = answer["value"]
        matches = json.dumps(predicted, sort_keys=True) == json.dumps(observed, sort_keys=True)
        rows.append({"id": key, "result": "matches" if matches else "contradicts", "value": predicted,
                     "observed": observed, "quote": quote})
    counts = Counter(row["result"] for row in rows)
    return {"count": len(rows), "counts": {key: counts[key] for key in ("matches", "contradicts", "unclear")}, "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", action="store_true", help="Print reader inputs without reference outcomes")
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--answers", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.questions:
        print(json.dumps(QUESTIONS, indent=2))
        return 0
    if not all((args.spec, args.answers, args.output)):
        parser.error("scoring requires --spec, --answers and --output (a new directory)")
    spec = args.spec.read_bytes()
    answers = args.answers.read_bytes()
    args.output.mkdir(parents=True, exist_ok=False)
    probe = qualify(args.output / "native")
    (args.output / "native/report.json").write_text(json.dumps(probe, indent=2) + "\n")
    result = {"native_status": probe["status"], "spec_sha256": hashlib.sha256(spec).hexdigest(),
              "answers_sha256": hashlib.sha256(answers).hexdigest()}
    if probe["status"] == "PASS":
        result.update(score(spec.decode("utf-8"), json.loads(answers), probe["observations"]))
    (args.output / "readback.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows", "spec_sha256", "answers_sha256")}))
    return 0 if probe["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
