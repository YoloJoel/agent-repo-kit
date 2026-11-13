"""Build/check portable native Skill artifacts from the authoritative runtime/assets."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/agent_repo_kit"
ASSETS = PACKAGE / "assets"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def native_files():
    files = {}
    for path in sorted((ASSETS / "skills").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            relative = path.relative_to(ASSETS / "skills").as_posix()
            if relative.endswith("/WORKFLOW.md"):
                relative = relative[:-len("WORKFLOW.md")] + "SKILL.md"
            files["skills/" + relative] = path.read_text(encoding="utf-8").encode("utf-8")
    engine = (PACKAGE / "core.py").read_text(encoding="utf-8").encode("utf-8")
    version = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
    assets = {path.relative_to(ASSETS).as_posix(): path.read_text(encoding="utf-8") for path in sorted(ASSETS.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}
    bundle = {
        "schema_version": 1, "version": version,
        "engine_sha256": hashlib.sha256(engine).hexdigest(),
        "resources_sha256": hashlib.sha256(canonical(assets)).hexdigest(), "files": assets,
    }
    prefix = "skills/initialize-repo/scripts/"
    files[prefix + "engine.py"] = engine
    files[prefix + "initialize.py"] = (ROOT / "tools/native_initialize.py").read_text(encoding="utf-8").encode("utf-8")
    files[prefix + "resources.json"] = (json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = native_files()
    different = [relative for relative, data in expected.items() if not (ROOT / relative).is_file() or (ROOT / relative).read_bytes() != data]
    extra = [p.relative_to(ROOT).as_posix() for p in (ROOT / "skills").rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.relative_to(ROOT).as_posix() not in expected]
    if args.check:
        print(json.dumps({"status": "FAIL" if different or extra else "PASS", "stale": different, "unexpected": extra}))
        return 1 if different or extra else 0
    if extra:
        print(json.dumps({"status": "FAIL", "unexpected": extra, "error": "Inspect unexpected files; the builder will not delete them."}))
        return 1
    for relative, data in expected.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(json.dumps({"status": "PASS", "files": len(expected), "skills": len(list((ASSETS / "skills").glob("*/WORKFLOW.md")))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
