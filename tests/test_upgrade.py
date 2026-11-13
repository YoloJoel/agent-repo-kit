"""Explicit upgrade preserves human work and atomically retires only owned copies."""
from unittest.mock import patch
from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class UpgradeTests(RepositoryCase):
    def legacy(self, custom=False):
        p = self.initialize()
        legacy = ".agents/skills/deliver-change/SKILL.md"
        asset = "hack/ai/assets/skills/deliver-change/SKILL.md"
        self.write(legacy, "# Legacy tool-owned workflow\n")
        self.write(asset, "# Old generated workflow\n")
        manifest = kit.read_json(self.root / kit.MANIFEST)
        manifest["kit_version"] = "0.1.0"
        for path in (legacy, asset):
            manifest["files"][path] = kit.digest((self.root / path).read_bytes())
        kit.atomic(self.root / kit.MANIFEST, kit.dump(manifest))
        p["kit_version"] = "0.1.0"
        kit.atomic(self.root / kit.POLICY, kit.dump(p))
        if custom:
            self.write(legacy, "# Human customized workflow\nThis custom skill remains optional.\n")
        self.write("docs/baseline/raw/original.md", "Immutable old observation\n")
        self.write("README.md", "Dirty human draft\n")
        return legacy, asset

    def test_upgrade_is_explicit_and_keeps_human_work_and_history(self):
        legacy, asset = self.legacy()
        before = (self.root / kit.POLICY).read_bytes()
        with self.assertRaisesRegex(kit.KitError, "explicitly"):
            kit.init_repo(self.root)
        self.assertEqual((self.root / kit.POLICY).read_bytes(), before)
        kit.init_repo(self.root, upgrade=True)
        self.assertFalse((self.root / legacy).exists())
        self.assertFalse((self.root / asset).exists())
        self.assertEqual((self.root / "docs/baseline/raw/original.md").read_text(), "Immutable old observation\n")
        self.assertEqual((self.root / "README.md").read_text(), "Dirty human draft\n")
        self.assertEqual(kit.init_repo(self.root, upgrade=True)["changed"], [])
        self.assertEqual(kit.structure_findings(self.root, kit.policy_at(self.root)), [])

    def test_customized_retired_copy_is_preserved_and_detached(self):
        legacy, asset = self.legacy(custom=True)
        before = (self.root / legacy).read_bytes()
        kit.init_repo(self.root, upgrade=True)
        manifest = kit.read_json(self.root / kit.MANIFEST)
        self.assertEqual((self.root / legacy).read_bytes(), before)
        self.assertNotIn(legacy, manifest["files"])
        self.assertIn(legacy, manifest["migrations"][-1]["preserved_custom"])
        self.assertFalse((self.root / asset).exists())

    def test_modified_owned_runtime_aborts_before_retiring_any_file(self):
        legacy, _ = self.legacy()
        self.write("hack/ai/ark.py", "# Human customization\n")
        with self.assertRaisesRegex(kit.KitError, "conflict"):
            kit.init_repo(self.root, upgrade=True)
        self.assertTrue((self.root / legacy).is_file())
        self.assertEqual(kit.read_json(self.root / kit.MANIFEST)["kit_version"], "0.1.0")

    def test_failed_transaction_restores_a_deleted_owned_file(self):
        self.write("old.txt", "Original content\n")
        self.write("later.txt", "Previous content\n")
        actual = kit.atomic
        def fail(path, content):
            if path.name == "later.txt" and content == b"Updated\n":
                raise OSError("simulated disk failure")
            return actual(path, content)
        with patch.object(kit, "atomic", side_effect=fail):
            with self.assertRaises(OSError):
                kit.transact(self.root, {"old.txt": None, "later.txt": "Updated\n"})
        self.assertEqual((self.root / "old.txt").read_text(), "Original content\n")
        self.assertEqual((self.root / "later.txt").read_text(), "Previous content\n")

    def test_existing_native_adr_directory_does_not_gain_an_incompatible_readme(self):
        self.write("docs/adr/0001-existing.md", "# Native ADR\n- Status: Accepted\n## Context\nA\n## Decision\nB\n## Alternatives\nC\n## Consequences\nD\n")
        self.initialize()
        self.assertFalse((self.root / "docs/adr/README.md").exists())

    def test_mapped_evidence_stays_outside_native_raw_batches_and_is_immutable(self):
        self.git_start()
        self.write("app.py", "def double(x):\n    return x * 2\n")
        p = self.initialize("existing")
        p["paths"]["evidence"] = "docs/machine-evidence"
        kit.atomic(self.root / kit.POLICY, kit.dump(p))
        kit.baseline_inventory(self.root, p)
        self.review_app(p)
        item = kit.read_json(self.root / "docs/baseline/knowledge.json")["documents"]["docs/baseline/modules/app.md"]
        self.assertTrue(item["snapshot"].startswith("docs/machine-evidence/reviews/"))
        self.assertFalse((self.root / "docs/baseline/raw/reviews").exists())
        self.assertNotIn(item["snapshot"] + "/record.json", kit.inventory_files(self.root, p))
        self.commit()
        target = self.root / item["snapshot"] / "record.json"
        target.write_text('{"tampered":true}\n', encoding="utf-8")
        result = kit.local_check(self.root, p)
        self.assertEqual(result["status"], "FAIL", result)
        self.assertIn("raw-history", {x.get("code") for x in result["changes"]})
