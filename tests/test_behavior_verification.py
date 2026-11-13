"""Real old-version characterization, preserved regression and intended targets."""
from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class BehaviorVerificationTests(RepositoryCase):
    def prepare(self, mode="existing"):
        if mode == "new":
            p = self.initialize()
        self.write("app.py", "def double(x):\n    if x is None: raise ValueError('missing')\n    return x * 2\n")
        if mode == "existing":
            p = self.initialize("existing")
        self.write("tests/preserve.py", "from app import double\nassert double(-2) == -4\ntry:\n    double(None)\nexcept ValueError as error:\n    assert str(error) == 'missing'\nelse:\n    raise AssertionError('missing error')\n")
        self.write("tests/target.py", "from app import double\nassert double(3) == 6\n")
        self.configure(p, [{"name": "regression", "argv": ["{python}", "-c", "exec(open('tests/preserve.py').read())"]},
                           {"name": "target", "argv": ["{python}", "-c", "exec(open('tests/target.py').read())"]}])
        self.change(p, change="refactor", scope=["app.py", "tests"])
        self.write("openspec/changes/refactor/behavior-plan.json", kit.dump({"cases": [
            {"id": "DT-01", "effect": "preserve", "source": "app.py:L1-L3", "expected": "Negative values double; None raises ValueError missing", "checks": ["regression"], "fixtures": ["tests/preserve.py"]},
            {"id": "DT-02", "effect": "target", "source": "proposal: arithmetic refactor", "expected": "Three returns six", "checks": ["target"]}]}))
        kit.baseline_inventory(self.root, p)
        self.write("docs/baseline/modules/app.md", "# App\n## Purpose\nDouble values.\n## Flow\nReject None, return multiplication.\n## State and failure\nStateless; missing raises ValueError.\n## Evidence\napp.py:L1-L3\n## Gaps\nNo concurrency claim.\n")
        kit.baseline_review(self.root, p, "docs/baseline/modules/app.md", ["app.py"], "fixture")
        return p

    def test_real_prechange_then_refactor_and_mutation(self):
        p = self.prepare()
        ready = kit.verify(self.root, p, "ready", "refactor")
        self.assertEqual(ready["status"], "PASS", ready)
        self.assertEqual([x["name"] for x in ready["checks"]], ["regression"])
        anchor = self.root / "openspec/changes/refactor/baseline-anchor.json"
        original = anchor.read_bytes()
        self.write("app.py", "def double(x):\n    if x is None: raise ValueError('missing')\n    return x + x\n")
        stale = kit.verify(self.root, p, "delivery", "refactor")
        self.assertEqual(stale["status"], "PENDING", stale)
        self.assertIn("knowledge-stale", {item["code"] for item in stale["findings"]})
        snapshots = {path: path.read_bytes() for path in (self.root / "docs/baseline/raw").rglob("*") if path.is_file()}
        kit.baseline_inventory(self.root, p)
        self.write("docs/baseline/modules/app.md", "# App\n## Purpose\nDouble values.\n## Flow\nReject None, then add the value to itself.\n## State and failure\nStateless; missing raises ValueError.\n## Evidence\napp.py:L1-L3\n## Gaps\nNo concurrency claim.\n")
        kit.baseline_review(self.root, p, "docs/baseline/modules/app.md", ["app.py"], "fixture")
        self.assertTrue(all(path.read_bytes() == content for path, content in snapshots.items()))
        good = kit.verify(self.root, p, "delivery", "refactor")
        self.assertEqual(good["status"], "PASS", good)
        self.assertEqual(good["behavior"][0]["before"], {"regression": "PASS"})
        self.write("app.py", "def double(x):\n    if x is None: return 0\n    return abs(x) * 2\n")
        bad = kit.verify(self.root, p, "delivery", "refactor")
        self.assertEqual(bad["status"], "FAIL", bad)
        self.assertEqual(bad["checks"][0]["status"], "FAIL")
        self.assertEqual(bad["checks"][1]["status"], "PASS")
        self.assertEqual(anchor.read_bytes(), original)

    def test_baseline_cannot_be_established_after_source_mutation(self):
        p = self.prepare()
        self.write("app.py", "def double(x):\n    return 9\n")
        report = kit.verify(self.root, p, "ready", "refactor")
        self.assertIn("baseline-late", {x["code"] for x in report["findings"]})
        self.assertFalse((self.root / "openspec/changes/refactor/baseline-anchor.json").exists())

    def test_changed_regression_fixture_does_not_reuse_original_pass(self):
        p = self.prepare()
        self.assertEqual(kit.verify(self.root, p, "ready", "refactor")["status"], "PASS")
        self.write("tests/preserve.py", "assert True\n")
        report = kit.verify(self.root, p, "delivery", "refactor")
        self.assertEqual(report["status"], "PENDING", report)
        self.assertIn("baseline-anchor", {x["code"] for x in report["findings"]})

    def test_missing_external_prechange_condition_is_pending(self):
        p = self.prepare()
        p["checks"][0] = {"name": "regression", "type": "external"}
        self.configure(p, p["checks"])
        report = kit.verify(self.root, p, "ready", "refactor")
        self.assertEqual(report["status"], "PENDING")
        self.assertEqual(report["checks"][0]["status"], "NOT_RUN")

    def test_initially_new_repo_acquires_old_behavior_without_git_or_ci(self):
        p = self.prepare("new")
        first = kit.verify(self.root, p, "delivery", "refactor")
        self.assertEqual(first["status"], "PASS", first)
        self.change(p, change="next", scope=["app.py"])
        report = kit.verify(self.root, p, "delivery", "next")
        self.assertEqual(report["status"], "PENDING", report)
        self.assertIn("behavior-plan", {x["code"] for x in report["findings"]})
        self.assertEqual(p["mode"], "new")
        self.assertFalse((self.root / ".git").exists())

    def test_handwritten_anchor_is_not_execution_evidence(self):
        p = self.prepare()
        self.write("openspec/changes/refactor/baseline-anchor.json", kit.dump({"scope": ["app.py", "tests"], "ready_fingerprint": "PASS", "reviewed_files": {"app.py": {}}}))
        report = kit.verify(self.root, p, "delivery", "refactor")
        self.assertEqual(report["status"], "PENDING")
        self.assertIn("baseline-anchor", {x["code"] for x in report["findings"]})

    def test_json_replay_keeps_business_differences_and_requires_explicit_normalization(self):
        p = self.initialize()
        self.write("before.json", kit.dump({"output": {"time": 1, "balance": 12}}))
        self.write("after.json", kit.dump({"output": {"time": 2, "balance": 12}}))
        self.assertEqual(kit.replay_compare(self.root, "before.json", "after.json")["status"], "FAIL")
        with self.assertRaises(kit.KitError):
            kit.replay_compare(self.root, "before.json", "after.json", ["/output/time"])
        self.assertEqual(kit.replay_compare(self.root, "before.json", "after.json", ["/output/time"], "Clock is outside this contract")["status"], "PASS")
        self.write("after.json", kit.dump({"output": {"time": 2, "balance": 99}}))
        self.assertEqual(kit.replay_compare(self.root, "before.json", "after.json", ["/output/time"], "Clock is outside this contract")["status"], "FAIL")
        with self.assertRaises(kit.KitError):
            kit.replay_compare(self.root, "before.json", "after.json", ["/output"], "Cannot remove everything")

    def test_excluded_target_check_is_not_delivery_pass(self):
        p = self.prepare()
        p["checks"][1]["phases"] = ["ready"]
        self.configure(p, p["checks"])
        self.assertEqual(kit.verify(self.root, p, "ready", "refactor")["status"], "PASS")
        report = kit.verify(self.root, p, "delivery", "refactor")
        self.assertEqual(report["status"], "PENDING")
        self.assertEqual(next(item for item in report["checks"] if item["name"] == "target")["status"], "NOT_RUN")

    def test_git_lf_storage_and_crlf_checkout_keep_real_original_fingerprints(self):
        self.git_start()
        self.run_git("config", "core.autocrlf", "true")
        p = self.initialize()
        path = self.root / "app.py"
        path.write_bytes(b"value = 1\r\n")
        self.commit()
        metadata = {"scope": ["app.py"]}
        before = kit.established_behavior(self.root, p, metadata, "edit")
        self.assertEqual(before["app.py"], kit.digest(path.read_bytes()))
        path.write_bytes(b"value = 2\r\n")
        self.assertNotEqual(kit.established_behavior(self.root, p, metadata, "edit")["app.py"], kit.digest(path.read_bytes()))
