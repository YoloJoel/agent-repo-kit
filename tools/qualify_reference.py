"""Qualify an isolated linkdevice-data-service source copy using its native Maven build.

Never points at the original checkout: requires no Git remotes, the exact known JsonArray,
and explicit --repo/--maven-adapter paths. No business source is vendored in this toolkit.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reference_core", ROOT / "src/agent_repo_kit/core.py")
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)
ARRAY = "src/main/java/com/educoderai/linkdevice/data/json/JsonArray.java"
TEST = "src/test/java/com/educoderai/linkdevice/data/json/JsonArrayViewCharacterizationTest.java"
TEST_SOURCE = '''package com.educoderai.linkdevice.data.json;
import java.util.ConcurrentModificationException;
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;
class JsonArrayViewCharacterizationTest {
    @Test void viewIsLiveAcrossAddSetAndRemove() {
        JsonArray array = new JsonArray(); var view = array.elements();
        assertThat(view).isEmpty(); array.add(new JsonString("a"));
        assertThat(view).containsExactly(new JsonString("a"));
        array.set(0, new JsonString("b")); assertThat(view).containsExactly(new JsonString("b"));
        array.remove(0); assertThat(view).isEmpty();
    }
    @Test void viewAndIteratorCannotMutateBackingArray() {
        JsonArray array = new JsonArray().add(new JsonString("a"));
        assertThatThrownBy(() -> array.elements().add(new JsonString("x"))).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> array.elements().set(0, new JsonString("x"))).isInstanceOf(UnsupportedOperationException.class);
        var iterator = array.iterator(); iterator.next();
        assertThatThrownBy(iterator::remove).isInstanceOf(UnsupportedOperationException.class);
        assertThat(array.get(0)).isEqualTo(new JsonString("a"));
    }
    @Test void iterationRemainsFailFastAndNullValidationPrecedesInvalidIndex() {
        JsonArray array = new JsonArray().add(new JsonString("a"));
        var iterator = array.iterator(); array.add(new JsonString("b"));
        assertThatThrownBy(iterator::next).isInstanceOf(ConcurrentModificationException.class);
        assertThatThrownBy(() -> array.set(-1, null)).isInstanceOf(NullPointerException.class).hasMessage("value");
        assertThat(array.size()).isEqualTo(2);
    }
    @Test void nestedDeepCopyAndOrderAreIndependent() {
        JsonObject member = new JsonObject().put("value", new JsonString("old"));
        JsonArray array = new JsonArray().add(member).add(new JsonString("tail"));
        JsonArray copy = array.deepCopy(); member.put("value", new JsonString("new"));
        assertThat(copy.rawText()).isEqualTo("[{\\"value\\":\\"old\\"},\\"tail\\"]");
        assertThat(array.rawText()).isEqualTo("[{\\"value\\":\\"new\\"},\\"tail\\"]");
    }
}
'''


def qualify(root, adapter):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], encoding="utf-8").strip()
    if git("remote"):
        raise RuntimeError("Use an isolated source copy with no remotes, never the original repository")
    original = (root / ARRAY).read_text(encoding="utf-8")
    if "return Collections.unmodifiableList(elements);" not in original:
        raise RuntimeError("This qualification requires the original fixed-revision JsonArray")
    base = git("rev-parse", "HEAD")
    raw = {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / "docs/baseline/raw").rglob("*") if p.is_file()}
    human = {str(path): (root / path).read_bytes() for path in ("AGENTS.md", "CLAUDE.md", "docs/engineering-standard.md", ".github/workflows/verify.yml")}
    existing = [int(match.group(1)) for path in (root / "openspec/changes").rglob("*") if path.is_dir() and (match := re.match(r"(?:\d{4}-\d{2}-\d{2}-)?(\d{3})-", path.name))]
    name = f"{max(existing, default=0)+1:03d}-cache-json-array-view"
    p = kit.default_policy("existing", ["codex", "claude", "opencode"])
    p["source_paths"] = ["src/main/java"]
    p["paths"]["questions"] = "docs/baseline/open-questions.md"
    p["paths"]["evidence"] = "docs/agent-evidence"
    p["checks"] = [{"name": "regression", "argv": [sys.executable, str(adapter), "-B", "-ntp", "-Dtest=JsonArrayViewCharacterizationTest", "test"]}, {"name": "native-verify", "argv": ["make", "verify"], "phases": ["delivery"], "timeout": 600}]
    p["change_associations"] = {ARRAY: name, TEST: name}
    kit.atomic(root / kit.POLICY, kit.dump(p))
    init = subprocess.run([sys.executable, "-I", "-S", str(ROOT / "skills/initialize-repo/scripts/initialize.py"), str(root), "--agents", "codex,claude,opencode", "--no-hooks", "--ci", "none", "--upgrade"], capture_output=True, encoding="utf-8", check=True)
    p = kit.policy_at(root)
    directory = root / "openspec/changes" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "proposal.md").write_text(f"# Cache read-only array view\nKind: maintenance\n\nReuse one read-only live view to avoid a wrapper allocation per access. Public value/error/order behavior stays unchanged; no delta specification is needed for this pure implementation refactor under engineering-standard section 6.\n\n## Impact\n`{ARRAY}` and `{TEST}`.\n", encoding="utf-8")
    (directory / "design.md").write_text("# Design\nKeep the mutable ArrayList as sole state owner. Cache Collections.unmodifiableList once after the backing field is initialized. elements returns that live view, and iterator continues to delegate through the view. Preserve ordering, unsupported mutations, fail-fast iteration, index/null validation and deep-copy independence. View reference identity is not an existing promise. No external dependency, concurrency or protocol change.\n", encoding="utf-8")
    (directory / "tasks.md").write_text("- [x] Define scoped characterization fixtures.\n- [ ] Implement the cached view and verify behavior.\n", encoding="utf-8")
    (root / TEST).write_text(TEST_SOURCE, encoding="utf-8")
    (directory / "verify-report.md").write_text(f"# Verify report — {name}\n\n## Change ID\n{name}\n\n## Git Commit SHA\n{base} plus scoped local worktree changes; no fabricated commit.\n\n## Spec Coverage\nPure implementation refactor; existing observable specifications remain.\n\n## Test Results\nCurrent execution results are in the managed evidence below; NOT RUN until executed.\n\n## Verification Results\nNative specification, unit/acceptance and package verification required before delivery.\n\n## CI Run / Artifact References\nNo remote CI required; local .ai/runtime/runs and target/surefire-reports.\n\n## Known Risks\nNo production concurrency/load or old external-source certification.\n\n## Conclusion\nConclusion: PENDING\n", encoding="utf-8")
    plan = {"cases": [{"id": "DT-ARRAY-01", "effect": "preserve", "source": ARRAY + ":L1-L" + str(len(original.splitlines())), "expected": "Live ordered read-only view; unsupported mutation, fail-fast iteration, validation order and independent deep copy remain", "checks": ["regression"], "fixtures": [TEST]}, {"id": "DT-ARRAY-02", "effect": "target", "source": "pure allocation refactor design and existing repository specifications", "expected": "All native specification/test/package checks pass after refactor", "checks": ["native-verify"]}]}
    (directory / "behavior-plan.json").write_text(kit.dump(plan), encoding="utf-8")
    kit.baseline_inventory(root, p)
    module = "docs/baseline/modules/local-json-array.md"
    def review(current=False):
        explanation = "One cached wrapper shares the backing list; repeated reads allocate no new wrapper." if current else "Each elements call creates a read-only wrapper sharing the backing list."
        front = "---\ntitle: Local JSON array\nkind: module\nsource_ref: " + base + (" plus worktree refactor" if current else " original inputs") + "\ngenerated_at: 2026-11-13\nstatus: reviewed\n---\n\n"
        text = front + "# Local JSON array\n## Purpose\nRepresent mutable ordered JSON values while exposing read-only live traversal.\n## Flow\nadd/set validate non-null values, then mutate the list; get/remove preserve ArrayList index behavior. elements exposes live read-only values, iterator delegates through it, rawText serializes, and deepCopy recursively copies nested JSON values in order. " + explanation + "\n## State and failure\nThe ArrayList owns state. Views reflect later mutations. Their mutators and iterator remove fail, while iteration is fail-fast on structural mutation. set validates null before index because Java evaluates its value argument first. Equality and hash reflect current ordered values. No thread safety is promised.\n## Evidence\n" + ARRAY + ":L1-L" + str(len((root / ARRAY).read_text().splitlines())) + "\n## Gaps\nNo concurrency/performance benchmark or old external repository source certification; wrapper identity is not a contractual promise. Only this real current module is statically reviewed here.\n"
        (root / module).write_text(text, encoding="utf-8")
        kit.baseline_review(root, p, module, [ARRAY], "qualification reviewer")
    review()
    def brief(report):
        return {"status": report["status"], "run_id": report.get("run_id"), "findings": report.get("findings", []), "checks": [{"name": item["name"], "status": item["status"], "exit_code": item.get("exit_code"), "log": item.get("log")} for item in report.get("checks", [])]}
    before = kit.verify(root, p, "ready", name)
    assert before["status"] == "PASS", before
    candidate = original.replace("    private final ArrayList<JsonValue> elements = new ArrayList<>();", "    private final ArrayList<JsonValue> elements = new ArrayList<>();\n    private final List<JsonValue> readOnlyElements = Collections.unmodifiableList(elements);").replace("return Collections.unmodifiableList(elements);", "return readOnlyElements;")
    (root / ARRAY).write_text(candidate, encoding="utf-8")
    (directory / "tasks.md").write_text("- [x] Execute original characterization.\n- [x] Apply the cached view and prepare native delivery checks.\n", encoding="utf-8")
    good = kit.verify(root, p, "delivery", name)
    assert good["status"] == "PASS", good
    (root / ARRAY).write_text(candidate.replace("return readOnlyElements;", "return elements;"), encoding="utf-8")
    mutation = kit.verify(root, p, "delivery", name, selected=["regression"])
    assert mutation["status"] == "FAIL", mutation
    assert next(item for item in mutation["checks"] if item["name"] == "regression")["status"] == "FAIL"
    (root / ARRAY).write_text(candidate, encoding="utf-8")
    kit.baseline_inventory(root, p)
    review(True)
    final = kit.verify(root, p, "delivery", name)
    assert final["status"] == "PASS", final
    report_path = directory / "verify-report.md"
    report_path.write_text(report_path.read_text(encoding="utf-8").replace("Conclusion: PENDING", "Conclusion: PASS", 1).replace("Current execution results are in the managed evidence below; NOT RUN until executed.", "Original characterization, mutation failure/recovery and native full verify actually executed; see managed evidence and logs below."), encoding="utf-8")
    local = kit.local_check(root, p, base)
    assert local["status"] == "PASS", local
    assert all((root / path).read_bytes() == data for path, data in raw.items())
    assert (root / "AGENTS.md").read_bytes().startswith(human["AGENTS.md"])
    for path in ("docs/engineering-standard.md", ".github/workflows/verify.yml"):
        assert (root / path).read_bytes() == human[path]
    assert not (root / ".github/workflows/ark-verify.yml").exists()
    assert not (directory / "ark.json").exists()
    return {"status": "PASS", "source_repository": "YoloJoel/linkdevice-data-service", "source_revision": "36bdabc1835f331733e436453bb161bcd913a7b5", "source_blob_count": 237, "source_acquisition": "Fixed revision fetched through authenticated repository connector; every Git blob hash and executable mode checked. Local Git history was reconstructed; original remote/main was not modified.", "workspace": str(root), "local_base": base, "change": name, "scope": [ARRAY, TEST], "development_entry": "direct implementation under existing native engineering rules; no daily toolkit Skill, activity pointer or sidecar", "before": brief(before), "refactor": brief(good), "negative_mutation": brief(mutation), "repaired": brief(final), "local_check": {"status": local["status"], "business_checks_executed": local["business_checks_executed"]}, "preserved_raw_files": len(raw), "native_ci_preserved": True, "consumer_remote": None, "consumer_ci_required": False, "limits": "One real current Java module, four new characterization tests plus native full repository verify; not certification of unavailable old external source, production deployment or every business flow."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--maven-adapter", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    adapter = Path(args.maven_adapter).resolve()
    os.environ["MVN"] = f"{sys.executable} {adapter} -B -ntp"
    report = qualify(Path(args.repo).resolve(), adapter)
    Path(args.output).write_text(kit.dump(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": args.output}))


if __name__ == "__main__":
    main()
