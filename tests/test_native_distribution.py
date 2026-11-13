"""Native distribution contracts, including an installed-folder-only execution path."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def files_hash(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


class NativeDistributionTests(unittest.TestCase):
    """REQ-NATIVE-001: platform installation is separate from project initialization."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name).resolve()
        self.target = self.workspace / "business repository"
        self.target.mkdir()
        self.installed = self.workspace / "installed skills"
        shutil.copytree(ROOT / "skills", self.installed)

    def run_initializer(self, *args):
        path = self.installed / "initialize-repo/scripts/initialize.py"
        return subprocess.run([sys.executable, "-I", "-S", str(path), str(self.target), "--agents", "codex,claude", *args],
                              cwd=self.workspace, capture_output=True, encoding="utf-8")

    def test_claude_manifest_marketplace_and_standard_skill_layout(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], "agent-repo-kit")
        self.assertEqual(market["plugins"][0]["name"], plugin["name"])
        self.assertEqual(market["plugins"][0]["source"], "./")
        self.assertFalse((ROOT / "CLAUDE.md").exists(), "Claude does not load root CLAUDE as plugin instructions")
        names = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual(names, ["baseline-repo", "initialize-repo"])
        for path in (ROOT / "skills").rglob("*"):
            self.assertFalse(path.is_symlink(), str(path))

    def test_copied_skill_only_initializes_without_repository_or_packages(self):
        shutil.rmtree(self.installed / "baseline-repo")
        (self.target / "app.py").write_text("def double(x):\n    return x * 2\n")
        (self.target / "README.md").write_text("Uncommitted user note\n")
        original = b"# Existing human rule\r\nPreserve API.  \r\n"
        (self.target / "AGENTS.md").write_bytes(original)
        result = self.run_initializer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["entry"], "installed-skill")
        self.assertEqual(data["skill_delivery"], "installed")
        self.assertEqual(data["mode"], "existing")
        self.assertEqual(data["baseline"], "PENDING")
        self.assertTrue((self.target / "AGENTS.md").read_bytes().startswith(original))
        self.assertEqual((self.target / "README.md").read_text(encoding="utf-8"), "Uncommitted user note\n")
        self.assertFalse((self.target / ".agents/skills").exists())
        self.assertFalse((self.target / ".claude/skills").exists())
        self.assertTrue(all(item["skill_files"] is None for item in data["diagnostics"]["adapters"]))
        shutil.rmtree(self.installed)
        command = [sys.executable, "-I", "-S", str(self.target / "hack/ai/ark.py"), "doctor"]
        run = subprocess.run(command, cwd=self.target, capture_output=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_installer_lock_does_not_turn_an_empty_repository_into_legacy_code(self):
        (self.target / "skills-lock.json").write_text('{"version": 1, "skills": {}}\n')
        result = self.run_initializer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "new")

    def test_project_installed_skills_are_preserved_without_duplicate_copy(self):
        installed = self.target / ".agents/skills"
        shutil.copytree(self.installed, installed)
        self.installed = installed
        before = files_hash(installed)
        first = self.run_initializer()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(files_hash(installed), before)
        second = self.run_initializer()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(json.loads(second.stdout)["changed"], [])
        self.assertEqual(files_hash(installed), before)

    def test_bundle_corruption_fails_before_target_changes(self):
        resource = self.installed / "initialize-repo/scripts/resources.json"
        data = json.loads(resource.read_text(encoding="utf-8"))
        data["files"]["agents.md"] += "\nUnexpected change\n"
        resource.write_text(json.dumps(data))
        result = self.run_initializer()
        self.assertEqual(result.returncode, 1)
        self.assertIn("resources changed", json.loads(result.stdout)["error"])
        self.assertFalse((self.target / ".ai").exists())

    def test_resource_traversal_is_rejected_even_with_updated_checksum(self):
        resource = self.installed / "initialize-repo/scripts/resources.json"
        data = json.loads(resource.read_text(encoding="utf-8"))
        data["files"]["../escape.py"] = "raise RuntimeError('outside')\n"
        canonical = json.dumps(data["files"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        data["resources_sha256"] = hashlib.sha256(canonical).hexdigest()
        resource.write_text(json.dumps(data))
        result = self.run_initializer()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unsafe repository path", json.loads(result.stdout)["error"])
        self.assertFalse((self.target / ".ai").exists())

    def test_generated_native_bundle_drift_check(self):
        clone = self.workspace / "build-check"
        for name in ("src", "skills", "tools", ".claude-plugin"):
            shutil.copytree(ROOT / name, clone / name, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        command = [sys.executable, str(clone / "tools/build_native.py"), "--check"]
        good = subprocess.run(command, capture_output=True, encoding="utf-8")
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        path = clone / "skills/initialize-repo/scripts/engine.py"
        path.write_text(path.read_text(encoding="utf-8") + "\n# stale emitted artifact\n", encoding="utf-8")
        bad = subprocess.run(command, capture_output=True, encoding="utf-8")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("skills/initialize-repo/scripts/engine.py", json.loads(bad.stdout)["stale"])


if __name__ == "__main__":
    unittest.main()
