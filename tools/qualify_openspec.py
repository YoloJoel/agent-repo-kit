"""Real OpenSpec 2.0 lifecycle plus no-remote new-project behavior evolution.

Requires Node/npm/network for the native CLI, Git and Python 3.11+. No model/API calls.
The journal is a scoped demonstration, not a production WAL or multi-writer guarantee.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qualification_core", ROOT / "src/agent_repo_kit/core.py")
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)


def qualify(root):
    records = []
    def run(argv):
        result = subprocess.run(argv, cwd=root, capture_output=True, encoding="utf-8", timeout=240)
        records.append({"argv": argv, "exit_code": result.returncode, "stdout": result.stdout[-10000:], "stderr": result.stderr[-2000:]})
        if result.returncode:
            raise RuntimeError(json.dumps(records[-1], ensure_ascii=False))
        return result.stdout
    def write(relative, text):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    def native(*args):
        return run(["npx", "--yes", "@fission-ai/openspec@2.0.0", *args])
    def require(report, status="PASS"):
        assert report["status"] == status, report
        return {"status": report["status"], "run_id": report.get("run_id"), "checks": [{"name": x["name"], "status": x["status"]} for x in report.get("checks", [])]}
    def work(name, description, capability, block):
        native("new", "change", name, "--json")
        write(f"openspec/changes/{name}/proposal.md", f"## Why\n{description}\n## What Changes\n{description}\n## Capabilities\n### New Capabilities\n- {capability}: {description}\n### Modified Capabilities\nNone.\n## Impact\nUpdate `journal.py` and `tests/`.\n")
        write(f"openspec/changes/{name}/tasks.md", "## Implementation\n- [x] Implement and verify observable scenarios.\n")
        write(f"openspec/changes/{name}/specs/{capability}/spec.md", "## ADDED Requirements\n\n" + block)
    run(["git", "init", "-b", "main"])
    run(["git", "config", "user.name", "Qualification"])
    run(["git", "config", "user.email", "qualification@example.invalid"])
    run([sys.executable, "-I", "-S", str(ROOT / "skills/initialize-repo/scripts/initialize.py"), str(root), "--agents", "codex", "--no-hooks", "--ci", "none"])
    native("init", "--tools", "none", "--no-animation", "--no-copilot-cloud")
    p = kit.policy_at(root)
    p["checks"] = [{"name": "regression", "argv": ["{python}", "-m", "unittest", "discover", "-s", "tests", "-p", "test_journal.py"]}]
    p["requirements"] = {"REQ-JOURNAL-001": {"type": "automated", "checks": ["regression"]}}
    kit.atomic(root / kit.POLICY, kit.dump(p))
    run(["git", "add", "--all"])
    run(["git", "commit", "-m", "Initialize local-only engineering"])
    block = "### Requirement: Durable idempotent event append REQ-JOURNAL-001\nThe journal SHALL replay durable events, suppress identical IDs without appending, reject conflicts and report corrupt input explicitly.\n#### Scenario: Replay and retry\n- WHEN an event is appended, the journal is reopened and the same event retried\n- THEN one record remains and the retry returns false\n"
    work("add-event-journal", "Add a single-writer offline event journal with explicit corruption handling.", "event-journal", block)
    shutil.copyfile(ROOT / "examples/event-journal/journal.py", root / "journal.py")
    (root / "tests").mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "examples/event-journal/tests/test_journal.py", root / "tests/test_journal.py")
    first = require(kit.verify(root, p, "delivery", "add-event-journal"))
    native("validate", "add-event-journal", "--strict")
    native("archive", "add-event-journal", "--yes", "--json")
    first_archive = require(kit.verify(root, p, "delivery", "add-event-journal"))
    run(["git", "add", "--all"])
    run(["git", "commit", "-m", "Deliver durable event journal through native OpenSpec"])
    base = run(["git", "rev-parse", "HEAD"]).strip()
    listing = "### Requirement: List committed event identities REQ-JOURNAL-LIST-001\nThe journal SHALL list event IDs in insertion order after replay without exposing a mutable collection.\n#### Scenario: Duplicate event does not reorder IDs\n- WHEN a, b and duplicate a are appended and replayed\n- THEN ids returns the immutable tuple (a, b)\n"
    work("list-event-identities", "List durable event identities while preserving original append/replay/error behavior.", "event-listing", listing)
    p["checks"].append({"name": "acceptance", "argv": ["{python}", "-m", "unittest", "discover", "-s", "tests", "-p", "test_listing.py"]})
    p["requirements"]["REQ-JOURNAL-LIST-001"] = {"type": "automated", "checks": ["acceptance"]}
    kit.atomic(root / kit.POLICY, kit.dump(p))
    plan = {"cases": [{"id": "DT-JOURNAL-01", "effect": "preserve", "source": "original journal and six regression tests", "expected": "Durability, idempotent return/no append, conflicts, invalid input and corruption failures remain", "checks": ["regression"], "fixtures": ["tests/test_journal.py"]}, {"id": "DT-JOURNAL-02", "effect": "target", "source": "REQ-JOURNAL-LIST-001", "expected": "Immutable insertion-ordered IDs survive replay and duplicates", "checks": ["acceptance"]}]}
    write("openspec/changes/list-event-identities/behavior-plan.json", kit.dump(plan))
    findings = kit.change_findings(root, p, "list-event-identities", "delivery")
    assert any(x["code"] == "baseline-anchor" for x in findings), findings
    kit.baseline_inventory(root, p)
    def explanation(addition):
        write("docs/baseline/modules/journal.md", "# Offline journal\n## Purpose\nPersist single-writer events and deduplicate identities.\n## Flow\nReplay every JSON line; reject conflicting replay. Append validates identity and serializability before file I/O, rejects conflicting IDs, returns false for exact duplicate, writes, flushes/fsyncs, then updates memory. " + addition + "\n## State and failure\nThe object owns an insertion-ordered event map. Reopen reads disk. Invalid identity/unserializable input has no file side effect. Corrupt/torn JSON and conflicting replay fail explicitly; no silent repair. Single writer only.\n## Evidence\njournal.py:L1-L" + str(len((root / "journal.py").read_text().splitlines())) + "\n## Gaps\nNo multi-writer locking, parent directory fsync, crash/power-loss fault injection or production throughput certification.\n")
        kit.baseline_review(root, p, "docs/baseline/modules/journal.md", ["journal.py"], "qualification reviewer")
    explanation("Listing is not implemented yet.")
    before = require(kit.verify(root, p, "ready", "list-event-identities"))
    write("tests/test_listing.py", "import tempfile,unittest\nfrom pathlib import Path\nfrom journal import Journal\nclass Listing(unittest.TestCase):\n    def test_replay_order_and_duplicate(self):\n        with tempfile.TemporaryDirectory() as directory:\n            path=Path(directory)/'events'\n            journal=Journal(path)\n            self.assertEqual(journal.ids(), ())\n            journal.append('a', 1); journal.append('b', 2); journal.append('a', 1)\n            self.assertEqual(Journal(path).ids(), ('a','b'))\n")
    candidate = (root / "journal.py").read_text() + "\n    def ids(self):\n        return tuple(self.events)\n"
    write("journal.py", candidate)
    target = require(kit.verify(root, p, "delivery", "list-event-identities"))
    write("journal.py", candidate.replace("return False", "return True"))
    mutation = require(kit.verify(root, p, "delivery", "list-event-identities"), "FAIL")
    assert mutation["checks"] == [{"name": "regression", "status": "FAIL"}, {"name": "acceptance", "status": "PASS"}], mutation
    write("journal.py", candidate)
    kit.baseline_inventory(root, p)
    explanation("ids returns a tuple of map keys in insertion order; replay preserves the order and duplicates do not move IDs.")
    repaired = require(kit.verify(root, p, "delivery", "list-event-identities"))
    native("validate", "list-event-identities", "--strict")
    native("archive", "list-event-identities", "--yes", "--json")
    final = kit.local_check(root, p, base)
    require(final)
    assert not list(root.glob("openspec/changes/**/ark.json"))
    assert not run(["git", "remote"]).strip()
    assert not (root / ".github").exists()
    return {"status": "PASS", "workspace": str(root), "python": sys.version.split()[0], "openspec": "2.0.0", "entry": "installed initialize helper then native OpenSpec/direct implementation; no delivery Skill/pointer/sidecar", "remote": None, "consumer_ci": None, "first": first, "first_archive": first_archive, "baseline_before_second": before, "target": target, "negative_mutation": mutation, "repaired": repaired, "final": {"status": final["status"], "business_checks_executed": final["business_checks_executed"]}, "commands": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.workspace).resolve() if args.workspace else Path(tempfile.mkdtemp(prefix="ark-openspec-qualification-")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise SystemExit("Qualification workspace must be empty")
    report = qualify(root)
    Path(args.output).write_text(kit.dump(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "workspace": str(root), "output": args.output}))


if __name__ == "__main__":
    main()
