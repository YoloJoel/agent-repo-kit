"""Observable CLI/consumer workflows. No network, model API or third-party dependency."""

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_repo_kit import core as kit


class RepositoryCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def initialize(self, mode="new", **options):
        kit.init_repo(self.root, mode, agents=["codex", "claude", "opencode"], **options)
        return kit.policy_at(self.root)

    def configure(self, p, checks):
        p["checks"] = checks
        kit.atomic(self.root / kit.POLICY, kit.dump(p))

    def change(self, p, change="example", kind="maintenance", scope=None, requirements=None):
        kit.new_change(self.root, p, change, kind, scope or ["app.py", "tests"], requirements or [])
        base = f"{p['paths']['changes']}/{change}"
        self.write(base + "/proposal.md", "# Proposal\nPreserve input/output while restructuring implementation.\n")
        self.write(base + "/design.md", "# Design\nKeep public API; existing boundary tests establish compatibility.\n")
        self.write(base + "/tasks.md", "# Tasks\n- [x] Inspect actual behavior and complete the scoped work.\n")
        return self.root / base

    def review_app(self, p, flow="Return x * 2."):
        self.write("docs/baseline/modules/app.md", "# App\n\n## Purpose\nDouble a number.\n\n## Flow\n" + flow + "\n\n## State and failure\nNo persistent state. Python arithmetic errors propagate.\n\n## Evidence\napp.py:L1-L2\n\n## Gaps\nStatic review; tests are separate execution evidence.\n")
        return kit.baseline_review(self.root, p, "docs/baseline/modules/app.md", ["app.py"], "test-reviewer")

    def preserve_double(self, p):
        self.write("tests/preserve.py", "from app import double\nassert double(3) == 6 and double(-1) == -2\n")
        self.write("openspec/changes/example/behavior-plan.json", kit.dump({"cases": [{"id": "DT-DOUBLE-01", "effect": "preserve", "source": "app.py:L1-L2", "expected": "Positive and negative inputs double", "checks": ["unit"], "fixtures": ["tests/preserve.py"]}]}))

    def characterize_value_change(self, p):
        self.write("tests/before.py", "from app import value\nassert value == 1\n")
        p["checks"].append({"name": "before", "argv": ["{python}", "-c", "exec(open('tests/before.py').read())"], "phases": ["ready"]})
        self.configure(p, p["checks"])
        self.write("docs/value-choice.md", "Change the initial value from one to two; this is the intended behavior change.\n")
        self.write("openspec/changes/example/behavior-plan.json", kit.dump({"cases": [{"id": "DT-VALUE-01", "effect": "target", "source": "app.py:L1", "expected": "Value is two", "checks": ["unit"], "before_checks": ["before"], "before_expected": "Value is one", "replaces": "initial value one", "decision": "docs/value-choice.md", "fixtures": ["tests/before.py"]}]}))
        kit.baseline_inventory(self.root, p)
        self.write("docs/baseline/modules/value.md", "# Value\n## Purpose\nProvide initial value.\n## Flow\nRead module constant.\n## State and failure\nImport-time state, no external failure.\n## Evidence\napp.py:L1\n## Gaps\nOnly this constant is reviewed.\n")
        kit.baseline_review(self.root, p, "docs/baseline/modules/value.md", ["app.py"], "fixture")
        result = kit.verify(self.root, p, "ready", "example")
        self.assertEqual(result["status"], "PASS", result)

    def review_current_value(self, p):
        kit.baseline_inventory(self.root, p)
        self.write("docs/baseline/modules/value.md", "# Value\n## Purpose\nProvide initial value.\n## Flow\nRead the constant two after the accepted change.\n## State and failure\nImport-time state; no external failure.\n## Evidence\napp.py:L1\n## Gaps\nOnly this constant is reviewed.\n")
        kit.baseline_review(self.root, p, "docs/baseline/modules/value.md", ["app.py"], "fixture")

    def git_start(self):
        if not shutil.which("git"):
            self.skipTest("Git is not installed")
        self.run_git("init", "-b", "main")
        self.run_git("config", "user.name", "Fixture")
        self.run_git("config", "user.email", "fixture@example.invalid")

    def run_git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def commit(self):
        self.run_git("add", "--all")
        self.run_git("commit", "-m", "fixture")
        return self.run_git("rev-parse", "HEAD")


class InitializationTests(RepositoryCase):
    def test_repeat_without_agent_flag_preserves_existing_selection(self):
        kit.init_repo(self.root, agents=["codex"])
        result = kit.init_repo(self.root)
        self.assertEqual(result["changed"], [])
        self.assertEqual(kit.policy_at(self.root)["agents"], ["codex"])
        self.assertFalse((self.root / ".claude").exists())

    def test_doctor_distinguishes_missing_and_generated_hook_config(self):
        p = self.initialize()
        report = kit.doctor(self.root, p)
        self.assertEqual(report["adapters"][0]["hooks"], "NOT_CONFIGURED")
        self.initialize(hooks=True)
        report = kit.doctor(self.root, kit.policy_at(self.root))
        self.assertTrue(all(x["hooks"] == "CONFIGURATION_ONLY" for x in report["adapters"] if x["agent"] != "opencode"))

    def test_human_instruction_bytes_keep_crlf_and_trailing_spaces(self):
        original = b"# Human rules\r\nPreserve formatting.  \r\n"
        (self.root / "AGENTS.md").write_bytes(original)
        self.initialize()
        self.assertTrue((self.root / "AGENTS.md").read_bytes().startswith(original))

    def test_empty_repository_is_new_without_fabricated_baseline(self):
        result = kit.init_repo(self.root)
        self.assertEqual(result["mode"], "new")
        self.assertEqual(result["baseline"], "NOT_APPLICABLE")
        self.assertFalse((self.root / "docs/baseline/coverage.json").exists())
        self.assertEqual(kit.structure_findings(self.root, kit.policy_at(self.root)), [])

    def test_idempotent_merge_preserves_human_rules_native_specs_and_dirty_files(self):
        # REQ-INIT-001: preserve human assets and make repeated installation inert.
        self.write("app.py", "def double(x):\n    return x * 2\n")
        human = "# Existing project\nKeep the old API and formatting rules.\n"
        self.write("AGENTS.md", human)
        native = "### Requirement: Stable contract STK-007\nThe original ID stays.\n"
        self.write("openspec/specs/original/spec.md", native)
        self.write("openspec/config.yaml", "schema: spec-driven\n")
        self.write("README.md", "Human's uncommitted draft\n")
        p = self.initialize("existing")
        before = {x.relative_to(self.root).as_posix(): x.read_bytes() for x in self.root.rglob("*") if x.is_file() and ".ai/runtime/" not in x.relative_to(self.root).as_posix() and x.name != "init-report.json"}
        second = kit.init_repo(self.root, agents=p["agents"])
        after = {relative: (self.root / relative).read_bytes() for relative in before}
        self.assertEqual(before, after)
        self.assertEqual(second["changed"], [])
        self.assertTrue((self.root / "AGENTS.md").read_text().startswith(human))
        self.assertEqual((self.root / "openspec/specs/original/spec.md").read_text(), native)
        self.assertEqual((self.root / "README.md").read_text(), "Human's uncommitted draft\n")

    def test_conflict_is_preflighted_before_writing_policy_or_rules(self):
        self.write("hack/ai/ark.py", "human content\n")
        self.write("AGENTS.md", "human rules\n")
        with self.assertRaisesRegex(kit.KitError, "conflict"):
            self.initialize()
        self.assertFalse((self.root / kit.POLICY).exists())
        self.assertEqual((self.root / "AGENTS.md").read_text(), "human rules\n")

    def test_edited_managed_block_is_never_silently_overwritten(self):
        self.initialize()
        path = self.root / "AGENTS.md"
        path.write_text(path.read_text().replace("Use the user's language", "Use human customization"))
        with self.assertRaisesRegex(kit.KitError, "managed block"):
            self.initialize()

    def test_existing_hooks_merge_once_without_changing_other_settings(self):
        existing = {"permissions": {"allow": ["Read"]}, "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo custom"}]}]}}
        self.write(".claude/settings.json", kit.dump(existing))
        self.initialize(hooks=True)
        self.initialize(hooks=True)
        result = kit.read_json(self.root / ".claude/settings.json")
        self.assertEqual(result["permissions"], existing["permissions"])
        self.assertEqual(len(result["hooks"]["SessionStart"]), 2)
        self.assertEqual(result["hooks"]["SessionStart"][0], existing["hooks"]["SessionStart"][0])

    def test_vendored_runtime_runs_from_nested_directory_without_package_install(self):
        self.initialize()
        nested = self.root / "source/nested"
        nested.mkdir(parents=True)
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        result = subprocess.run([sys.executable, str(self.root / "hack/ai/ark.py"), "doctor"], cwd=nested, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["branch_protection"], "NOT_VERIFIED")
        self.assertTrue(all(x["live_loading"] == "NOT_VERIFIED" for x in data["adapters"]))

    def test_unconfirmed_build_candidates_are_not_executed(self):
        self.write("pom.xml", "<project/>\n")
        p = self.initialize("existing")
        self.assertEqual(p["checks"], [])
        self.assertEqual(p["command_candidates"][0]["argv"], ["mvn", "test"])
        self.assertFalse(p["command_candidates"][0]["confirmed"])

    def test_transaction_restores_only_touched_files_on_partial_failure(self):
        self.write("human.txt", "unchanged")
        self.write("first.txt", "before")
        real_atomic = kit.atomic
        count = 0

        def fail_second(path, data):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("disk full")
            return real_atomic(path, data)

        with patch.object(kit, "atomic", side_effect=fail_second):
            with self.assertRaises(OSError):
                kit.transact(self.root, {"first.txt": "after", "second.txt": "new"})
        self.assertEqual((self.root / "first.txt").read_text(), "before")
        self.assertEqual((self.root / "human.txt").read_text(), "unchanged")
        self.assertFalse((self.root / "second.txt").exists())

    def test_path_traversal_and_symlink_destinations_are_rejected(self):
        for relative in ("../outside", "/outside", "C:/outside", "a/../../outside", "a\\outside"):
            with self.subTest(path=relative), self.assertRaises(kit.KitError):
                kit.safe(self.root, relative)
        try:
            (self.root / "linked").symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        with self.assertRaises(kit.KitError):
            kit.safe(self.root, "linked/file")


class BaselineTests(RepositoryCase):
    def test_combined_source_and_test_citations_do_not_match_filename_suffix(self):
        self.write("app.py", "def double(x):\n    return x * 2\n")
        self.write("tests/test_app.py", "# tests\n" * 20)
        p = self.initialize("existing")
        self.write("docs/baseline/modules/combined.md", "# Module\n## Purpose\nDouble and test.\n## Flow\nReturn the product.\n## State and failure\nStateless.\n## Evidence\napp.py:L1-L2\ntests/test_app.py:L1-L20\n## Gaps\nStatic review only.\n")
        kit.baseline_review(self.root, p, "docs/baseline/modules/combined.md", ["app.py", "tests/test_app.py"], "agent")
        self.assertEqual(kit.baseline_findings(self.root, p, ["app.py", "tests/test_app.py"]), [])

    def test_inventory_is_pending_and_review_needs_real_explanation_and_citations(self):
        # REQ-BASELINE-001: inventory is not approval; citations need real ranges.
        self.write("app.py", "def double(x):\n    return x * 2\n")
        p = self.initialize("existing")
        self.assertTrue(kit.baseline_findings(self.root, p, ["app.py"]))
        self.write("docs/baseline/modules/app.md", "# Functions\napp.py:L999\n")
        with self.assertRaisesRegex(kit.KitError, "module template"):
            kit.baseline_review(self.root, p, "docs/baseline/modules/app.md", ["app.py"], "agent")
        self.review_app(p)
        self.assertEqual(kit.baseline_findings(self.root, p, ["app.py"]), [])

    def test_refresh_preserves_unchanged_review_and_raw_snapshots(self):
        self.write("app.py", "def double(x):\n    return x * 2\n")
        p = self.initialize("existing")
        self.review_app(p)
        raw = {x.name: x.read_bytes() for x in (self.root / "docs/baseline/raw").glob("*.json")}
        kit.baseline_inventory(self.root, p)
        self.assertEqual(kit.baseline_findings(self.root, p, ["app.py"]), [])
        self.write("app.py", "def double(x):\n    return x + x\n")
        self.assertTrue(kit.baseline_findings(self.root, p, ["app.py"]))
        kit.baseline_inventory(self.root, p)
        for name, content in raw.items():
            self.assertEqual((self.root / "docs/baseline/raw" / name).read_bytes(), content)

    def test_refactor_keeps_prechange_anchor_and_can_deliver_after_source_changes(self):
        self.write("app.py", "def double(x):\n    return x * 2\n")
        p = self.initialize("existing")
        self.review_app(p)
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "from app import double; assert double(3)==6 and double(-1)==-2"]}])
        self.change(p, scope=["app.py"])
        self.preserve_double(p)
        ready = kit.verify(self.root, p, "ready", "example")
        self.assertEqual(ready["status"], "PASS", ready)
        anchor = self.root / "openspec/changes/example/baseline-anchor.json"
        before = anchor.read_bytes()
        self.write("app.py", "def double(x):\n    return x + x\n")
        kit.baseline_inventory(self.root, p)
        self.review_app(p, "Return x + x; observed integer results are preserved.")
        delivery = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(delivery["status"], "PASS", delivery)
        self.assertEqual(anchor.read_bytes(), before)
        self.assertEqual(kit.verify(self.root, p, "ready", "example")["status"], "PENDING")
        self.assertEqual(anchor.read_bytes(), before)

    def test_custom_baseline_mapping_does_not_inventory_its_own_reports(self):
        self.write("app.py", "def double(x):\n    return x * 2\n")
        p = self.initialize("existing")
        p["paths"]["baseline"] = "knowledge/current"
        kit.atomic(self.root / kit.POLICY, kit.dump(p))
        kit.baseline_inventory(self.root, p)
        self.write("knowledge/current/modules/app.md", "module explanation\n")
        kit.baseline_inventory(self.root, p)
        coverage = kit.read_json(self.root / "knowledge/current/coverage.json")
        self.assertFalse(any(x.startswith("knowledge/current/") for x in coverage["files"]))


class DeliveryTests(RepositoryCase):
    def test_archive_rebases_evidence_and_keeps_ci_and_context_usable(self):
        # REQ-ARCHIVE-001: successful close must leave a usable candidate workflow.
        self.git_start()
        p = self.initialize()
        self.write("app.py", "value = 1\n")
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "from app import value; assert value == 2"]}])
        p["requirements"] = {"REQ-OUTPUT-001": {"type": "automated", "checks": ["unit"]}}
        self.configure(p, p["checks"])
        base = self.commit()
        directory = self.change(p, scope=["app.py", "tests"])
        self.characterize_value_change(p)
        self.write("app.py", "value = 2\n")
        spec = "### Requirement: Current output REQ-OUTPUT-001\nThe system SHALL output two.\nVerification: automated\n#### Scenario: Output\n- WHEN read\n- THEN value is two.\n"
        self.write("openspec/changes/example/specs/output/spec.md", "## MODIFIED Requirements\n" + spec)
        self.write("openspec/specs/output/spec.md", spec)
        artifact = "openspec/changes/example/sync-review.md"
        self.write(artifact, "Reviewed actual delta and current spec: output is now two; explicit reviewed synchronization, native CLI not invoked.\n")
        kit.record_sync(self.root, p, "example", artifact, "agent")
        self.review_current_value(p)
        kit.activate(self.root, "example", "session-a")
        self.assertEqual(kit.verify(self.root, p, "delivery", "example")["status"], "PASS")
        before = kit.fingerprint(self.root, p, "example")
        archived = kit.close_change(self.root, p, "example")
        sync = kit.read_json(self.root / archived["path"] / "spec-sync.json")
        self.assertTrue((self.root / sync["artifact"]).is_file())
        self.assertEqual(kit.fingerprint(self.root, p, "example"), before)
        self.assertIsNone(kit.context(self.root, p, "session-a")["active_change"])
        result = kit.ci_verify(self.root, p, base)
        self.assertEqual(result["status"], "PASS", result)

    def test_retired_requirement_sync_and_exact_id_matching(self):
        p = self.initialize()
        directory = self.change(p, kind="feature", requirements=["REQ-LEGACY-001"])
        metadata = kit.read_json(directory / "ark.json")
        metadata["removed_requirements"] = ["REQ-LEGACY-001"]
        kit.atomic(directory / "ark.json", kit.dump(metadata))
        self.write("openspec/changes/example/specs/change/spec.md", "## REMOVED Requirements\n### Requirement: Retired entry REQ-LEGACY-001\n#### Scenario: Legacy entry no longer exposed\n")
        self.write("openspec/specs/current/spec.md", "### Requirement: REQ-LEGACY-0010\nA different current requirement.\n")
        self.write("docs/sync-review.md", "Reviewed removal of the old entry and retained the distinct 0010 identity.\n")
        kit.record_sync(self.root, p, "example", "docs/sync-review.md", "agent")
        metadata["removed_requirements"] = []
        kit.atomic(directory / "ark.json", kit.dump(metadata))
        with self.assertRaisesRegex(kit.KitError, "missing from current"):
            kit.record_sync(self.root, p, "example", "docs/sync-review.md", "agent")

    def test_real_consumer_tests_pass_and_changed_source_invalidates_completion(self):
        # REQ-VERIFY-001: actual assertions execute and changed inputs invalidate PASS.
        p = self.initialize()
        self.write("app.py", "def clamp(x, lo, hi):\n    if lo > hi:\n        raise ValueError('inverted')\n    return max(lo, min(x, hi))\n")
        self.write("tests/test_app.py", "import unittest\nfrom app import clamp\nclass ClampTests(unittest.TestCase):\n    def test_bounds(self):\n        # REQ-CLAMP-001\n        self.assertEqual(clamp(-1, 0, 10), 0)\n        self.assertEqual(clamp(11, 0, 10), 10)\n        self.assertEqual(clamp(4, 0, 10), 4)\n    def test_invalid(self):\n        with self.assertRaises(ValueError): clamp(1, 10, 0)\n")
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-m", "unittest", "discover", "-s", "tests"], "required": True}])
        directory = self.change(p, kind="feature", requirements=["REQ-CLAMP-001"])
        spec = "### Requirement: Clamp REQ-CLAMP-001\nThe system SHALL clamp input and reject inverted bounds.\nVerification: automated\n#### Scenario: Out of range\n- WHEN input is outside bounds\n- THEN return closest bound; reject inverted bounds.\n"
        self.write("openspec/changes/example/specs/change/spec.md", "## ADDED Requirements\n" + spec)
        self.write("openspec/specs/clamp/spec.md", spec)
        self.write("docs/sync-review.md", "Reviewed actual current spec against the delta: bounded output and inverted-bound rejection are preserved.\n")
        kit.record_sync(self.root, p, "example", "docs/sync-review.md", "fixture-agent")
        result = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["checks"][0]["exit_code"], 0)
        self.assertIn("Ran 2 tests", (self.root / result["checks"][0]["log"]).read_text())
        self.write("app.py", "def clamp(x, lo, hi):\n    return x\n")
        with self.assertRaisesRegex(kit.KitError, "Fresh PASS"):
            kit.close_change(self.root, p, "example")
        failed = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(failed["status"], "FAIL")
        self.assertEqual(failed["checks"][0]["status"], "FAIL")

    def test_no_checks_or_missing_required_executable_is_pending(self):
        p = self.initialize()
        self.change(p)
        self.assertEqual(kit.verify(self.root, p, "delivery", "example")["status"], "PENDING")
        self.configure(p, [{"name": "unavailable", "argv": ["ark-nonexistent-check-executable"]}])
        result = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(result["status"], "PENDING")
        self.assertEqual(result["checks"][0]["status"], "NOT_RUN")

    def test_partial_execution_cannot_satisfy_unselected_required_checks(self):
        p = self.initialize()
        self.change(p)
        self.configure(p, [{"name": name, "argv": ["{python}", "-c", "print('executed')"]} for name in ("unit", "integration")])
        result = kit.verify(self.root, p, "delivery", "example", selected=["unit"])
        self.assertEqual(result["status"], "PENDING")
        self.assertEqual([x["status"] for x in result["checks"]], ["PASS", "NOT_RUN"])

    def test_timeout_is_failed_optional_failure_remains_visible(self):
        p = self.initialize()
        self.change(p)
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "pass"]}, {"name": "optional", "argv": ["{python}", "-c", "import sys;sys.exit(1)"], "required": False}])
        report = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"][1]["status"], "FAIL")
        self.configure(p, [{"name": "slow", "argv": ["{python}", "-c", "import time;time.sleep(1)"], "timeout": 0.02}])
        report = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"][0]["reason"], "timeout")

    def test_check_modifying_verification_input_is_failed(self):
        p = self.initialize()
        self.write("app.py", "value = 1\n")
        self.change(p)
        self.configure(p, [{"name": "mutator", "argv": ["{python}", "-c", "from pathlib import Path;Path('app.py').write_text('value = 2\\n')"]}])
        report = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("inputs-changed", [x["code"] for x in report["findings"]])

    def test_manual_requirement_uses_real_external_record_without_fake_test(self):
        p = self.initialize()
        directory = self.change(p, kind="maintenance", requirements=["REQ-OPS-001"])
        self.write("openspec/specs/ops/spec.md", "### Requirement: REQ-OPS-001\nThe system SHALL support operator recovery.\nVerification: manual\n#### Scenario: Operator can recover\n- WHEN recovery is requested\n- THEN the service resumes.\n")
        p["requirements"] = {"REQ-OPS-001": {"type": "manual", "checks": ["inspection"]}}
        self.configure(p, [{"name": "inspection", "type": "manual", "required": True}])
        self.assertEqual(kit.verify(self.root, p, "delivery", "example")["status"], "PENDING")
        self.write("docs/inspection.txt", "Actual operator recovery result and observations.\n")
        kit.record_evidence(self.root, p, "example", "inspection", "docs/inspection.txt", "operator", "PASS", "Recovery observed")
        report = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(report["status"], "PASS", report)
        self.write("docs/inspection.txt", "Changed observation\n")
        self.assertEqual(kit.verify(self.root, p, "delivery", "example")["status"], "PENDING")

    def test_committed_pass_without_runtime_execution_cannot_close(self):
        p = self.initialize()
        directory = self.change(p)
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "pass"]}])
        report = kit.verify(self.root, p, "delivery", "example")
        self.assertEqual(report["status"], "PASS")
        (self.root / ".ai/runtime/runs" / report["run_id"] / "result.json").unlink()
        with self.assertRaisesRegex(kit.KitError, "Fresh PASS"):
            kit.close_change(self.root, p, "example")

    def test_completion_archives_and_prevents_id_reuse(self):
        p = self.initialize()
        self.change(p)
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "pass"]}])
        self.assertEqual(kit.verify(self.root, p, "delivery", "example")["status"], "PASS")
        result = kit.close_change(self.root, p, "example")
        self.assertEqual(result["state"], "archived")
        self.assertTrue((self.root / result["path"] / "verify-report.md").is_file())
        with self.assertRaisesRegex(kit.KitError, "already archived"):
            kit.new_change(self.root, p, "example", "docs", ["README.md"], [])


class HookAndCITests(RepositoryCase):
    def test_stop_continuation_is_bounded_per_session_and_turn(self):
        # REQ-CONTEXT-001: changes cannot reset the same turn's continuation bound.
        p = self.initialize()
        p["hook_mode"] = "enforce"
        self.change(p)
        kit.activate(self.root, "example", "session-a")
        payload = {"session_id": "session-a", "turn_id": "turn-a", "stop_hook_active": False}
        first = kit.hook(self.root, p, "stop", "codex", payload)
        self.assertEqual(first["decision"], "block")
        self.write("app.py", "changed = True\n")
        self.assertNotIn("decision", kit.hook(self.root, p, "stop", "codex", payload))
        self.assertEqual(kit.hook(self.root, p, "stop", "codex", {**payload, "stop_hook_active": True}), {})
        self.assertEqual(kit.hook(self.root, p, "stop", "codex", {**payload, "session_id": "session-b"}), {})

    def test_blocked_checkpoint_and_startup_allow_pause_without_full_scan(self):
        p = self.initialize()
        p["hook_mode"] = "enforce"
        self.change(p)
        kit.activate(self.root, "example", "abc")
        kit.checkpoint(self.root, p, "example", "Actual progress saved", "Need an external test environment", True)
        self.assertEqual(kit.hook(self.root, p, "stop", "claude", {"session_id": "abc"}), {})
        with patch.object(kit, "inventory_files", side_effect=AssertionError("startup must not scan")):
            result = kit.hook(self.root, p, "session", "claude", {"session_id": "abc"})
        self.assertIn("checkpoint.md", result["hookSpecificOutput"]["additionalContext"])

    def test_actual_hook_subprocess_protocol_from_nested_cwd(self):
        self.initialize(hooks=True)
        nested = self.root / "nested"
        nested.mkdir()
        result = subprocess.run([sys.executable, str(self.root / "hack/ai/ark.py"), "hook", "session", "--agent", "codex"], input=kit.dump({"cwd": str(nested), "session_id": "xyz"}), cwd=nested, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        response = json.loads(result.stdout)
        self.assertEqual(response["hookSpecificOutput"]["hookEventName"], "SessionStart")
        invalid = subprocess.run([sys.executable, str(self.root / "hack/ai/ark.py"), "hook", "stop", "--agent", "claude"], input="not json", text=True, capture_output=True)
        self.assertEqual(invalid.returncode, 0)
        self.assertIn("unavailable", json.loads(invalid.stdout)["systemMessage"])

    def test_branch_and_worktree_pointers_are_isolated(self):
        self.git_start()
        p = self.initialize()
        self.write("README.md", "fixture\n")
        self.change(p)
        self.commit()
        kit.activate(self.root, "example", "session")
        self.run_git("switch", "-c", "other")
        self.assertIsNone(kit.active(self.root, "session"))
        other = self.root.parent / (self.root.name + "-worktree")
        self.run_git("worktree", "add", "-b", "worktree", str(other))
        self.addCleanup(lambda: self.run_git("worktree", "remove", "--force", str(other)))
        self.assertIsNone(kit.active(other, "session"))

    def test_ci_catches_unscoped_source_and_rechecks_completed_archive(self):
        self.git_start()
        p = self.initialize()
        self.write("app.py", "value = 1\n")
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "from app import value;assert value==2"]}])
        base = self.commit()
        self.write("app.py", "value = 2\n")
        self.assertEqual(kit.ci_verify(self.root, p, base)["status"], "FAIL")
        self.write("app.py", "value = 1\n")
        self.change(p, scope=["app.py", "tests"])
        self.characterize_value_change(p)
        self.write("app.py", "value = 2\n")
        self.review_current_value(p)
        self.assertEqual(kit.verify(self.root, p, "delivery", "example")["status"], "PASS")
        kit.close_change(self.root, p, "example")
        result = kit.ci_verify(self.root, p, base)
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["changes"][0]["run_id"])

    def test_lightweight_note_is_hash_bound_and_runs_existing_checks(self):
        # REQ-CI-001: declarations cover exact content and cannot hide later changes.
        self.git_start()
        p = self.initialize()
        self.write("app.py", "value=1\n")
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "from app import value;assert value==1"]}])
        base = self.commit()
        self.write("app.py", "value = 1\n")
        kit.note_change(self.root, p, ["app.py"], "mechanical", "Only whitespace formatting changed; token semantics are unchanged.", "agent")
        result = kit.ci_verify(self.root, p, base)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["lightweight_checks"][0]["status"], "PASS")
        self.write("app.py", "value = 2\n")
        self.assertEqual(kit.ci_verify(self.root, p, base)["status"], "FAIL")

    def test_ci_preserves_accepted_adr_and_raw_history(self):
        self.git_start()
        p = self.initialize()
        adr = "# Choice\nStatus: Accepted\n## Context\nOriginal\n## Decision\nA\n## Alternatives\nB\n## Consequences\nC\n"
        self.write("docs/adr/0001-choice.md", adr)
        self.write("docs/baseline/raw/original.json", "{}\n")
        base = self.commit()
        self.write("docs/adr/0001-choice.md", adr.replace("Original", "Rewritten"))
        self.write("docs/baseline/raw/original.json", '{"rewritten":true}\n')
        report = kit.ci_verify(self.root, p, base)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual({x["code"] for x in report["changes"]}, {"accepted-adr", "raw-history"})

    def test_invalid_policy_and_nonzero_cli_status_are_actionable(self):
        p = self.initialize()
        p["checks"] = [{"name": "unsafe", "argv": "echo pretend"}]
        kit.atomic(self.root / kit.POLICY, kit.dump(p))
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = kit.main(["--repo", str(self.root), "doctor"])
        self.assertEqual(status, 1)
        self.assertIn("argv", json.loads(stream.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()
