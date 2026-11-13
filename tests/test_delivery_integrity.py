"""REQ-INTEGRITY-001: reject the actual audit counterexamples through local delivery."""
import json
from pathlib import Path
import subprocess
import sys

from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class DeliveryIntegrityTests(RepositoryCase):
    def test_unknown_inputs_and_common_build_config_are_not_document_only(self):
        self.git_start()
        p = self.initialize()
        self.commit()
        for name in ("src/main/resources/application.properties", "build.gradle", "go.mod",
                     "CMakeLists.txt", "requirements.txt", "protocol/device.proto", "config/runtime.conf",
                     "fixtures/payload.txt", "config/custom-format", "payload.deviceformat"):
            with self.subTest(path=name):
                path = self.write(name, "changed runtime input\n")
                report = kit.local_check(self.root, p)
                self.assertEqual(report["status"], "FAIL", report)
                self.assertIn(name, report["behavior_files"])
                path.unlink()

    def test_vendored_cli_rejects_the_properties_counterexample(self):
        self.git_start()
        self.write("application.properties", "feature.enabled=true\n")
        p = self.initialize("existing")
        self.configure(p, [{"name": "config-regression", "argv": ["{python}", "-c", "from pathlib import Path; assert 'feature.enabled=true' in Path('application.properties').read_text()"]}])
        self.commit()
        self.write("application.properties", "feature.enabled=false\n")
        result = subprocess.run([sys.executable, "hack/ai/ark.py", "check"], cwd=self.root, capture_output=True, encoding="utf-8")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL")

    def test_known_documents_remain_light_and_runtime_documents_can_opt_in(self):
        self.git_start()
        p = self.initialize()
        self.commit()
        self.write("README.md", "Correct the usage wording.\n")
        report = kit.local_check(self.root, p)
        self.assertEqual(report["status"], "PASS", report)
        self.assertFalse(report["business_checks_executed"])
        p["behavior_paths"] = ["prompts/*.md"]
        self.configure(p, [])
        self.write("prompts/device.md", "Runtime policy for device routing.\n")
        self.assertIn("prompts/device.md", kit.local_check(self.root, p)["behavior_files"])
        p["behavior_paths"] = ["../outside"]
        self.write(kit.POLICY, kit.dump(p))
        with self.assertRaises(kit.KitError):
            kit.policy_at(self.root)

    def current_fixture(self):
        self.git_start()
        self.write("app.py", "def ping(): return 'pong'\ndef health(): return 'ready'\n")
        p = self.initialize("existing")
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-m", "unittest", "discover", "-s", "tests"]}])
        for name, identifier, output in (("ping", "REQ-PING-001", "pong"), ("health", "REQ-HEALTH-001", "ready")):
            self.write(f"tests/test_{name}.py", f"import unittest\nfrom app import {name}\n# {identifier}\nclass Check(unittest.TestCase):\n    def test_result(self): self.assertEqual({name}(), '{output}')\n")
            self.write(f"openspec/specs/{name}/spec.md", f"### Requirement: {identifier} {name}\nVerification: automated\nThe service SHALL return {output}.\n#### Scenario: Respond\n- WHEN {name} is requested\n- THEN {output} is returned\n")
        self.commit()
        return p

    def test_removing_only_one_requirements_test_is_detected_globally(self):
        p = self.current_fixture()
        test = self.root / "tests/test_ping.py"
        original = test.read_bytes()
        test.unlink()
        self.write("openspec/changes/clean-tests/proposal.md", "# Clean tests\nKind: maintenance\n## Impact\nUpdate `tests/`.\n")
        self.write("openspec/changes/clean-tests/tasks.md", "- [x] Clean the test layout.\n")
        report = kit.local_check(self.root, p)
        self.assertEqual(report["status"], "PENDING", report)
        self.assertTrue(any(item["code"] == "current-requirement-test" and "REQ-PING-001" in item["message"] for item in report["findings"]))
        (self.root / "tests/test_ping_relocated.py").write_bytes(original)
        repaired = kit.local_check(self.root, p)
        self.assertEqual(repaired["status"], "PASS", repaired)
        self.assertTrue(repaired["business_checks_executed"])

    def test_spec_only_change_cannot_hide_a_current_unverified_requirement(self):
        p = self.current_fixture()
        (self.root / "tests/test_ping.py").unlink()
        self.commit()
        self.write("README.md", "Document the existing ping endpoint.\n")
        self.assertEqual(kit.local_check(self.root, p)["status"], "PENDING")

    def test_current_mapping_must_be_required_and_applicable_to_delivery(self):
        p = self.current_fixture()
        (self.root / "tests/test_ping.py").unlink()
        p["requirements"] = {"REQ-PING-001": {"type": "automated", "checks": ["unit"]}}
        p["checks"][0]["phases"] = ["ready"]
        self.assertIn("current-requirement-test", {item["code"] for item in kit.structure_findings(self.root, p)})
        p["checks"][0]["phases"] = ["ready", "delivery"]
        self.assertEqual(kit.structure_findings(self.root, p), [])

    def test_empty_and_opaque_inputs_have_content_bound_source_evidence(self):
        p = self.initialize()
        for relative, content in (("schema/opaque.bin", b"\x00\xff\x01"), ("schema/empty.marker", b"")):
            with self.subTest(path=relative):
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                kit.baseline_inventory(self.root, p)
                document = "docs/baseline/modules/opaque.md"
                explanation = "# Input\n## Purpose\nDocument the reader input.\n## Flow\nRead opaque bytes; interpretation requires the caller contract.\n## State and failure\nEmpty/binary marker, no code lines to quote.\n## Evidence\n" + relative + "@sha256:" + kit.digest(content) + "\n## Gaps\nNo semantic certification of the binary schema.\n"
                self.write(document, explanation)
                self.assertEqual(kit.baseline_review(self.root, p, document, [relative], "reviewer")["status"], "PASS")
                self.write(document, explanation.replace(kit.digest(content), "0" * 64))
                with self.assertRaises(kit.KitError):
                    kit.baseline_review(self.root, p, document, [relative], "reviewer")

    def test_stale_document_is_pending_but_unrelated_and_retired_history_are_allowed(self):
        self.write("app.py", "def double(x):\n    return x * 2\n")
        p = self.initialize("existing")
        self.review_app(p)
        self.write("app.py", "def double(x):\n    return x + x\n")
        self.assertEqual(kit.delivery_knowledge_findings(self.root, p, ["other.py"]), [])
        findings = kit.delivery_knowledge_findings(self.root, p, ["app.py"])
        self.assertEqual(findings[0]["code"], "knowledge-stale")
        self.write("docs/retire.md", "Retain the former multiplication description as historical evidence; the replacement description is maintained separately.\n")
        kit.knowledge_transition(self.root, p, "docs/baseline/modules/app.md", "reviewer", "docs/retire.md", obsolete=True)
        self.assertEqual(kit.delivery_knowledge_findings(self.root, p, ["app.py"]), [])

    def test_external_current_promise_cannot_be_downgraded_to_a_unit_check(self):
        p = self.current_fixture()
        path = self.root / "openspec/specs/ping/spec.md"
        path.write_text(path.read_text(encoding="utf-8").replace("Verification: automated", "Verification: external"), encoding="utf-8")
        p["requirements"] = {"REQ-PING-001": {"type": "automated", "checks": ["unit"]}}
        self.assertIn("requirement-verification", {item["code"] for item in kit.structure_findings(self.root, p)})
        p["requirements"]["REQ-PING-001"]["type"] = "external"
        self.assertIn("current-requirement-check", {item["code"] for item in kit.structure_findings(self.root, p)})

    def test_document_edits_alone_require_knowledge_rereview(self):
        self.git_start()
        self.write("app.py", "def double(x):\n    return x * 2\n")
        p = self.initialize("existing")
        self.review_app(p)
        self.commit()
        document = "docs/baseline/modules/app.md"
        path = self.root / document
        path.write_text(path.read_text(encoding="utf-8") + "\nAdditional explanation.\n", encoding="utf-8")
        report = kit.local_check(self.root, p)
        self.assertEqual(report["status"], "PENDING", report)
        kit.baseline_review(self.root, p, document, ["app.py"], "reviewer")
        self.assertEqual(kit.local_check(self.root, p)["status"], "PASS")
