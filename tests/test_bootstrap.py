"""First-use guarantees: no package installation, disposable source, local hooks."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from agent_repo_kit import core as kit


class BootstrapTests(unittest.TestCase):
    """REQ-ONBOARD-001: onboarding and hooks require no global toolkit installation."""
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name).resolve()
        self.target = self.workspace / "project with spaces"
        self.target.mkdir()
        self.toolkit = self.workspace / "temporary toolkit"
        package = Path(kit.__file__).parent
        shutil.copytree(package, self.toolkit / "src/agent_repo_kit", ignore=shutil.ignore_patterns("__pycache__"))
        bootstrap = Path(__file__).resolve().parents[1] / "bootstrap.py"
        shutil.copy2(bootstrap, self.toolkit / "bootstrap.py")

    def bootstrap(self, *arguments):
        # -I -S disables PYTHONPATH, user-site and installed packages. stdlib only.
        result = subprocess.run([sys.executable, "-I", "-S", str(self.toolkit / "bootstrap.py"), str(self.target), *arguments], cwd=self.workspace, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_existing_repository_needs_no_pip_and_preserves_user_content(self):
        (self.target / "app.py").write_text("def double(x):\n    return x * 2\n")
        human = b"# Existing human rule\r\nKeep the public API.  \r\n"
        (self.target / "AGENTS.md").write_bytes(human)
        first = self.bootstrap("--agents", "codex,claude")
        self.assertEqual(first["mode"], "existing")
        self.assertEqual(first["baseline"], "PENDING")
        self.assertIn("baseline-repo", first["agent_next_step"])
        self.assertTrue((self.target / "AGENTS.md").read_bytes().startswith(human))
        for relative in (".codex/hooks.json", ".claude/settings.json"):
            self.assertTrue((self.target / relative).is_file())
        second = self.bootstrap()
        self.assertEqual(second["changed"], [])

    def test_failed_diagnostics_do_not_claim_overall_bootstrap_pass(self):
        for capability in ("first", "second"):
            path = self.target / "openspec/specs" / capability / "spec.md"
            path.parent.mkdir(parents=True)
            path.write_text("### Requirement: Duplicate REQ-DUPLICATE-001\n")
        result = subprocess.run([sys.executable, "-I", "-S", str(self.toolkit / "bootstrap.py"), str(self.target)], capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["scaffold_status"], "PASS")
        self.assertEqual(data["status"], "FAIL")
        self.assertIn("duplicate-requirement", [x["code"] for x in data["diagnostics"]["findings"]])

    def test_hook_commands_survive_toolkit_removal_without_global_ark(self):
        self.bootstrap("--agents", "codex,claude")
        configurations = [("codex", ".codex/hooks.json"), ("claude", ".claude/settings.json")]
        commands = []
        for agent, relative in configurations:
            data = json.loads((self.target / relative).read_text())
            command = data["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            self.assertFalse(command.startswith("ark "))
            self.assertNotIn(str(self.toolkit), command)
            commands.append(command)
        shutil.rmtree(self.toolkit)
        nested = self.target / "src/nested"
        nested.mkdir(parents=True)
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        for command in commands:
            result = subprocess.run(command, shell=True, cwd=nested, env=env,
                                    input=json.dumps({"cwd": str(nested), "session_id": "no-global-install"}),
                                    capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            event = json.loads(result.stdout)["hookSpecificOutput"]
            self.assertEqual(event["hookEventName"], "SessionStart")
            self.assertEqual(json.loads(event["additionalContext"])["project"], str(self.target))

    def test_ci_is_opt_in_even_for_github_repositories(self):
        if not shutil.which("git"):
            self.skipTest("Git unavailable")
        subprocess.run(["git", "init", str(self.target)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.target), "remote", "add", "origin", "git@github.com:example/project.git"], check=True)
        self.bootstrap()
        self.assertFalse((self.target / ".github/workflows/ark-verify.yml").exists())
        self.bootstrap("--ci", "github")
        self.assertTrue((self.target / ".github/workflows/ark-verify.yml").is_file())
        self.assertEqual(self.bootstrap()["changed"], [])

    def test_legacy_global_hook_is_migrated_without_user_hook_loss_or_duplicates(self):
        settings = self.target / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_text(kit.dump({"permissions": {"allow": ["Read"]}, "hooks": {"SessionStart": [{"matcher": "startup", "hooks": [{"type": "command", "command": "echo user-hook"}, {"type": "command", "command": "ark hook session --agent claude", "timeout": 20}]}]}}))
        self.bootstrap("--agents", "claude")
        self.bootstrap()
        data = json.loads(settings.read_text())
        self.assertEqual(data["permissions"], {"allow": ["Read"]})
        entry = data["hooks"]["SessionStart"][0]
        self.assertEqual(entry["matcher"], "startup")
        self.assertEqual(entry["hooks"][0]["command"], "echo user-hook")
        self.assertEqual(entry["hooks"][1]["timeout"], 20)
        own = [h for group in data["hooks"]["SessionStart"] for h in group["hooks"] if kit.is_kit_hook(h.get("command"), "session", "claude")]
        self.assertEqual(len(own), 1)
        self.assertFalse(own[0]["command"].startswith("ark "))


if __name__ == "__main__":
    unittest.main()
