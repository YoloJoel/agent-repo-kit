"""Installed Skill entry. Only this Skill folder and Python stdlib are needed."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.version_info < (3, 11):
        print(json.dumps({"status": "FAIL", "error": "Python 3.11+ is required; locate an available interpreter before initializing."}))
        return 1
    parser = argparse.ArgumentParser(description="Initialize using resources bundled with this installed Skill.")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--agents", help="Current runtime; select automatically, not as a user setup question.")
    parser.add_argument("--mode", choices=["auto", "new", "existing"], default="auto")
    parser.add_argument("--no-hooks", action="store_true")
    parser.add_argument("--ci", choices=["auto", "github", "none"], default="none")
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--path", action="append", dest="mappings", help="Existing asset mapping: KEY=repository-relative-path")
    args = parser.parse_args(argv)
    scripts = Path(__file__).resolve().parent
    try:
        bundle = json.loads((scripts / "resources.json").read_text(encoding="utf-8"))
        engine_path = scripts / "engine.py"
        if bundle.get("schema_version") != 1 or not isinstance(bundle.get("files"), dict):
            raise ValueError("Unsupported or incomplete installed Skill resources")
        if hashlib.sha256(engine_path.read_bytes()).hexdigest() != bundle.get("engine_sha256"):
            raise ValueError("Installed Skill runtime/resources differ; update the complete Skill folder")
        if hashlib.sha256(canonical(bundle["files"])).hexdigest() != bundle.get("resources_sha256"):
            raise ValueError("Installed Skill resources changed; restore/update the complete Skill folder")
        spec = importlib.util.spec_from_file_location("_ark_installed_engine", engine_path)
        if spec is None or spec.loader is None:
            raise ValueError("Installed Skill runtime is unavailable")
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        if engine.VERSION != bundle.get("version"):
            raise ValueError("Installed Skill version mismatch")
        with tempfile.TemporaryDirectory(prefix="ark-skill-assets-") as temporary:
            assets = Path(temporary).resolve()
            for relative, content in bundle["files"].items():
                if not isinstance(content, str):
                    raise ValueError("Installed resource contents must be UTF-8 text")
                engine.atomic(engine.safe(assets, relative), content)
            engine.ASSETS = assets
            result = engine.onboard_repo(
                Path(args.path).expanduser().resolve(), args.mode,
                args.agents.split(",") if args.agents else None,
                not args.no_hooks, args.ci, args.upgrade, copy_skills=False, path_overrides=engine.parse_paths(args.mappings),
            )
        result["entry"] = "installed-skill"
        result["installation"] = "Use the platform-installed Skills. No repository download, pip, global CLI or duplicate project Skill installation is needed."
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        # The hook/runtime trust boundary belongs to the host. Fail setup clearly.
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
