"""Native specification/relationship failures and bounded format-debt exceptions."""
from datetime import datetime, timedelta, timezone
import sys

from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class SpecificationValidationTests(RepositoryCase):
    def prepare(self, label="Scale a value"):
        p = self.initialize()
        self.write("app.py", "def scale(x):\n    return x * 3\n")
        self.write("tests/test_app.py", "import unittest\nfrom app import scale\nclass Scale(unittest.TestCase):\n    def test_values(self):\n        self.assertEqual(scale(4), 12)\n        self.assertEqual(scale(-2), -6)\n")
        identifier = kit.requirement_identity(label, "math")
        p["requirements"] = {identifier: {"type": "automated", "checks": ["unit"]}}
        self.configure(p, [{"name": "unit", "argv": [sys.executable, "-m", "unittest", "discover", "-s", "tests"]}])
        base = "openspec/changes/scale"
        self.write(base + "/proposal.md", "# Scale\n## Impact\nChange " + chr(96) + "app.py" + chr(96) + " and " + chr(96) + "tests/" + chr(96) + ".\n")
        self.write(base + "/tasks.md", "- [x] Specify and verify scaling.\n")
        block = "### Requirement: " + label + "\nThe system SHALL multiply input values by three.\n#### Scenario: Four\n- **WHEN** input is 4\n- **THEN** output is 12\n"
        self.write(base + "/specs/math/spec.md", "## ADDED Requirements\n" + block)
        self.write("openspec/specs/math/spec.md", block)
        return p, base, block

    def test_native_title_and_explicit_check_mapping_need_no_rewritten_ids(self):
        p, base, _ = self.prepare()
        report = kit.verify(self.root, p, "delivery", "scale")
        self.assertEqual(report["status"], "PASS", report)
        self.assertFalse((self.root / base / "ark.json").exists())
        self.assertIn("math::Scale a value", kit.change_at(self.root, p, "scale")[1]["requirements"])

    def test_foreign_identifier_is_preserved(self):
        p, _, _ = self.prepare("Scale STK-007")
        self.assertEqual(kit.verify(self.root, p, "delivery", "scale")["status"], "PASS")

    def test_missing_then_fails(self):
        p, base, block = self.prepare()
        self.write(base + "/specs/math/spec.md", "## ADDED Requirements\n" + block.replace("**THEN**", "**RESULT**"))
        self.assertIn("scenario-conditions", {x["code"] for x in kit.change_findings(self.root, p, "scale", "specification")})

    def test_fenced_examples_do_not_declare_requirements(self):
        p, _, block = self.prepare()
        self.write("openspec/specs/math/spec.md", block + "\n" + chr(96) * 3 + "markdown\n" + block + chr(96) * 3 + "\n")
        self.assertEqual(kit.structure_findings(self.root, p), [])

    def test_retired_identity_cannot_return_to_current(self):
        p, _, _ = self.prepare("Scale REQ-MATH-001")
        self.write("openspec/changes/archive/2026-01-01-retire/proposal.md", "# Retire\n")
        self.write("openspec/changes/archive/2026-01-01-retire/specs/math/spec.md", "## REMOVED Requirements\n### Requirement: Scale REQ-MATH-001\nReason: retired interface.\nMigration: use replacement.\n")
        self.assertIn("retired-id-reuse", {x["code"] for x in kit.structure_findings(self.root, p)})

    def test_broken_evidence_and_superseding_adr_are_located(self):
        p, _, block = self.prepare()
        self.write("openspec/specs/math/spec.md", block + "Source: docs/missing.md:L1-L2\n")
        self.write("docs/adr/0001-scale.md", "# Scale\nStatus: Superseded by ADR-9999\n## Context\nA\n## Decision\nB\n## Alternatives\nC\n## Consequences\nD\n")
        findings = kit.structure_findings(self.root, p)
        self.assertTrue({"broken-evidence-link", "adr-supersession"}.issubset({x["code"] for x in findings}))
        self.assertTrue(next(x for x in findings if x["code"] == "broken-evidence-link")["line"])

    def test_specification_phase_is_not_delivery_and_does_not_run_business_checks(self):
        p, base, _ = self.prepare()
        self.write(base + "/tasks.md", "- [ ] Implement scaling.\n")
        report = kit.verify(self.root, p, "specification", "scale")
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["checks"], [])
        with self.assertRaises(kit.KitError):
            kit.close_change(self.root, p, "scale")
        self.assertEqual(kit.verify(self.root, p, "delivery", "scale")["status"], "PENDING")

    def test_human_report_is_preserved_and_malformed_markers_cannot_overwrite_it(self):
        p, base, _ = self.prepare()
        original = "# Human observations\nCheck overflow separately.\n"
        self.write(base + "/verify-report.md", original)
        for _ in range(2):
            kit.verify(self.root, p, "delivery", "scale")
        target = self.root / base / "verify-report.md"
        self.assertTrue(target.read_text(encoding="utf-8").startswith(original))
        self.assertEqual(target.read_text(encoding="utf-8").count(kit.VERIFY_START), 1)
        corrupted = target.read_text(encoding="utf-8") + kit.VERIFY_END
        target.write_text(corrupted, encoding="utf-8")
        report = kit.verify(self.root, p, "delivery", "scale")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(target.read_text(encoding="utf-8"), corrupted)

    def test_requirement_reference_has_exact_identity_boundaries(self):
        p, _, _ = self.prepare("Scale REQ-MATH-001")
        p["requirements"] = {}
        target = self.root / "tests/test_app.py"
        target.write_text(target.read_text(encoding="utf-8") + "# REQ-MATH-0010\n", encoding="utf-8")
        report = kit.verify(self.root, p, "delivery", "scale")
        self.assertEqual(report["status"], "PENDING")
        self.assertIn("requirement-test", {x["code"] for x in report["findings"]})

    def test_native_rename_can_retain_stable_identity(self):
        p, base, block = self.prepare("New name REQ-MATH-001")
        self.write(base + "/specs/math/spec.md", "## RENAMED Requirements\n- FROM: " + chr(96) + "### Requirement: Old name REQ-MATH-001" + chr(96) + "\n- TO: " + chr(96) + "### Requirement: New name REQ-MATH-001" + chr(96) + "\n")
        self.assertEqual(kit.change_findings(self.root, p, "scale", "specification"), [])
        self.assertEqual(kit.verify(self.root, p, "delivery", "scale")["status"], "PASS")

    def test_format_exception_is_explicit_bounded_and_never_waives_command_failure(self):
        p, base, block = self.prepare()
        source = self.write("openspec/specs/math/spec.md", block.replace("SHALL", "does"))
        decision = self.write("docs/format-debt.md", "Owner accepts this exact wording debt until the expiry; business tests remain required.\n")
        p["format_exceptions"] = [{"code": "requirement-wording", "path": "openspec/specs/math/spec.md",
            "sha256": kit.digest(source.read_bytes()), "owner": "reviewer", "reason": "Existing wording migration",
            "expires": (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat(),
            "decision": "docs/format-debt.md", "decision_sha256": kit.digest(decision.read_bytes())}]
        self.assertEqual(kit.structure_findings(self.root, p)[0]["status"], "WARN")
        p["checks"][0]["argv"] = [sys.executable, "-c", "raise SystemExit(9)"]
        self.assertEqual(kit.verify(self.root, p, "delivery", "scale")["status"], "FAIL")
        p["format_exceptions"][0]["expires"] = "2000-01-01"
        self.assertEqual(kit.structure_findings(self.root, p)[0]["status"], "FAIL")
        p["format_exceptions"][0]["expires"] = "2099-01-01"
        source.write_text(source.read_text(encoding="utf-8") + "\nChanged\n", encoding="utf-8")
        self.assertEqual(kit.structure_findings(self.root, p)[0]["status"], "FAIL")
