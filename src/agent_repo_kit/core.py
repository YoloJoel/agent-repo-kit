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
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
import uuid

VERSION = "0.1.0"
ASSETS = Path(__file__).parent / "assets"
POLICY = ".ai/policy.json"
MANIFEST = ".ai/manifest.json"
START = "<!-- agent-repo-kit:start -->"
END = "<!-- agent-repo-kit:end -->"
FILL = "<!-- ARK:FILL -->"
REQ = re.compile(r"\bREQ-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SKILLS = ("initialize-repo", "baseline-repo", "deliver-change")
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
    for key in ("baseline", "specs", "changes", "adr", "templates"):
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
    for relative in p["test_paths"]:
        safe(root, relative)
    for relative in p.get("source_paths", ["."]):
        if relative != ".":
            safe(root, relative)
    if any(not isinstance(x, str) or not x for x in p["exclude"]):
        raise KitError("policy.exclude must contain nonempty glob strings")
    if not isinstance(p.get("requirements", {}), dict):
        raise KitError("policy.requirements must be an object")
    for requirement, mapping in p.get("requirements", {}).items():
        if not REQ.fullmatch(requirement) or not isinstance(mapping, dict) or mapping.get("type") not in {"automated", "manual", "external"}:
            raise KitError(f"Invalid requirement verification mapping: {requirement}")
        if not isinstance(mapping.get("checks", []), list) or any(name not in names for name in mapping.get("checks", [])):
            raise KitError(f"Unknown requirement check mapping: {requirement}")
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
    if any(under(relative, p.get("paths", {}).get(key, "@none")) for key in ("baseline", "changes", "templates")):
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


def is_behavior(relative):
    return Path(relative).suffix.lower() in SOURCE_SUFFIXES or Path(relative).name in {"Dockerfile", "Makefile", "Jenkinsfile"}


def default_policy(mode, agents):
    return {
        "$schema": "../hack/ai/assets/policy.schema.json", "schema_version": 1, "kit_version": VERSION, "mode": mode,
        "agents": sorted(set(agents)), "source_paths": ["."], "test_paths": ["tests", "src/test"],
        "paths": {"baseline": "docs/baseline", "specs": "openspec/specs", "changes": "openspec/changes", "adr": "docs/adr", "templates": "docs/templates"},
        "exclude": [".ai", "hack/ai", ".agents/skills", ".claude/skills", ".opencode/skills", "skills-lock.json", "docs/baseline", "docs/templates", "openspec/changes"],
        "checks": [], "requirements": {}, "command_candidates": [], "hook_mode": "advisory",
    }


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


def init_repo(root, mode="auto", agents=None, hooks=False, ci=False, upgrade=False, copy_skills=None):
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
            detected = "existing" if any(is_behavior(x) for x in observed) else "new"
            p = default_policy(detected if mode == "auto" else mode, agents)
            candidates = []
            for marker, argv in (("pom.xml", ["mvn", "test"]), ("build.gradle", ["./gradlew", "test"]), ("go.mod", ["go", "test", "./..."]), ("package.json", ["npm", "test"]), ("pyproject.toml", ["python", "-m", "unittest", "discover", "-s", "tests"])):
                if (root / marker).is_file():
                    candidates.append({"marker": marker, "argv": argv, "confirmed": False})
            p["command_candidates"] = candidates
        if copy_skills is None:
            copy_skills = p.get("skill_delivery", "repository") == "repository"
        p["skill_delivery"] = "repository" if copy_skills else "installed"
        writes = {POLICY: dump(p)}
        owned = dict(old_manifest.get("files", {}))

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
        routing = (ASSETS / "agents.md").read_text(encoding="utf-8").replace("{{BASELINE}}", p["paths"]["baseline"]).replace("{{SPECS}}", p["paths"]["specs"]).replace("{{CHANGES}}", p["paths"]["changes"])
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
            "docs/engineering-standard.md": (ASSETS / "engineering-standard.md").read_text(encoding="utf-8"),
            p["paths"]["baseline"] + "/README.md": "# Baseline\n\n" + ("Existing repository: inventory is pending review. Use baseline-repo; inventory alone is not an approved baseline.\n" if p["mode"] == "existing" else "New repository: no historical system is asserted. Build specifications from real requirements.\n"),
            p["paths"]["baseline"] + "/questions.json": dump({"schema_version": 1, "questions": []}),
            p["paths"]["adr"] + "/README.md": "# Architecture decisions\n\nRecord consequential, long-lived choices using docs/templates/adr.md. Preserve accepted history and link superseding decisions.\n",
        }
        for relative, content in defaults.items():
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
        writes[MANIFEST] = dump(manifest)
        changed = transact(root, writes)
        if p["mode"] == "existing":
            baseline_inventory(root, p)
        baseline_status = "NOT_APPLICABLE" if p["mode"] == "new" else ("PENDING" if baseline_findings(root, p) else "STATIC_REVIEW_CURRENT")
        report = {"status": "PASS", "meaning": "Scaffolding installed; no semantic baseline or runtime hook trust is asserted.", "mode": p["mode"], "changed": changed, "changed_scope": "Installation/configuration assets; excludes this generated report and baseline/runtime observations.", "baseline": baseline_status, "checks": "NOT_RUN", "hook_trust": "NOT_VERIFIED", "branch_protection": "NOT_VERIFIED", "kit_version": VERSION}
        atomic(safe(root, ".ai/init-report.json"), dump(report))
        return report


def onboard_repo(root, mode="auto", agents=None, hooks=True, ci="auto", upgrade=False, copy_skills=None):
    """Shared first-use operation for installed Skills and the compatibility entry."""
    origin = git(root, "remote", "get-url", "origin", optional=True)
    github = bool(origin and re.search(r"(?:^|[@/:])github\.com[:/]", origin.decode("utf-8"), re.IGNORECASE))
    enable_ci = ci == "github" or (ci == "auto" and github)
    result = init_repo(root, mode, agents, hooks, enable_ci, upgrade, copy_skills)
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
    snapshot = p["paths"]["baseline"] + "/raw/inventory-" + coverage["source_fingerprint"][:16] + ".json"
    writes = {path: dump(coverage)}
    if not safe(root, snapshot).exists():
        writes[snapshot] = dump(coverage)
    transact(root, writes)
    return {"status": "PENDING", "files": len(reviewed), "reviewed": sum(x["status"] == "reviewed" for x in reviewed.values()), "coverage": path, "meaning": "Inventory is evidence navigation, not semantic approval."}


def baseline_review(root, p, document, files, reviewer):
    path = safe(root, document)
    if not path.is_file():
        raise KitError("Write the module explanation before recording a review.")
    text = path.read_text(encoding="utf-8")
    required = ("## Purpose", "## Flow", "## State and failure", "## Evidence", "## Gaps")
    if FILL in text or any(title not in text for title in required):
        raise KitError("Module explanation must fill the module template: Purpose, Flow, State and failure, Evidence, Gaps.")
    coverage_path = safe(root, p["paths"]["baseline"] + "/coverage.json")
    coverage = read_json(coverage_path)
    for relative in files:
        source = safe(root, relative)
        if relative not in coverage["files"] or not source.is_file():
            raise KitError(f"File is not in the current inventory: {relative}")
        if digest(source.read_bytes()) != coverage["files"][relative]["sha256"]:
            raise KitError(f"Inventory is stale for {relative}; refresh it first.")
        pattern = re.compile(r"(?<![\w./-])" + re.escape(relative) + r":L(\d+)(?:-L?(\d+))?\b")
        refs = pattern.findall(text)
        lines = len(source.read_text(encoding="utf-8").splitlines())
        if not refs or any(not 1 <= int(begin) <= int(finish or begin) <= lines for begin, finish in refs):
            raise KitError(f"Provide valid file:L1-LN evidence for {relative}")
    for relative in files:
        coverage["files"][relative].update(status="reviewed", document=document, document_sha256=digest(path.read_bytes()), reviewer=reviewer, level="static", reviewed_at=now())
    atomic(coverage_path, dump(coverage))
    return {"status": "PASS", "meaning": "Static review declaration recorded; semantic correctness still requires review and behavioral verification.", "files": files}


def baseline_findings(root, p, scope=None):
    if p["mode"] == "new":
        return []
    coverage = read_json(safe(root, p["paths"]["baseline"] + "/coverage.json"), {"files": {}})
    findings = []
    current = inventory_files(root, p)
    for relative in sorted(set(current) - set(coverage.get("files", {}))):
        if is_behavior(relative) and (not scope or any(under(relative, prefix) for prefix in scope)) and any(under(relative, prefix) for prefix in p.get("source_paths", ["."])):
            findings.append({"status": "PENDING", "code": "baseline-uninventoried", "message": f"No baseline inventory record for {relative}; inspect its origin and refresh scope."})
    for relative, item in coverage.get("files", {}).items():
        if scope and not any(under(relative, prefix) for prefix in scope):
            continue
        if not is_behavior(relative):
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


def change_at(root, p, change):
    if not ID.fullmatch(change or ""):
        raise KitError("Change ID must be lowercase words separated by hyphens")
    directory = safe(root, p["paths"]["changes"] + "/" + change)
    if not directory.exists():
        matches = []
        for path in safe(root, p["paths"]["changes"] + "/archive").glob("*/ark.json"):
            if read_json(path).get("id") == change:
                matches.append(path.parent)
        if len(matches) != 1:
            raise KitError(f"Expected one active/archived change with ID {change}; found {len(matches)}")
        directory = matches[0]
    metadata = read_json(directory / "ark.json")
    if metadata.get("id") != change or metadata.get("kind") not in {"feature", "fix", "refactor", "maintenance", "docs"}:
        raise KitError(f"Invalid change metadata: {change}")
    if not isinstance(metadata.get("scope"), list) or not metadata["scope"]:
        raise KitError(f"Change scope is missing: {change}")
    for relative in metadata["scope"]:
        if relative != ".":
            safe(root, relative)
    if not isinstance(metadata.get("requirements", []), list) or any(not isinstance(x, str) or not REQ.fullmatch(x) for x in metadata.get("requirements", [])):
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
    seen = {}
    for path in sorted(safe(root, p["paths"]["specs"]).glob("**/*.md")):
        text = safe(root, path.relative_to(root).as_posix()).read_text(encoding="utf-8")
        if FILL in text:
            findings.append({"status": "FAIL", "code": "spec-placeholder", "message": f"Unfilled current specification: {path.relative_to(root)}"})
        declarations = set()
        for line in text.splitlines():
            if re.match(r"^#{2,4}\s+Requirement:", line):
                declarations.update(REQ.findall(line))
        for requirement in declarations:
            if requirement in seen:
                findings.append({"status": "FAIL", "code": "duplicate-requirement", "message": f"{requirement} appears in multiple current specs: {seen[requirement]}, {path.relative_to(root)}"})
            seen[requirement] = path.relative_to(root).as_posix()
    for path in sorted(safe(root, p["paths"]["adr"]).glob("[0-9]*.md")):
        text = safe(root, path.relative_to(root).as_posix()).read_text(encoding="utf-8")
        if any(heading not in text for heading in ("## Context", "## Decision", "## Alternatives", "## Consequences")):
            findings.append({"status": "FAIL", "code": "adr-structure", "message": f"ADR missing required sections: {path.relative_to(root)}"})
    return findings


def change_findings(root, p, change, phase):
    directory, metadata = change_at(root, p, change)
    findings = []
    for name in ("proposal.md", "tasks.md", "design.md"):
        path = directory / name
        if not path.is_file():
            findings.append({"status": "FAIL", "code": "missing-artifact", "message": f"Missing {change}/{name}"})
        elif phase != "structure" and FILL in path.read_text(encoding="utf-8"):
            findings.append({"status": "PENDING", "code": "draft-artifact", "message": f"Fill {change}/{name} or explain why its sections do not apply."})
    deltas = list(directory.glob("specs/**/*.md"))
    if phase != "structure":
        if metadata["kind"] in {"feature", "fix", "refactor"} and not metadata.get("requirements"):
            findings.append({"status": "PENDING", "code": "missing-requirements", "message": "Declare the affected stable requirement IDs in ark.json before implementation."})
        for path in deltas:
            text = path.read_text(encoding="utf-8")
            if FILL in text or "#### Scenario:" not in text:
                findings.append({"status": "PENDING", "code": "delta-scenarios", "message": f"Fill observable scenarios in {path.relative_to(root)}"})
        if metadata["kind"] == "docs" and any(is_behavior(x) and not x.startswith("docs/") for x in metadata["scope"] if x != "."):
            findings.append({"status": "FAIL", "code": "task-classification", "message": "A docs change cannot declare source/configuration file scope."})
    if phase == "ready" and metadata["kind"] != "docs":
        findings += baseline_findings(root, p, metadata["scope"])
    if phase == "delivery":
        if p["mode"] == "existing" and metadata["kind"] != "docs":
            anchor = read_json(directory / "baseline-anchor.json", {})
            if anchor.get("scope") != metadata["scope"] or not anchor.get("ready_fingerprint") or not anchor.get("reviewed_files"):
                findings.append({"status": "PENDING", "code": "baseline-anchor", "message": "Establish reviewed pre-change baseline and run ready verification before implementation."})
        tasks = directory / "tasks.md"
        if tasks.is_file() and re.search(r"^\s*- \[ \]", tasks.read_text(encoding="utf-8"), re.MULTILINE):
            findings.append({"status": "PENDING", "code": "unfinished-tasks", "message": "Change tasks still contain unchecked items."})
        tests = "\n".join(safe(root, path).read_text(encoding="utf-8", errors="replace") for path in inventory_files(root, p) if any(under(path, prefix) for prefix in p["test_paths"]))
        spec_text = "\n".join(path.read_text(encoding="utf-8") for path in deltas)
        current_text = "\n".join(path.read_text(encoding="utf-8") for path in safe(root, p["paths"]["specs"]).glob("**/*.md"))
        for requirement in metadata.get("requirements", []):
            if requirement not in set(REQ.findall(spec_text + current_text)):
                findings.append({"status": "FAIL", "code": "requirement-spec", "message": f"{requirement} has no specification reference."})
            mapping = p.get("requirements", {}).get(requirement, {"type": "automated"})
            verification_type = mapping.get("type", "automated")
            if verification_type == "automated" and requirement not in set(REQ.findall(tests)):
                findings.append({"status": "PENDING", "code": "requirement-test", "message": f"{requirement} has no test-source reference; a reference still does not prove assertion quality."})
            elif verification_type in {"manual", "external"}:
                configured = {check["name"] for check in p["checks"] if check.get("type") == verification_type and check.get("required", True)}
                if not mapping.get("checks") or not set(mapping["checks"]).issubset(configured):
                    findings.append({"status": "PENDING", "code": "requirement-check", "message": f"{requirement} needs an explicit required {verification_type} check mapping."})
        if deltas:
            sync = read_json(directory / "spec-sync.json", {})
            actual_deltas = {path.relative_to(directory).as_posix(): digest(path.read_bytes()) for path in deltas}
            actual_specs = spec_hashes(root, p)
            if sync.get("deltas") != actual_deltas or sync.get("specs") != actual_specs or not artifact_valid(root, sync):
                findings.append({"status": "PENDING", "code": "spec-sync", "message": "Synchronize deltas using the native OpenSpec workflow, review the result, and record-sync before delivery verification."})
    return findings


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


def verify(root, p, phase="structure", change=None, base=None, selected=None):
    findings = structure_findings(root, p)
    metadata = None
    if change:
        _, metadata = change_at(root, p, change)
        findings += change_findings(root, p, change, phase)
        if base:
            outside = [x for x in changed_files(root, base) if is_behavior(x) and not excluded(x, p) and not any(under(x, scope) for scope in metadata["scope"])]
            if outside:
                findings.append({"status": "FAIL", "code": "scope", "message": f"Behavior/config changes outside declared scope: {outside}"})
    elif phase != "structure":
        raise KitError("A ready/delivery verification needs --change ID")
    start_fingerprint = fingerprint(root, p, change)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    run_dir = safe(root, ".ai/runtime/runs/" + run_id)
    run_dir.mkdir(parents=True)
    checks = []
    if phase == "delivery":
        if os.environ.get("ARK_VERIFY_ACTIVE"):
            raise KitError("Recursive verification detected; a check cannot run its own delivery verifier.")
        if selected and set(selected) - {x["name"] for x in p["checks"]}:
            raise KitError("Unknown --check selection")
        external = read_json(change_at(root, p, change)[0] / "evidence.json", {"checks": {}})
        for check in p["checks"]:
            if selected and check["name"] not in selected:
                checks.append({"name": check["name"], "required": check.get("required", True), "status": "NOT_RUN", "reason": "Not selected; partial execution cannot satisfy required delivery checks."})
            elif check.get("type", "command") == "command":
                checks.append(run_check(root, check, run_dir))
            else:
                evidence = external.get("checks", {}).get(check["name"], {})
                valid = evidence.get("fingerprint") == start_fingerprint and artifact_valid(root, evidence)
                checks.append({"name": check["name"], "type": check["type"], "required": check.get("required", True), "status": evidence.get("status", "NOT_RUN") if valid else "NOT_RUN", "reason": evidence.get("summary", "No current external/manual evidence")})
        if not any(x.get("required", True) for x in p["checks"]) and metadata["kind"] != "docs":
            checks.append({"name": "behavioral-verification", "required": True, "status": "NOT_RUN", "reason": "Confirm real project checks in policy.checks; command candidates are not executed automatically."})
    if fingerprint(root, p, change) != start_fingerprint:
        findings.append({"status": "FAIL", "code": "inputs-changed", "message": "Verification inputs changed while checks were running; inspect generated files and rerun."})
    report = {"schema_version": 1, "run_id": run_id, "phase": phase, "change": change, "created_at": now(), "kit_version": VERSION, "python": sys.version.split()[0], "platform": sys.platform, "source_ref": (git(root, "rev-parse", "HEAD", optional=True) or b"").decode().strip() or None, "fingerprint": start_fingerprint, "base": base, "findings": findings, "checks": checks, "status": overall(findings, checks)}
    atomic(run_dir / "result.json", dump(report))
    if change:
        directory, change_metadata = change_at(root, p, change)
        if phase == "ready" and report["status"] == "PASS" and p["mode"] == "existing" and change_metadata["kind"] != "docs":
            coverage = read_json(safe(root, p["paths"]["baseline"] + "/coverage.json"), {"files": {}})
            reviewed_files = {relative: record for relative, record in coverage["files"].items() if record.get("status") == "reviewed" and any(under(relative, prefix) for prefix in change_metadata["scope"]) and is_behavior(relative)}
            anchor_path = directory / "baseline-anchor.json"
            if anchor_path.exists():
                previous = read_json(anchor_path)
                if previous.get("ready_fingerprint") != start_fingerprint:
                    raise KitError("A different pre-change baseline is already anchored; retain history and create a new change rather than replacing it.")
            else:
                atomic(anchor_path, dump({"scope": change_metadata["scope"], "source_ref": report["source_ref"], "ready_fingerprint": start_fingerprint, "run_id": run_id, "reviewed_files": reviewed_files}))
        atomic(directory / "verification.json", dump(report))
        lines = [f"# Verification: {change}", "", f"Conclusion: {report['status']}", f"Phase: {phase}", f"Fingerprint: {start_fingerprint}", f"Run: {run_id}", "", "## Findings", ""]
        lines += [f"- {x['status']}: {x['message']}" for x in findings] or ["- No structural findings. This does not establish semantic completeness."]
        lines += ["", "## Checks", ""] + [f"- {x['name']}: {x['status']} — {x.get('reason', x.get('log', ''))}" for x in checks]
        lines += ["", "## Evidence", "", f"Runtime evidence: `.ai/runtime/runs/{run_id}/result.json`. CI must independently verify the candidate commit.", ""]
        atomic(directory / "verify-report.md", "\n".join(lines))
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
    findings = change_findings(root, p, change, "delivery")
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


def checkpoint(root, p, change, summary, next_step, blocked=False):
    directory, metadata = change_at(root, p, change)
    metadata.update(state="blocked" if blocked else "implementing", updated_at=now())
    transact(root, {(directory / "ark.json").relative_to(root).as_posix(): dump(metadata), (directory / "checkpoint.md").relative_to(root).as_posix(): f"# Checkpoint: {change}\n\nStatus: {metadata['state']}\nUpdated: {now()}\n\n## Completed / current state\n\n{summary}\n\n## Next step\n\n{next_step}\n"})
    return {"status": "PENDING", "change": change, "state": metadata["state"]}


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


def context(root, p, session="default"):
    change = active(root, session)
    if change:
        try:
            directory, metadata = change_at(root, p, change)
            if directory.parent.name == "archive" or metadata.get("state") == "complete":
                change = None
        except KitError:
            change = None
    return {"project": str(root), "mode": p["mode"], "active_change": change, "routing": {"facts": p["paths"]["baseline"], "behavior": p["paths"]["specs"], "decisions": p["paths"]["adr"], "work": p["paths"]["changes"]}, "workflow": "Use initialize-repo for onboarding, baseline-repo for evidence gaps, deliver-change for changes. Read only relevant context. Never report NOT_RUN as PASS.", "resume": f"Read {p['paths']['changes']}/{change}/checkpoint.md and actual diff." if change else "Choose an explicit related change; do not infer it from modification time."}


def ci_verify(root, p, base):
    """Re-execute candidate changes; never trust committed verification reports."""
    if not base or set(base) == {"0"}:
        raise KitError("CI requires a real comparison base; configure the main-branch base for an initial push.")
    changed = changed_files(root, base)
    immutable = []
    for relative in changed:
        old = git(root, "show", f"{base}:{relative}", optional=True)
        if old is None:
            continue
        path = safe(root, relative)
        new = path.read_bytes() if path.is_file() else b""
        if under(relative, p["paths"]["baseline"] + "/raw") and old != new:
            immutable.append({"status": "FAIL", "code": "raw-history", "message": f"Historical raw evidence changed: {relative}"})
        if under(relative, p["paths"]["adr"]) and re.search(rb"^Status:\s*Accepted\s*$", old, re.MULTILINE):
            normalized_old = re.sub(rb"^Status:.*$", b"Status:", old, flags=re.MULTILINE)
            normalized_new = re.sub(rb"^Status:.*$", b"Status:", new, flags=re.MULTILINE)
            if normalized_old != normalized_new:
                immutable.append({"status": "FAIL", "code": "accepted-adr", "message": f"Accepted ADR body changed; preserve it and add a superseding decision: {relative}"})
    manifest = read_json(safe(root, MANIFEST))
    owned = set(manifest.get("files", {}))
    behavior = [x for x in changed if is_behavior(x) and not excluded(x, p) and x not in owned]
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
    candidates = []
    directory = safe(root, p["paths"]["changes"])
    metadata_paths = sorted(directory.glob("*/ark.json")) + sorted(directory.glob("archive/*/ark.json"))
    for path in metadata_paths:
        item = read_json(path)
        relative_directory = path.parent.relative_to(root).as_posix()
        if path.parent.parent.name == "archive" and not any(under(relative, relative_directory) for relative in changed):
            continue
        scopes = item.get("scope", [])
        if any(any(under(relative, scope) for scope in scopes) for relative in behavior):
            candidates.append(item["id"])
    uncovered = []
    for relative in behavior:
        if not any(any(under(relative, scope) for scope in change_at(root, p, change)[1]["scope"]) for change in candidates):
            uncovered.append(relative)
    results = list(immutable)
    if uncovered:
        results.append({"status": "FAIL", "code": "untracked-behavior-change", "message": f"Behavior/configuration changes need a scoped active or newly archived change: {uncovered}"})
    for change in candidates:
        if change_at(root, p, change)[1]["kind"] == "docs":
            results.append({"status": "FAIL", "code": "classification", "message": f"{change} is marked docs but intersects behavior/configuration changes."})
        else:
            report = verify(root, p, "delivery", change)
            results.append({"status": report["status"], "change": change, "run_id": report["run_id"]})
    light_checks = []
    if lightweight:
        run_dir = safe(root, ".ai/runtime/runs/light-" + uuid.uuid4().hex[:12])
        run_dir.mkdir(parents=True)
        for check in p["checks"]:
            if check.get("type", "command") == "command":
                light_checks.append(run_check(root, check, run_dir))
            elif check.get("required", True):
                light_checks.append({"name": check["name"], "required": True, "status": "NOT_RUN", "reason": "Required outside verification needs a scoped change/evidence record."})
        atomic(run_dir / "result.json", dump({"checks": light_checks, "status": overall([], light_checks)}))
    return {"status": overall(results, light_checks), "base": base, "behavior_files": behavior, "lightweight_files": sorted(lightweight), "lightweight_checks": light_checks, "changes": results, "control_review": "Review lightweight declarations and policy/runtime/CI/manifest changes independently; repository-controlled checks are not a security boundary."}


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
    change = active(root, session)
    if not change:
        return {}
    try:
        directory, metadata = change_at(root, p, change)
    except KitError:
        return {}
    if metadata.get("state") == "blocked":
        return {}
    verification = read_json(directory / "verification.json", {})
    fresh = verification.get("phase") == "delivery" and verification.get("status") == "PASS" and verification.get("fingerprint") == fingerprint(root, p, change)
    if fresh:
        return {}
    reason = f"Change {change} has no fresh PASS delivery verification. Run deliver-change checks or save a blocked/pending checkpoint; do not declare the whole change complete."
    if p.get("hook_mode") != "enforce":
        return {"systemMessage": reason}
    # At most one continuation for a session+turn, even if the model changes files.
    token = digest((session + "\0" + str(payload.get("turn_id", "turn"))).encode())[:24]
    marker = safe(root, ".ai/runtime/hook-stops/" + token + ".json")
    if marker.exists():
        return {"systemMessage": reason + " Automatic continuation already used; leaving a recoverable pending task."}
    atomic(marker, dump({"change": change, "created_at": now(), "fingerprint": fingerprint(root, p, change)}))
    return {"decision": "block", "reason": reason}


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
    sub.add_parser("doctor")
    ctx = sub.add_parser("context")
    ctx.add_argument("--session", default="default")
    baseline = sub.add_parser("baseline").add_subparsers(dest="operation", required=True)
    baseline.add_parser("inventory")
    review = baseline.add_parser("review")
    review.add_argument("--document", required=True)
    review.add_argument("--files", nargs="+", required=True)
    review.add_argument("--reviewer", required=True)
    baseline.add_parser("validate")
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
    verify_parser.add_argument("--phase", choices=["structure", "ready", "delivery"], default="structure")
    verify_parser.add_argument("--change")
    verify_parser.add_argument("--base")
    verify_parser.add_argument("--check", action="append", dest="selected")
    ci = sub.add_parser("ci")
    ci.add_argument("--base", required=True)
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
    cp.add_argument("--blocked", action="store_true")
    hk = sub.add_parser("hook")
    hk.add_argument("action", choices=["session", "stop"])
    hk.add_argument("--agent", choices=["codex", "claude"], required=True)
    return ap


def main(argv=None):
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
            result = init_repo(root, args.mode, args.agents.split(",") if args.agents else None, args.hooks, bool(args.ci), args.upgrade)
        else:
            root = root_at(args.repo or payload.get("cwd") or Path.cwd())
            p = policy_at(root)
            if args.command == "hook":
                result = hook(root, p, args.action, args.agent, payload)
            elif args.command == "doctor":
                result = doctor(root, p)
            elif args.command == "context":
                result = context(root, p, args.session)
            elif args.command == "verify":
                with lock(root, "verification"):
                    result = verify(root, p, args.phase, args.change, args.base, args.selected)
            elif args.command == "ci":
                with lock(root, "verification"):
                    findings = structure_findings(root, p)
                    result = {"status": overall(findings, []), "findings": findings} if findings else ci_verify(root, p, args.base)
            elif args.command == "note":
                with lock(root):
                    result = note_change(root, p, args.scope, args.kind, args.reason, args.reviewer, args.base)
            elif args.command == "baseline":
                with lock(root):
                    if args.operation == "inventory":
                        result = baseline_inventory(root, p)
                    elif args.operation == "review":
                        result = baseline_review(root, p, args.document, args.files, args.reviewer)
                    else:
                        findings = baseline_findings(root, p)
                        result = {"status": overall(findings, []), "findings": findings, "meaning": "Static evidence freshness only; not proof of complete behavioral understanding."}
            elif args.command == "change":
                with lock(root):
                    if args.operation == "new":
                        result = new_change(root, p, args.id, args.kind, args.scope, args.requirements, args.remove_requirements)
                    elif args.operation == "inspect":
                        changed = changed_files(root, args.base)
                        result = {"files": changed, "behavior_candidates": [x for x in changed if is_behavior(x) and not excluded(x, p)], "meaning": "Candidates require semantic impact review; line count does not determine risk."}
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
                    result = checkpoint(root, p, args.change, args.summary, args.next_step, args.blocked)
            else:
                raise KitError("Unsupported operation")
        print(dump(result), end="")
        if args.command in {"init", "change", "checkpoint", "evidence", "hook"}:
            return 0
        return {"FAIL": 1, "PENDING": 2}.get(result.get("status"), 0)
    except (KitError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        if args.command == "hook":
            print(dump({"systemMessage": f"Agent Repo Kit hook unavailable: {exc}. Run ark doctor; required CI remains independent."}), end="")
            return 0
        print(dump({"status": "FAIL", "error": str(exc)}), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
