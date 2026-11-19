"""REQ-WORKFLOW-001: a routed Change has the same obligations at all entry points."""
from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class ProjectObligationsTests(RepositoryCase):
    change = "openspec/changes/add-store/"
    spec = ("## ADDED Requirements\n### Requirement: REQ-STORE-001 Empty store\n"
            "The service SHALL create an empty store.\n#### Scenario: First open\n"
            "- WHEN a new store opens\n- THEN it contains no rows.\n")

    def setUp(self):
        super().setUp()
        self.git_start()
        self.p = self.initialize()
        self.write("README.md", "Storage schema changes require design, spec and an accepted decision.\n")
        self.p["artifact_rules"] = {"storage": {"paths": ["store.py"], "source": "README.md", "requires": ["spec", "design", "adr"]}}
        self.configure(self.p, [{"name": "unit", "argv": ["{python}", "-c", "import runpy; runpy.run_path('tests/test_store.py')"]}])
        self.base = self.commit()
        self.write("store.py", "import sqlite3\n\ndef open_store(path):\n    with sqlite3.connect(path) as db:\n        db.execute('create table if not exists events (id integer primary key)')\n    db.close()\n")
        self.write("tests/test_store.py", "# REQ-STORE-001\nimport sqlite3, tempfile\nfrom pathlib import Path\nfrom store import open_store\nwith tempfile.TemporaryDirectory() as directory:\n    path = Path(directory) / 'log.db'\n    open_store(path)\n    with sqlite3.connect(path) as reopened:\n        assert reopened.execute('select id from events').fetchall() == []\n    reopened.close()\n")
        self.write(self.change + "proposal.md", "# Open a store\n## Impact\nUpdate `store.py` and `tests/`.\n")
        self.write(self.change + "tasks.md", "- [x] Verify opening a new store.\n")

    def report(self):
        return kit.local_check(self.root, kit.policy_at(self.root), self.base)

    def codes(self):
        return {f["code"] for result in self.report()["changes"] for f in result.get("findings", [])}

    def test_incomplete_change_does_not_default_to_maintenance(self):
        self.p.pop("artifact_rules")
        self.configure(self.p, self.p["checks"])
        self.assertIn("change-intent", self.codes())
        self.write(self.change + "proposal.md", "# Feature\nKind: feature\n## Impact\nUpdate `store.py` and `tests/`.\n")
        self.assertIn("required-delta", self.codes())

    def test_scoped_project_policy_applies_to_actual_diff_and_reuses_accepted_adr(self):
        proposal = self.write(self.change + "proposal.md", "# Storage\n## Impact\nUpdate `store.py` and `tests/`.\nRisks: none\nRisk-Reason: reviewed by developer\n")
        self.assertTrue({"required-delta", "required-design", "required-adr"}.issubset(self.codes()))
        self.write(self.change + "specs/store/spec.md", self.spec)
        self.write(self.change + "design.md", "# Storage layout\nUse a single local empty table.\n")
        adr = self.write("docs/adr/0001-storage.md", "# Storage\nStatus: Proposed\n## Context\nLocal records.\n## Decision\nKeep durable state.\n## Alternatives\nMemory only.\n## Consequences\nUse disk.\n")
        proposal.write_text(proposal.read_text() + "ADR: docs/adr/0001-storage.md\n")
        self.assertIn("required-adr", self.codes())
        adr.write_text(adr.read_text().replace("Status: Proposed", "Status: Accepted"))
        report = self.report()
        self.assertEqual(report["status"], "PASS", report)

    def test_current_requirement_can_cover_restorative_fix(self):
        self.p.pop("artifact_rules")
        self.configure(self.p, self.p["checks"])
        self.write("openspec/specs/store/spec.md", self.spec.split("\n",1)[1])
        proposal = self.write(self.change + "proposal.md", "# Restore empty store\nKind: fix\nCurrent-Requirements: REQ-STORE-001\n## Impact\nUpdate `store.py` and `tests/`.\n")
        report = self.report()
        self.assertEqual(report["status"], "PASS", report)
        proposal.write_text(proposal.read_text().replace("REQ-STORE-001","REQ-STORE-999"))
        self.assertIn("unknown-current-requirement", self.codes())

    def test_semantic_rule_requires_assessment_and_named_rule_enforces_assets(self):
        self.p["artifact_rules"]["storage"].pop("paths")
        self.configure(self.p, self.p["checks"])
        self.write(self.change + "specs/store/spec.md", self.spec)
        self.assertIn("risk-assessment", self.codes())
        self.write(self.change + "proposal.md", "# Change\nRisks: storage\n## Impact\nUpdate `store.py` and `tests/`.\n")
        self.assertTrue({"required-design","required-adr"}.issubset(self.codes()))

    def test_matching_policy_paths_keep_lightweight_notes_from_waiving_requirements(self):
        kit.note_change(self.root,self.p,["store.py"],"mechanical","Preserve existing schema.","reviewer",self.base)
        report=self.report()
        self.assertNotIn("store.py", report["lightweight_files"])
        self.assertIn("required-adr", self.codes())

    def test_handoff_follows_original_superpowers_plan_and_binds_its_content(self):
        self.write(self.change + "specs/store/spec.md", self.spec)
        self.write(self.change + "proposal.md", "# Feature\n## Impact\nUpdate `store.py` and `tests/`.\n")
        self.p.pop("artifact_rules")
        self.configure(self.p, self.p["checks"])
        plan = self.write("docs/superpowers/plans/store.md", "# Implementation\n- [ ] Test opening twice.\n")
        self.write(self.change + "tasks.md", "# Tasks\nWorkflow-Source: docs/superpowers/plans/store.md\n")
        self.write("docs/superpowers/specs/store-design.md", "# Design\nKeep durable rows in one local table.\n")
        self.write(self.change + "design.md", "# Design\nWorkflow-Source: docs/superpowers/specs/store-design.md\n")
        self.assertIn("unfinished-tasks", self.codes())
        first = kit.fingerprint(self.root, self.p, "add-store")
        plan.write_text(plan.read_text().replace("[ ]", "[x]"))
        self.assertNotEqual(first, kit.fingerprint(self.root, self.p, "add-store"))
        report = self.report()
        self.assertEqual(report["status"], "PASS", report)
        self.assertFalse((self.root / self.change / "ark.json").exists())
        self.assertFalse((self.root / "openspec/specs/store/spec.md").exists())

    def test_broken_or_recursive_workflow_document_cannot_be_delivered(self):
        self.write(self.change + "tasks.md", "Workflow-Source: docs/superpowers/plans/store.md\n")
        with self.assertRaisesRegex(kit.KitError, "Workflow-Source"):
            self.report()
        self.write("docs/superpowers/plans/store.md", "Workflow-Source: openspec/changes/add-store/tasks.md\n")
        with self.assertRaisesRegex(kit.KitError, "Workflow-Source"):
            self.report()
