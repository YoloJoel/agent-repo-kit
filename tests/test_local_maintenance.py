"""Pointer-free navigation, real local enforcement, bounded handoff and impact."""
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class LocalMaintenanceTests(RepositoryCase):
    def fixture(self):
        self.git_start()
        p = self.initialize(hooks=True)
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "from app import value; assert value == 2"]}])
        self.commit()
        self.write("app.py", "value = 2\n")
        self.change(p, "alpha", scope=["app.py"])
        return p

    def test_startup_finds_real_diff_without_pointer_or_full_inventory(self):
        p = self.fixture()
        with patch.object(kit, "inventory_files", side_effect=AssertionError("Startup must not scan inventory")), patch.object(kit, "run_check", side_effect=AssertionError("Startup must not run business tests")):
            result = kit.context(self.root, p, "new-session")
        self.assertEqual(result["active_change"], "alpha")
        self.assertIsNone(kit.active(self.root, "new-session"))
        self.assertNotIn("deliver-change", result["workflow"])
        response = kit.hook(self.root, p, "stop", "claude", {"session_id": "new-session"})
        self.assertIn("systemMessage", response)
        self.assertNotIn("decision", response)

    def test_explicit_overlapping_scopes_stay_ambiguous(self):
        p = self.fixture()
        self.change(p, "beta", scope=["app.py"])
        self.assertIsNone(kit.context(self.root, p)["active_change"])
        result = kit.local_check(self.root, p)
        self.assertEqual(result["status"], "PENDING")
        self.assertEqual(result["overlaps"], {"app.py": ["alpha", "beta"]})
        self.assertFalse(result["business_checks_executed"])

    def test_disjoint_work_items_validate_actual_diff_without_false_scope_failure(self):
        p = self.fixture()
        self.write("other.py", "other = 3\n")
        self.change(p, "beta", scope=["other.py"])
        result = kit.local_check(self.root, p, "HEAD")
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual({item["change"] for item in result["changes"]}, {"alpha", "beta"})
        self.assertTrue(result["business_checks_executed"])
        self.assertEqual(kit.read_json(self.root / ".ai/runtime/last-check.json"), result)

    def test_document_only_pass_explicitly_reports_no_business_execution(self):
        self.git_start()
        p = self.initialize()
        self.commit()
        self.write("README.md", "Small wording improvement\n")
        result = kit.local_check(self.root, p)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stage"], "structure-or-documents")
        self.assertFalse(result["business_checks_executed"])

    def test_native_pause_does_not_create_a_second_lifecycle(self):
        p = self.fixture()
        directory = self.root / "openspec/changes/alpha"
        (directory / "ark.json").unlink()
        result = kit.checkpoint(self.root, p, "alpha", "Partial implementation", "Continue target validation", paused=True)
        self.assertEqual(result["state"], "paused")
        self.assertFalse((directory / "ark.json").exists())
        self.assertEqual(kit.hook(self.root, p, "stop", "claude", {}), {})
        self.assertIn("alpha/checkpoint.md", kit.context(self.root, p)["resume"])

    def test_impact_targets_changed_source_without_rewriting_history(self):
        p = self.fixture()
        kit.baseline_inventory(self.root, p)
        self.write("docs/baseline/modules/app.md", "# App\n## Purpose\nProvide value two.\n## Flow\nImport constant.\n## State and failure\nConstant state.\n## Evidence\napp.py:L1\n## Gaps\nNo external claim.\n")
        kit.baseline_review(self.root, p, "docs/baseline/modules/app.md", ["app.py"], "reviewer")
        raw = {x.relative_to(self.root).as_posix(): x.read_bytes() for x in (self.root / "docs/baseline/raw").rglob("*") if x.is_file()}
        self.write("app.py", "value = 4\n")
        result = kit.impact(self.root, p)
        self.assertEqual(result["status"], "PENDING", result)
        self.assertEqual(result["knowledge"][0]["freshness"], "stale")
        self.assertEqual(raw, {name: (self.root / name).read_bytes() for name in raw})

    def test_local_history_protection_uses_head_without_ci_base(self):
        self.git_start()
        p = self.initialize()
        self.write("docs/baseline/raw/fact.json", "{}\n")
        self.commit()
        self.write("docs/baseline/raw/fact.json", '{"changed":true}\n')
        result = kit.local_check(self.root, p)
        self.assertEqual(result["status"], "FAIL", result)
        self.assertIn("raw-history", {x.get("code") for x in result["changes"]})

    def test_real_precommit_blocks_missing_scope_and_preserves_custom_hooks(self):
        p = self.fixture()
        report = kit.install_git_hook(self.root, p)
        self.assertEqual(report["status"], "PASS", report)
        self.write("unscoped.py", "value = 99\n")
        self.run_git("add", "--all")
        run = subprocess.run(["git", "-C", str(self.root), "commit", "-m", "should be rejected"], capture_output=True, encoding="utf-8")
        self.assertNotEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("untracked-behavior-change", run.stdout + run.stderr)
        hook = Path(report["path"])
        hook.write_text("#!/bin/sh\necho human hook\n", encoding="utf-8")
        before = hook.read_bytes()
        self.assertEqual(kit.install_git_hook(self.root, p)["status"], "PENDING")
        self.assertEqual(hook.read_bytes(), before)

    def test_path_association_disambiguates_native_work_without_a_global_pointer(self):
        p = self.fixture()
        self.change(p, "beta", scope=["app.py"])
        p["change_associations"] = {"app.py": "alpha"}
        self.configure(p, p["checks"])
        result = kit.local_check(self.root, p)
        self.assertEqual(result["status"], "PASS", result)
        alpha = next(item for item in result["changes"] if item.get("change") == "alpha")
        beta = next(item for item in result["changes"] if item.get("change") == "beta")
        self.assertEqual(alpha["phase"], "delivery")
        self.assertEqual(beta["phase"], "specification")
        self.assertIsNone(kit.active(self.root))
        p["change_associations"] = {"app.py": "missing-work"}
        result = kit.local_check(self.root, p)
        self.assertEqual(result["status"], "FAIL", result)

    def test_native_bulleted_adr_status_is_valid_and_accepted_body_is_protected(self):
        self.git_start()
        p = self.initialize()
        text = "# Native ADR\n- Status: Accepted\n## Context\nOriginal\n## Decision\nUse native artifacts.\n## Alternatives\nRewrite everything.\n## Consequences\nPreserve history.\n"
        self.write("docs/adr/0001-native.md", text)
        self.assertEqual(kit.structure_findings(self.root, p), [])
        self.commit()
        self.write("docs/adr/0001-native.md", text.replace("Original", "Changed accepted history"))
        result = kit.local_check(self.root, p)
        self.assertEqual(result["status"], "FAIL", result)
        self.assertIn("accepted-adr", {item.get("code") for item in result["changes"]})
