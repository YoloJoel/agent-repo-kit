"""Concrete consumer regressions found during the pretest release review."""

import json
import os
import subprocess
import sys
from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class ReleaseReadinessTests(RepositoryCase):
    def test_relative_check_readiness_uses_the_declared_working_directory(self):
        p = self.initialize()
        name = "check-local.cmd" if os.name == "nt" else "check-local"
        for directory in ("", "checks/"):
            self.write(directory + name, "@echo off\n" if os.name == "nt" else "#!/bin/sh\nexit 0\n").chmod(0o755)
        for cwd, available in ((".", True), ("checks", True), ("missing", False)):
            with self.subTest(cwd=cwd):
                check = {"name": "native", "argv": ["./" + name]}
                if cwd != ".":
                    check["cwd"] = cwd
                self.configure(p, [check])
                result = kit.engineering_status(self.root, p)
                self.assertEqual(result["checks"][0]["executable_available"], available)
                self.assertEqual(result["execution"], "NOT_RUN")
        if os.name != "nt":
            (self.root / name).chmod(0o644)
            self.configure(p, [{"name": "native", "argv": ["./" + name]}])
            self.assertFalse(kit.engineering_status(self.root, p)["checks"][0]["executable_available"])

    def test_compound_requirement_dependencies_are_resolved_as_full_ids(self):
        p = self.initialize()
        body = ("# Lookup\n## Purpose\nRead the current value.\n## Requirements\n"
                "### Requirement: REQ-LOOKUP-001 Lookup\nVerification: manual\n"
                "Depends-On: REQ-PAYLOAD-WIRE-001\nThe service SHALL return the current value.\n"
                "#### Scenario: Lookup\n- WHEN lookup is requested\n- THEN return the current value\n")
        self.write("openspec/specs/lookup/spec.md", body)
        findings = kit.specification_findings(self.root, p)
        missing = [item for item in findings if item["code"] == "spec-missing-owner"]
        self.assertEqual(len(missing), 1)
        self.assertIn("REQ-PAYLOAD-WIRE-001", missing[0]["message"])
        self.write("openspec/specs/payload/spec.md", body.replace("Read the current value.", "Define the wire payload.")
                   .replace("REQ-LOOKUP-001", "REQ-PAYLOAD-WIRE-001").replace("Depends-On: REQ-PAYLOAD-WIRE-001\n", ""))
        self.assertNotIn("spec-missing-owner", {item["code"] for item in kit.specification_findings(self.root, p)})

    def test_verified_native_change_hands_archive_to_its_native_workflow(self):
        p = self.initialize()
        self.write("app.py", "def value():\n    return 7\n")
        self.write("tests/assert_value.py", "from app import value\nassert value() == 7\n")
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", "exec(open('tests/assert_value.py').read())"]}])
        prefix = "openspec/changes/native"
        self.write(prefix + "/proposal.md", "# Native change\nKind: maintenance\n## Impact\nUpdate \x60app.py\x60 and \x60tests\x60.\n")
        self.write(prefix + "/tasks.md", "- [x] Verify current behavior.\n")
        self.assertEqual(kit.verify(self.root, p, "delivery", "native")["status"], "PASS")
        directory = self.root / prefix
        before = {path.relative_to(directory): path.read_bytes() for path in directory.rglob("*") if path.is_file()}
        result = kit.close_change(self.root, p, "native")
        self.assertEqual(result["status"], "PENDING")
        self.assertEqual(result["state"], "native-archive-required")
        command = subprocess.run([sys.executable, "-I", "-S", str(self.root / "hack/ai/ark.py"),
                                  "change", "close", "native"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(command.returncode, 2, command.stdout + command.stderr)
        self.assertEqual(json.loads(command.stdout)["state"], "native-archive-required")
        self.assertEqual(before, {path.relative_to(directory): path.read_bytes() for path in directory.rglob("*") if path.is_file()})
        self.assertFalse((directory / "ark.json").exists())
        archive = self.root / "openspec/changes/archive/2026-11-18-native"
        archive.parent.mkdir(parents=True, exist_ok=True)
        directory.rename(archive)
        self.assertEqual(kit.change_at(self.root, p, "native")[0], archive)

    def lightweight_mutation(self, changed_path):
        self.git_start()
        p = self.initialize()
        self.write("app.py", "value = 1\n")
        self.write("docs/baseline/raw/accepted.txt", "Original immutable observation.\n")
        mutation = ("from pathlib import Path; assert 'value = 1' in Path('app.py').read_text(); "
                    f"Path({changed_path!r}).write_text('value = 999\\n')")
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", mutation]}])
        base = self.commit()
        self.write("app.py", "value = 1  # whitespace/comment-only change\n")
        kit.note_change(self.root, p, ["app.py"], "mechanical", "Comment-only edit preserving the value.", "reviewer")
        result = kit.local_check(self.root, p, base)
        self.assertEqual(result["lightweight_checks"][0]["status"], "PASS")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("inputs-changed", {item["code"] for item in result["lightweight_findings"]})
        return result

    def test_lightweight_pass_cannot_survive_source_changes_during_the_check(self):
        self.lightweight_mutation("app.py")

    def test_lightweight_pass_cannot_survive_new_immutable_history_changes(self):
        self.lightweight_mutation("docs/baseline/raw/accepted.txt")

    def test_lightweight_pass_binds_the_note_itself_during_execution(self):
        self.git_start()
        p = self.initialize()
        self.write("app.py", "value = 1\n")
        mutator = "from pathlib import Path; next(Path('.ai/notes').glob('*.json')).write_text('{}\\n')"
        self.configure(p, [{"name": "unit", "argv": ["{python}", "-c", mutator]}])
        base = self.commit()
        self.write("app.py", "value = 1  # reviewed comment\n")
        kit.note_change(self.root, p, ["app.py"], "mechanical", "Comment only.", "reviewer")
        before = kit.fingerprint(self.root, p), kit.changed_files(self.root, base)
        result = kit.local_check(self.root, p, base)
        self.assertEqual(before, (kit.fingerprint(self.root, p), kit.changed_files(self.root, base)))
        self.assertEqual(result["lightweight_checks"][0]["status"], "PASS")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("inputs-changed", {item["code"] for item in result["lightweight_findings"]})

    def assertion(self, path, content, snippet, reference):
        self.write(path, content)
        return kit.behavior_assertion_valid(self.root, {
            "path": path, "reference": reference, "role": "assertion", "explains": "Actual selected test statement.",
            "input": "one", "expected": "one", "assertion": snippet, "detects": "A different value fails the check.",
        })

    def test_literals_and_comment_interiors_do_not_establish_executable_assertions(self):
        cases = [
            ("py", 'description = "assert value == 1"\n', "assert value == 1", "L1", False),
            ("py", '"""Documentation.\nassert value == 1\n"""\n', "assert value == 1", "L2", False),
            ("java", "/* Documentation.\nassertEquals(1, value);\n*/\n", "assertEquals(1, value);", "L2", False),
            ("cpp", 'const char *notes = R"TAG("example" assert(value == 1);)TAG";\n', "assert(value == 1);", "L1", False),
            ("java", 'String note = "assertEquals(1, value);";\n', "assertEquals(1, value);", "L1", False),
            ("py", 'assert "http://host/#fragment" == "http://host/#fragment"\n',
             'assert "http://host/#fragment" == "http://host/#fragment"', "L1", True),
            ("java", 'assertEquals("http://host", actual);\n', 'assertEquals("http://host", actual);', "L1", True),
        ]
        for extension, content, snippet, lines, expected in cases:
            with self.subTest(extension=extension, content=content):
                path = "tests/assertion." + extension
                self.assertEqual(self.assertion(path, content, snippet, path + ":" + lines), expected)

    def test_disjoint_evidence_ranges_cannot_assemble_a_nonexistent_statement(self):
        path = "tests/multiline.py"
        content = "assert (\n    value == 1\n)\n"
        sparse = path + ":L1 " + path + ":L3"
        self.assertFalse(self.assertion(path, content, "assert (\n)", sparse))
        self.assertFalse(self.assertion(path, content, content.strip(), sparse))
        self.assertTrue(self.assertion(path, content, content.strip(), path + ":L1-L3"))

    def test_rust_literals_nested_comments_and_lifetimes(self):
        snippet = "assert_eq!(1, 2);"
        cases = [
            ("// " + snippet + "\nfn main() {}\n", "L1", False),
            ('fn main() { let note = "' + snippet + '"; }\n', "L1", False),
            ('fn main() { let note = r###"quote " ' + snippet + '"###; }\n', "L1", False),
            ("/* outer /* nested */\n" + snippet + "\n*/\n", "L2", False),
            ("fn identity<'a>(s: &'a str) -> &'a str { s }\n#[test]\nfn check() { " + snippet + " }\n", "L3", True),
        ]
        for content, lines, expected in cases:
            with self.subTest(content=content):
                path = "tests/assertion.rs"
                self.assertEqual(self.assertion(path, content, snippet, path + ":" + lines), expected)

    def test_cpp_digit_separators_preserve_real_assertion_locations(self):
        content = "int thousand = 1'000; assert(thousand == 1000); int million = 1'000'000;\n"
        path = "tests/separators.cpp"
        self.assertTrue(self.assertion(path, content, "assert(thousand == 1000);", path + ":L1"))

    def test_cpp_raw_literal_does_not_gain_a_terminator_through_splicing(self):
        path = "tests/raw.cpp"
        content = 'const char *note = R"TAG()TAG\\\n" assert(false);\n)TAG";\nassert(true);\n'
        self.assertFalse(self.assertion(path, content, "assert(false);", path + ":L2"))
        self.assertTrue(self.assertion(path, content, "assert(true);", path + ":L4"))

    def test_cpp_line_splicing_is_applied_before_comment_locations(self):
        path = "tests/spliced.cpp"
        for content, lines in [("// continued \\\nassert(1 == 2);\n", "L2"),
                               ("/\\\n/ assert(1 == 2);\nint main() {}\n", "L2")]:
            with self.subTest(content=content):
                self.assertFalse(self.assertion(path, content, "assert(1 == 2);", path + ":" + lines))
        self.assertTrue(self.assertion(path, "assert(1 == 1);\n", "assert(1 == 1);", path + ":L1"))
