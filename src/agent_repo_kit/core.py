"""Dependency-free runtime. Also vendored as hack/ai/ark.py in consumer repos.

The runtime records observations and runs checks. It never claims to understand
source semantics or turn inventory into an approved specification by itself.
"""

from __future__ import annotations

import argparse
import contextlib
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timezone
import uuid
import xml.etree.ElementTree as ET

VERSION = "0.2.1"
ASSETS = Path(__file__).parent / "assets"
POLICY = ".ai/policy.json"
MANIFEST = ".ai/manifest.json"
START = "<!-- agent-repo-kit:start -->"
END = "<!-- agent-repo-kit:end -->"
FILL = "<!-- ARK:FILL -->"
REQ = re.compile(r"\bREQ-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
DECLARED_ID = re.compile(r"\b[A-Z][A-Z0-9_]*(?:-[A-Z0-9_]+)*-\d+[A-Z0-9_]*\b")
VERIFY_START = "<!-- agent-repo-kit:verification:start -->"
VERIFY_END = "<!-- agent-repo-kit:verification:end -->"
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SKILLS = ("initialize-repo", "baseline-repo")
AGENT_DIRS = {"codex": ".agents/skills", "claude": ".claude/skills", "opencode": ".opencode/skills"}
IGNORED_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "target", "build", "dist"}
SOURCE_SUFFIXES = {".py", ".java", ".kt", ".go", ".rs", ".c", ".h", ".cpp", ".hpp", ".js", ".ts", ".tsx", ".jsx", ".cs", ".rb", ".php", ".sh", ".sql", ".yaml", ".yml", ".toml", ".xml", ".json"}


class KitError(Exception):
    """An actionable input or repository error, rather than a Python traceback."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(root, relative):
    """Reject traversal and symlinked components, including not-yet-existing leaves."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise KitError(f"Expected a repository-relative POSIX path: {relative!r}")
    part = PurePosixPath(relative)
    if part.is_absolute() or ".." in part.parts or ":" in relative or part == PurePosixPath("."):
        raise KitError(f"Unsafe repository path: {relative}")
    result = root
    for name in part.parts:
        result = result / name
        if result.is_symlink():
            raise KitError(f"Refusing a symlink in managed/evidence path: {relative}")
    if not result.resolve().is_relative_to(root.resolve()):
        raise KitError(f"Path escapes repository: {relative}")
    return result


def read_json(path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise KitError(f"Missing {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise KitError(f"Invalid JSON in {path}: {exc}") from exc


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = data.encode("utf-8") if isinstance(data, str) else data
    fd, temporary = tempfile.mkstemp(prefix=".ark-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def lock(root, name="mutation"):
    path = safe(root, f".ai/runtime/locks/{name}.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise KitError(f"Another operation owns {path}; inspect its PID before removing a stale lock.") from exc
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(dump({"pid": os.getpid(), "started": now()}))
        yield
    finally:
        path.unlink(missing_ok=True)


def transact(root, writes):
    """Preflight all destinations and restore only this operation on write failure."""
    paths = {relative: safe(root, relative) for relative in writes}
    before = {}
    for relative, path in paths.items():
        if path.exists() and not path.is_file():
            raise KitError(f"Expected a file at {relative}")
        before[relative] = path.read_bytes() if path.exists() else None
    changed = []
    try:
        for relative, data in writes.items():
            content = data.encode("utf-8") if isinstance(data, str) else data
            if before[relative] != content:
                if content is None:
                    paths[relative].unlink(missing_ok=True)
                else:
                    atomic(paths[relative], content)
                changed.append(relative)
    except BaseException:
        for relative in reversed(changed):
            if before[relative] is None:
                paths[relative].unlink(missing_ok=True)
            else:
                atomic(paths[relative], before[relative])
        raise
    return changed


def block(text, body):
    generated = f"{START}\n{body.strip()}\n{END}"
    if START not in text and END not in text:
        separator = ("\n" if text.endswith(("\n", "\r")) else "\n\n") if text else ""
        return text + separator + generated + "\n"
    if text.count(START) != 1 or text.count(END) != 1 or text.index(END) < text.index(START):
        raise KitError("Malformed or duplicate agent-repo-kit managed block; resolve it before initializing.")
    begin, finish = text.index(START), text.index(END) + len(END)
    return text[:begin] + generated + text[finish:]


def git(root, *arguments, optional=False):
    try:
        result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        if optional:
            return None
        raise KitError(f"Git is unavailable: {exc}") from exc
    if result.returncode:
        if optional:
            return None
        raise KitError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def root_at(start):
    path = Path(start).expanduser().resolve()
    if not path.is_dir():
        raise KitError(f"Not a directory: {path}")
    for candidate in (path, *path.parents):
        if (candidate / POLICY).is_file():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return path


def policy_at(root):
    p = read_json(safe(root, POLICY))
    if not isinstance(p, dict) or p.get("schema_version") != 1:
        raise KitError("Unsupported policy schema_version; use a compatible toolkit/migration.")
    if p.get("mode") not in {"new", "existing"}:
        raise KitError("policy.mode must be new or existing")
    if not isinstance(p.get("paths"), dict):
        raise KitError("policy.paths must be an object")
    if p.get("hook_mode", "advisory") not in {"advisory", "enforce"}:
        raise KitError("policy.hook_mode must be advisory or enforce")
    if p.get("skill_delivery", "repository") not in {"repository", "installed"}:
        raise KitError("policy.skill_delivery must be repository or installed")
    if not isinstance(p.get("agents", []), list) or any(a not in AGENT_DIRS for a in p.get("agents", [])):
        raise KitError("policy.agents must contain supported adapter IDs")
    for key in ("baseline", "specs", "changes", "adr", "templates", *[name for name in ("context", "standard", "questions", "decision_view", "decision_details", "evidence") if name in p["paths"]]):
        safe(root, p.get("paths", {}).get(key))
    for key in ("exclude", "test_paths", "checks", "source_paths"):
        if not isinstance(p.get(key), list):
            raise KitError(f"policy.{key} must be an array")
    names = set()
    for check in p["checks"]:
        if not isinstance(check, dict) or not ID.fullmatch(str(check.get("name", ""))):
            raise KitError("Every check needs a lowercase hyphenated name")
        if check["name"] in names:
            raise KitError(f"Duplicate check: {check['name']}")
        names.add(check["name"])
        if check.get("type", "command") not in {"command", "manual", "external"}:
            raise KitError(f"Unknown check type: {check['name']}")
        if check.get("type", "command") == "command":
            argv = check.get("argv")
            if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or not a for a in argv):
                raise KitError(f"check {check['name']} requires nonempty argv, never a shell string")
        cwd = check.get("cwd", ".")
        if cwd != ".":
            safe(root, cwd)
        if not isinstance(check.get("timeout", 300), (int, float)) or not 0 < check.get("timeout", 300) <= 3600:
            raise KitError(f"Invalid check timeout: {check['name']}")
        if not isinstance(check.get("required", True), bool):
            raise KitError(f"check.required must be a boolean: {check['name']}")
        phases = check.get("phases", ["ready", "delivery"])
        if not isinstance(phases, list) or not phases or any(phase not in {"ready", "delivery"} for phase in phases):
            raise KitError("check.phases must select ready and/or delivery")
    for relative in p["test_paths"]:
        safe(root, relative)
    for relative in p.get("source_paths", ["."]):
        if relative != ".":
            safe(root, relative)
    if not isinstance(p.get("behavior_paths", []), list):
        raise KitError("policy.behavior_paths must be an array of repository paths or glob patterns")
    for relative in p.get("behavior_paths", []):
        if relative != ".":
            safe(root, relative)
    if any(not isinstance(x, str) or not x for x in p["exclude"]):
        raise KitError("policy.exclude must contain nonempty glob strings")
    if not isinstance(p.get("requirements", {}), dict):
        raise KitError("policy.requirements must be an object")
    for requirement, mapping in p.get("requirements", {}).items():
        if not isinstance(requirement, str) or not requirement.strip() or not isinstance(mapping, dict) or mapping.get("type") not in {"automated", "manual", "external"}:
            raise KitError(f"Invalid requirement verification mapping: {requirement}")
        if not isinstance(mapping.get("checks", []), list) or any(name not in names for name in mapping.get("checks", [])):
            raise KitError(f"Unknown requirement check mapping: {requirement}")
    associations = p.get("change_associations", {})
    if not isinstance(associations, dict):
        raise KitError("policy.change_associations must map concrete path prefixes to change IDs")
    for prefix, change in associations.items():
        safe(root, prefix)
        if not isinstance(change, str) or not ID.fullmatch(change):
            raise KitError("Change associations must name existing native-format change IDs")
    return p


def under(relative, prefix):
    return prefix == "." or relative == prefix or relative.startswith(prefix.rstrip("/") + "/")


def excluded(relative, p):
    parts = PurePosixPath(relative).parts
    if any(part in IGNORED_DIRS for part in parts):
        return True
    if any(part.endswith(".egg-info") for part in parts):
        return True
    if parts[-1] == ".env" or parts[-1].endswith((".p12", ".pfx", ".pyc")):
        return True
    if any(under(relative, p.get("paths", {}).get(key, "@none")) for key in ("baseline", "changes", "templates", "evidence")):
        return True
    return any(fnmatch.fnmatchcase(relative, pattern) or under(relative, pattern.rstrip("/")) for pattern in p.get("exclude", []))


def inventory_files(root, p):
    """Prefer Git's ignore-aware inventory; never traverse symlinks."""
    listed = git(root, "ls-files", "-co", "--exclude-standard", "-z", optional=True)
    if listed is None:
        candidates = []
        for parent, directories, files in os.walk(root, followlinks=False):
            directories[:] = sorted(d for d in directories if d not in IGNORED_DIRS and not (Path(parent) / d).is_symlink())
            candidates.extend((Path(parent) / name).relative_to(root).as_posix() for name in files)
    else:
        candidates = [x.decode("utf-8", errors="strict") for x in listed.split(b"\0") if x]
    answer = {}
    for relative in sorted(set(candidates)):
        if excluded(relative, p):
            continue
        try:
            path = safe(root, relative)
        except KitError:
            continue
        if not path.is_file():
            continue
        content = path.read_bytes()
        answer[relative] = {"sha256": digest(content), "bytes": len(content)}
    return answer


def is_behavior(relative, p=None):
    """Unknown inputs require impact review; an extension allowlist cannot prove safety."""
    if any(fnmatch.fnmatchcase(relative, pattern) or under(relative, pattern.rstrip("/"))
           for pattern in (p or {}).get("behavior_paths", [])):
        return True
    path = PurePosixPath(relative)
    if path.suffix.lower() in SOURCE_SUFFIXES or path.name in {"Dockerfile", "Makefile", "Jenkinsfile", "CMakeLists.txt"}:
        return True
    if path.suffix.lower() in {".md", ".rst", ".adoc", ".asciidoc"}:
        return False
    if path.suffix.lower() == ".txt" and (path.parts[0] in {"docs", "doc"} or path.stem.upper() in {"README", "CHANGELOG", "LICENSE", "COPYING", "NOTICE", "AUTHORS"}):
        return False
    return path.name not in {"README", "LICENSE", "COPYING", "NOTICE", "AUTHORS", ".gitignore", ".gitattributes", ".editorconfig"}


def default_policy(mode, agents):
    return {
        "$schema": "../hack/ai/assets/policy.schema.json", "schema_version": 1, "kit_version": VERSION, "mode": mode,
        "agents": sorted(set(agents)), "source_paths": ["."], "test_paths": ["tests", "src/test"],
        "paths": {"baseline": "docs/baseline", "specs": "openspec/specs", "changes": "openspec/changes", "adr": "docs/adr", "templates": "docs/templates", "context": "docs/project-context.md", "standard": "docs/engineering-standard.md"},
        "exclude": [".ai", "hack/ai", ".agents/skills", ".claude/skills", ".opencode/skills", ".codex/hooks.json", ".claude/settings.json", "skills-lock.json", "openspec/config.yaml", "docs/baseline", "docs/templates", "openspec/changes"],
        "checks": [], "requirements": {}, "command_candidates": [], "hook_mode": "advisory", "behavior_paths": [],
    }


def project_profile(root, p):
    """Observed project facts only. Build markers are not executed or treated as proof."""
    inventory = inventory_files(root, p)
    owned = set(read_json(safe(root, MANIFEST), {}).get("files", {}))
    inventory = {name: record for name, record in inventory.items() if name not in owned and name not in {".codex/hooks.json", ".claude/settings.json"}}
    suffixes = {".java": "Java", ".kt": "Kotlin", ".py": "Python", ".c": "C", ".h": "C/C++ headers", ".cpp": "C++", ".go": "Go", ".rs": "Rust", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript"}
    languages = sorted({suffixes[Path(name).suffix] for name in inventory if Path(name).suffix in suffixes})
    markers = {"pom.xml", "build.gradle", "build.gradle.kts", "package.json", "pyproject.toml", "go.mod", "Cargo.toml", "CMakeLists.txt", "Makefile"}
    manifests = [name for name in inventory if Path(name).name in markers]
    versions, unknown = {}, []
    for name in manifests:
        path = safe(root, name)
        if path.stat().st_size > 1024 * 1024:
            unknown.append(f"Inspect oversized build manifest: {name}")
            continue
        if path.name == "pom.xml":
            try:
                node = ET.fromstring(path.read_text(encoding="utf-8"))
                def child(parent, label):
                    return next((x for x in parent if x.tag.rsplit('}', 1)[-1] == label), None) if parent is not None else None
                properties = child(node, "properties")
                for label in ("java.version", "maven.compiler.release", "maven.compiler.source"):
                    value = child(properties, label)
                    if value is not None and value.text:
                        versions[name + ":" + label] = value.text.strip()
                parent = child(node, "parent")
                artifact, version = child(parent, "artifactId"), child(parent, "version")
                if artifact is not None and version is not None and version.text:
                    versions[name + ":parent:" + (artifact.text or "unknown")] = version.text.strip()
            except (ET.ParseError, UnicodeError):
                unknown.append(f"Could not parse build facts: {name}")
    source_roots = [name for name in ("src/main", "src", "app", "lib", "source") if (root / name).is_dir()]
    test_roots = [name for name in p["test_paths"] if (root / name).is_dir()]
    behavior = {name: item["sha256"] for name, item in inventory.items() if is_behavior(name, p)}
    return {"schema_version": 1, "languages": languages, "build_manifests": manifests,
            "source_roots": source_roots, "test_roots": test_roots, "declared_versions": versions,
            "source_fingerprint": digest(dump(behavior).encode()),
            "unknowns": unknown + ["Runtime topology, external contracts and semantic boundaries require source-grounded analysis.", "Candidate build/test commands require actual confirmation; no business check has been assumed to pass."]}


def project_context(profile):
    lines = ["# Project context", "", "Observed facts; maintain this explanation with source evidence. Unknown dimensions remain explicit.", "",
             "## Languages", ", ".join(profile["languages"]) or "Not established; no product stack is assumed.", "", "## Build evidence"]
    lines += [f"- `{name}`" for name in profile["build_manifests"]] or ["- No supported build manifest observed."]
    lines += ["", "## Declared versions"] + [f"- `{name}`: `{value}` (declared, not executed)" for name, value in profile["declared_versions"].items()]
    lines += ["", "## Source and test roots", f"Source candidates: {', '.join(profile['source_roots']) or 'not established'}.", f"Observed tests: {', '.join(profile['test_roots']) or 'not established'}.", "", "## Unknowns"]
    lines += ["- " + item for item in profile["unknowns"]]
    lines += ["", "## Evidence", "Current observed build/source fingerprint: `" + profile["source_fingerprint"] + "`.", "Machine observations: `.ai/project.json`. Confirm runtime facts and architecture separately.", ""]
    return "\n".join(lines)


def fingerprint(root, p, change=None):
    files = inventory_files(root, p)
    # Configuration/contract inputs are always bound, even if excluded from inventory.
    required = [POLICY, MANIFEST, "AGENTS.md"]
    spec_root = safe(root, p["paths"]["specs"])
    if spec_root.exists():
        required += [f.relative_to(root).as_posix() for f in spec_root.rglob("*.md") if f.is_file()]
    if change:
        directory, metadata = change_at(root, p, change)
        for name in ("proposal.md", "design.md"):
            if (directory / name).is_file():
                data = (directory / name).read_bytes()
                files["@change/" + name] = {"sha256": digest(data), "bytes": len(data)}
        for path in directory.glob("specs/**/*.md"):
            data = safe(root, path.relative_to(root).as_posix()).read_bytes()
            files["@change/" + path.relative_to(directory).as_posix()] = {"sha256": digest(data), "bytes": len(data)}
        plan = behavior_plan(root, p, change)
        files["@behavior-plan"] = plan
        files["@behavior-fixtures"] = behavior_signature(root, p, change)["fixtures"]
        files["@change"] = {k: metadata.get(k) for k in ("id", "kind", "scope", "requirements", "removed_requirements")}
    for relative in required:
        path = safe(root, relative)
        if path.is_file():
            files[relative] = {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size}
    return digest(dump(files).encode())


def hook_command(action, agent):
    """A repository-relative launcher: no installed ark or toolkit checkout required."""
    interpreter = "python" if os.name == "nt" else "python3"
    code = (
        "import pathlib,runpy,sys;agent_repo_kit_hook_v1=True;"
        "p=pathlib.Path.cwd();"
        "r=next((q for q in (p,*p.parents) if (q/'.ai/policy.json').is_file()),None);"
        "r is None and sys.exit(0);"
        "sys.argv=[str(r/'hack/ai/ark.py'),*sys.argv[1:]];"
        "runpy.run_path(sys.argv[0],run_name='__main__')"
    )
    return f'{interpreter} -X utf8 -c "{code}" hook {action} --agent {agent}'


def is_kit_hook(command, action, agent):
    if not isinstance(command, str):
        return False
    return command == f"ark hook {action} --agent {agent}" or (
        "agent_repo_kit_hook_v1=True" in command
        and command.endswith(f" hook {action} --agent {agent}")
    )


def parse_paths(values):
    result = {}
    for item in values or []:
        if "=" not in item:
            raise KitError("Path mappings use KEY=repository-relative-path")
        key, value = item.split("=", 1)
        if key in result or not value:
            raise KitError("Path mappings must have unique keys and nonempty paths")
        result[key] = value
    return result


def init_repo(root, mode="auto", agents=None, hooks=False, ci=False, upgrade=False, copy_skills=None, path_overrides=None):
    root.mkdir(parents=True, exist_ok=True)
    if agents is not None and (not agents or any(a not in AGENT_DIRS for a in agents)):
        raise KitError("Supported adapters: codex, claude, opencode")
    with lock(root):
        old_manifest = read_json(safe(root, MANIFEST), {})
        if old_manifest and old_manifest.get("kit_version") != VERSION and not upgrade:
            raise KitError("Toolkit version differs; explicitly run init --upgrade after reviewing the migration.")
        if safe(root, POLICY).exists():
            p = policy_at(root)
            if mode != "auto" and mode != p["mode"]:
                raise KitError("Existing mode is preserved; change policy explicitly after reviewing its implications.")
            p["agents"] = sorted(set(p.get("agents", [])) | set(agents or []))
            p["kit_version"] = VERSION
        else:
            agents = agents or ["codex", "claude", "opencode"]
            probe = default_policy("new", agents)
            observed = inventory_files(root, probe)
            detected = "existing" if any(is_behavior(x, probe) for x in observed) else "new"
            p = default_policy(detected if mode == "auto" else mode, agents)
            candidates = []
            for marker, argv in (("pom.xml", ["mvn", "test"]), ("build.gradle", ["./gradlew", "test"]), ("go.mod", ["go", "test", "./..."]), ("package.json", ["npm", "test"]), ("pyproject.toml", ["python", "-m", "unittest", "discover", "-s", "tests"])):
                if (root / marker).is_file():
                    candidates.append({"marker": marker, "argv": argv, "confirmed": False})
            p["command_candidates"] = candidates
        for key, value in (path_overrides or {}).items():
            if key not in {"baseline", "specs", "changes", "adr", "templates", "context", "standard", "questions", "decision_view", "decision_details", "evidence"}:
                raise KitError("Unknown managed asset path key: " + key)
            safe(root, value)
            if old_manifest and p["paths"].get(key) != value:
                raise KitError("Set path mappings before first initialization; existing asset relocation requires an explicit migration with preserved history")
            p["paths"][key] = value
        if copy_skills is None:
            copy_skills = p.get("skill_delivery", "repository") == "repository"
        p["skill_delivery"] = "repository" if copy_skills else "installed"
        writes = {POLICY: dump(p)}
        if not safe(root, ".ai/established.json").exists():
            writes[".ai/established.json"] = dump({"files": {path: {"sha256": sha, "change": None} for path, sha in scoped_sources(root, p, p["source_paths"]).items()}})
        owned = dict(old_manifest.get("files", {}))
        retired, preserved_custom = [], []
        if upgrade:
            for relative, expected in list(owned.items()):
                old_skill = any(under(relative, prefix + "/deliver-change") for prefix in [*AGENT_DIRS.values(), "hack/ai/assets/skills"])
                old_asset_entry = relative.startswith("hack/ai/assets/skills/") and relative.endswith("/SKILL.md")
                if old_skill or old_asset_entry:
                    owned.pop(relative)
                    target = safe(root, relative)
                    if target.is_file():
                        if digest(target.read_bytes()) == expected:
                            writes[relative] = None
                            retired.append(relative)
                        else:
                            preserved_custom.append(relative)
        profile = project_profile(root, p)
        writes[".ai/project.json"] = dump(profile)

        def managed(relative, content):
            path = safe(root, relative)
            data = content.encode() if isinstance(content, str) else content
            if path.exists():
                previous = owned.get(relative)
                current = digest(path.read_bytes())
                if current != digest(data) and (not previous or current != previous):
                    raise KitError(f"Managed-file conflict at {relative}; preserve/merge it before retrying.")
            writes[relative] = data
            owned[relative] = digest(data)

        managed("hack/ai/ark.py", Path(__file__).read_bytes())
        for path in sorted(ASSETS.rglob("*")):
            if path.is_file():
                managed("hack/ai/assets/" + path.relative_to(ASSETS).as_posix(), path.read_bytes())
        context_path = p["paths"].get("context", "docs/project-context.md")
        standard_path = p["paths"].get("standard", "docs/engineering-standard.md")
        routing = (ASSETS / "agents.md").read_text(encoding="utf-8").replace("{{BASELINE}}", p["paths"]["baseline"]).replace("{{SPECS}}", p["paths"]["specs"]).replace("{{CHANGES}}", p["paths"]["changes"]).replace("docs/engineering-standard.md", standard_path)
        routing += "\nProject observations: " + (", ".join(profile["languages"]) or "stack not established") + ". "
        routing += "Build evidence: " + (", ".join(profile["build_manifests"]) or "not established") + f".\nRead {context_path} for observed roots, declared versions and unresolved facts.\n"
        agent_path = safe(root, "AGENTS.md")
        existing = agent_path.read_bytes().decode("utf-8") if agent_path.exists() else ""
        previous_block = old_manifest.get("agents_block")
        if START in existing and previous_block:
            old_block = existing[existing.index(START):existing.index(END) + len(END)]
            if digest(old_block.encode()) != previous_block:
                raise KitError("AGENTS.md managed block was edited; merge its changes before reinitializing.")
        merged = block(existing, routing)
        writes["AGENTS.md"] = merged
        block_text = merged[merged.index(START):merged.index(END) + len(END)]
        ignore_path = safe(root, ".gitignore")
        ignore_text = ignore_path.read_bytes().decode("utf-8") if ignore_path.exists() else ""
        if ".ai/runtime/" not in ignore_text.splitlines():
            writes[".gitignore"] = ignore_text + ("\n" if ignore_text and not ignore_text.endswith("\n") else "") + "# Agent Repo Kit local evidence, locks, and session pointers\n.ai/runtime/\n"
        if copy_skills:
            for agent in p["agents"]:
                for skill in SKILLS:
                    for path in sorted((ASSETS / "skills" / skill).rglob("*")):
                        if path.is_file():
                            relative = path.relative_to(ASSETS / "skills" / skill).as_posix()
                            if relative == "WORKFLOW.md":
                                relative = "SKILL.md"
                            managed(f"{AGENT_DIRS[agent]}/{skill}/{relative}", path.read_bytes())
        if "claude" in p["agents"]:
            path = safe(root, "CLAUDE.md")
            text = path.read_bytes().decode("utf-8") if path.exists() else ""
            if "@AGENTS.md" not in text.splitlines():
                writes["CLAUDE.md"] = text + ("\n" if text and not text.endswith("\n") else "") + "\n@AGENTS.md\n"
        for path in sorted((ASSETS / "templates").rglob("*")):
            if path.is_file():
                destination = p["paths"]["templates"] + "/" + path.relative_to(ASSETS / "templates").as_posix()
                if not safe(root, destination).exists() or destination in owned:
                    managed(destination, path.read_bytes())
        defaults = {
            context_path: project_context(profile),
            standard_path: (ASSETS / "engineering-standard.md").read_text(encoding="utf-8").replace("docs/project-context.md", context_path),
            p["paths"]["baseline"] + "/README.md": "# Baseline\n\n" + ("Existing repository: inventory is pending review. Use baseline-repo; inventory alone is not an approved baseline.\n" if p["mode"] == "existing" else "New repository: no historical system is asserted. Build specifications from real requirements.\n"),
            p["paths"].get("questions", p["paths"]["baseline"] + "/questions.json"): dump({"schema_version": 1, "questions": []}) if p["paths"].get("questions", "questions.json").endswith(".json") else "# Questions and decisions\n\nMaintain the existing native ledger format and decision identifiers.\n",
            p["paths"]["adr"] + "/README.md": "# Architecture decisions\n\nRecord consequential, long-lived choices using docs/templates/adr.md. Preserve accepted history and link superseding decisions.\n",
        }
        for relative, content in defaults.items():
            if relative == p["paths"]["adr"] + "/README.md" and any(safe(root, p["paths"]["adr"]).glob("[0-9]*.md")):
                continue
            if not safe(root, relative).exists():
                writes[relative] = content
        if hooks or old_manifest.get("hooks_requested", False):
            for agent, relative in (("codex", ".codex/hooks.json"), ("claude", ".claude/settings.json")):
                if agent not in p["agents"]:
                    continue
                config = read_json(safe(root, relative), {})
                if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
                    raise KitError(f"Cannot merge hook configuration: {relative}")
                hooks_map = config.setdefault("hooks", {})
                for event, action in (("SessionStart", "session"), ("Stop", "stop")):
                    command = hook_command(action, agent)
                    entries = hooks_map.setdefault(event, [])
                    if not isinstance(entries, list):
                        raise KitError(f"{relative}: hooks.{event} must be an array")
                    found = False
                    merged_entries = []
                    for entry in entries:
                        handlers = []
                        for handler in entry.get("hooks", []):
                            if is_kit_hook(handler.get("command"), action, agent):
                                if not found:
                                    handlers.append({**handler, "command": command})
                                    found = True
                            else:
                                handlers.append(handler)
                        if handlers or not entry.get("hooks"):
                            merged_entries.append({**entry, "hooks": handlers})
                    if not found:
                        merged_entries.append({"hooks": [{"type": "command", "command": command, "timeout": 15}]})
                    hooks_map[event] = merged_entries
                writes[relative] = dump(config)
        if ci:
            managed(".github/workflows/ark-verify.yml", (ASSETS / "consumer-ci.yml").read_bytes())
        manifest = {"schema_version": 1, "kit_version": VERSION, "files": owned, "agents_block": digest(block_text.encode()), "hooks_requested": hooks or old_manifest.get("hooks_requested", False), "ci_requested": ci or old_manifest.get("ci_requested", False)}
        migrations = list(old_manifest.get("migrations", []))
        if retired or preserved_custom:
            migrations.append({"from": old_manifest.get("kit_version"), "to": VERSION, "retired": retired, "preserved_custom": preserved_custom})
        if migrations:
            manifest["migrations"] = migrations
        writes[MANIFEST] = dump(manifest)
        changed = transact(root, writes)
        if p["mode"] == "existing":
            baseline_inventory(root, p)
        baseline_status = "NOT_APPLICABLE" if p["mode"] == "new" else ("PENDING" if baseline_findings(root, p) else "STATIC_REVIEW_CURRENT")
        report = {"status": "PASS", "meaning": "Scaffolding installed; no semantic baseline or runtime hook trust is asserted.", "mode": p["mode"], "changed": changed, "changed_scope": "Installation/configuration assets; excludes this generated report and baseline/runtime observations.", "baseline": baseline_status, "checks": "NOT_RUN", "hook_trust": "NOT_VERIFIED", "branch_protection": "NOT_VERIFIED", "kit_version": VERSION}
        atomic(safe(root, ".ai/init-report.json"), dump(report))
        return report


def onboard_repo(root, mode="auto", agents=None, hooks=True, ci="none", upgrade=False, copy_skills=None, path_overrides=None):
    """Shared first-use operation for installed Skills and the compatibility entry."""
    # A GitHub remote says nothing about whether this project wants hosted CI.
    enable_ci = ci == "github"
    result = init_repo(root, mode, agents, hooks, enable_ci, upgrade, copy_skills, path_overrides)
    p = policy_at(root)
    health = doctor(root, p)
    result["scaffold_status"] = result["status"]
    result["status"] = health["status"]
    result["setup"] = "No package or global command installation required; use the vendored runtime after initialization."
    result["skill_delivery"] = p["skill_delivery"]
    result["local_command"] = [sys.executable, "hack/ai/ark.py"]
    result["diagnostics"] = health
    result["agent_next_step"] = (
        "Continue initialize-repo and baseline-repo: inspect actual source/config/tests, confirm real checks, explain behavior and record coverage/gaps. Scaffolding PASS is not semantic completion."
        if result["mode"] == "existing" else
        "Continue initialize-repo; retain historical Baseline as not applicable and establish real requirements only when goals are known."
    )
    return result


def evidence_root(p):
    return p["paths"].get("evidence", p["paths"]["baseline"] + "/raw")


def baseline_inventory(root, p):
    path = p["paths"]["baseline"] + "/coverage.json"
    old = read_json(safe(root, path), {"files": {}})
    files = inventory_files(root, p)
    reviewed = {}
    for relative, details in files.items():
        if not any(under(relative, prefix) for prefix in p.get("source_paths", ["."])):
            continue
        previous = old.get("files", {}).get(relative, {})
        state = previous.get("status", "unreviewed") if previous.get("sha256") == details["sha256"] else ("stale" if previous else "unreviewed")
        reviewed[relative] = {**details, "status": state, "document": previous.get("document"), "document_sha256": previous.get("document_sha256"), "reviewer": previous.get("reviewer"), "reviewed_at": previous.get("reviewed_at"), "level": previous.get("level"), "module": relative.split("/")[0] if "/" in relative else "root"}
    source = git(root, "rev-parse", "HEAD", optional=True)
    coverage = {"schema_version": 1, "source_ref": source.decode().strip() if source else None, "source_fingerprint": digest(dump(files).encode()), "files": reviewed, "removed": sorted(set(old.get("files", {})) - set(reviewed))}
    snapshot = evidence_root(p) + "/inventory-" + coverage["source_fingerprint"][:16] + ".json"
    writes = {path: dump(coverage)}
    if not safe(root, snapshot).exists():
        writes[snapshot] = dump(coverage)
    transact(root, writes)
    return {"status": "PENDING", "files": len(reviewed), "reviewed": sum(x["status"] == "reviewed" for x in reviewed.values()), "coverage": path, "meaning": "Inventory is evidence navigation, not semantic approval."}


def source_reference_valid(text, relative, content):
    try:
        lines = len(content.decode("utf-8").splitlines()) if b"\0" not in content else 0
    except UnicodeError:
        lines = 0
    if not lines:
        return bool(re.search(r"(?<![\w./-])" + re.escape(relative + "@sha256:" + digest(content)) + r"(?![a-f0-9])", text))
    refs = re.findall(r"(?<![\w./-])" + re.escape(relative) + r":L(\d+)(?:-L?(\d+))?\b", text)
    return bool(refs) and all(1 <= int(a) <= int(b or a) <= lines for a, b in refs)


def baseline_review(root, p, document, files, reviewer):
    path = safe(root, document)
    if not path.is_file():
        raise KitError("Write the module explanation before recording a review.")
    text = path.read_text(encoding="utf-8")
    if FILL in text or not knowledge_sections_present(p, "module", text):
        raise KitError("Module explanation must fill the module template: Purpose, Flow, State and failure, Evidence, Gaps.")
    coverage_path = safe(root, p["paths"]["baseline"] + "/coverage.json")
    coverage = read_json(coverage_path)
    for relative in files:
        source = safe(root, relative)
        if relative not in coverage["files"] or not source.is_file():
            raise KitError(f"File is not in the current inventory: {relative}")
        if digest(source.read_bytes()) != coverage["files"][relative]["sha256"]:
            raise KitError(f"Inventory is stale for {relative}; refresh it first.")
        if not source_reference_valid(text, relative, source.read_bytes()):
            raise KitError(f"Provide valid file:L1-LN evidence for {relative}; empty/binary inputs use file@sha256:<actual digest>")
    for relative in files:
        coverage["files"][relative].update(status="reviewed", document=document, document_sha256=digest(path.read_bytes()), reviewer=reviewer, level="static", reviewed_at=now())
    atomic(coverage_path, dump(coverage))
    knowledge_record(root, p, "module", document, files, reviewer)
    return {"status": "PASS", "meaning": "Static review declaration recorded; semantic correctness still requires review and behavioral verification.", "files": files}


def knowledge_sections_present(p, kind, text):
    aliases = {
        "module": {"purpose": ["## Purpose", "## 职责", "## 模块职责"], "flow": ["## Flow", "## 流程", "## 业务流程", "## 处理流程"], "state": ["## State and failure", "## 状态与异常"], "evidence": ["## Evidence", "## 证据", "## 源码证据"], "gaps": ["## Gaps", "## 缺口", "## 未核实项"]},
        "contract": {"evidence": ["## Source version and evidence", "## 来源与证据"], "interface": ["## Inputs and outputs", "## 输入与输出"], "failure": ["## Timing and failure", "## 时序与异常"], "promotion": ["## Compatibility and promotion", "## 兼容与晋升"]},
        "cases": {"scope": ["## Scope and source", "## 范围与来源"], "cases": ["## Cases", "## 用例"]},
    }
    if kind not in aliases:
        return False
    mapped = p.get("knowledge_sections", {}).get(kind, {})
    return all(any(heading in text for heading in ([mapped[role]] if role in mapped else names)) for role, names in aliases[kind].items())


def knowledge_record(root, p, kind, document, files, reviewer):
    """Record an explained artifact with immutable source/document snapshots, not approval."""
    if not reviewer.strip() or not files:
        raise KitError("Knowledge needs a reviewer identity and actual source scope")
    headings = {
        "module": ("## Purpose", "## Flow", "## State and failure", "## Evidence", "## Gaps"),
        "contract": ("## Source version and evidence", "## Inputs and outputs", "## Timing and failure", "## Compatibility and promotion"),
        "cases": ("## Scope and source", "## Cases"),
    }
    if kind not in headings:
        raise KitError("Knowledge kind must be module, contract or cases")
    path = safe(root, document)
    text = path.read_text(encoding="utf-8")
    if FILL in text or not knowledge_sections_present(p, kind, text):
        raise KitError(f"Fill the {kind} explanation before recording it")
    sources = {}
    for relative in files:
        source = safe(root, relative)
        if not source.is_file() or excluded(relative, p):
            raise KitError(f"Knowledge source is absent or excluded: {relative}")
        if not source_reference_valid(text, relative, source.read_bytes()):
            raise KitError(f"Provide valid source evidence for {relative}; empty/binary inputs use file@sha256:<actual digest>")
        sources[relative] = digest(source.read_bytes())
    cases = []
    if kind == "cases":
        for line in text.splitlines():
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            if line.startswith('|') and len(cells) >= 6 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", cells[0]) and any(x.isdigit() for x in cells[0]):
                if any(not cell for cell in cells[:6]):
                    raise KitError("Each behavior case needs preconditions, input, expected result, evidence and verification")
                cases.append(cells[0])
        if not cases or len(cases) != len(set(cases)):
            raise KitError("Behavior cases need actual, uniquely identified scenarios")
    base = p["paths"]["baseline"]
    index_path = safe(root, base + "/knowledge.json")
    index = read_json(index_path, {"schema_version": 1, "documents": {}})
    record = {"kind": kind, "document": document, "document_sha256": digest(path.read_bytes()), "sources": sources,
              "reviewer": reviewer, "level": "static-declared", "state": "reviewed", "cases": cases, "promoted_to": []}
    identity = digest(dump(record).encode())
    snapshot = evidence_root(p) + "/reviews/" + identity
    record.update(snapshot=snapshot, source_ref=(git(root, "rev-parse", "HEAD", optional=True) or b"").decode().strip() or None)
    previous = index["documents"].get(document)
    if previous and previous.get("snapshot") == snapshot:
        return {"status": "PASS", "meaning": "Unchanged static declaration retained", "document": document, "snapshot": snapshot}
    index["documents"][document] = record
    writes = {base + "/knowledge.json": dump(index)}
    if not safe(root, snapshot + "/record.json").exists():
        writes[snapshot + "/record.json"] = dump(record)
        writes[snapshot + "/document.md"] = text
    transact(root, writes)
    return {"status": "PASS", "meaning": "Static declaration recorded; case execution and semantic review are separate", "document": document, "snapshot": snapshot}


def knowledge_status(root, p, scope=None):
    index = read_json(safe(root, p["paths"]["baseline"] + "/knowledge.json"), {"documents": {}})
    documents = []
    for name, item in index["documents"].items():
        if scope and not any(under(name, prefix) or any(under(path, prefix) for path in item["sources"]) for prefix in scope):
            continue
        stale = []
        if item.get("state") != "obsolete":
            evidence = {name: item["document_sha256"], **item["sources"]}
            if item.get("decision"):
                evidence[item["decision"]] = item["decision_sha256"]
            for relative, expected in evidence.items():
                path = safe(root, relative)
                if not path.is_file() or digest(path.read_bytes()) != expected:
                    stale.append(relative)
        documents.append({**item, "freshness": "stale" if stale else "historical" if item.get("state") == "obsolete" else "current", "changed": stale})
    return {"status": "PENDING" if any(item["freshness"] == "stale" for item in documents) else "PASS", "documents": documents,
            "meaning": "Source/document currency and declared coverage, not certified semantic completeness or executed cases"}


def delivery_knowledge_findings(root, p, scope):
    if not scope:
        return []
    return [{"status": "PENDING", "code": "knowledge-stale", "path": item["document"],
             "message": f"Recheck affected knowledge {item['document']} against {item['changed']}; refresh its declaration or explicitly retire it with a decision. Original snapshots stay immutable."}
            for item in knowledge_status(root, p, scope)["documents"] if item["freshness"] == "stale"]


def knowledge_transition(root, p, document, reviewer, decision, requirements=None, obsolete=False):
    base = p["paths"]["baseline"]
    index = read_json(safe(root, base + "/knowledge.json"))
    if document not in index["documents"]:
        raise KitError("Register source-backed knowledge before transitioning it")
    artifact = safe(root, decision)
    if not reviewer.strip() or not artifact.is_file() or not artifact.read_bytes().strip():
        raise KitError("An actual accepted decision/compatibility artifact and reviewer are required")
    if not obsolete:
        status = next(item for item in knowledge_status(root, p)["documents"] if item["document"] == document)
        if status["freshness"] != "current":
            raise KitError("Refresh stale source/document evidence before promotion")
        current = current_requirement_ids(root, p)
        if not requirements or not set(requirements).issubset(current):
            raise KitError("Promotion must name real current requirement declarations")
    item = index["documents"][document]
    item.update(state="obsolete" if obsolete else "promoted", promoted_to=[] if obsolete else requirements,
                decision=decision, decision_sha256=digest(artifact.read_bytes()), decision_reviewer=reviewer)
    event = {"document": document, "record": item, "decision_text": artifact.read_text(encoding="utf-8"), "recorded_at": now(), "meaning": "Recorded decision; authority and semantic quality require review"}
    event_path = evidence_root(p) + "/transitions/" + digest(dump(event).encode()) + ".json"
    transact(root, {base + "/knowledge.json": dump(index), event_path: dump(event)})
    return {"status": "PASS", "state": item["state"], "document": document, "meaning": event["meaning"]}


def decision_record(root, p, identity, category=None, question=None, scope=None, evidence=None, outcome=None, reviewer=None, options=None, recommendation=None, owner=None):
    path = p["paths"].get("questions", p["paths"]["baseline"] + "/questions.json")
    if not path.endswith(".json"):
        raise KitError("The mapped decision ledger uses its native file format. Update it with the existing workflow; no parallel ledger will be created.")
    ledger = read_json(safe(root, path), {"schema_version": 1, "questions": []})
    if not isinstance(ledger.get("questions"), list):
        raise KitError("Map the existing decision ledger before updating its schema")
    if not re.fullmatch(r"[A-Z][A-Z0-9-]*", identity):
        raise KitError("Use an existing stable uppercase decision ID")
    existing = next((item for item in ledger["questions"] if item.get("id") == identity), None)
    if outcome is None:
        if existing or not question or not scope:
            raise KitError("A new question needs a unique ID, concrete question and scope")
        for relative in scope:
            if relative != ".": safe(root, relative)
        existing = {"id": identity, "category": category, "question": question, "scope": scope, "status": "open", "history": [], "options": options or [], "recommendation": recommendation, "owner": owner}
        ledger["questions"].append(existing)
    else:
        if not existing or not reviewer or not evidence:
            raise KitError("Resolve an existing item with an actual reviewer and evidence")
        for relative in evidence:
            if not safe(root, relative).is_file(): raise KitError(f"Decision evidence missing: {relative}")
        existing.setdefault("history", []).append({key: value for key, value in existing.items() if key != "history"})
        existing.update(status="resolved", outcome=outcome, reviewer=reviewer,
                        evidence={relative: digest(safe(root, relative).read_bytes()) for relative in evidence})
    rows = ["# Questions and decisions", "", f"Generated from `{path}`; edit the ledger through explicit records, not this view.", "", "| ID | Category | Status | Question | Outcome |", "| --- | --- | --- | --- | --- |"]
    for item in ledger["questions"]:
        cells = [str(item.get(key, "")).replace('|', '\\|').replace('\n', ' ') for key in ("id", "category", "status", "question", "outcome")]
        rows.append("| " + " | ".join(cells) + " |")
    cards = ["# Decision details", "", f"Generated from `{path}`; this view is not a second status source.", ""]
    for item in ledger["questions"]:
        cards += ["## " + item['id'], item.get('question', ''), "", "Status: " + item.get('status', 'unknown'), "Owner: " + str(item.get('owner') or 'not assigned')]
        cards += ["- " + option for option in item.get('options', [])]
        cards += ["Recommendation: " + str(item.get('recommendation') or 'not established'), "Outcome: " + str(item.get('outcome') or 'unresolved'), ""]
    summary_path = p["paths"].get("decision_view", p["paths"]["baseline"] + "/questions.md")
    details_path = p["paths"].get("decision_details", p["paths"]["baseline"] + "/decision-details.md")
    if len({path, summary_path, details_path}) != 3:
        raise KitError("Decision source and generated view paths must be distinct")
    transact(root, {path: dump(ledger), summary_path: "\n".join(rows) + "\n", details_path: "\n".join(cards)})
    return {"status": "PASS", "id": identity, "state": existing["status"], "meaning": "Decision declaration recorded; not independent approval"}


def baseline_findings(root, p, scope=None):
    if p["mode"] == "new" and not safe(root, p["paths"]["baseline"] + "/coverage.json").exists():
        return []
    coverage = read_json(safe(root, p["paths"]["baseline"] + "/coverage.json"), {"files": {}})
    findings = []
    current = inventory_files(root, p)
    for relative in sorted(set(current) - set(coverage.get("files", {}))):
        if is_behavior(relative, p) and (not scope or any(under(relative, prefix) for prefix in scope)) and any(under(relative, prefix) for prefix in p.get("source_paths", ["."])):
            findings.append({"status": "PENDING", "code": "baseline-uninventoried", "message": f"No baseline inventory record for {relative}; inspect its origin and refresh scope."})
    for relative, item in coverage.get("files", {}).items():
        if scope and not any(under(relative, prefix) for prefix in scope):
            continue
        if not is_behavior(relative, p):
            continue
        detail = current.get(relative)
        if not detail:
            findings.append({"status": "PENDING", "code": "baseline-removed", "message": f"Historical behavior was removed at {relative}; record its compatibility decision before refreshing inventory."})
            continue
        document = item.get("document")
        document_path = safe(root, document) if document else None
        if item.get("status") != "reviewed" or item.get("sha256") != detail["sha256"] or not document_path or not document_path.is_file() or item.get("document_sha256") != digest(document_path.read_bytes()):
            findings.append({"status": "PENDING", "code": "baseline-unverified", "message": f"Baseline needs source/document review: {relative}"})
    return findings


def change_directories(root, p, archived=False):
    base = safe(root, p["paths"]["changes"])
    parents = [base] + ([base / "archive"] if archived else [])
    return sorted(path for parent in parents if parent.is_dir() for path in parent.iterdir()
                  if path.is_dir() and path.name != "archive" and
                  ((path / "ark.json").is_file() or (path / "proposal.md").is_file()))


def file_change_metadata(root, p, directory):
    """Read ordinary change documents; no toolkit-owned lifecycle or sidecar is needed."""
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", directory.name) if directory.parent.name == "archive" else directory.name
    proposal = (directory / "proposal.md").read_text(encoding="utf-8")
    deltas = list(directory.glob("specs/**/*.md"))
    text = "\n".join(path.read_text(encoding="utf-8") for path in deltas)
    kind_match = re.search(r"^Kind:\s*(feature|fix|refactor|maintenance|docs)\s*$", proposal, re.MULTILINE)
    scope = []
    for candidate in re.findall(r"`([^`\n]+)`", proposal):
        candidate = candidate.rstrip("/")
        try:
            path = safe(root, candidate)
        except KitError:
            continue
        if path.exists() and not excluded(candidate, p) and (path.is_dir() or is_behavior(candidate, p)):
            scope.append(candidate)
    origin = "proposal" if scope else "repository"
    if not scope:
        origin = "repository"
        scope = p.get("source_paths", ["."])
    records = [item for path in deltas for item in spec_records(path.read_text(encoding="utf-8"), path.parent.name)]
    removed = [item["id"] for item in records if item["section"] == "REMOVED"]
    return {"schema_version": 1, "id": name, "kind": kind_match.group(1) if kind_match else ("feature" if deltas else "maintenance"),
            "scope": sorted(set(scope)), "scope_source": origin, "requirements": sorted({item["id"] for item in records}),
            "removed_requirements": sorted(set(removed)), "state": "complete" if directory.parent.name == "archive" else "draft", "origin": "files"}


def change_at(root, p, change):
    if not ID.fullmatch(change or ""):
        raise KitError("Change ID must be lowercase words separated by hyphens")
    directory = safe(root, p["paths"]["changes"] + "/" + change)
    if not directory.exists():
        matches = []
        for path in change_directories(root, p, archived=True):
            if path.parent.name == "archive" and re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.name) == change:
                matches.append(path)
        if len(matches) != 1:
            raise KitError(f"Expected one active/archived change with ID {change}; found {len(matches)}")
        directory = matches[0]
    metadata = read_json(directory / "ark.json") if (directory / "ark.json").is_file() else file_change_metadata(root, p, directory)
    if metadata.get("id") != change or metadata.get("kind") not in {"feature", "fix", "refactor", "maintenance", "docs"}:
        raise KitError(f"Invalid change metadata: {change}")
    if not isinstance(metadata.get("scope"), list) or not metadata["scope"]:
        raise KitError(f"Change scope is missing: {change}")
    for relative in metadata["scope"]:
        if relative != ".":
            safe(root, relative)
    if not isinstance(metadata.get("requirements", []), list) or any(not isinstance(x, str) or not x.strip() for x in metadata.get("requirements", [])):
        raise KitError(f"Malformed requirement ID in {change}")
    removed = metadata.get("removed_requirements", [])
    if not isinstance(removed, list) or not set(removed).issubset(metadata.get("requirements", [])):
        raise KitError("removed_requirements must be a subset of the affected requirements")
    return directory, metadata


def new_change(root, p, change, kind, scope, requirements, removed=None):
    if not ID.fullmatch(change):
        raise KitError("Use a lowercase hyphenated change ID")
    base = p["paths"]["changes"] + "/" + change
    if safe(root, base).exists():
        raise KitError(f"Change already exists: {change}")
    for path in safe(root, p["paths"]["changes"] + "/archive").glob("*/ark.json"):
        if read_json(path).get("id") == change:
            raise KitError(f"Change ID was already archived: {change}")
    for relative in scope:
        if relative != ".":
            safe(root, relative)
    if any(not REQ.fullmatch(x) for x in requirements):
        raise KitError("Requirements must use REQ-UPPERCASE-001 identifiers")
    if not set(removed or []).issubset(requirements):
        raise KitError("Removed requirements must also be listed as affected requirements")
    metadata = {"schema_version": 1, "id": change, "kind": kind, "scope": scope, "requirements": requirements, "removed_requirements": removed or [], "state": "draft", "created_at": now()}
    writes = {base + "/ark.json": dump(metadata)}
    for template, name in (("proposal.md", "proposal.md"), ("tasks.md", "tasks.md"), ("design.md", "design.md")):
        writes[base + "/" + name] = (ASSETS / "templates" / template).read_text(encoding="utf-8").replace("{{CHANGE}}", change)
    if kind in {"feature", "fix", "refactor"}:
        writes[base + "/specs/change/spec.md"] = (ASSETS / "templates" / "delta.md").read_text(encoding="utf-8").replace("{{REQUIREMENTS}}", ", ".join(requirements) or "REQ-EXAMPLE-001")
    transact(root, writes)
    return {"status": "PENDING", "change": change, "state": "draft", "path": base}


def changed_files(root, base=None):
    answer = set()
    if base:
        merge = git(root, "merge-base", base, "HEAD").decode().strip()
        values = [git(root, "diff", "--name-only", "-z", merge, "HEAD")]
    else:
        values = []
    diff = git(root, "diff", "--name-only", "-z", "HEAD", optional=not bool(base))
    if diff is not None:
        values.append(diff)
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z", optional=True)
    if untracked:
        values.append(untracked)
    for value in values:
        answer.update(x.decode("utf-8") for x in value.split(b"\0") if x)
    return sorted(answer)


def context_key(root, session="default"):
    # Worktree root is included; branch changes cannot borrow another task pointer.
    branch = git(root, "symbolic-ref", "--short", "HEAD", optional=True)
    return digest((str(root.resolve()) + "\0" + (branch.decode().strip() if branch else "detached") + "\0" + session).encode())[:24]


def activate(root, change, session="default"):
    relative = f".ai/runtime/contexts/{context_key(root, session)}.json"
    branch = (git(root, "symbolic-ref", "--short", "HEAD", optional=True) or b"detached").decode().strip()
    atomic(safe(root, relative), dump({"change": change, "session": session, "branch": branch, "activated_at": now()}))
    return relative


def active(root, session="default"):
    return read_json(safe(root, f".ai/runtime/contexts/{context_key(root, session)}.json"), {}).get("change")


def specification_findings(root, p, paths=None):
    findings, seen = [], {}
    paths = list(paths) if paths is not None else sorted(safe(root, p["paths"]["specs"]).glob("**/*.md"))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        text = safe(root, relative).read_text(encoding="utf-8")
        records = spec_records(text, path.parent.name)
        def issue(status, code, message, line=1):
            findings.append({"status": status, "code": code, "path": relative, "line": line, "message": f"{relative}:{line}: {message}"})
        if path.name == "spec.md" and not records:
            issue("PENDING", "spec-empty", "Declare observable requirements or valid native renames.")
        for item in records:
            identifier, body, line = item["id"], item["body"], item["line"]
            if item["section"] != "RENAMED":
                if identifier in seen:
                    issue("FAIL", "duplicate-requirement", f"{identifier} also declared in {seen[identifier]}", line)
                seen[identifier] = relative
            if item["section"] == "REMOVED":
                if not re.search(r"(?i)(reason|migration|原因|迁移)", body):
                    issue("PENDING", "removal-rationale", f"Explain removal and compatibility of {identifier}.", line)
                continue
            if item["section"] == "RENAMED":
                continue
            if not re.search(r"\b(SHALL|MUST|SHOULD)\b|必须|应当", body):
                issue("FAIL", "requirement-wording", f"{identifier} needs an observable normative statement.", line)
            scenarios = re.split(r"(?m)^#### Scenario:[^\n]*\n", body)[1:]
            if not scenarios or any(not re.search(r"\bWHEN\b|当", scenario, re.I) or not re.search(r"\bTHEN\b|则", scenario, re.I) for scenario in scenarios):
                issue("FAIL", "scenario-conditions", f"{identifier} needs named scenarios with WHEN and THEN.", line)
            verification = re.search(r"(?im)^Verification:\s*(.+)$", body)
            if verification and not re.match(r"(automated|manual|external)\b", verification.group(1), re.I):
                issue("FAIL", "verification-type", f"{identifier}: use automated, manual or external verification.", line)
            for match in re.finditer(r"(?im)^(?:Source|Baseline|Decision):\s*\x60?([^\s\x60]+)", body):
                reference = re.sub(r":L?\d+(?:-L?\d+)?$", "", match.group(1).split("#", 1)[0])
                if "://" not in reference and not safe(root, reference).is_file():
                    issue("FAIL", "broken-evidence-link", f"Missing referenced evidence: {reference}", line)
        for section in re.split(r"(?m)^## ", markdown_structure(text)):
            if section.startswith("RENAMED Requirements"):
                tags = re.findall(r"(?m)^\s*-?\s*(FROM|TO):", section)
                if not tags or len(tags) % 2 or any(tag != ("FROM" if i % 2 == 0 else "TO") for i, tag in enumerate(tags)):
                    issue("FAIL", "rename-pairs", "Native renames require alternating FROM and TO pairs.")
    return findings


def requirement_test_findings(root, p, records, current=False):
    """Check every effective promise, including ones absent from the selected delta."""
    findings = []
    tests = "\n".join(safe(root, name).read_text(encoding="utf-8", errors="replace")
                      for name in inventory_files(root, p) if any(under(name, prefix) for prefix in p["test_paths"]))
    for item in records:
        if item["section"] in {"REMOVED", "RENAMED"}:
            continue
        identifier = item["id"]
        declared = re.search(r"(?im)^Verification:\s*(automated|manual|external)\b", item["body"])
        mapping = p.get("requirements", {}).get(identifier, {})
        kind = mapping.get("type", declared.group(1).lower() if declared else "automated")
        if declared and kind != declared.group(1).lower():
            findings.append({"status": "FAIL", "code": "requirement-verification", "path": item.get("path"),
                             "line": item.get("line", 1), "message": f"{identifier}: check mapping must preserve declared Verification: {declared.group(1).lower()}."})
            continue
        checks = {check["name"] for check in p["checks"] if check.get("required", True)
                  and "delivery" in check.get("phases", ["ready", "delivery"])
                  and check.get("type", "command") == ("command" if kind == "automated" else kind)}
        mapped = bool(mapping.get("checks")) and set(mapping["checks"]).issubset(checks)
        referenced = bool(re.search(r"(?<![\w-])" + re.escape(identifier) + r"(?![\w-])", tests))
        if kind == "automated" and (mapped or referenced) or kind in {"manual", "external"} and mapped:
            continue
        code = "requirement-test" if kind == "automated" else "requirement-check"
        findings.append({"status": "PENDING", "code": "current-" + code if current else code,
                         "path": item.get("path"), "line": item.get("line", 1),
                         "message": f"{identifier} needs {'a test-source reference or explicit required delivery check mapping' if kind == 'automated' else 'an explicit required ' + kind + ' delivery check mapping'}; textual references do not certify assertion quality."})
    return findings


def current_test_findings(root, p):
    records = [{**item, "path": path.relative_to(root).as_posix()}
               for path in sorted(safe(root, p["paths"]["specs"]).glob("**/*.md"))
               for item in spec_records(path.read_text(encoding="utf-8"), path.parent.name)]
    return requirement_test_findings(root, p, records, current=True)


def adr_status(text):
    match = re.search(r"(?m)^[ \t]*(?:[-*][ \t]+)?(?:\*\*Status:\*\*|(?:\*\*)?Status(?:\*\*)?:)[ \t]*(.+?)[ \t]*$", markdown_structure(text))
    return (match.group(1).strip().strip("`"), match.start(), match.end()) if match else None


def adr_body(text):
    status = adr_status(text)
    return text[:status[1]] + "Status:" + text[status[2]:] if status else text


def engineering_relations(root, p):
    findings = []
    current = current_requirement_ids(root, p)
    for directory in change_directories(root, p, archived=True):
        if directory.parent.name != "archive":
            continue
        for path in directory.glob("specs/**/*.md"):
            for item in spec_records(path.read_text(encoding="utf-8"), path.parent.name):
                if item["section"] == "REMOVED" and item["id"] in current:
                    findings.append({"status": "FAIL", "code": "retired-id-reuse", "path": path.relative_to(root).as_posix(),
                                     "message": f"Retired requirement remains/reappears current: {item['id']}"})
    numbers, adrs = {}, []
    for path in sorted(safe(root, p["paths"]["adr"]).glob("[0-9]*.md")):
        number = int(re.match(r"\d+", path.name).group())
        if number in numbers:
            findings.append({"status": "FAIL", "code": "adr-number", "message": f"Duplicate ADR number: {path.name}, {numbers[number]}"})
        numbers[number] = path.name
        adrs.append((number, path, path.read_text(encoding="utf-8")))
    for number, path, text in adrs:
        status = adr_status(text)
        if not status or not re.match(r"(Proposed|Accepted|Rejected|Deprecated|Superseded)\b", status[0]):
            findings.append({"status": "FAIL", "code": "adr-status", "message": f"Declare an ADR lifecycle status: {path.relative_to(root)}"})
        elif status[0].startswith("Superseded"):
            target = re.search(r"(?:ADR[- ]|by\s+)(\d+)", status[0], re.I)
            if not target or int(target.group(1)) not in numbers or int(target.group(1)) == number:
                findings.append({"status": "FAIL", "code": "adr-supersession", "message": f"Missing/distinct superseding ADR required: {path.relative_to(root)}"})
    index = read_json(safe(root, p["paths"]["baseline"] + "/knowledge.json"), {"documents": {}})
    for document, item in index["documents"].items():
        if item.get("state") == "promoted" and not set(item.get("promoted_to", [])).issubset(current):
            findings.append({"status": "FAIL", "code": "knowledge-promotion", "message": f"Promotion refers to missing current requirements: {document}"})
    return findings


def apply_format_exceptions(root, p, findings):
    """Only explicit, content-bound, expiring format debt can become WARN."""
    allowed = {"requirement-wording", "scenario-conditions", "verification-type"}
    rules = p.get("format_exceptions", [])
    if not isinstance(rules, list):
        raise KitError("policy.format_exceptions must be an array")
    result = []
    for finding in findings:
        entry = dict(finding)
        for rule in rules:
            if not isinstance(rule, dict):
                raise KitError("Format exceptions must be objects")
            if rule.get("code") != entry.get("code") or rule.get("path") != entry.get("path"):
                continue
            valid = rule.get("code") in allowed and all(isinstance(rule.get(key), str) and rule[key].strip() for key in ("owner", "reason", "expires", "decision", "sha256", "decision_sha256"))
            try:
                valid = valid and date.fromisoformat(rule["expires"]) >= datetime.now(timezone.utc).date()
                source, decision = safe(root, rule["path"]), safe(root, rule["decision"])
                valid = valid and source.is_file() and decision.is_file() and digest(source.read_bytes()) == rule["sha256"] and digest(decision.read_bytes()) == rule["decision_sha256"]
            except (KitError, ValueError, KeyError):
                valid = False
            if valid:
                entry.update(status="WARN", exception={key: rule[key] for key in ("owner", "reason", "expires", "decision")})
            else:
                entry["exception_rejected"] = "Expired, unsafe, unsupported, incomplete or changed content/decision."
        result.append(entry)
    return result


def verification_document(existing, generated):
    managed = VERIFY_START + "\n" + generated.rstrip() + "\n" + VERIFY_END
    if VERIFY_START not in existing and VERIFY_END not in existing:
        return existing + ("\n\n" if existing else "") + managed + "\n"
    if existing.count(VERIFY_START) != 1 or existing.count(VERIFY_END) != 1 or existing.index(VERIFY_END) < existing.index(VERIFY_START):
        return existing
    return existing[:existing.index(VERIFY_START)] + managed + existing[existing.index(VERIFY_END) + len(VERIFY_END):]


def structure_findings(root, p):
    findings = []
    manifest = read_json(safe(root, MANIFEST))
    if manifest.get("kit_version") != VERSION or p.get("kit_version") != VERSION:
        findings.append({"status": "FAIL", "code": "version", "message": "Installed runtime, manifest and policy differ; explicitly migrate."})
    for relative, expected in manifest.get("files", {}).items():
        path = safe(root, relative)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            findings.append({"status": "FAIL", "code": "managed-drift", "message": f"Managed file missing or changed: {relative}"})
    agents = safe(root, "AGENTS.md").read_text(encoding="utf-8")
    if agents.count(START) != 1 or agents.count(END) != 1:
        findings.append({"status": "FAIL", "code": "agents", "message": "Managed routing block is missing or malformed."})
    elif digest(agents[agents.index(START):agents.index(END) + len(END)].encode()) != manifest.get("agents_block"):
        findings.append({"status": "FAIL", "code": "agents-drift", "message": "Managed routing block differs from the installed version."})
    if "claude" in p.get("agents", []):
        claude = safe(root, "CLAUDE.md")
        if not claude.is_file() or "@AGENTS.md" not in claude.read_text(encoding="utf-8").splitlines():
            findings.append({"status": "FAIL", "code": "claude-entry", "message": "CLAUDE.md compatibility import is missing."})
    for path in sorted(safe(root, p["paths"]["adr"]).glob("[0-9]*.md")):
        text = safe(root, path.relative_to(root).as_posix()).read_text(encoding="utf-8")
        if any(heading not in text for heading in ("## Context", "## Decision", "## Alternatives", "## Consequences")):
            findings.append({"status": "FAIL", "code": "adr-structure", "message": f"ADR missing required sections: {path.relative_to(root)}"})
    return apply_format_exceptions(root, p, findings + specification_findings(root, p) + engineering_relations(root, p)) + current_test_findings(root, p)


def scoped_sources(root, p, scope):
    return {path: item["sha256"] for path, item in inventory_files(root, p).items()
            if is_behavior(path, p) and any(under(path, prefix) for prefix in scope)
            and not any(under(path, prefix) for prefix in p["test_paths"])}


def established_behavior(root, p, metadata, change):
    """Observe retained behavior, including code delivered after an empty initialization."""
    records = read_json(safe(root, ".ai/established.json"), {"files": {}})["files"]
    result = {}
    for path, item in records.items():
        original = item.get("previous") if item.get("change") == change else item
        if original and any(under(path, prefix) for prefix in metadata["scope"]):
            result[path] = original["sha256"]
    listed = git(root, "ls-tree", "-r", "--name-only", "-z", "HEAD", optional=True)
    dirty = set(changed_files(root)) if listed is not None else set()
    for raw in (listed or b"").split(b"\0"):
        path = raw.decode("utf-8")
        if not path or excluded(path, p) or not is_behavior(path, p) or any(under(path, prefix) for prefix in p["test_paths"]):
            continue
        if any(under(path, prefix) for prefix in metadata["scope"]) and records.get(path, {}).get("change") != change:
            content = git(root, "show", "HEAD:" + path, optional=True)
            if content is not None:
                # Git can store LF while the unchanged checkout uses CRLF. Keep raw
                # workspace fingerprints; use Git's actual diff to identify that
                # unchanged checkout instead of treating line endings as late work.
                current = safe(root, path)
                original = current.read_bytes() if path not in dirty and current.is_file() else content
                result.setdefault(path, digest(original))
    return result


def behavior_plan(root, p, change):
    directory, _ = change_at(root, p, change)
    relative = p.get("behavior_plans", {}).get(change, (directory / "behavior-plan.json").relative_to(root).as_posix())
    path = safe(root, relative)
    plan = read_json(path, {"cases": []})
    if not isinstance(plan, dict) or not isinstance(plan.get("cases"), list):
        raise KitError("Behavior plan must contain a cases array")
    names = {item["name"] for item in p["checks"] if item.get("required", True)}
    seen = set()
    for case in plan["cases"]:
        if not isinstance(case, dict) or any(not isinstance(case.get(key), str) or not case[key].strip() for key in ("id", "effect", "source", "expected")):
            raise KitError("Every behavior case needs id, effect, source and expected outcome")
        if case["id"] in seen or case["effect"] not in {"preserve", "target"}:
            raise KitError("Behavior case IDs must be unique; effect is preserve or target")
        seen.add(case["id"])
        for key in ("checks", "before_checks"):
            values = case.get(key, [])
            if not isinstance(values, list) or any(name not in names for name in values):
                raise KitError("Behavior cases must reference configured required checks")
        if not case.get("checks"):
            raise KitError("Behavior cases need actual required verification checks")
        if case["effect"] == "preserve":
            if not isinstance(case.get("fixtures"), list) or not case["fixtures"]:
                raise KitError("Preserved behavior needs actual fixture/test source paths")
            for relative in case["fixtures"]:
                if not safe(root, relative).is_file():
                    raise KitError("Missing preserved behavior fixture: " + relative)
        if case.get("replaces"):
            if not case.get("before_checks") or not case.get("before_expected") or not safe(root, case.get("decision")).is_file():
                raise KitError("Intentional replacement needs before checks/outcome and an actual compatibility decision")
    return plan


def behavior_signature(root, p, change):
    plan = behavior_plan(root, p, change)
    before = {name for case in plan["cases"] for name in (case["checks"] if case["effect"] == "preserve" else case.get("before_checks", []))}
    fixtures = {relative: digest(safe(root, relative).read_bytes()) for case in plan["cases"] for relative in case.get("fixtures", [])}
    definitions = [item for item in p["checks"] if item["name"] in before]
    return {"plan": plan, "before_checks": sorted(before), "definitions": definitions, "fixtures": fixtures,
            "sha256": digest(dump({"plan": plan, "definitions": definitions, "fixtures": fixtures}).encode())}


def behavior_findings(root, p, change, phase):
    directory, metadata = change_at(root, p, change)
    if metadata["kind"] == "docs" or phase not in {"ready", "delivery"}:
        return []
    prior = established_behavior(root, p, metadata, change)
    signature = behavior_signature(root, p, change)
    findings = []
    if prior and not signature["before_checks"]:
        findings.append({"status": "PENDING", "code": "behavior-plan", "message": "Map retained behavior or deliberate replacements to real pre-change checks and fixture sources before implementation."})
    if phase == "ready":
        previous = read_json(directory / "baseline-anchor.json", {})
        if previous and previous.get("ready_fingerprint") != fingerprint(root, p, change):
            findings.append({"status": "PENDING", "code": "baseline-anchored", "message": "Original executed evidence is already anchored; preserve it and verify delivery instead of replacing it."})
        if prior and not safe(root, p["paths"]["baseline"] + "/coverage.json").is_file():
            findings.append({"status": "PENDING", "code": "baseline-static", "message": "Inventory and explain affected original behavior before recording characterization."})
        current = scoped_sources(root, p, metadata["scope"])
        late = [path for path, sha in prior.items() if current.get(path) != sha]
        if late:
            findings.append({"status": "PENDING", "code": "baseline-late", "message": f"Affected original inputs already differ: {late}. Run pre-change characterization on the original version; do not relabel modified code as a baseline."})
    elif prior or (directory / "baseline-anchor.json").is_file():
        anchor = read_json(directory / "baseline-anchor.json", {})
        snapshot = anchor.get("snapshot")
        raw = safe(root, snapshot) if snapshot else None
        record = read_json(raw, {}) if raw and raw.is_file() else {}
        valid = (anchor.get("scope") == metadata["scope"] and anchor.get("signature") == signature["sha256"]
                 and raw and raw.is_file() and digest(raw.read_bytes()) == anchor.get("snapshot_sha256")
                 and record.get("status") == "PASS" and record.get("source_files")
                 and set(record.get("source_files", {})).issuperset(prior)
                 and {item["name"] for item in record.get("checks", []) if item["status"] == "PASS"}.issuperset(signature["before_checks"]))
        if not valid:
            findings.append({"status": "PENDING", "code": "baseline-anchor", "message": "Fresh, executed pre-change characterization is missing or its plan/fixtures/checks changed. Preserve the original evidence and re-establish it on original inputs."})
    return findings


def behavior_results(root, p, change, checks):
    directory, _ = change_at(root, p, change)
    anchor = read_json(directory / "baseline-anchor.json", {})
    original = read_json(safe(root, anchor["snapshot"]), {}) if anchor.get("snapshot") else {}
    before = {item["name"]: item["status"] for item in original.get("checks", [])}
    current = {item["name"]: item["status"] for item in checks}
    return [{"id": case["id"], "effect": case["effect"], "source": case["source"], "expected": case["expected"],
             "before": {name: before.get(name, "NOT_RUN") for name in (case["checks"] if case["effect"] == "preserve" else case.get("before_checks", []))},
             "current": {name: current.get(name, "NOT_RUN") for name in case["checks"]}}
            for case in behavior_plan(root, p, change)["cases"]]


def change_findings(root, p, change, phase):
    directory, metadata = change_at(root, p, change)
    findings = []
    report_path = directory / "verify-report.md"
    if report_path.is_file():
        report_text = report_path.read_text(encoding="utf-8")
        if VERIFY_START in report_text or VERIFY_END in report_text:
            if report_text.count(VERIFY_START) != 1 or report_text.count(VERIFY_END) != 1 or report_text.index(VERIFY_END) < report_text.index(VERIFY_START):
                findings.append({"status": "FAIL", "code": "verification-block", "message": "Repair malformed verification markers; human report has been preserved."})
    names = ["proposal.md", "tasks.md"]
    if metadata.get("origin") != "files" or (directory / "design.md").exists() or metadata["kind"] == "refactor" or any(Path(scope).name in {"pom.xml", "package.json", "go.mod", "build.gradle", "Cargo.toml"} for scope in metadata["scope"]):
        names.append("design.md")
    for name in names:
        path = directory / name
        if not path.is_file():
            findings.append({"status": "FAIL", "code": "missing-artifact", "message": f"Missing {change}/{name}"})
        elif phase != "structure" and FILL in path.read_text(encoding="utf-8"):
            findings.append({"status": "PENDING", "code": "draft-artifact", "message": f"Fill {change}/{name} or explain why its sections do not apply."})
    deltas = list(directory.glob("specs/**/*.md"))
    if phase != "structure":
        findings += apply_format_exceptions(root, p, specification_findings(root, p, deltas))
        if metadata["kind"] in {"feature", "fix", "refactor"} and not metadata.get("requirements"):
            findings.append({"status": "PENDING", "code": "missing-requirements", "message": "Declare affected requirements in current/delta specifications before implementation."})
        for path in deltas:
            text = path.read_text(encoding="utf-8")
            needs_scenarios = any(item["section"] not in {"REMOVED", "RENAMED"} for item in spec_records(text, path.parent.name))
            if FILL in text or needs_scenarios and "#### Scenario:" not in text:
                findings.append({"status": "PENDING", "code": "delta-scenarios", "message": f"Fill observable scenarios in {path.relative_to(root)}"})
        if metadata["kind"] == "docs" and any(is_behavior(x, p) and not x.startswith("docs/") for x in metadata["scope"] if x != "."):
            findings.append({"status": "FAIL", "code": "task-classification", "message": "A docs change cannot declare source/configuration file scope."})
    if phase == "ready" and metadata["kind"] != "docs":
        findings += baseline_findings(root, p, list(established_behavior(root, p, metadata, change))) if established_behavior(root, p, metadata, change) else []
    findings += behavior_findings(root, p, change, phase)
    if phase == "delivery":
        findings += delivery_knowledge_findings(root, p, metadata["scope"])
        tasks = directory / "tasks.md"
        if tasks.is_file() and re.search(r"^\s*- \[ \]", tasks.read_text(encoding="utf-8"), re.MULTILINE):
            findings.append({"status": "PENDING", "code": "unfinished-tasks", "message": "Change tasks still contain unchecked items."})
        records = [item for path in deltas for item in spec_records(path.read_text(encoding="utf-8"), path.parent.name)]
        declared = current_requirement_ids(root, p) | {item["id"] for item in records}
        for requirement in metadata.get("requirements", []):
            if requirement not in declared:
                findings.append({"status": "FAIL", "code": "requirement-spec", "message": f"{requirement} has no specification reference."})
        findings += requirement_test_findings(root, p, records)
        if deltas and metadata.get("origin") == "files" and directory.parent.name == "archive":
            current_blocks = {re.sub(r"\s+", " ", block).strip() for path in safe(root, p["paths"]["specs"]).glob("**/*.md")
                              for block in requirement_blocks(path.read_text(encoding="utf-8"))}
            for path in deltas:
                section = ""
                for part in re.split(r"(?m)(?=^## )", path.read_text(encoding="utf-8")):
                    if part.startswith("## "):
                        section = part.splitlines()[0]
                    if section in {"## ADDED Requirements", "## MODIFIED Requirements"}:
                        for block in requirement_blocks(part):
                            if re.sub(r"\s+", " ", block).strip() not in current_blocks:
                                findings.append({"status": "PENDING", "code": "spec-sync", "message": f"Synchronize and review current specifications using the selected workflow: {path.relative_to(root)}"})
            current_labels = {(path.parent.name, item["label"]) for path in safe(root, p["paths"]["specs"]).glob("**/*.md") for item in spec_records(path.read_text(encoding="utf-8"), path.parent.name)}
            for path in deltas:
                for old, new in rename_pairs(path.read_text(encoding="utf-8")):
                    if (path.parent.name, new) not in current_labels or old != new and (path.parent.name, old) in current_labels:
                        findings.append({"status": "PENDING", "code": "spec-sync", "message": f"Native rename not reflected in current specifications: {old} -> {new}"})
            for requirement in metadata.get("removed_requirements", []):
                if requirement in current_requirement_ids(root, p):
                    findings.append({"status": "PENDING", "code": "spec-sync", "message": f"Retired requirement remains current: {requirement}"})
        elif deltas and metadata.get("origin") != "files":
            sync = read_json(directory / "spec-sync.json", {})
            actual_deltas = {path.relative_to(directory).as_posix(): digest(path.read_bytes()) for path in deltas}
            actual_specs = spec_hashes(root, p)
            if sync.get("deltas") != actual_deltas or sync.get("specs") != actual_specs or not artifact_valid(root, sync):
                findings.append({"status": "PENDING", "code": "spec-sync", "message": "Synchronize deltas using the native OpenSpec workflow, review the result, and record-sync before delivery verification."})
    return findings


def markdown_structure(text):
    """Mask fenced examples without moving source locations."""
    lines, fence = [], None
    for line in text.splitlines(keepends=True):
        match = re.match(r"^\s*(\x60{3,}|~{3,})", line)
        if match:
            marker = match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            lines.append("".join("\n" if char == "\n" else " " for char in line))
        elif fence:
            lines.append("".join("\n" if char == "\n" else " " for char in line))
        else:
            lines.append(line)
    return "".join(lines)


def requirement_blocks(text):
    return [text[m.start():m.end()] for m in re.finditer(r"(?ms)^### Requirement:.*?(?=^### Requirement:|^## |\Z)", markdown_structure(text))]


def requirement_identity(label, capability):
    identifier = DECLARED_ID.search(label) or REQ.search(label)
    return identifier.group() if identifier else capability + "::" + label.strip()


def rename_pairs(text):
    result = []
    for section in re.split(r"(?m)^## ", markdown_structure(text)):
        if not section.startswith("RENAMED Requirements"):
            continue
        pending = None
        for match in re.finditer(r"(?m)^\s*-?\s*(FROM|TO):\s*(.+)$", section):
            label = match.group(2).strip().strip("\x60").removeprefix("### Requirement:").strip()
            if match.group(1) == "FROM":
                pending = label
            elif pending:
                result.append((pending, label))
                pending = None
    return result


def spec_records(text, capability):
    masked = markdown_structure(text)
    result = []
    for match in re.finditer(r"(?ms)^### Requirement:[ \t]*([^\n]+).*?(?=^### Requirement:|^## |\Z)", masked):
        previous = list(re.finditer(r"(?m)^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements\s*$", masked[:match.start()]))
        section = previous[-1].group(1) if previous else "CURRENT"
        label = match.group(1).strip()
        result.append({"id": requirement_identity(label, capability), "label": label,
                       "body": masked[match.start():match.end()], "raw": text[match.start():match.end()],
                       "section": section, "line": text.count("\n", 0, match.start()) + 1})
    for _, label in rename_pairs(text):
        result.append({"id": requirement_identity(label, capability), "label": label, "body": "", "raw": "", "section": "RENAMED", "line": 1})
    return result


def current_requirement_ids(root, p):
    return {item["id"] for path in safe(root, p["paths"]["specs"]).glob("**/*.md")
            for item in spec_records(path.read_text(encoding="utf-8"), path.parent.name)}


def spec_hashes(root, p):
    return {path.relative_to(root).as_posix(): digest(safe(root, path.relative_to(root).as_posix()).read_bytes()) for path in sorted(safe(root, p["paths"]["specs"]).glob("**/*.md"))}


def artifact_valid(root, record):
    if not record.get("artifact") or not record.get("artifact_sha256") or not record.get("reviewer"):
        return False
    path = safe(root, record["artifact"])
    return path.is_file() and digest(path.read_bytes()) == record["artifact_sha256"]


def record_sync(root, p, change, artifact, reviewer, method="reviewed"):
    directory, metadata = change_at(root, p, change)
    path = safe(root, artifact)
    if not path.is_file() or not path.read_bytes().strip() or FILL in path.read_text(encoding="utf-8"):
        raise KitError("Provide a filled review artifact documenting actual OpenSpec synchronization and its method.")
    current = "\n".join(safe(root, relative).read_text(encoding="utf-8") for relative in spec_hashes(root, p))
    current_ids = set(REQ.findall(current))
    missing = [x for x in metadata["requirements"] if x not in metadata.get("removed_requirements", []) and x not in current_ids]
    if missing:
        raise KitError(f"Requirements are missing from current specifications: {missing}")
    unexpected = [x for x in metadata.get("removed_requirements", []) if x in current_ids]
    if unexpected:
        raise KitError(f"Removed requirements are still in current specifications: {unexpected}")
    data = {"method": method, "reviewer": reviewer, "recorded_at": now(), "artifact": artifact, "artifact_sha256": digest(path.read_bytes()), "deltas": {f.relative_to(directory).as_posix(): digest(f.read_bytes()) for f in directory.glob("specs/**/*.md")}, "specs": spec_hashes(root, p), "meaning": "Reviewed synchronization declaration; hashes check freshness, not semantic equivalence. Reviewed file synchronization does not assert execution of the native CLI."}
    atomic(directory / "spec-sync.json", dump(data))
    return {"status": "PASS", "change": change, "record": str((directory / "spec-sync.json").relative_to(root))}


def run_check(root, check, run_dir):
    result = {"name": check["name"], "type": check.get("type", "command"), "required": check.get("required", True), "started_at": now()}
    argv = [sys.executable if part == "{python}" else part for part in check["argv"]]
    cwd = root if check.get("cwd", ".") == "." else safe(root, check["cwd"])
    result.update(argv=argv, cwd=str(cwd))
    log = run_dir / (check["name"] + ".log")
    started = time.monotonic()
    try:
        with log.open("wb") as stream:
            completed = subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=check.get("timeout", 300), check=False, env={**os.environ, "ARK_VERIFY_ACTIVE": "1", "PYTHONPYCACHEPREFIX": str(run_dir / "bytecode")})
        result.update(status="PASS" if completed.returncode == 0 else "FAIL", exit_code=completed.returncode)
    except FileNotFoundError as exc:
        result.update(status="NOT_RUN", reason=str(exc))
    except subprocess.TimeoutExpired:
        result.update(status="FAIL", reason="timeout")
    except OSError as exc:
        result.update(status="NOT_RUN", reason=str(exc))
    result.update(duration_seconds=round(time.monotonic() - started, 3), finished_at=now(), log=log.relative_to(root).as_posix())
    return result


def overall(findings, checks):
    statuses = [x["status"] for x in findings] + [x["status"] for x in checks if x.get("required", True)]
    if "FAIL" in statuses:
        return "FAIL"
    if any(s in {"PENDING", "NOT_RUN"} for s in statuses):
        return "PENDING"
    return "PASS"


def verify(root, p, phase="structure", change=None, base=None, selected=None, peer_scopes=None):
    findings = structure_findings(root, p)
    metadata = None
    if change:
        _, metadata = change_at(root, p, change)
        findings += change_findings(root, p, change, phase)
        if base:
            outside = [x for x in changed_files(root, base) if is_behavior(x, p) and not excluded(x, p) and not any(under(x, scope) for scope in metadata["scope"] + (peer_scopes or []))]
            if outside:
                findings.append({"status": "FAIL", "code": "scope", "message": f"Behavior/config changes outside declared scope: {outside}"})
    elif phase != "structure":
        raise KitError("A ready/delivery verification needs --change ID")
    start_fingerprint = fingerprint(root, p, change)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    run_dir = safe(root, ".ai/runtime/runs/" + run_id)
    run_dir.mkdir(parents=True)
    checks = []
    if phase in {"ready", "delivery"}:
        if os.environ.get("ARK_VERIFY_ACTIVE"):
            raise KitError("Recursive verification detected; a check cannot run its own delivery verifier.")
        if selected and set(selected) - {x["name"] for x in p["checks"]}:
            raise KitError("Unknown --check selection")
        external = read_json(change_at(root, p, change)[0] / "evidence.json", {"checks": {}})
        before_names = set(behavior_signature(root, p, change)["before_checks"]) if phase == "ready" else None
        for check in p["checks"]:
            if phase not in check.get("phases", ["ready", "delivery"]):
                continue
            if before_names is not None and check["name"] not in before_names:
                continue
            if selected and check["name"] not in selected:
                checks.append({"name": check["name"], "required": check.get("required", True), "status": "NOT_RUN", "reason": "Not selected; partial execution cannot satisfy required delivery checks."})
            elif check.get("type", "command") == "command":
                checks.append(run_check(root, check, run_dir))
            else:
                evidence = external.get("checks", {}).get(check["name"], {})
                valid = evidence.get("fingerprint") == start_fingerprint and artifact_valid(root, evidence)
                checks.append({"name": check["name"], "type": check["type"], "required": check.get("required", True), "status": evidence.get("status", "NOT_RUN") if valid else "NOT_RUN", "reason": evidence.get("summary", "No current external/manual evidence")})
        if phase == "delivery" and not any(x.get("required", True) for x in checks) and metadata["kind"] != "docs":
            checks.append({"name": "behavioral-verification", "required": True, "status": "NOT_RUN", "reason": "Confirm real project checks in policy.checks; command candidates are not executed automatically."})
    if phase in {"ready", "delivery"}:
        required_names = (set(behavior_signature(root, p, change)["before_checks"]) if phase == "ready"
                          else {name for case in behavior_plan(root, p, change)["cases"] for name in case["checks"]})
        for name in sorted(required_names - {item["name"] for item in checks}):
            checks.append({"name": name, "required": True, "status": "NOT_RUN", "reason": "The behavior plan requires this check at this phase; check.phases excluded it."})
    if fingerprint(root, p, change) != start_fingerprint:
        findings.append({"status": "FAIL", "code": "inputs-changed", "message": "Verification inputs changed while checks were running; inspect generated files and rerun."})
    report = {"schema_version": 1, "run_id": run_id, "phase": phase, "change": change, "created_at": now(), "kit_version": VERSION, "python": sys.version.split()[0], "platform": sys.platform, "source_ref": (git(root, "rev-parse", "HEAD", optional=True) or b"").decode().strip() or None, "fingerprint": start_fingerprint, "base": base, "findings": findings, "checks": checks, "status": overall(findings, checks)}
    if change and metadata.get("origin") == "files":
        report["specification_state"] = "current-after-archive" if change_at(root, p, change)[0].parent.name == "archive" else "proposed; native tool owns synchronization and archive"
    if change:
        report["behavior"] = behavior_results(root, p, change, checks)
    atomic(run_dir / "result.json", dump(report))
    if change:
        directory, change_metadata = change_at(root, p, change)
        if phase == "ready" and report["status"] == "PASS" and change_metadata["kind"] != "docs":
            signature = behavior_signature(root, p, change)
            if signature["before_checks"]:
                anchor_path = directory / "baseline-anchor.json"
                previous = read_json(anchor_path, {})
                if previous and previous.get("ready_fingerprint") != start_fingerprint:
                    raise KitError("A different pre-change baseline is already anchored; preserve history and characterize the original version.")
                if not previous:
                    coverage = read_json(safe(root, p["paths"]["baseline"] + "/coverage.json"), {"files": {}})
                    record = {"status": report["status"], "source_ref": report["source_ref"], "source_files": scoped_sources(root, p, change_metadata["scope"]),
                              "fingerprint": start_fingerprint, "signature": signature, "checks": checks, "python": report["python"], "platform": report["platform"],
                              "logs": {item["name"]: safe(root, item["log"]).read_text(encoding="utf-8", errors="replace") for item in checks if item.get("log")}}
                    snapshot = evidence_root(p) + "/behavior/" + digest(dump(record).encode()) + ".json"
                    transact(root, {snapshot: dump(record), anchor_path.relative_to(root).as_posix(): dump({"scope": change_metadata["scope"], "source_ref": report["source_ref"],
                        "ready_fingerprint": start_fingerprint, "signature": signature["sha256"], "snapshot": snapshot, "snapshot_sha256": digest(dump(record).encode()),
                        "run_id": run_id, "reviewed_files": {path: item for path, item in coverage["files"].items() if path in record["source_files"]}})})
        if phase == "delivery" and report["status"] == "PASS" and change_metadata["kind"] != "docs":
            established_path = safe(root, ".ai/established.json")
            established = read_json(established_path, {"files": {}})
            original = established_behavior(root, p, change_metadata, change)
            for relative, sha in scoped_sources(root, p, change_metadata["scope"]).items():
                previous = established["files"].get(relative, {})
                prior = previous.get("previous") if previous.get("change") == change else ({"sha256": original[relative]} if relative in original else None)
                established["files"][relative] = {"sha256": sha, "change": change, "previous": prior}
            atomic(established_path, dump(established))
        atomic(directory / "verification.json", dump(report))
        lines = [f"# Verification: {change}", "", f"Conclusion: {report['status']}", f"Phase: {phase}", f"Fingerprint: {start_fingerprint}", f"Run: {run_id}", "", "## Findings", ""]
        lines += [f"- {x['status']}: {x['message']}" for x in findings] or ["- No structural findings. This does not establish semantic completeness."]
        lines += ["", "## Checks", ""] + [f"- {x['name']}: {x['status']} — {x.get('reason', x.get('log', ''))}" for x in checks]
        lines += ["", "## Evidence", "", f"Runtime evidence: `.ai/runtime/runs/{run_id}/result.json`. Verify the candidate locally; optional CI can independently run the same checks.", ""]
        report_path = directory / "verify-report.md"
        existing = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
        atomic(report_path, verification_document(existing, "\n".join(lines)))
    return report


def record_evidence(root, p, change, check, artifact, reviewer, status, summary):
    directory, _ = change_at(root, p, change)
    definition = next((x for x in p["checks"] if x["name"] == check and x.get("type") in {"manual", "external"}), None)
    if not definition:
        raise KitError("Evidence must name a configured manual/external check")
    path = safe(root, artifact)
    if not path.is_file() or not path.read_bytes().strip():
        raise KitError("A nonempty existing evidence artifact is required")
    data = read_json(directory / "evidence.json", {"schema_version": 1, "checks": {}})
    data["checks"][check] = {"status": status, "summary": summary, "reviewer": reviewer, "artifact": artifact, "artifact_sha256": digest(path.read_bytes()), "fingerprint": fingerprint(root, p, change), "recorded_at": now()}
    atomic(directory / "evidence.json", dump(data))
    return {"status": "PASS", "meaning": "Evidence declaration recorded, not independently certified", "check": check}


def close_change(root, p, change):
    directory, metadata = change_at(root, p, change)
    result = read_json(directory / "verification.json", {})
    # The ignored local run is required: a committed PASS JSON alone is not enough.
    run_id = result.get("run_id", "")
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}-[a-f0-9]{8}", run_id):
        raise KitError("Run a fresh delivery verification in this workspace before closing")
    runtime = read_json(safe(root, f".ai/runtime/runs/{run_id}/result.json"), {})
    if result != runtime or result.get("phase") != "delivery" or result.get("status") != "PASS" or result.get("fingerprint") != fingerprint(root, p, change):
        raise KitError("Fresh PASS delivery evidence is required; stale/partial/committed reports cannot close a change")
    findings = [item for item in structure_findings(root, p) + change_findings(root, p, change, "delivery") if item["status"] in {"FAIL", "PENDING", "NOT_RUN"}]
    if findings:
        raise KitError("Change completion conditions no longer hold: " + findings[0]["message"])
    archive = safe(root, p["paths"]["changes"] + "/archive/" + datetime.now(timezone.utc).strftime("%Y-%m-%d-") + change)
    if archive.exists():
        raise KitError("Archive destination already exists")
    if directory.parent.name == "archive":
        raise KitError("Change is already archived")
    metadata["state"] = "complete"
    metadata["completed_at"] = now()
    old_prefix = directory.relative_to(root).as_posix()
    new_prefix = archive.relative_to(root).as_posix()
    writes = {old_prefix + "/ark.json": dump(metadata)}
    for name in ("spec-sync.json", "evidence.json"):
        path = directory / name
        if not path.is_file():
            continue
        record = read_json(path)
        items = record.get("checks", {}).values() if name == "evidence.json" else [record]
        for item in items:
            artifact = item.get("artifact", "")
            if under(artifact, old_prefix):
                item["artifact"] = new_prefix + artifact[len(old_prefix):]
        writes[old_prefix + "/" + name] = dump(record)
    before = {relative: safe(root, relative).read_bytes() for relative in writes}
    transact(root, writes)
    archive.parent.mkdir(parents=True, exist_ok=True)
    try:
        directory.rename(archive)
    except OSError:
        transact(root, before)
        raise
    branch = (git(root, "symbolic-ref", "--short", "HEAD", optional=True) or b"detached").decode().strip()
    for pointer in safe(root, ".ai/runtime/contexts").glob("*.json"):
        item = read_json(pointer)
        if item.get("change") == change and item.get("branch", branch) == branch:
            pointer.unlink()
    return {"status": "PASS", "change": change, "state": "archived", "path": archive.relative_to(root).as_posix()}


def checkpoint(root, p, change, summary, next_step, blocked=False, paused=False):
    directory, metadata = change_at(root, p, change)
    state = "blocked" if blocked else "paused" if paused else "implementing"
    writes = {(directory / "checkpoint.md").relative_to(root).as_posix(): f"# Checkpoint: {change}\n\nStatus: {state}\nUpdated: {now()}\n\n## Completed / current state\n\n{summary}\n\n## Next step\n\n{next_step}\n"}
    if metadata.get("origin") != "files":
        metadata.update(state=state, updated_at=now())
        writes[(directory / "ark.json").relative_to(root).as_posix()] = dump(metadata)
    transact(root, writes)
    return {"status": "PENDING", "change": change, "state": state}


def doctor(root, p):
    findings = structure_findings(root, p)
    adapters = []
    for agent in p.get("agents", []):
        executable = shutil.which("claude" if agent == "claude" else agent)
        configured = False
        if agent in {"codex", "claude"}:
            config_path = ".codex/hooks.json" if agent == "codex" else ".claude/settings.json"
            settings = read_json(safe(root, config_path), {})
            hooks_map = settings.get("hooks", {})
            configured = all(any(is_kit_hook(h.get("command"), action, agent) for entry in hooks_map.get(event, []) for h in entry.get("hooks", [])) for event, action in (("SessionStart", "session"), ("Stop", "stop")))
        skill_delivery = p.get("skill_delivery", "repository")
        skill_files = all(safe(root, AGENT_DIRS[agent] + "/" + skill + "/SKILL.md").is_file() for skill in SKILLS) if skill_delivery == "repository" else None
        adapters.append({"agent": agent, "executable": executable, "skill_delivery": skill_delivery, "skill_files": skill_files, "live_loading": "NOT_VERIFIED", "hook_trust": "NOT_VERIFIED", "hooks": ("CONFIGURATION_ONLY" if configured else "NOT_CONFIGURED") if agent in {"codex", "claude"} else "NOT_IMPLEMENTED"})
    return {"status": overall(findings, []), "kit_version": VERSION, "mode": p["mode"], "python": sys.version.split()[0], "git": shutil.which("git"), "ark_on_path": shutil.which("ark"), "findings": findings, "adapters": adapters, "branch_protection": "NOT_VERIFIED", "checks_configured": len(p["checks"]), "unconfirmed_command_candidates": [x for x in p.get("command_candidates", []) if not x.get("confirmed", False)], "baseline_findings": baseline_findings(root, p)}


def work_selection(root, p, changed=None, behavior=None):
    changed = changed_files(root) if changed is None else changed
    behavior = [path for path in changed if is_behavior(path, p) and not excluded(path, p)] if behavior is None else behavior
    candidates, catalog = [], []
    associations = p.get("change_associations", {})
    def owner(path):
        prefixes = [prefix for prefix in associations if under(path, prefix)]
        return associations[max(prefixes, key=len)] if prefixes else None
    for directory in change_directories(root, p, archived=True):
        metadata = read_json(directory / "ark.json") if (directory / "ark.json").is_file() else file_change_metadata(root, p, directory)
        relative = directory.relative_to(root).as_posix()
        if directory.parent.name != "archive":
            catalog.append(metadata["id"])
        elif not any(under(path, relative) for path in changed):
            continue
        matched = [path for path in behavior if any(under(path, scope) for scope in metadata["scope"]) and owner(path) in {None, metadata["id"]}]
        if matched or any(under(path, relative) for path in changed):
            candidates.append({"id": metadata["id"], "path": relative, "files": matched, "scope": metadata["scope"], "scope_source": metadata.get("scope_source", "declared")})
    overlaps = {path: [item["id"] for item in candidates if path in item["files"]] for path in behavior}
    overlaps = {path: names for path, names in overlaps.items() if len(names) > 1}
    return {"candidates": candidates, "catalog": catalog, "overlaps": overlaps,
            "ambiguous": bool(overlaps), "changed_files": changed, "behavior_files": behavior}


def knowledge_navigation(root, p, changed):
    index = read_json(safe(root, p["paths"]["baseline"] + "/knowledge.json"), {"documents": {}})
    return [document for document, item in index["documents"].items()
            if item.get("state") != "obsolete" and (document in changed or any(path in changed for path in item.get("sources", {})))]


def context(root, p, session="default"):
    selection = work_selection(root, p)
    declared = active(root, session)
    change = None
    if not selection["ambiguous"]:
        candidates = [item for item in selection["candidates"] if "/archive/" not in item["path"]]
        if len(candidates) == 1:
            change = candidates[0]["id"]
        elif declared:
            try:
                directory, metadata = change_at(root, p, declared)
                if directory.parent.name != "archive" and metadata.get("state") != "complete" and not candidates:
                    change = declared
            except KitError:
                pass
    resume = None
    if change:
        directory, _ = change_at(root, p, change)
        resume = (directory / "checkpoint.md").relative_to(root).as_posix()
    return {"project": str(root), "mode": p["mode"], "active_change": change, "declared_change": declared,
            "selection": selection, "affected_knowledge": knowledge_navigation(root, p, selection["changed_files"]),
            "routing": {"facts": p["paths"]["baseline"], "behavior": p["paths"]["specs"], "decisions": p["paths"]["adr"], "work": p["paths"]["changes"]},
            "workflow": "Use OpenSpec, another development tool or direct conversation. Read relevant rules/evidence; run local checks before claiming delivery. No daily toolkit Skill or activation is required.",
            "resume": f"Read {resume} and actual diff." if resume else "Inspect candidate work and actual diff; overlapping scope stays ambiguous. No task is guessed from modification time.",
            "last_check": ".ai/runtime/last-check.json", "meaning": "Navigation and diff-based association; no tests, whole-repository inventory or semantic certification on startup"}


def impact(root, p, base=None):
    selection = work_selection(root, p, changed_files(root, base))
    affected = set(knowledge_navigation(root, p, selection["changed_files"]))
    documents = [item for item in knowledge_status(root, p)["documents"] if item["document"] in affected]
    result = {"status": "PENDING" if selection["ambiguous"] or any(item["freshness"] == "stale" for item in documents) else "PASS",
              "base": base, "selection": selection, "knowledge": documents, "created_at": now(),
              "meaning": "Path/hash impact candidates require semantic review; no automatic business conclusion"}
    atomic(safe(root, ".ai/runtime/last-impact.json"), dump(result))
    return result


def local_check(root, p, base=None, local=True):
    findings = structure_findings(root, p)
    result = {"status": overall(findings, []), "findings": findings} if any(item["status"] in {"FAIL", "PENDING", "NOT_RUN"} for item in findings) else ci_verify(root, p, base, local=local)
    result.setdefault("findings", findings)
    result.update(created_at=now(), execution="local" if local else "ci", base=base)
    result["business_checks_executed"] = bool(result.get("executed_check_count", 0))
    changed = changed_files(root, base)
    result["knowledge_review_candidates"] = knowledge_navigation(root, p, changed)
    result["stage"] = "candidate-delivery" if result.get("behavior_files") or result.get("lightweight_files") else "structure-or-documents"
    atomic(safe(root, ".ai/runtime/last-check.json"), dump(result))
    return result


def install_git_hook(root, p):
    """Opt-in local enforcement; custom hooks are never replaced or appended blindly."""
    location = git(root, "rev-parse", "--git-path", "hooks/pre-commit").decode().strip()
    path = Path(location)
    path = path if path.is_absolute() else root / path
    common = Path(git(root, "rev-parse", "--git-common-dir").decode().strip())
    common = common if common.is_absolute() else root / common
    if not (path.resolve().is_relative_to(root.resolve()) or path.resolve().is_relative_to(common.resolve())):
        raise KitError("A shared/global hooksPath is outside this repository; use its existing hook manager")
    if path.is_symlink() or path.parent.is_symlink():
        raise KitError("Refusing a symlinked Git hook path")
    command = shlex.quote(Path(sys.executable).as_posix())
    content = '#!/bin/sh\n# agent-repo-kit local check\nroot=$(git rev-parse --show-toplevel) || exit 1\nexec ' + command + ' "$root/hack/ai/ark.py" --repo "$root" check\n'
    if path.exists() and path.read_text(encoding="utf-8") != content:
        return {"status": "PENDING", "path": str(path), "message": "Existing custom hook preserved. Add the local check to its reachable execution path using the existing project hook manager."}
    atomic(path, content)
    path.chmod(path.stat().st_mode | 0o111)
    return {"status": "PASS", "path": str(path), "meaning": "Local pre-commit check installed; remote hosting and CI are unnecessary. Git hooks can be bypassed and are not server protection."}


def ci_verify(root, p, base, local=False):
    """Re-execute candidate changes; never trust committed verification reports."""
    if (not base or set(base) == {"0"}) and not local:
        raise KitError("CI requires a real comparison base; configure the main-branch base for an initial push.")
    changed = changed_files(root, base)
    if local and git(root, "rev-parse", "--is-inside-work-tree", optional=True) is None:
        changed = sorted(inventory_files(root, p))
    immutable = []
    for relative in changed:
        comparison = (git(root, "merge-base", base, "HEAD").decode().strip() if base else "HEAD")
        old = git(root, "show", f"{comparison}:{relative}", optional=True)
        if old is None:
            continue
        path = safe(root, relative)
        new = path.read_bytes() if path.is_file() else b""
        if under(relative, p["paths"]["changes"] + "/archive") and old != new:
            immutable.append({"status": "FAIL", "code": "archive-history", "message": f"Archived history changed; add a supplemental change: {relative}"})
        if (under(relative, p["paths"]["baseline"] + "/raw") or under(relative, evidence_root(p))) and old != new:
            immutable.append({"status": "FAIL", "code": "raw-history", "message": f"Historical raw evidence changed: {relative}"})
        old_text = old.decode("utf-8", errors="strict") if under(relative, p["paths"]["adr"]) else ""
        new_text = new.decode("utf-8", errors="strict") if old_text else ""
        previous_status = adr_status(old_text)
        if previous_status and previous_status[0] == "Accepted":
            current_status = adr_status(new_text)
            if not current_status or not re.match(r"^(Accepted|Superseded\b.*)$", current_status[0]):
                immutable.append({"status": "FAIL", "code": "accepted-adr-status", "message": f"Accepted decision can only remain Accepted or name a superseding decision: {relative}"})
            if adr_body(old_text) != adr_body(new_text):
                immutable.append({"status": "FAIL", "code": "accepted-adr", "message": f"Accepted ADR body changed; preserve it and add a superseding decision: {relative}"})
    manifest = read_json(safe(root, MANIFEST))
    owned = set(manifest.get("files", {}))
    behavior = [x for x in changed if is_behavior(x, p) and not excluded(x, p) and x not in owned]
    lightweight = set()
    for path in safe(root, ".ai/notes").glob("*.json"):
        if path.relative_to(root).as_posix() not in changed:
            continue
        note = read_json(path)
        if not note.get("reason") or not note.get("reviewer") or note.get("kind") not in {"docs", "mechanical", "test-only"}:
            continue
        for relative, expected in note.get("files", {}).items():
            target = safe(root, relative)
            actual = digest(target.read_bytes()) if target.is_file() else None
            if actual == expected:
                lightweight.add(relative)
    behavior = [relative for relative in behavior if relative not in lightweight]
    selection = work_selection(root, p, changed, behavior)
    candidates = [item["id"] for item in selection["candidates"]]
    uncovered = [path for path in behavior if not any(path in item["files"] for item in selection["candidates"])]
    results = list(immutable) + delivery_knowledge_findings(root, p, changed)
    if selection["ambiguous"]:
        return {"status": "PENDING", "code": "ambiguous-change", "message": "Overlapping work scopes match the same real diff; clarify associations without guessing.", "candidates": candidates, "overlaps": selection["overlaps"], "behavior_files": behavior, "executed_check_count": 0}
    executed_count = 0
    if uncovered:
        results.append({"status": "FAIL", "code": "untracked-behavior-change", "message": f"Behavior/configuration changes need a scoped active or newly archived change: {uncovered}"})
    for change in candidates:
        affects_behavior = bool(next(item for item in selection["candidates"] if item["id"] == change)["files"])
        if affects_behavior and change_at(root, p, change)[1]["kind"] == "docs":
            results.append({"status": "FAIL", "code": "classification", "message": f"{change} is marked docs but intersects behavior/configuration changes."})
        else:
            peers = [scope for item in selection["candidates"] if item["id"] != change for scope in item["scope"]]
            report = verify(root, p, "delivery" if affects_behavior else "specification", change, base, peer_scopes=peers)
            executed_count += sum(item["status"] in {"PASS", "FAIL"} and "argv" in item for item in report["checks"])
            results.append({"status": report["status"], "change": change, "phase": report["phase"], "run_id": report["run_id"], "checks": report["checks"]})
    light_checks = []
    if lightweight:
        run_dir = safe(root, ".ai/runtime/runs/light-" + uuid.uuid4().hex[:12])
        run_dir.mkdir(parents=True)
        for check in p["checks"]:
            if "delivery" not in check.get("phases", ["ready", "delivery"]):
                continue
            if check.get("type", "command") == "command":
                light_checks.append(run_check(root, check, run_dir))
            elif check.get("required", True):
                light_checks.append({"name": check["name"], "required": True, "status": "NOT_RUN", "reason": "Required outside verification needs a scoped change/evidence record."})
        atomic(run_dir / "result.json", dump({"checks": light_checks, "status": overall([], light_checks)}))
    return {"status": overall(results, light_checks), "execution": "local" if local else "ci", "base": base, "executed_check_count": executed_count + sum(item["status"] in {"PASS", "FAIL"} for item in light_checks), "behavior_files": behavior, "lightweight_files": sorted(lightweight), "lightweight_checks": light_checks, "changes": results, "control_review": "Review lightweight declarations and policy/runtime/CI/manifest changes independently; repository-controlled checks are not a security boundary."}


def note_change(root, p, scope, kind, reason, reviewer, base=None):
    for relative in scope:
        if relative != ".":
            safe(root, relative)
    candidates = changed_files(root, base)
    if git(root, "rev-parse", "--is-inside-work-tree", optional=True) is None:
        candidates = list(inventory_files(root, p))
    files = {}
    for relative in candidates:
        if any(under(relative, prefix) for prefix in scope) and not excluded(relative, p):
            path = safe(root, relative)
            files[relative] = digest(path.read_bytes()) if path.is_file() else None
    if not files or not reason.strip() or not reviewer.strip():
        raise KitError("A lightweight note needs changed in-scope files, an actual nonbehavior rationale, and a reviewer identity")
    identifier = uuid.uuid4().hex[:12]
    relative = ".ai/notes/" + identifier + ".json"
    atomic(safe(root, relative), dump({"schema_version": 1, "kind": kind, "reason": reason, "reviewer": reviewer, "created_at": now(), "files": files, "meaning": "Reviewed nonbehavior declaration, not automatic semantic classification. CI reruns configured project checks."}))
    return {"status": "PASS", "meaning": "Lightweight declaration recorded; verification is separate", "note": relative, "files": sorted(files)}


def hook(root, p, action, agent, payload):
    session = str(payload.get("session_id", "default"))
    if action == "session":
        # No scanning, model call, business tests, or mutation on session startup.
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": dump(context(root, p, session))}}
    if payload.get("stop_hook_active"):
        return {}
    declared = active(root, session)
    navigation = context(root, p, session)
    change = navigation["active_change"]
    if navigation["selection"]["ambiguous"]:
        return {"systemMessage": "Several work items overlap the actual diff. Keep a pending handoff and clarify association; no automatic selection or forced continuation."}
    if not change:
        return {"systemMessage": "Behavior differences need scoped work and local verification before declaring delivery. Save a checkpoint when pausing."} if navigation["selection"]["behavior_files"] else {}
    try:
        directory, metadata = change_at(root, p, change)
    except KitError:
        return {}
    checkpoint_path = directory / "checkpoint.md"
    state_text = checkpoint_path.read_text(encoding="utf-8") if checkpoint_path.is_file() else ""
    if metadata.get("state") in {"blocked", "paused"} or re.search(r"(?m)^Status:\s*(blocked|paused)\s*$", state_text):
        return {}
    verification = read_json(directory / "verification.json", {})
    fresh = verification.get("phase") == "delivery" and verification.get("status") == "PASS" and verification.get("fingerprint") == fingerprint(root, p, change)
    if fresh:
        return {}
    reason = f"Change {change} has no fresh PASS delivery verification. Run repository checks using the selected development workflow or save a blocked/pending checkpoint; do not declare the whole change complete."
    if p.get("hook_mode") != "enforce" or not declared:
        return {"systemMessage": reason}
    # At most one continuation for a session+turn, even if the model changes files.
    token = digest((session + "\0" + str(payload.get("turn_id", "turn"))).encode())[:24]
    marker = safe(root, ".ai/runtime/hook-stops/" + token + ".json")
    if marker.exists():
        return {"systemMessage": reason + " Automatic continuation already used; leaving a recoverable pending task."}
    atomic(marker, dump({"change": change, "created_at": now(), "fingerprint": fingerprint(root, p, change)}))
    return {"decision": "block", "reason": reason}


def replay_compare(root, before, after, ignored=None, reason=None):
    """Compare recorded JSON results; normalization is explicit and never edits inputs."""
    left, right = read_json(safe(root, before)), read_json(safe(root, after))
    raw_equal = left == right
    ignored = ignored or []
    if ignored and (not isinstance(reason, str) or not reason.strip()):
        raise KitError("Normalization requires a concrete nonbusiness-field reason")
    for pointer in ignored:
        parts = pointer.split("/")[1:] if pointer.startswith("/") else []
        if len(parts) < 2 or any(part in {"", "id", "input"} for part in parts):
            raise KitError("Normalize specific output leaf fields using JSON pointers; never IDs, inputs or the whole result")
        for value in (left, right):
            parent = value
            try:
                for encoded in parts[:-1]:
                    part = encoded.replace("~1", "/").replace("~0", "~")
                    parent = parent[int(part)] if isinstance(parent, list) else parent[part]
                key = parts[-1].replace("~1", "/").replace("~0", "~")
                item = parent[int(key)] if isinstance(parent, list) else parent[key]
                if isinstance(item, (list, dict)):
                    raise KitError("Normalization cannot remove a container")
                if isinstance(parent, list):
                    parent[int(key)] = "<explicitly-normalized>"
                else:
                    parent[key] = "<explicitly-normalized>"
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise KitError("Normalization pointer must exist in both results: " + pointer) from exc
    return {"status": "PASS" if left == right else "FAIL", "raw_equal": raw_equal, "normalization": {"pointers": ignored, "reason": reason},
            "before_sha256": digest(safe(root, before).read_bytes()), "after_sha256": digest(safe(root, after).read_bytes()),
            "meaning": "JSON result equality under the declared normalization; not proof of complete behavioral coverage"}


def parser():
    ap = argparse.ArgumentParser(prog="ark", description="Agent Repo Kit: initialize once, keep evidence and checks current.")
    ap.add_argument("--version", action="version", version=VERSION)
    ap.add_argument("--repo", help="Repository/worktree root; defaults to discovery from cwd")
    sub = ap.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--mode", choices=["auto", "new", "existing"], default="auto")
    init.add_argument("--agents", help="Comma-separated adapters; defaults to all for new installs and preserves existing selection on repeat")
    init.add_argument("--hooks", action="store_true")
    init.add_argument("--ci", choices=["github"])
    init.add_argument("--upgrade", action="store_true")
    init.add_argument("--path", action="append", dest="mappings", help="Reuse an existing asset location: KEY=repository-relative-path")
    sub.add_parser("doctor")
    ctx = sub.add_parser("context")
    ctx.add_argument("--session", default="default")
    affected = sub.add_parser("impact")
    affected.add_argument("--base")
    sub.add_parser("install-git-hook")
    baseline = sub.add_parser("baseline").add_subparsers(dest="operation", required=True)
    baseline.add_parser("inventory")
    review = baseline.add_parser("review")
    review.add_argument("--document", required=True)
    review.add_argument("--files", nargs="+", required=True)
    review.add_argument("--reviewer", required=True)
    baseline.add_parser("validate")
    baseline.add_parser("status")
    register = baseline.add_parser("register")
    register.add_argument("--kind", choices=["module", "contract", "cases"], required=True)
    register.add_argument("--document", required=True)
    register.add_argument("--files", nargs="+", required=True)
    register.add_argument("--reviewer", required=True)
    for operation in ("promote", "retire"):
        transition = baseline.add_parser(operation)
        transition.add_argument("--document", required=True)
        transition.add_argument("--decision", required=True)
        transition.add_argument("--reviewer", required=True)
        if operation == "promote": transition.add_argument("--requirements", nargs="+", required=True)
    decision = sub.add_parser("decision").add_subparsers(dest="operation", required=True)
    question = decision.add_parser("add")
    question.add_argument("--id", required=True)
    question.add_argument("--category", choices=["fact", "behavior-decision", "design-task", "validation-gate"], required=True)
    question.add_argument("--question", required=True)
    question.add_argument("--scope", nargs="+", required=True)
    question.add_argument("--options", nargs="+")
    question.add_argument("--recommendation")
    question.add_argument("--owner")
    resolution = decision.add_parser("resolve")
    resolution.add_argument("--id", required=True)
    resolution.add_argument("--outcome", required=True)
    resolution.add_argument("--reviewer", required=True)
    resolution.add_argument("--evidence", nargs="+", required=True)
    decision.add_parser("list")
    change = sub.add_parser("change").add_subparsers(dest="operation", required=True)
    new = change.add_parser("new")
    new.add_argument("id")
    new.add_argument("--kind", choices=["feature", "fix", "refactor", "maintenance", "docs"], required=True)
    new.add_argument("--scope", nargs="+", required=True)
    new.add_argument("--requirements", nargs="*", default=[])
    new.add_argument("--remove-requirements", nargs="*", default=[])
    inspect = change.add_parser("inspect")
    inspect.add_argument("--base")
    for name in ("activate", "status", "close", "record-sync"):
        item = change.add_parser(name)
        item.add_argument("id")
        if name == "activate":
            item.add_argument("--session", default="default")
        if name == "record-sync":
            item.add_argument("--artifact", required=True)
            item.add_argument("--reviewer", required=True)
            item.add_argument("--method", choices=["native", "reviewed"], default="reviewed")
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--phase", choices=["structure", "specification", "ready", "delivery"], default="structure")
    verify_parser.add_argument("--change")
    verify_parser.add_argument("--base")
    verify_parser.add_argument("--check", action="append", dest="selected")
    spec = sub.add_parser("spec").add_subparsers(dest="operation", required=True)
    validate = spec.add_parser("validate")
    validate.add_argument("--change")
    replay = sub.add_parser("replay")
    replay.add_argument("--before", required=True)
    replay.add_argument("--after", required=True)
    replay.add_argument("--ignore-pointer", action="append", dest="ignored")
    replay.add_argument("--normalization-reason", dest="reason")
    ci = sub.add_parser("ci")
    ci.add_argument("--base", required=True)
    check = sub.add_parser("check", help="Run repository checks locally; no hosted service or CI is needed")
    check.add_argument("--base", help="Optional Git comparison base; defaults to the current worktree diff")
    note = sub.add_parser("note")
    note.add_argument("--scope", nargs="+", required=True)
    note.add_argument("--kind", choices=["docs", "mechanical", "test-only"], required=True)
    note.add_argument("--reason", required=True)
    note.add_argument("--reviewer", required=True)
    note.add_argument("--base")
    evidence = sub.add_parser("evidence")
    evidence.add_argument("--change", required=True)
    evidence.add_argument("--check", required=True)
    evidence.add_argument("--artifact", required=True)
    evidence.add_argument("--reviewer", required=True)
    evidence.add_argument("--status", choices=["PASS", "FAIL"], required=True)
    evidence.add_argument("--summary", required=True)
    cp = sub.add_parser("checkpoint")
    cp.add_argument("--change", required=True)
    cp.add_argument("--summary", required=True)
    cp.add_argument("--next", dest="next_step", required=True)
    pause = cp.add_mutually_exclusive_group()
    pause.add_argument("--blocked", action="store_true")
    pause.add_argument("--paused", action="store_true")
    hk = sub.add_parser("hook")
    hk.add_argument("action", choices=["session", "stop"])
    hk.add_argument("--agent", choices=["codex", "claude"], required=True)
    return ap


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    payload = {}
    try:
        if args.command == "hook":
            raw = sys.stdin.read(1024 * 1024)
            payload = json.loads(raw) if raw.strip() else {}
            if not isinstance(payload, dict):
                raise KitError("Hook input must be a JSON object")
        if args.command == "init":
            root = Path(args.repo or args.path).expanduser().resolve()
            result = init_repo(root, args.mode, args.agents.split(",") if args.agents else None, args.hooks, bool(args.ci), args.upgrade, path_overrides=parse_paths(args.mappings))
        else:
            root = root_at(args.repo or payload.get("cwd") or Path.cwd())
            p = policy_at(root)
            if args.command == "hook":
                result = hook(root, p, args.action, args.agent, payload)
            elif args.command == "doctor":
                result = doctor(root, p)
            elif args.command == "context":
                result = context(root, p, args.session)
            elif args.command == "impact":
                result = impact(root, p, args.base)
            elif args.command == "install-git-hook":
                result = install_git_hook(root, p)
            elif args.command == "verify":
                with lock(root, "verification"):
                    result = verify(root, p, args.phase, args.change, args.base, args.selected)
            elif args.command == "replay":
                result = replay_compare(root, args.before, args.after, args.ignored, args.reason)
            elif args.command == "spec":
                findings = structure_findings(root, p)
                if args.change:
                    findings += change_findings(root, p, args.change, "specification")
                result = {"status": overall(findings, []), "stage": "specification-structure", "findings": findings, "business_checks_executed": False}
            elif args.command in {"ci", "check"}:
                with lock(root, "verification"):
                    result = local_check(root, p, args.base, local=args.command == "check")
            elif args.command == "note":
                with lock(root):
                    result = note_change(root, p, args.scope, args.kind, args.reason, args.reviewer, args.base)
            elif args.command == "baseline":
                with lock(root):
                    if args.operation == "inventory":
                        result = baseline_inventory(root, p)
                    elif args.operation == "review":
                        result = baseline_review(root, p, args.document, args.files, args.reviewer)
                    elif args.operation == "register":
                        result = baseline_review(root, p, args.document, args.files, args.reviewer) if args.kind == "module" else knowledge_record(root, p, args.kind, args.document, args.files, args.reviewer)
                    elif args.operation == "status":
                        result = knowledge_status(root, p)
                    elif args.operation in {"promote", "retire"}:
                        result = knowledge_transition(root, p, args.document, args.reviewer, args.decision, getattr(args, "requirements", None), obsolete=args.operation == "retire")
                    else:
                        findings = baseline_findings(root, p)
                        findings += [{"status": "PENDING", "code": "knowledge-stale", "message": f"Refresh affected knowledge: {item['document']} ({item['changed']})"} for item in knowledge_status(root, p)["documents"] if item["freshness"] == "stale"]
                        result = {"status": overall(findings, []), "findings": findings, "meaning": "Static evidence freshness only; not proof of complete behavioral understanding."}
            elif args.command == "decision":
                with lock(root):
                    if args.operation == "list":
                        ledger_path = p["paths"].get("questions", p["paths"]["baseline"] + "/questions.json")
                        result = read_json(safe(root, ledger_path)) if ledger_path.endswith(".json") else {"status": "PASS", "provider": "native-file", "path": ledger_path, "content": safe(root, ledger_path).read_text(encoding="utf-8")}
                    elif args.operation == "add":
                        result = decision_record(root, p, args.id, args.category, args.question, args.scope, options=args.options, recommendation=args.recommendation, owner=args.owner)
                    else:
                        result = decision_record(root, p, args.id, outcome=args.outcome, reviewer=args.reviewer, evidence=args.evidence)
            elif args.command == "change":
                with lock(root):
                    if args.operation == "new":
                        result = new_change(root, p, args.id, args.kind, args.scope, args.requirements, args.remove_requirements)
                    elif args.operation == "inspect":
                        changed = changed_files(root, args.base)
                        result = {"files": changed, "behavior_candidates": [x for x in changed if is_behavior(x, p) and not excluded(x, p)], "meaning": "Candidates require semantic impact review; line count does not determine risk."}
                    elif args.operation == "activate":
                        change_at(root, p, args.id)
                        result = {"status": "PASS", "pointer": activate(root, args.id, args.session)}
                    elif args.operation == "status":
                        result = change_at(root, p, args.id)[1]
                    elif args.operation == "record-sync":
                        result = record_sync(root, p, args.id, args.artifact, args.reviewer, args.method)
                    else:
                        result = close_change(root, p, args.id)
            elif args.command == "evidence":
                with lock(root):
                    result = record_evidence(root, p, args.change, args.check, args.artifact, args.reviewer, args.status, args.summary)
            elif args.command == "checkpoint":
                with lock(root):
                    result = checkpoint(root, p, args.change, args.summary, args.next_step, args.blocked, args.paused)
            else:
                raise KitError("Unsupported operation")
        print(dump(result), end="")
        if args.command in {"init", "change", "checkpoint", "evidence", "hook"}:
            return 0
        return {"FAIL": 1, "PENDING": 2}.get(result.get("status"), 0)
    except (KitError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        if args.command == "hook":
            print(dump({"systemMessage": f"Agent Repo Kit hook unavailable: {exc}. Run ark doctor; local checks remain available and CI is optional."}), end="")
            return 0
        print(dump({"status": "FAIL", "error": str(exc)}), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
