"""Dependency-free runtime. Also vendored as hack/ai/ark.py in consumer repos.

The runtime records observations and runs checks. It never claims to understand
source semantics or turn inventory into an approved specification by itself.
"""

from __future__ import annotations

import argparse
import ast
from bisect import bisect_left, bisect_right
import contextlib
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import tokenize
from datetime import date, datetime, timezone
import uuid
import xml.etree.ElementTree as ET

VERSION = "0.4.0-rc.3"
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
TEST_SOURCE_SUFFIXES = (SOURCE_SUFFIXES - {".yaml", ".yml", ".toml", ".xml", ".json"}) | {
    ".mjs", ".cjs", ".mts", ".cts", ".kts", ".cc", ".cxx", ".hh", ".hxx",
    ".swift", ".m", ".mm", ".scala", ".groovy", ".dart", ".lua", ".r", ".jl",
    ".pl", ".pm", ".ex", ".exs", ".erl", ".hs", ".lhs", ".ml", ".fs", ".fsx",
    ".f", ".f90", ".f95", ".bash", ".zsh", ".ps1", ".psm1", ".bat", ".cmd",
    ".feature", ".robot", ".phpt",
}
SPEC_CODE_SUFFIXES = SOURCE_SUFFIXES | TEST_SOURCE_SUFFIXES | {
    ".proto", ".gradle", ".cmake", ".vue", ".svelte", ".tcl", ".zig", ".ini", ".conf",
}
SPEC_CODE_LOCATION = re.compile(
    # Explicit source-host/editor anchors are unambiguous even for extensionless scripts.
    r"(?<![\w.-])(?:[\w.-]+\.[\w+-]+|[\w.-]+(?:/[\w.-]+)+|Makefile|Dockerfile|Jenkinsfile)`?"
    r"(?::L|#L|#lines?-)[0-9]+\b"
    # Bare numbers also occur in ports and prose; require a recognizable code/build filename.
    r"|(?<!://)(?<![\w.-])(?:[\w.-]+(?:" + "|".join(sorted(map(re.escape, SPEC_CODE_SUFFIXES))) +
    r")|Makefile|Dockerfile|Jenkinsfile|CMakeLists\.txt)`?"
    r"(?::\d+\b|[ \t]+L\d+\b|[ ,:(]+lines?\s+\d+\b"
    r"|[ ，,:：（(]*(?:的)?第\s*\d+(?:\s*[-–至到]\s*\d+)?\s*行)",
    re.IGNORECASE,
)
LOCAL_IGNORE = "# Agent Repo Kit local evidence, locks, and session pointers\n.ai/runtime/\n"


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
    rules = p.get("artifact_rules", {})
    if not isinstance(rules, dict):
        raise KitError("policy.artifact_rules must map project risk IDs to artifact requirements")
    for name, rule in rules.items():
        if not ID.fullmatch(name) or name == "none" or not isinstance(rule, dict):
            raise KitError(f"Invalid artifact rule: {name}")
        requires, paths = rule.get("requires"), rule.get("paths", [])
        if not isinstance(requires, list) or not requires or any(x not in ("spec", "design", "adr") for x in requires):
            raise KitError(f"Rule {name} requires spec, design or adr")
        if not isinstance(paths, list):
            raise KitError(f"Rule {name} paths must be repository paths or globs")
        for path in paths:
            if path != ".":
                safe(root, path)
        source = safe(root, rule.get("source"))
        if not source.is_file():
            raise KitError(f"Rule {name} needs a real repository policy source: {source.relative_to(root)}")
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
        report = check.get("case_report")
        if report is not None and (not isinstance(report, dict) or report.get("format") not in {"junit", "ark-json"}
                                   or not isinstance(report.get("required_cases", []), list)
                                   or any(not isinstance(x, str) or not x for x in report.get("required_cases", []))):
            raise KitError("case_report needs junit/ark-json format and optional nonempty required case identities")
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
        if not isinstance(mapping.get("targets", {}),dict): raise KitError("Requirement targets must map actual Change IDs")
        for change,target in mapping.get("targets",{}).items():
            if not isinstance(change,str) or not ID.fullmatch(change) or not isinstance(target,dict) or target.get("type") not in {"automated","manual","external"} or not isinstance(target.get("checks"),list) or any(name not in names for name in target["checks"]):
                raise KitError(f"Invalid target verification mapping: {requirement}/{change}")
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
    return path.name not in {"README", "LICENSE", "COPYING", "NOTICE", "AUTHORS"}


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
    # Initialization appends its local-runtime ignore rule. It is not a project
    # language/build fact; delivery fingerprints and diff checks still include it.
    behavior = {name: item["sha256"] for name, item in inventory.items() if name != ".gitignore" and is_behavior(name, p)}
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


def project_entry(root, p, profile, existing=""):
    """Render a project entrance; never dump the build inventory into AGENTS."""
    data = read_json(safe(root, ".ai/project-entry.json"), {})
    if not isinstance(data, dict):
        raise KitError("Project entry facts must be an object")
    context = p["paths"].get("context", "docs/project-context.md")
    standard = p["paths"].get("standard", "docs/engineering-standard.md")
    defaults = {
        "purpose": f"`{root.name}`. Project purpose requires source review; see `{context}`.",
        "stack": ", ".join(profile["languages"]) or "Not established; inspect actual source and build configuration.",
        "boundaries": "Observed source roots: " + (", ".join(profile["source_roots"]) or "not established") + f". Confirm actual module/runtime boundaries in `{context}`.",
        "constraints": "Preserve observable contracts and accepted decisions. Project-specific constraints require source review.",
        "workflow": f"Read current specs before behavior changes; record scope, design when needed, tests and actual verification. Project branch/review/release rules must be established from existing evidence in `{standard}`.",
        "precedence": "Explicit user instructions apply first. Current specs govern behavior, accepted ADRs decisions, the engineering standard process, and this file navigation. Record conflicts; do not invent or silently change accepted promises.",
    }
    values = {key: data.get(key, value) for key, value in defaults.items()}
    if any(not isinstance(value, str) for value in values.values()):
        raise KitError("Project entry sections must be text")
    commands = []
    for check in p["checks"]:
        argv = check.get("argv")
        command = " ".join(argv) if isinstance(argv, list) else "outside evidence"
        commands.append(f"- `{check['name']}`: `{command}` ({check.get('type', 'command')}; execution results are recorded separately)")
    values["commands"] = "\n".join(commands) or "No confirmed project checks yet. Candidate commands are unverified; do not claim compilation or tests passed."
    rows = [("Current behavior", p["paths"]["specs"]), ("Changes", p["paths"]["changes"]), ("Decisions", p["paths"]["adr"]),
            ("Source-backed knowledge", p["paths"]["baseline"]), ("Engineering standard", standard), ("Project context", context), ("Checks", "hack/ai/ark.py")]
    values["assets"] = "| Asset | Location |\n| --- | --- |\n" + "\n".join(f"| {name} | `{path}` |" for name, path in rows)
    text = (ASSETS / "agents.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key.upper() + "}}", value)
    if data.get("language") == "zh":
        for old, new in (("AI engineering entry", "AI 工程规则入口"), ("Project and stack", "项目定位与技术栈"), ("Architecture constraints", "架构约束"),
                         ("Asset navigation", "资产导航"), ("Source boundaries", "代码与模块边界"), ("Project commands", "工程命令"), ("Development workflow", "开发流程"), ("Rule precedence", "规则优先级")):
            text = text.replace(old, new)
        text = text.replace("Use the user's language. This is the project entrance; detailed procedures belong in the engineering standard.", "使用用户的语言。本文件是项目入口；详细流程以工程规范为准。")
        text = text.replace("execution results are recorded separately", "实际执行结果另行记录")
        for old, new in (("Asset | Location", "资产 | 位置"), ("Current behavior", "当前规格"), ("Changes", "变更"), ("Decisions", "决策"), ("Source-backed knowledge", "源码基线"), ("Engineering standard", "工程规范"), ("Project context", "项目上下文"), ("Checks", "检查入口")):
            text = text.replace("| " + old, "| " + new)
    outside = existing
    generated_project_entry = False
    if START in existing and END in existing:
        managed = existing[existing.index(START):existing.index(END)]
        generated_project_entry = bool(re.search(r"(?m)^## 1\. (?:Project and stack|项目定位与技术栈)$", managed))
        outside = existing[:existing.index(START)] + existing[existing.index(END) + len(END):]
    if outside.strip() and not generated_project_entry:
        # Existing human/native entry stays authoritative. Do not append a second
        # project outline or tool manual underneath it.
        text = f"## Engineering integration\n\nUse the user's language. Preserve the project rules above.\nRead `{standard}` and `{context}`; paths/checks are mapped in `.ai/policy.json`.\nLocal check: `python hack/ai/ark.py check`. Initialization is not onboarding completion.\n"
        if data.get("language") == "zh":
            text = f"## 工程工具接入\n\n保留以上项目规则。详细流程见 `{standard}`，项目上下文见 `{context}`。\n路径与确认后的命令见 `.ai/policy.json`；本地检查：`python hack/ai/ark.py check`。初始化不等于接入完成。\n"
    routing_note = ("通过 OpenSpec、Superpowers 或普通对话开发时，沿用同一 Change、当前规格、ADR 与仓内检查。"
                    "见 `hack/ai/assets/engineering-standard.md` 的跨工具流程；交付前运行 `python hack/ai/ark.py check`。"
                    if data.get("language") == "zh" else
                    "OpenSpec, Superpowers and direct requests share the same Change, current specs and ADRs. "
                    "See `hack/ai/assets/engineering-standard.md` for design and plan references. Verify delivery with `python hack/ai/ark.py check`.")
    return text.rstrip() + "\n\n" + routing_note + "\n"


def entry_refresh(root, p):
    path = safe(root, ".ai/project-entry.json")
    data = read_json(path)
    for key in ("purpose", "stack", "boundaries", "constraints", "workflow", "precedence", "reviewer"):
        if not isinstance(data.get(key), str) or not data[key].strip() or FILL in data[key]:
            raise KitError("Project entry needs source-backed " + key)
    evidence = data.get("source_evidence", {})
    if not isinstance(evidence, dict) or not evidence:
        raise KitError("Project entry needs actual source/config evidence")
    if not isinstance(data.get("gaps", []), list):
        raise KitError("Project entry gaps must be an explicit list")
    for name, reference in evidence.items():
        source = safe(root, name)
        if not source.is_file() or not isinstance(reference, str) or not source_reference_valid(reference, name, source.read_bytes()):
            raise KitError("Invalid project-entry source evidence: " + name)
    manifest = read_json(safe(root, MANIFEST))
    existing = safe(root, "AGENTS.md").read_bytes().decode("utf-8")
    old = existing[existing.index(START):existing.index(END) + len(END)]
    if digest(old.encode()) != manifest.get("agents_block"):
        raise KitError("AGENTS.md managed block was edited; explicitly merge human changes before refresh")
    updated = block(existing, project_entry(root, p, project_profile(root, p), existing))
    manifest["agents_block"] = digest(updated[updated.index(START):updated.index(END) + len(END)].encode())
    rule_sources = {rule["source"] for rule in p.get("artifact_rules", {}).values()}
    record = {"reviewer": data["reviewer"], "inputs": {name: digest(updated.encode()) if name == "AGENTS.md" else digest(safe(root, name).read_bytes()) for name in [".ai/project-entry.json", POLICY, *evidence, *rule_sources]},
              "rule_sources": {name: digest(safe(root, name).read_bytes()) for name in rule_sources},
              "agents_sha256": digest(updated.encode()), "gaps": data.get("gaps", []), "recorded_at": now(), "level": "agent-declared-project-entry"}
    transact(root, {"AGENTS.md": updated, MANIFEST: dump(manifest), ".ai/project-entry-review.json": dump(record)})
    return entry_status(root, p)


def entry_status(root, p):
    record = read_json(safe(root, ".ai/project-entry-review.json"), {})
    findings = []
    if not record:
        findings.append({"status": "PENDING", "code": "project-entry-unreviewed", "message": "Project entrance is setup only; curate real project purpose/boundaries/constraints/commands/workflow and run entry refresh."})
    else:
        changed = [name for name, sha in record["inputs"].items() if not safe(root, name).is_file() or digest(safe(root, name).read_bytes()) != sha]
        if digest(safe(root, "AGENTS.md").read_bytes()) != record["agents_sha256"]:
            changed.append("AGENTS.md")
        if changed:
            findings.append({"status": "PENDING", "code": "project-entry-stale", "changed": changed, "message": "Recheck project entrance against current inputs and confirmed checks."})
        if record.get("gaps"):
            findings.append({"status": "PENDING", "code": "project-entry-gaps", "message": "Project-specific facts remain unresolved.", "gaps": record["gaps"]})
    return {"status": overall(findings, []), "findings": findings, "meaning": "Declared project-specific entry review and currency, not semantic certification."}


def fingerprint(root, p, change=None):
    files = inventory_files(root, p)
    # Configuration/contract inputs are always bound, even if excluded from inventory.
    required = [POLICY, MANIFEST, "AGENTS.md", ".ai/project-entry.json", ".ai/project-entry-review.json", ".ai/capability-coverage-review.json", "openspec/config.yaml", ".ai/openspec-review.json", ".ai/rule-review.json", ".ai/external-review.json", p["paths"]["baseline"] + "/README.md"]
    files["@external"] = external_status(root, p)
    required.extend(rule["source"] for rule in p.get("artifact_rules", {}).values())
    behavior_review = read_json(safe(root, ".ai/behavior-review.json"), {})
    required += [".ai/behavior-review.json", *behavior_review.get("inputs", {})]
    spec_root = safe(root, p["paths"]["specs"])
    if spec_root.exists():
        required += [f.relative_to(root).as_posix() for f in spec_root.rglob("*.md") if f.is_file()]
    if change:
        directory, metadata = change_at(root, p, change)
        for name in ("design.md", "tasks.md"):
            content, source = workflow_document(root, directory, name)
            if source:
                files["@workflow/" + name] = digest(content.encode("utf-8"))
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
    files["@knowledge"] = knowledge_status(root, p, metadata["scope"] if change else None)["documents"]
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
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
                managed("hack/ai/assets/" + path.relative_to(ASSETS).as_posix(), path.read_bytes())
        context_path = p["paths"].get("context", "docs/project-context.md")
        standard_path = p["paths"].get("standard", "docs/engineering-standard.md")
        agent_path = safe(root, "AGENTS.md")
        existing = agent_path.read_bytes().decode("utf-8") if agent_path.exists() else ""
        routing = project_entry(root, p, profile, existing)
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
            writes[".gitignore"] = ignore_text + ("\n" if ignore_text and not ignore_text.endswith("\n") else "") + LOCAL_IGNORE
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
        config_path = safe(root, "openspec/config.yaml")
        if openspec_applicable(root, p) and (not config_path.exists() or not config_path.read_bytes().strip()):
            config = openspec_config_text(root, p, read_json(safe(root, ".ai/project-entry.json"), {"stack": ", ".join(profile["languages"])}))
            writes["openspec/config.yaml"] = config
            writes[".ai/openspec-generated.json"] = dump({"sha256": digest(config.encode())})
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
        report = {"status": "PASS", "report_kind": "initialization_snapshot", "created_at": now(), "meaning": "Historical setup snapshot, not current onboarding/verification status. Scaffolding installed; no semantic baseline or runtime hook trust is asserted.", "mode": p["mode"], "changed": changed, "changed_scope": "Installation/configuration assets; excludes this generated report and baseline/runtime observations.", "baseline": baseline_status, "checks": "NOT_RUN", "hook_trust": "NOT_VERIFIED", "branch_protection": "NOT_VERIFIED", "kit_version": VERSION}
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
    baseline_index_refresh(root, p)
    return {"status": "PASS", "meaning": "Static declaration recorded; case execution and semantic review are separate", "document": document, "snapshot": snapshot}


def knowledge_status(root, p, scope=None):
    index = read_json(safe(root, p["paths"]["baseline"] + "/knowledge.json"), {"documents": {}})
    documents = []
    for name, item in index["documents"].items():
        if scope and not any(under(name, prefix) or item.get("decision") and under(item["decision"], prefix)
                             or any(under(path, prefix) for path in item["sources"]) for prefix in scope):
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


def baseline_audit_record(root, p, report, files, artifacts, reviewer):
    """Bind a source-first audit and its rechecks to exact inputs, without certifying semantics."""
    if not reviewer.strip() or not files or not artifacts:
        raise KitError("A source audit needs an actual reviewer, source scope and reviewed artifacts")
    if set(files) & set(artifacts) or report in files or report in artifacts:
        raise KitError("Keep source, generated artifacts and audit report distinct")
    paths = sorted(set(files + artifacts + [report]))
    for relative in paths:
        if not safe(root, relative).is_file():
            raise KitError(f"Audit input missing: {relative}")
    data = read_json(safe(root, report))
    if not isinstance(data, dict) or data.get("review_mode") not in {"same-agent-separate-pass", "independent-reviewer"}:
        raise KitError("Declare actual same-agent-separate-pass or independent-reviewer mode")
    passes = data.get("passes", [])
    if not isinstance(passes, list) or len(passes) < 2:
        raise KitError("Record source-first and source-recheck passes in order")
    previous_ids = set()
    for index, audit in enumerate(passes):
        expected_kind = "source-first" if index == 0 else "source-recheck"
        if not isinstance(audit, dict) or audit.get("kind") != expected_kind:
            raise KitError("Record source-first followed by source-recheck passes in order")
        sources, reviewed = audit.get("sources", []), audit.get("artifacts", [])
        if not isinstance(sources, list) or not isinstance(reviewed, list):
            raise KitError("Audit passes need explicit source and artifact coverage")
        if not all(isinstance(item, dict) and isinstance(item.get("path"), str) for item in sources + reviewed):
            raise KitError("Audit coverage entries need actual paths")
        if {item.get("path") for item in sources} != set(files) or {item.get("path") for item in reviewed} != set(artifacts):
            raise KitError("Every audit pass must account for the complete selected source and artifact scope")
        for item in sources:
            if not isinstance(item.get("checked"), str) or not item["checked"].strip() or not source_reference_valid(item.get("evidence", ""), item["path"], safe(root, item["path"]).read_bytes()):
                raise KitError("Describe actual source branches checked with valid source evidence in each pass")
        if any(not isinstance(item.get("checked"), str) or not item["checked"].strip() for item in reviewed):
            raise KitError("Describe the claims or omissions checked in every artifact")
        findings = audit.get("findings")
        if not isinstance(findings, list):
            raise KitError("Each pass needs actual findings (an empty list means none found)")
        ids = set()
        for finding in findings:
            if not isinstance(finding, dict):
                raise KitError("Audit findings must be objects")
            identity = finding.get("id")
            if not isinstance(identity, str) or not identity.strip() or identity in ids:
                raise KitError("Audit findings need unique stable IDs within each pass")
            ids.add(identity)
            if not all(isinstance(finding.get(key), str) and finding[key].strip() for key in ("issue", "evidence")):
                raise KitError("Findings need an actual issue and source evidence")
            if not any(source_reference_valid(finding["evidence"], name, safe(root, name).read_bytes()) for name in files):
                raise KitError("Finding evidence must reference actual scoped source")
            if finding.get("status") not in {"open", "fixed", "rejected"}:
                raise KitError("Finding status must be open, fixed or rejected")
            if index == 0 and finding["status"] != "open":
                raise KitError("Persist first-pass findings as open before fixes/dispositions")
            if index > 0 and identity not in previous_ids and finding["status"] != "open":
                raise KitError("New recheck findings stay open until a further scoped source review")
            if finding["status"] != "open" and not str(finding.get("resolution", "")).strip():
                raise KitError("Fixed/rejected findings need resolution and recheck reasoning")
        if not previous_ids.issubset(ids):
            raise KitError("Recheck must retain every prior finding with its actual disposition")
        previous_ids = ids
    open_ids = sorted(finding["id"] for finding in passes[-1]["findings"] if finding["status"] == "open")
    record = {"report": report, "reviewer": reviewer, "files": sorted(set(files)), "artifacts": sorted(set(artifacts)),
              "review_mode": data["review_mode"], "pass_count": len(passes),
              "inputs": {name: digest(safe(root, name).read_bytes()) for name in paths}, "open_findings": open_ids,
              "level": "agent-declared-source-audit", "recorded_at": now()}
    base = p["paths"]["baseline"]
    ledger = read_json(safe(root, base + "/audits.json"), {"schema_version": 1, "reports": {}})
    earlier_open = set(ledger["reports"].get(report, {}).get("open_findings", []))
    missing = earlier_open - previous_ids
    if missing:
        raise KitError("Retain previously recorded open findings: " + ", ".join(sorted(missing)))
    ledger["reports"][report] = record
    snapshot = evidence_root(p) + "/audits/" + digest(dump(record).encode())
    transact(root, {base + "/audits.json": dump(ledger), snapshot + "/record.json": dump(record),
                    snapshot + "/report.json": dump(data)})
    return baseline_audit_status(root, p, report)


def baseline_audit_status(root, p, report=None):
    ledger = read_json(safe(root, p["paths"]["baseline"] + "/audits.json"), {"reports": {}})
    records = [item for name, item in ledger["reports"].items() if report is None or name == report]
    findings, rounds = [], []
    if not records:
        findings.append({"status": "PENDING", "code": "source-audit-missing", "message": "Run the source-first audit and post-fix source recheck; structural checks do not replace them."})
    for item in records:
        source_report = read_json(safe(root, item["report"]), {})
        previous_open = set()
        for number, review_pass in enumerate(source_report.get("passes", []), 1):
            open_ids = {finding["id"] for finding in review_pass.get("findings", []) if finding.get("status") == "open"}
            rounds.append({"report": item["report"], "round": number, "kind": review_pass.get("kind"),
                           "open": sorted(open_ids), "new_or_reopened": sorted(open_ids - previous_open),
                           "closed": sorted(previous_open - open_ids),
                           "diagnostic": "Repeated unresolved findings; inspect missing evidence/root cause and checkpoint if blocked." if open_ids and open_ids == previous_open else None})
            previous_open = open_ids
        changed = [name for name, expected in item["inputs"].items() if not safe(root, name).is_file() or digest(safe(root, name).read_bytes()) != expected]
        if changed:
            findings.append({"status": "PENDING", "code": "source-audit-stale", "path": item["report"], "changed": changed,
                             "message": "Source, generated artifacts or audit report changed; recheck the affected scope and record fresh evidence."})
        if item["open_findings"]:
            findings.append({"status": "PENDING", "code": "source-audit-open", "path": item["report"], "ids": item["open_findings"],
                             "message": "Unresolved source-audit findings remain; do not claim audit closure."})
    return {"status": overall(findings, []), "findings": findings, "reports": records, "rounds": rounds,
            "meaning": "Checks declared source-first/recheck coverage, dispositions and freshness; cannot prove rereading occurred or certify semantic correctness/zero defects."}


def capability_sources(root, p):
    return {name: item["sha256"] for name, item in inventory_files(root, p).items()
            if is_behavior(name, p) and any(under(name, prefix) for prefix in p["source_paths"])
            and not any(under(name, prefix) for prefix in p["test_paths"])}


def validate_source_cases(root, item, production_sources):
    cases = item.get("source_cases", [])
    if not isinstance(cases, list):
        raise KitError("Capability source cases must be a list")
    if not isinstance(item.get("source_case_dispositions", {}), dict):
        raise KitError("source_case_dispositions must map case IDs to reasons")
    ids, stimuli = set(), set()
    for case in cases:
        if not isinstance(case, dict) or not all(isinstance(case.get(k), str) and case[k].strip()
                                                for k in ("id", "stimulus", "path", "reference")) or "source_outcome" not in case:
            raise KitError("Each source case needs an ID, concrete stimulus, source anchor and typed outcome")
        if case["id"] in ids or case["stimulus"] in stimuli:
            raise KitError("Each source case within a capability needs a distinct ID and stimulus")
        ids.add(case["id"])
        stimuli.add(case["stimulus"])
        if case["path"] not in production_sources or case["path"] not in item["sources"] or not source_reference_valid(
                case["reference"], case["path"], safe(root, case["path"]).read_bytes()):
            raise KitError(f"Invalid capability source case anchor: {case['id']}")


def coverage_record(root, p, document, reviewer):
    data = read_json(safe(root, document))
    if not reviewer.strip() or not isinstance(data, dict) or not isinstance(data.get("capabilities"), list) or not data["capabilities"]:
        raise KitError("Map actual business/supporting capabilities with a reviewer before recording coverage")
    identities = set()
    inputs = capability_sources(root, p)
    for item in data["capabilities"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip() or item["id"] in identities:
            raise KitError("Capability map needs unique stable IDs")
        identities.add(item["id"])
        if item.get("kind") not in {"business", "supporting"} or item.get("status") not in {"specified", "pending", "excluded"}:
            raise KitError("Declare business/supporting kind and specified/pending/excluded status")
        if not isinstance(item.get("purpose"), str) or not item["purpose"].strip() or not isinstance(item.get("sources"), list) or not item["sources"]:
            raise KitError("Every capability needs actual responsibility and source files")
        for name in item["sources"]:
            if not isinstance(name, str) or not safe(root, name).is_file():
                raise KitError("Capability source is missing or unsafe")
        if item["status"] == "excluded" and not str(item.get("reason", "")).strip():
            raise KitError("Exclusions need a concrete scope/supporting/generated/vendor rationale")
        if not isinstance(item.get("requirements", []), list) or any(not isinstance(identity, str) for identity in item.get("requirements", [])):
            raise KitError("Requirements must be actual declared IDs/titles")
        validate_source_cases(root, item, inputs)
    ledger = ".ai/capability-coverage-review.json"
    previous = read_json(safe(root, ledger), {})
    if previous:
        # Compare with the reviewed bytes, including snapshots written by older versions.
        # The live map is normally already being edited at this point.
        prior_path = evidence_root(p) + "/capabilities/" + digest(dump(previous).encode()) + "/map.json"
        prior_file = safe(root, prior_path)
        if not prior_file.is_file():
            prior_file = safe(root, previous["document"])
            if not prior_file.is_file() or digest(prior_file.read_bytes()) != previous["sha256"]:
                raise KitError("Previous capability snapshot unavailable; restore the recorded map before replacing its scope")
        by_id = {item["id"]: item for item in data["capabilities"]}
        dispositions = data.get("capability_dispositions", {})
        if not isinstance(dispositions, dict):
            raise KitError("capability_dispositions must map prior capability IDs to their review reasons")
        for prior in read_json(prior_file)["capabilities"]:
            key = prior["id"]
            current = by_id.get(key)
            if current is None or (prior["kind"] == "business" and current["kind"] == "supporting"):
                if not isinstance(dispositions.get(key), str) or not dispositions[key].strip():
                    raise KitError(f"Capability {key} was removed or reclassified; retain it as pending or record its disposition")
                continue
            cases = {case["id"]: case for case in current.get("source_cases", [])}
            reasons = current.get("source_case_dispositions", {})
            for old in prior.get("source_cases", []):
                case = cases.get(old["id"])
                if case is None or case["stimulus"] != old["stimulus"] or dump(case["source_outcome"]) != dump(old["source_outcome"]):
                    reason = reasons.get(old["id"])
                    if not isinstance(reason, str) or not reason.strip() or reason == prior.get("source_case_dispositions", {}).get(old["id"]):
                        raise KitError(f"Record why source case {key}/{old['id']} was retired or its input/outcome changed")
    record = {"document": document, "sha256": digest(safe(root, document).read_bytes()), "sources": inputs,
              "reviewer": reviewer, "recorded_at": now(), "level": "agent-declared-capability-map"}
    snapshot = evidence_root(p) + "/capabilities/" + digest(dump(record).encode())
    transact(root, {ledger: dump(record), snapshot + "/record.json": dump(record), snapshot + "/map.json": dump(data)})
    return coverage_status(root, p)


def coverage_status(root, p):
    record = read_json(safe(root, ".ai/capability-coverage-review.json"), {})
    current_sources = capability_sources(root, p)
    findings, capabilities, mapped, included = [], [], set(), set()
    current = current_requirement_ids(root, p)
    if not record:
        findings.append({"status": "PENDING", "code": "capability-map-missing", "message": "Build a source-derived business capability map, not just a few lifecycle/cross-cutting specs."})
    else:
        path = safe(root, record["document"])
        if not path.is_file() or digest(path.read_bytes()) != record["sha256"] or record["sources"] != current_sources:
            findings.append({"status": "PENDING", "code": "capability-map-stale", "message": "Map or production-source inventory changed; reconcile scope before re-recording."})
        data = read_json(path, {"capabilities": []}) if path.is_file() else {"capabilities": []}
        for item in data["capabilities"]:
            sources = set(item["sources"]) & set(current_sources)
            mapped |= sources
            capabilities.append({"id": item["id"], "kind": item["kind"], "status": item["status"], "source_files": len(sources), "requirements": item.get("requirements", [])})
            if item["status"] == "pending" or item["status"] == "excluded" and item["kind"] == "business":
                findings.append({"status": "PENDING", "code": "capability-incomplete", "message": f"Business scope is not fully specified: {item['id']}"})
            if item["status"] != "excluded":
                included |= sources
            if item["kind"] == "business" and item["status"] == "specified" and (not item.get("requirements") or not set(item["requirements"]).issubset(current)):
                findings.append({"status": "PENDING", "code": "capability-spec-missing", "message": f"{item['id']} needs real current requirements; a baseline link or future uncreated owner is not a spec."})
        if included:
            findings += baseline_findings(root, p, sorted(included))
    missing = sorted(set(current_sources) - mapped)
    if missing:
        findings.append({"status": "PENDING", "code": "capability-unmapped-sources", "count": len(missing), "sample": missing[:10], "message": "Production/build/config sources are outside the declared capability coverage."})
    return {"status": overall(findings, []), "production_files": len(current_sources), "mapped_files": len(mapped),
            "unmapped_files": len(missing), "capabilities": capabilities, "findings": findings,
            "meaning": "Declared source/capability/current-requirement coverage; counts and mappings do not prove semantic completeness or assertion quality."}



BEHAVIOR_DIMENSIONS = {"normal", "negative", "boundary", "recovery", "concurrency", "resources", "compatibility"}
BEHAVIOR_SURFACES = {"api", "messages", "configuration", "lifecycle", "computation", "upgrade", "storage", "background"}


def behavior_data(root, p):
    record = read_json(safe(root, ".ai/behavior-review.json"), {})
    data = read_json(safe(root, record["document"]), {}) if record and safe(root, record["document"]).is_file() else {}
    return record, data


def discovery_scan(root, p):
    """Produce source-only candidates, without reading the author's Spec or inventory."""
    sources = capability_sources(root, p)
    candidates, imports, limitations = [], [], []
    for path in sorted(sources):
        text = safe(root, path).read_text(encoding="utf-8", errors="replace")
        counts = {}
        def add(kind, line, expression, owner=""):
            key = dump([path, owner, kind, expression])
            counts[key] = counts.get(key, 0) + 1
            candidates.append({"id": "SRC-" + digest((key + str(counts[key])).encode())[:20],
                               "path": path, "reference": f"{path}:L{line}", "kind": kind,
                               "owner": owner, "expression": expression, "source_sha256": sources[path]})
        if Path(path).suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError as exc:
                limitations.append({"path": path, "reason": "Python parse failed: " + str(exc)})
                continue
            class Visitor(ast.NodeVisitor):
                def __init__(self): self.owner = []
                def visit_FunctionDef(self, node):
                    self.owner.append(node.name)
                    add("entry", node.lineno, node.name, ".".join(self.owner))
                    self.generic_visit(node)
                    self.owner.pop()
                visit_AsyncFunctionDef = visit_FunctionDef
                def visit_ClassDef(self, node):
                    self.owner.append(node.name); self.generic_visit(node); self.owner.pop()
                def visit_If(self, node):
                    for outcome in ("true", "false"):
                        add("condition-" + outcome, node.lineno, ast.unparse(node.test), ".".join(self.owner))
                    self.generic_visit(node)
                def visit_Return(self, node):
                    expression = ast.unparse(node.value) if node.value else "None"
                    if isinstance(node.value, (ast.Compare, ast.BoolOp)):
                        for outcome in ("true", "false"):
                            add("return-" + outcome, node.lineno, expression, ".".join(self.owner))
                    else:
                        add("return", node.lineno, expression, ".".join(self.owner))
                    self.generic_visit(node)
                def visit_Raise(self, node):
                    add("exception", node.lineno, ast.unparse(node), ".".join(self.owner)); self.generic_visit(node)
                def visit_Import(self, node):
                    for alias in node.names: imports.append({"consumer": path, "module": alias.name, "reference": f"{path}:L{node.lineno}"})
                def visit_ImportFrom(self, node):
                    module = node.module or ""
                    if node.level:
                        parent = Path(path).parent
                        for _ in range(node.level - 1): parent = parent.parent
                        module = (parent.as_posix().replace("/", ".").strip(".") + "." + module).strip(".")
                    imports.append({"consumer": path, "module": module, "reference": f"{path}:L{node.lineno}"})
            Visitor().visit(tree)
        else:
            masked = assertion_code_mask(text, Path(path).suffix.lower())
            limitations.append({"path": path, "reason": "Lexical candidates only; inspect runtime enablement, dynamic dispatch and omitted constructs independently."})
            for number, line in enumerate((masked or "").splitlines(), 1):
                if re.search(r"\b(?:if|switch|case|return|throw|catch|register\w*|subscribe\w*|signal)\b", line):
                    add("lexical-path", number, line.strip())
        if not any(item["path"] == path for item in candidates):
            add("source-review", 1, "Inspect observable effects/configuration and justify exclusions")
    modules = {str(Path(path).with_suffix("")).replace("/", "."): path for path in sources if path.endswith(".py")}
    edges = [{**item, "producer": modules[item["module"]], "kind": "import-candidate"}
             for item in imports if item["module"] in modules and modules[item["module"]] != item["consumer"]]
    return {"schema_version": 1, "status": "PENDING", "sources": sources, "candidates": candidates,
            "edges": edges, "limitations": limitations,
            "meaning": "Source-only review candidates, not exhaustive behavior discovery or a verified call graph."}


def discovery_status(root, p):
    scan = discovery_scan(root, p)
    record = read_json(safe(root, ".ai/discovery-review.json"), {})
    data = read_json(safe(root, record["document"]), {}) if record and safe(root, record["document"]).is_file() else {}
    findings = []
    entries = {item.get("id"): item for item in data.get("candidates", []) if isinstance(item, dict)}
    current = current_requirement_ids(root, p)
    coverage = read_json(safe(root, ".ai/capability-coverage-review.json"), {})
    capabilities = read_json(safe(root, coverage["document"]), {}).get("capabilities", []) if coverage and safe(root, coverage["document"]).is_file() else []
    samples = {case["id"] for capability in capabilities for case in capability.get("source_cases", [])}
    for candidate in scan["candidates"]:
        item = entries.get(candidate["id"], {})
        disposition = item.get("disposition")
        valid = (item.get("source_sha256") == candidate["source_sha256"] and isinstance(item.get("reason"), str) and bool(item["reason"].strip()))
        if disposition == "specified":
            valid = valid and bool(item.get("requirements")) and set(item["requirements"]).issubset(current) and bool(item.get("source_cases")) and set(item["source_cases"]).issubset(samples)
        elif disposition not in {"baseline", "excluded"}:
            valid = False
        if not valid:
            findings.append({"status": "PENDING", "code": "discovery-candidate-unreviewed", "candidate": candidate["id"],
                             "path": candidate["path"], "reference": candidate["reference"], "kind": candidate["kind"],
                             "message": "Reconcile this independently scanned source candidate, including contrasting outcomes and actual enablement."})
    for limitation in scan["limitations"]:
        review = data.get("source_reviews", {}).get(limitation["path"], {})
        if (review.get("source_sha256") != scan["sources"][limitation["path"]] or not review.get("checked")
                or not review.get("limitations") or not review.get("reviewer")):
            findings.append({"status": "PENDING", "code": "discovery-provider-limited", **limitation,
                             "message": "Record a source review of unsupported/dynamic behavior; candidate count cannot establish completeness."})
    if not record or record.get("sha256") != digest(dump(data).encode()):
        findings.append({"status": "PENDING", "code": "discovery-review-unrecorded", "message": "Record the actual source-only discovery reconciliation."})
    return {"status": overall(findings, []), "candidate_count": len(scan["candidates"]),
            "unreviewed": sum(x["code"] == "discovery-candidate-unreviewed" for x in findings),
            "findings": findings, "edges": scan["edges"], "limitations": scan["limitations"],
            "meaning": "Coverage of scanned candidates plus declared independent source review; not universal semantic completeness."}


def discovery_record(root, p, document, reviewer):
    data = read_json(safe(root, document))
    if not reviewer.strip() or data.get("schema_version") != 1 or not isinstance(data.get("candidates"), list):
        raise KitError("Discovery reconciliation needs schema 1, candidate dispositions and a reviewer")
    identities = [item.get("id") for item in data["candidates"] if isinstance(item, dict)]
    if len(identities) != len(data["candidates"]) or len(set(identities)) != len(identities):
        raise KitError("Discovery dispositions must have unique candidate IDs")
    record = {"document": document, "sha256": digest(dump(data).encode()), "reviewer": reviewer,
              "recorded_at": now(), "sources": capability_sources(root, p), "review_mode": data.get("review_mode", "same-agent-separate-pass")}
    snapshot = evidence_root(p) + "/discovery/" + digest(dump(record).encode())
    transact(root, {".ai/discovery-review.json": dump(record), snapshot + "/record.json": dump(record), snapshot + "/review.json": dump(data)})
    return discovery_status(root, p)


def readback_directory(root, p, identity):
    if not ID.fullmatch(identity):
        raise KitError("Readback ID must be lowercase and hyphenated")
    return safe(root, p["paths"]["baseline"] + "/readbacks/" + identity)


def readback_open(root, p, identity, document, reviewer, mode="same-agent-separate-pass"):
    directory = readback_directory(root, p, identity)
    if directory.exists():
        raise KitError("Readback identity already exists; retain the frozen inputs and start a new round")
    data = read_json(safe(root, document))
    questions = data.get("questions")
    if (not reviewer.strip() or not isinstance(questions, list) or not questions
            or any(not isinstance(q, dict) or set(q) != {"id", "stimulus"} or not all(isinstance(v, str) and v.strip() for v in q.values()) for q in questions)
            or len({q["id"] for q in questions}) != len(questions)):
        raise KitError("Reader questions need unique IDs and stimuli only; keep answers/source anchors outside the reader input")
    if mode not in {"same-agent-separate-pass", "separate-context-attested"}:
        raise KitError("Declare the actual review mode; separate contexts are attested, not filesystem isolation")
    specs = {path: re.sub(r"(?m)^Baseline:.*\n?", "", safe(root, path).read_text(encoding="utf-8")) for path in spec_hashes(root, p)}
    if not specs:
        raise KitError("Freeze actual current specifications before readback")
    reader = {"schema_version": 1, "questions": questions, "specs": specs}
    record = {"schema_version": 1, "id": identity, "created_at": now(), "examiner": reviewer,
              "mode": mode, "specs": spec_hashes(root, p), "sources": capability_sources(root, p),
              "reader_sha256": digest(dump(reader).encode())}
    base = directory.relative_to(root).as_posix()
    transact(root, {base + "/open.json": dump(record), base + "/reader.json": dump(reader),
                    ".ai/readback-active.json": dump({"id": identity})})
    return {"status": "PENDING", "id": identity, "next": "Give only reader.json to the reader, then freeze predictions before revealing source outcomes.", "reader": base + "/reader.json"}


def readback_record(root, p, identity, document, reviewer, judge=False):
    directory = readback_directory(root, p, identity)
    opened = read_json(directory / "open.json")
    reader = read_json(directory / "reader.json")
    if digest(dump(reader).encode()) != opened["reader_sha256"]:
        raise KitError("Frozen reader input changed")
    if opened["specs"] != spec_hashes(root, p) or opened["sources"] != capability_sources(root, p):
        raise KitError("Source or Spec changed; preserve this round and open a new readback")
    name = "judgment.json" if judge else "predictions.json"
    if (directory / name).exists():
        raise KitError("A frozen readback stage cannot be overwritten")
    if not reviewer.strip(): raise KitError("Identify the actual reader/reviewer")
    data = read_json(safe(root, document))
    rows = data.get("answers")
    if (not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
            or len(rows) != len(reader["questions"]) or {row.get("id") for row in rows} != {q["id"] for q in reader["questions"]}):
        raise KitError("Account for every frozen question exactly once, including ambiguous answers")
    previous = read_json(directory / "predictions.json") if judge else None
    if opened["mode"] == "separate-context-attested" and not judge and reviewer == opened["examiner"]:
        raise KitError("Separate-context readback needs a distinct reader identity; identity alone does not prove isolation")
    for row in rows:
        if judge:
            prediction = next(item for item in previous["answers"] if item["id"] == row["id"])
            if row.get("status") not in {"entailed", "ambiguous", "contradicted", "source-unknown"} or not row.get("reason"):
                raise KitError("Adjudicate textual entailment separately from source agreement, with a reason")
            evidence = row.get("evidence", [])
            if row["status"] != "source-unknown" and (not evidence or not all(behavior_anchor(root, anchor) for anchor in evidence)):
                raise KitError("Judgments need actual source evidence")
            if row["status"] == "entailed" and (prediction.get("status") != "predicted" or "observed" not in row or dump(prediction["expected"]) != dump(row["observed"])):
                raise KitError("An ambiguous or contradicted prediction cannot be adjudicated entailed")
        else:
            if row.get("status") == "ambiguous":
                if not row.get("missing"): raise KitError("Describe the missing deciding premise")
                continue
            quotes = row.get("premises", [])
            if row.get("status") != "predicted" or "expected" not in row or not isinstance(quotes, list) or not quotes:
                raise KitError("Prediction needs typed expected output and exact Spec-only premises")
            if any(not isinstance(q, dict) or q.get("path") not in reader["specs"] or not q.get("quote") or q["quote"] not in reader["specs"][q["path"]] for q in quotes):
                raise KitError("Every prediction premise must occur in a frozen current Spec")
    record = {"schema_version": 1, "reviewer": reviewer, "recorded_at": now(), "reader_sha256": opened["reader_sha256"], "answers": rows}
    if judge: record["predictions_sha256"] = digest((directory / "predictions.json").read_bytes())
    atomic(directory / name, dump(record))
    return readback_status(root, p, identity)


def readback_status(root, p, identity=None):
    base = safe(root, p["paths"]["baseline"] + "/readbacks")
    active_id = identity or read_json(safe(root, ".ai/readback-active.json"), {}).get("id")
    directories = [readback_directory(root, p, identity)] if identity else sorted(path.parent for path in base.glob("*/open.json"))
    runs, findings = [], []
    for directory in directories:
        opened = read_json(directory / "open.json")
        prediction = read_json(directory / "predictions.json", {})
        judgment = read_json(directory / "judgment.json", {})
        state = "PASS"
        reason = "All frozen questions have source-agreeing, reviewer-adjudicated premises."
        if opened["specs"] != spec_hashes(root, p) or opened["sources"] != capability_sources(root, p):
            state, reason = "PENDING", "Frozen source/Spec inputs are no longer current."
        elif (not judgment or not prediction or judgment.get("predictions_sha256") != digest((directory / "predictions.json").read_bytes())
              or opened["reader_sha256"] != digest((directory / "reader.json").read_bytes())):
            state, reason = "PENDING", "Freeze predictions before recording complete source/textual adjudication."
        elif any(row["status"] == "contradicted" for row in judgment["answers"]):
            state, reason = "FAIL", "A frozen prediction contradicts the source."
        elif any(row["status"] != "entailed" for row in judgment["answers"]):
            state, reason = "PENDING", "Some questions lack sufficient Spec premises or source evidence."
        runs.append({"id": opened["id"], "status": state, "mode": opened["mode"], "reason": reason,
                     "questions": len(read_json(directory / "reader.json")["questions"]),
                     "prediction_frozen": bool(prediction), "adjudicated": bool(judgment)})
    active_runs = [run for run in runs if run["id"] == active_id]
    if not active_runs:
        findings.append({"status": "PENDING", "code": "readback-missing", "message": "Freeze a Spec-only reader round before declaring semantic usability."})
    else:
        reader = read_json(readback_directory(root, p, active_id) / "reader.json")
        coverage = read_json(safe(root, ".ai/capability-coverage-review.json"), {})
        mapping = read_json(safe(root, coverage["document"]), {}) if coverage and safe(root, coverage["document"]).is_file() else {}
        missing = sorted({case["stimulus"] for capability in mapping.get("capabilities", []) for case in capability.get("source_cases", [])}
                         - {question["stimulus"] for question in reader["questions"]})
        if missing:
            findings.append({"status": "PENDING", "code": "readback-unasked-source-cases", "stimuli": missing,
                             "message": "The active round must ask all recorded source-case stimuli, not only the author's favorable cases."})
        for run in active_runs:
            if run["status"] != "PASS":
                findings.append({"status": run["status"], "code": "readback-incomplete", "id": run["id"], "message": run["reason"]})
    return {"status": overall(findings, []), "active": active_id, "runs": runs, "findings": findings,
            "meaning": "Recorded order, input currency and reviewer adjudication; mode is attested, semantic truth and context isolation are not mechanically certified."}


def behavior_impact(root, p, changed, scan_sources=True):
    """Declared dependency closure, not a language-specific inferred call graph."""
    _, data = behavior_data(root, p)
    units = data.get("units", [])
    def matches(path):
        return bool(path) and any(under(path, name) for name in changed)
    affected = {u["id"] for u in units if any(matches(e.get("path")) for e in u.get("evidence", []))
                or any(matches(t.get("path")) for t in u.get("tests", []))
                or matches(u.get("spec_path"))}
    direct = sorted(affected)
    candidate_edges = discovery_scan(root, p)["edges"] if scan_sources else []
    source_affected = set(changed)
    while True:
        expanded_sources = source_affected | {edge["consumer"] for edge in candidate_edges if edge["producer"] in source_affected}
        if expanded_sources == source_affected: break
        source_affected = expanded_sources
    inferred_units = {u["id"] for u in units if any(e.get("path") in source_affected for e in u.get("evidence", []))} - affected
    affected |= inferred_units
    while True:
        expanded = affected | {u["id"] for u in units if set(u.get("depends_on", [])) & affected}
        if expanded == affected: break
        affected = expanded
    return {"direct": direct, "transitive": sorted(affected - set(direct)), "units": sorted(affected),
            "source_candidates": sorted(source_affected - set(changed)), "candidate_units": sorted(inferred_units),
            "candidate_edges": [edge for edge in candidate_edges if edge["producer"] in source_affected],
            "source_discovery": "scanned" if scan_sources else "NOT_ASSESSED: run impact or baseline discover explicitly",
            "requirements": sorted({u["requirement"] for u in units if u["id"] in affected and u.get("requirement")}),
            "meaning": "Declared behavior/source/test/spec dependency candidates; inspect callers and runtime configuration for missing edges."}


def behavior_anchor(root, entry):
    if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ("path", "reference", "role", "explains")):
        return False
    path = safe(root, entry["path"])
    return path.is_file() and source_reference_valid(entry["reference"], entry["path"], path.read_bytes())


def assertion_code_mask(text, suffix):
    """Mark literal/comment positions without interpreting assertion semantics."""
    masked = list(text)
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    def hide(start, end):
        for index in range(start, end):
            if masked[index] not in "\r\n":
                masked[index] = " "
    if suffix == ".py":
        ignored = {tokenize.COMMENT, tokenize.STRING}
        ignored.update(getattr(tokenize, name, -1) for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"))
        try:
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                if token.type in ignored:
                    hide(offsets[token.start[0] - 1] + token.start[1],
                         offsets[token.end[0] - 1] + token.end[1])
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return None
    elif suffix == ".rs":
        # Rust raw strings, nested block comments and lifetimes need separate handling.
        position = 0
        while position < len(text):
            start = position
            if text.startswith("//", position):
                end = text.find("\n", position)
                position = len(text) if end < 0 else end
            elif text.startswith("/*", position):
                position += 2
                depth = 1
                while position < len(text) and depth:
                    if text.startswith("/*", position):
                        depth += 1
                        position += 2
                    elif text.startswith("*/", position):
                        depth -= 1
                        position += 2
                    else:
                        position += 1
                if depth:
                    return None
            elif match := re.match(r'(?:br|cr|r)(#{0,255})"', text[position:]):
                end = text.find('"' + match.group(1), position + match.end())
                if end < 0:
                    return None
                position = end + 1 + len(match.group(1))
            elif text[position] == '"':
                match = re.match(r'"(?:\\.|[^"\\])*"', text[position:], re.S)
                if not match:
                    return None
                position += match.end()
            elif text[position] == "'" and (match := re.match(r"'(?:\\(?:u\{[0-9A-Fa-f_]+\}|x[0-9A-Fa-f]{2}|.)|[^'\\\r\n])'", text[position:])):
                position += match.end()
            else:
                position += 1
                continue
            hide(start, position)
    elif suffix in {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx",
                    ".java", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts",
                    ".cs", ".go", ".kt", ".kts", ".swift", ".m", ".mm", ".scala", ".groovy", ".dart"}:
        pattern = r'''(?:u8|[uUL])?R"(?P<delimiter>[^ ()\\\t\r\n]{0,16})\(.*?\)(?P=delimiter)"|""".*?"""|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\x60(?:\\.|[^\x60\\])*\x60|//[^\n]*|/\*.*?\*/'''
        lexical, positions = text, None
        if suffix in {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"}:
            # C/C++ joins escaped physical lines before recognizing comments.
            positions, pieces, start = [], [], 0
            for splice in re.finditer(r"\\\r?\n", text):
                pieces.append(text[start:splice.start()])
                positions.extend(range(start, splice.start()))
                start = splice.end()
            pieces.append(text[start:])
            positions.extend(range(start, len(text)))
            lexical = "".join(pieces)
            # Numeric separators are code, not character-literal openers.
            pattern = (r'(?P<raw_start>(?:u8|[uUL])?R"(?P<raw_delimiter>[^ ()\\\t\r\n]{0,16})\()|'
                       r"(?P<number_literal>\b[0-9][A-Za-z0-9_]*(?:'[A-Za-z0-9_]+)+(?:\.[A-Za-z0-9_']*)?)|" + pattern)
        scanner, position = re.compile(pattern, re.S), 0
        while match := scanner.search(lexical, position):
            position = match.end()
            if positions is not None and match.group("raw_start") is not None:
                # Phase-2 splicing is reverted within a C++ raw literal. Find its
                # actual terminator in the physical source, then skip that whole span.
                start = positions[match.start()]
                body = positions[match.end() - 1] + 1
                terminator = ")" + match.group("raw_delimiter") + '"'
                end = text.find(terminator, body)
                if end < 0:
                    return None
                end += len(terminator)
                hide(start, end)
                position = bisect_left(positions, end)
                continue
            if positions is not None and match.group("number_literal") is not None:
                continue
            hide(positions[match.start()] if positions is not None else match.start(),
                 positions[match.end() - 1] + 1 if positions is not None else match.end())
    return "".join(masked)


def behavior_assertion_valid(root, test):
    if not behavior_anchor(root, test) or test["role"] != "assertion" or Path(test["path"]).suffix.lower() not in TEST_SOURCE_SUFFIXES:
        return False
    if not all(isinstance(test.get(k), str) and test[k].strip() for k in ("input", "expected", "assertion", "detects")):
        return False
    content = safe(root, test["path"]).read_text(encoding="utf-8")
    ranges = re.findall(re.escape(test["path"]) + r":L(\d+)(?:-L?(\d+))?\b", test["reference"])
    covered = {line for a, b in ranges for line in range(int(a), int(b or a) + 1)}
    executable = assertion_code_mask(content, Path(test["path"]).suffix.lower())
    assertion = test["assertion"].strip()
    if executable is None or re.match(r"(#|//|/\*|\*)", assertion):
        return False
    # Require a complete assertion construct, not a substring of an assertion.
    # Python uses its actual parser; other languages retain bounded syntax recognition.
    if Path(test["path"]).suffix.lower() == ".py":
        try:
            tree = ast.parse(content)
            statements = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)
                          or isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                          and isinstance(node.value.func, ast.Attribute)
                          and re.fullmatch(r"assert[A-Z]\w*", node.value.func.attr)]
            return any(ast.get_source_segment(content, node) == assertion
                       and set(range(node.lineno, node.end_lineno + 1)).issubset(covered)
                       for node in statements)
        except SyntaxError:
            return False
    recognized = re.match(r"^(?:(?:\w+\.)*(?:assert\w*|ASSERT_\w+|EXPECT_\w+|CHECK|REQUIRE)\s*!?\s*\(|assert\s+)", assertion)
    recognized = recognized or re.match(r"^assert\.(?:strictEqual|deepStrictEqual|equal|deepEqual|ok|throws|rejects)\s*\(", assertion)
    recognized = recognized or (re.match(r"^expect\s*\(", assertion) and re.search(r"\)\s*\.(?:not\.)?to\w+\s*\(", assertion))
    recognized = recognized or (Path(test["path"]).suffix == ".go" and re.match(r"^if\s+", assertion)
                                and re.search(r"\{\s*(?:panic|\w+\.(?:Fatalf?|Errorf?))\s*\(", assertion))
    if not recognized:
        return False
    offsets = [0] + [match.end() for match in re.finditer("\n", content)]
    for match in re.finditer(re.escape(assertion), content):
        first, last = bisect_right(offsets, match.start()), bisect_right(offsets, match.end() - 1)
        if not executable[match.start()].isspace() and set(range(first, last + 1)).issubset(covered):
            return True
    return False


def spec_scenarios(body):
    """Content identities bind both the selecting conditions and every outcome line."""
    return [{"name": match.group(1).strip(), "sha256": digest(body[match.start():match.end()].strip().encode()),
             "body": body[match.start():match.end()].strip()}
            for match in re.finditer(r"(?ms)^#### Scenario:[ \t]*([^\n]+).*?(?=^#### Scenario:|^### |^## |\Z)", markdown_structure(body))]


def acceptance_readback_findings(unit, body):
    """Compare the two declared observations for one stimulus. Neither observation is inferred here."""
    cases = unit.get("acceptance_cases")
    if not isinstance(cases, list) or not cases:
        yield "PENDING", "behavior-case-missing", "Derive a concrete case from the Spec alone, then compare it with the effective source path."
        return
    scoped_evidence = {e["reference"] for e in unit["evidence"] if e["role"] in {"branch", "effect"}}
    outcome_lines = {line.strip() for line in body.splitlines()
                     if re.search(r"\b(?:SHALL|MUST)\b", line, re.I)
                     or re.match(r"^\s*(?:[-*]\s+)?(?:\*\*)?(?:THEN\b|AND\b|则|那么|并且)", line, re.I)}
    for index, case in enumerate(cases, 1):
        prefix = f"Acceptance case {index}: "
        if not isinstance(case, dict) or not isinstance(case.get("stimulus"), str) or not case["stimulus"].strip():
            yield "PENDING", "behavior-case-missing", prefix + "describe a concrete input and initial state."
            continue
        if case.get("status") in ("spec-ambiguous", "source-unknown"):
            yield "PENDING", "behavior-case-gap", prefix + case["status"] + " for " + case["stimulus"]
            continue
        if case.get("status") != "compared" or not {"expected", "source_outcome"}.issubset(case):
            yield "PENDING", "behavior-case-incomplete", prefix + "record the Spec prediction and source outcome for the same input."
            continue
        if json.dumps(case["expected"], sort_keys=True) != json.dumps(case["source_outcome"], sort_keys=True):
            yield "FAIL", "behavior-case-contradicted", prefix + "the Spec prediction and the source outcome disagree for " + case["stimulus"]
        quote = case.get("spec_quote")
        if not isinstance(quote, str) or not quote.strip() or quote.strip() not in outcome_lines:
            yield "PENDING", "behavior-case-spec-evidence", prefix + "cite the full outcome line from this requirement."
        premises = case.get("premises", [])
        if (not isinstance(premises, list) or not premises or quote not in premises
                or any(not isinstance(line, str) or not line.strip() or line.strip() not in body for line in premises)):
            yield "PENDING", "behavior-case-premises", prefix + "retain the exact deciding Spec premises, including the outcome; equality alone is not entailment."
        if not isinstance(case.get("source_reference"), str) or case["source_reference"] not in scoped_evidence:
            yield "PENDING", "behavior-case-source-evidence", prefix + "cite the decisive branch/effect in the unit's source evidence."


def behavior_inventory_findings(root, p, data):
    """Check explicit evidence obligations. The reviewer supplies semantics; no semantic PASS is inferred."""
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise KitError("Behavior inventory schema_version must be 1")
    if data.get("scope") not in {"whole", "limited"} or not isinstance(data.get("scope_reason"), str) or not data["scope_reason"].strip():
        raise KitError("Declare whole/limited behavior scope with a concrete rationale")
    if not isinstance(data.get("discovery"), dict) or not all(isinstance(data["discovery"].get(k), str) and data["discovery"][k].strip() for k in ("method", "source_first", "independence")):
        raise KitError("Describe actual source-first discovery separately from the generated spec outline")
    sources, units, surfaces = data.get("sources"), data.get("units"), data.get("surfaces")
    if not isinstance(sources, list) or not sources or not all(isinstance(x, str) and safe(root, x).is_file() for x in sources):
        raise KitError("Behavior inventory needs actual source/build/configuration inputs")
    if len(sources) != len(set(sources)):
        raise KitError("Duplicate inventory source")
    if not isinstance(units, list) or not units or not all(isinstance(u, dict) and isinstance(u.get("id"), str) and u["id"].strip() for u in units):
        raise KitError("Enumerate observable behavior units with stable IDs before writing specs")
    identities = [u["id"] for u in units]
    if len(identities) != len(set(identities)):
        raise KitError("Duplicate behavior ID")
    findings = []
    def add(code, message, identity=None, status="PENDING"):
        findings.append({"status": status, "code": code, "unit": identity, "message": message})
    if data["scope"] == "limited": add("behavior-limited", "Limited inventory cannot establish whole-repository behavior coverage")
    elif set(sources) != set(capability_sources(root, p)):
        add("behavior-source-scope", "Whole behavior inventory must reconcile every current production/build/config input")
    records = [{**r, "path": path.relative_to(root).as_posix()} for path in sorted(safe(root, p["paths"]["specs"]).rglob("*.md"))
               for r in spec_records(path.read_text(encoding="utf-8"), path.parent.name)]
    requirements = {r["id"]: r for r in records}
    if not isinstance(surfaces, dict) or set(surfaces) != BEHAVIOR_SURFACES:
        raise KitError("Explicitly inspect api/messages/configuration/lifecycle/computation/upgrade/storage/background applicability")
    for name, surface in surfaces.items():
        if not isinstance(surface, dict) or surface.get("status") not in {"applicable", "not-applicable", "unknown"} or not str(surface.get("reason", "")).strip():
            raise KitError("Each cross-cutting surface needs applicability and source-based reasoning")
        evidence = surface.get("evidence", [])
        if not isinstance(evidence, list) or not evidence or not all(behavior_anchor(root, e) and e["path"] in sources for e in evidence):
            raise KitError("Surface applicability needs real in-scope source evidence")
        links = surface.get("units", [])
        if not isinstance(links, list) or not set(links).issubset(identities): raise KitError("Unknown behavior in surface map")
        if surface["status"] == "unknown" or surface["status"] == "applicable" and not links:
            add("behavior-surface-gap", f"Inspect or enumerate {name} behavior; directory coverage is insufficient")
    facts, mapped, quoted = {}, set(), {}
    catalog = data.get("contract_catalog", {})
    aliases = {}
    if not isinstance(catalog, dict): raise KitError("contract_catalog must map canonical names to explicit aliases and conditions")
    for canonical, contract in catalog.items():
        if not isinstance(contract, dict) or not isinstance(contract.get("aliases", []), list) or not isinstance(contract.get("conditions", {}), dict):
            raise KitError("Contract catalog needs aliases and canonical condition mappings")
        for alias in [canonical, *contract.get("aliases", [])]:
            if not isinstance(alias, str) or not alias.strip() or alias in aliases: raise KitError("Contract aliases must be unique and nonempty")
            aliases[alias] = canonical
    for unit in units:
        identity = unit["id"]
        for key in ("capability", "trigger", "condition", "outcome", "owner"):
            if not isinstance(unit.get(key), str) or not unit[key].strip(): raise KitError(f"{identity}: describe {key}")
        if unit.get("confidence") not in {"verified", "inferred", "unknown", "defect"} or unit.get("disposition") not in {"current", "baseline", "gap"}:
            raise KitError("Separate verified/inferred/unknown/defect evidence from current/baseline/gap disposition")
        if not isinstance(unit.get("reason"), str) or not unit["reason"].strip(): raise KitError("Every preservation/exclusion/gap needs reasoning")
        dependencies = unit.get("depends_on", [])
        if not isinstance(dependencies, list) or not set(dependencies).issubset(identities) or identity in dependencies:
            raise KitError("Behavior dependencies must name other known behavior units")
        evidence = unit.get("evidence", [])
        if not isinstance(evidence, list) or not evidence or not all(behavior_anchor(root, e) and e["path"] in sources for e in evidence):
            raise KitError(f"{identity}: missing/invalid actual source anchors")
        if any(e["role"] not in {"entry", "branch", "call", "effect", "definition", "config-use"} for e in evidence):
            raise KitError("Source role must distinguish definition from executed branch/call/use/effect")
        roles = {e["role"] for e in evidence}
        if not roles & {"entry", "call", "config-use"} or not roles & {"branch", "effect"}:
            add("behavior-evidence-chain", "Trace trigger/caller/use through branch/effect; definitions and same-name symbols are insufficient", identity)
        dimensions = unit.get("dimensions", {})
        if not isinstance(dimensions, dict) or set(dimensions) != BEHAVIOR_DIMENSIONS:
            raise KitError(f"{identity}: explicitly assess all behavior dimensions")
        for name, detail in dimensions.items():
            if not isinstance(detail, dict) or detail.get("status") not in {"reviewed", "not-applicable", "unknown"} or not str(detail.get("reason", "")).strip():
                raise KitError("Each dimension needs reviewed/not-applicable/unknown and concrete reasoning")
            if detail["status"] == "unknown": add("behavior-dimension-gap", f"Unresolved {name} behavior", identity)
        requirement = unit.get("requirement")
        if unit["disposition"] == "current":
            if unit["confidence"] != "verified": add("behavior-unverified-promise", "Inferred/unknown/defect observations cannot become current normative promises", identity, "FAIL")
            if requirement not in requirements:
                add("behavior-spec-gap", "Current unit needs an existing authoritative requirement", identity)
            else:
                spec = requirements[requirement]
                mapped.add(requirement)
                quote = unit.get("normative_quote", "")
                if unit.get("spec_path") != spec["path"] or not isinstance(quote, str) or not quote.strip() or quote not in spec["body"]:
                    add("behavior-claim-drift", "Bind the actual normative clause, not merely a requirement ID", identity)
                else: quoted.setdefault(requirement, []).append(quote)
                for status, code, message in acceptance_readback_findings(unit, spec["body"]):
                    add(code, message, identity, status)
        elif requirement:
            add("behavior-gap-promoted", "Baseline/gap observations must not masquerade as current promises", identity, "FAIL")
        if unit["disposition"] == "gap" or unit["confidence"] in {"inferred", "unknown"}:
            add("behavior-unresolved", unit["reason"], identity)
        challenge = unit.get("challenge", {})
        if not isinstance(challenge, dict) or not all(isinstance(challenge.get(k), str) and challenge[k].strip() for k in ("counterexample", "alternative", "reason")) or challenge.get("result") not in {"supported", "contradicted", "unknown"}:
            raise KitError("Each unit needs an attempted counterexample, competing explanation and actual disposition")
        if challenge["result"] != "supported":
            add("behavior-counterexample", "Counterexample/alternative is unresolved; do not close this behavior", identity,
                "FAIL" if challenge["result"] == "contradicted" and unit["disposition"] == "current" else "PENDING")
        contract_facts = unit.get("contract_facts", [])
        if not isinstance(contract_facts, list): raise KitError("contract_facts must be a list")
        for fact in contract_facts:
            if not isinstance(fact, dict) or not all(isinstance(fact.get(k), str) and fact[k].strip() for k in ("key", "condition")) or "value" not in fact:
                raise KitError("Canonical contract facts need key, effective condition and typed value")
            if unit["disposition"] == "current":
                canonical = aliases.get(fact["key"], fact["key"])
                condition = catalog.get(canonical, {}).get("conditions", {}).get(fact["condition"], fact["condition"])
                if not isinstance(condition, str) or not condition.strip(): raise KitError("Canonical conditions must be nonempty names")
                if catalog and fact["key"] not in aliases:
                    add("behavior-contract-unregistered", "Reconcile this shared fact with the canonical catalog: " + fact["key"], identity)
                key = (canonical, condition)
                value = json.dumps(fact["value"], sort_keys=True, ensure_ascii=False)
                if key in facts and facts[key][0] != value:
                    add("behavior-contract-conflict", f"Conflicting {key} with {facts[key][1]}; reconcile actual applicability/contract", identity, "FAIL")
                else: facts[key] = (value, identity)
        verification = unit.get("verification", "unverified")
        if verification not in {"automated", "manual", "external", "unverified"}: raise KitError("Unknown assertion verification mode")
        tests = unit.get("tests", [])
        if not isinstance(tests, list): raise KitError("Assertion tests must be a list")
        if unit["disposition"] == "current":
            if requirement in requirements:
                declared = re.search(r"(?im)^Verification:\s*(automated|manual|external)\b", requirements[requirement]["body"])
                if declared and verification != declared.group(1).lower():
                    add("behavior-verification-conflict", "Assertion mode conflicts with authoritative Spec", identity, "FAIL")
            checks = {c["name"] for c in p["checks"] if c.get("required", True) and "delivery" in c.get("phases", ["ready", "delivery"])
                      and c.get("type", "command") == ("command" if verification == "automated" else verification)}
            if verification == "automated" and not tests:
                add("behavior-assertion-missing", "Automated claim needs an actual test assertion, input and expected outcome", identity)
            if verification == "unverified": add("behavior-verification-gap", "No actual verification method established", identity)
            if verification in {"manual", "external"} and (not str(unit.get("verification_reason", "")).strip() or not set(unit.get("checks", [])) or not set(unit["checks"]).issubset(checks)):
                add("behavior-manual-gap", "Manual/external claims need justified method and required evidence check; a mock limitation is not validation", identity)
            for test in tests:
                if not behavior_anchor(root, test) or not any(under(test["path"], prefix) for prefix in p["test_paths"]):
                    raise KitError("Assertion evidence needs valid actual test-source lines under mapped test roots")
                if Path(test["path"]).suffix.lower() not in TEST_SOURCE_SUFFIXES:
                    raise KitError("Assertion references cannot be README/fixture/coverage tables")
                if not all(isinstance(test.get(k), str) and test[k].strip() for k in ("input", "expected", "assertion", "detects")):
                    raise KitError("Describe actual test input/expected/assertion and why a wrong implementation would fail")
                if not behavior_assertion_valid(root,test):
                    add("behavior-test-comment", "Assertion must occur in the selected executable lines; an ID/comment is only navigation", identity)
                if not isinstance(test.get("checks"), list) or not test["checks"] or not set(test["checks"]).issubset(checks):
                    add("behavior-test-command", "Assertion needs actual required automated command mapping", identity)
    for identifier in sorted(set(requirements) - mapped):
        add("behavior-requirement-unmapped", f"Current requirement {identifier} lacks a behavior/claim review")
        findings[-1]["path"] = requirements[identifier]["path"]
    for identifier in sorted(mapped):
        for clause in re.findall(r"(?im)^[^\n]*\b(?:SHALL|MUST)\b[^\n]*", requirements[identifier]["body"]):
            if not any(clause.strip() in quote for quote in quoted.get(identifier, [])):
                add("behavior-clause-unmapped", f"{identifier}: normative clause lacks an actual behavior review: {clause.strip()}")
                findings[-1]["path"] = requirements[identifier]["path"]
        cases = [case for unit in units if unit.get("requirement") == identifier
                 and unit.get("disposition") == "current" for case in unit.get("acceptance_cases", [])
                 if isinstance(case, dict) and case.get("status") == "compared"]
        for scenario in spec_scenarios(requirements[identifier]["raw"]):
            bindings = [binding for case in cases for binding in case.get("scenarios", []) if isinstance(binding, dict)]
            if not any(binding.get("name") == scenario["name"] and binding.get("sha256") == scenario["sha256"] for binding in bindings):
                add("behavior-scenario-unmapped", f"{identifier}: review this complete Scenario's conditions/outcomes: {scenario['name']}")
                findings[-1]["path"] = requirements[identifier]["path"]
    return findings


def behavior_inputs(root, p, data, document):
    paths = set(data["sources"]) | {document, POLICY}
    paths.update(path.relative_to(root).as_posix() for path in safe(root, p["paths"]["specs"]).rglob("*.md"))
    for unit in data["units"]:
        paths.update(test["path"] for test in unit.get("tests", []))
    return {name: digest(safe(root, name).read_bytes()) if safe(root, name).is_file() else None for name in sorted(paths)}


def behavior_record(root, p, document, reviewer):
    if not reviewer.strip(): raise KitError("Identify the actual behavior reviewer")
    data = read_json(safe(root, document))
    findings = behavior_inventory_findings(root, p, data)
    previous, _ = behavior_data(root, p)
    transitions = []
    old_units = previous.get("unit_states", {})
    for unit in data["units"]:
        prior = old_units.get(unit["id"])
        if prior and prior.get("verification") == "automated" and unit.get("verification") != "automated":
            transition = unit.get("verification_change", {})
            if not isinstance(transition, dict) or not all(isinstance(transition.get(k), str) and transition[k].strip() for k in ("reason", "alternatives", "remaining_gap", "reviewer")):
                raise KitError("Automated verification downgrade needs reason, attempted alternatives, remaining gap and actual reviewer")
            transitions.append({"id": unit["id"], "from": "automated", "to": unit.get("verification"), **transition})
    removed = sorted(set(old_units) - {u["id"] for u in data["units"]})
    if removed:
        dispositions = data.get("removed_units", {})
        if not isinstance(dispositions, dict) or any(not isinstance(dispositions.get(i), str) or not dispositions[i].strip() for i in removed):
            raise KitError("Removed behavior units need explicit dispositions; do not shrink the coverage denominator silently")
    record = {"schema_version": 1, "document": document, "reviewer": reviewer, "recorded_at": now(),
              "source_revision": (git(root, "rev-parse", "HEAD", optional=True) or b"").decode().strip() or None,
              "production_sources": capability_sources(root, p), "inputs": behavior_inputs(root, p, data, document),
              "unit_states": {u["id"]: {"verification": u.get("verification"), "disposition": u["disposition"]} for u in data["units"]},
              "unit_inputs": {u["id"]: {name: digest(safe(root, name).read_bytes()) if safe(root, name).is_file() else None
                                        for name in {e["path"] for e in u.get("evidence", []) + u.get("tests", [])} | {u.get("spec_path") or POLICY}} for u in data["units"]},
              "unit_sha256": {u["id"]: digest(dump(u).encode()) for u in data["units"]},
              "verification_changes": transitions, "previous_record": digest(dump(previous).encode()) if previous else None,
              "level": "declared-behavior-evidence-review"}
    snapshot = evidence_root(p) + "/behaviors/" + digest(dump(record).encode())
    transact(root, {".ai/behavior-review.json": dump(record), snapshot + "/record.json": dump(record), snapshot + "/inventory.json": dump(data)})
    return behavior_status(root, p)


def behavior_status(root, p):
    record, data = behavior_data(root, p)
    if not record or not data:
        return {"status": "PENDING", "findings": [{"status": "PENDING", "code": "behavior-inventory-missing", "message": "Discover behavior units from source, then map claims/branches/tests; a file/capability map is insufficient."}],
                "coverage": {"discovered_units": 0, "reviewed_units": 0, "ratio": None}, "execution": "NOT_ASSESSED"}
    changed = [name for name, expected in record["inputs"].items() if not safe(root, name).is_file() or digest(safe(root, name).read_bytes()) != expected]
    try:
        findings = behavior_inventory_findings(root, p, data)
    except KitError as exc:
        findings = [{"status": "PENDING" if changed else "FAIL", "code": "behavior-evidence-invalid", "message": str(exc)}]
    if changed or record["production_sources"] != capability_sources(root, p):
        findings.append({"status": "PENDING", "code": "behavior-evidence-stale", "changed": changed,
                         "message": "Source/spec/test/policy/inventory changed or production files added/removed; re-open affected evidence before recording again."})
    pending = {x.get("unit") for x in findings}
    total = len(data["units"])
    reviewed = sum(u["confidence"] in {"verified", "defect"} and u["disposition"] != "gap" and u["id"] not in pending for u in data["units"])
    stale_units = set()
    if changed or any(x["code"] == "behavior-evidence-stale" for x in findings):
        if not record.get("unit_inputs") or POLICY in changed:
            stale_units = {u["id"] for u in data["units"]}
        else:
            changed_sources = set(record["production_sources"]) ^ set(capability_sources(root, p))
            stale_units = set(behavior_impact(root, p, list(set(changed) | changed_sources))["units"])
            for unit in data["units"]:
                if record.get("unit_sha256", {}).get(unit["id"]) != digest(dump(unit).encode()): stale_units.add(unit["id"])
                if any(not safe(root, name).is_file() or digest(safe(root, name).read_bytes()) != expected
                       for name, expected in record["unit_inputs"].get(unit["id"], {}).items()): stale_units.add(unit["id"])
        reviewed = sum(u["confidence"] in {"verified", "defect"} and u["disposition"] != "gap" and u["id"] not in pending | stale_units for u in data["units"])
    return {"status": overall(findings, []), "findings": findings, "source_revision": record["source_revision"],
            "coverage": {"discovered_units": total, "reviewed_units": reviewed, "ratio": reviewed / total,
                         "current_units": sum(u["disposition"] == "current" for u in data["units"]),
                         "unresolved_units": sum(u["disposition"] == "gap" or u["confidence"] in {"unknown", "inferred"} for u in data["units"])},
            "stale_units": sorted(stale_units), "verification_changes": record.get("verification_changes", []), "execution": "NOT_ASSESSED",
            "meaning": "Coverage of the declared source-derived inventory only; neither complete behavior discovery, semantic certification nor executed assertion coverage. Review actual assertion quality and run native checks separately."}


def behavior_candidate_inputs(root, p, change, report):
    record, data = behavior_data(root, p)
    return {"fingerprint": fingerprint(root, p, change), "report_sha256": digest(safe(root, report).read_bytes()),
            "baseline_review_sha256": digest(dump(record).encode()),
            "baseline_inventory_sha256": digest(dump(data).encode())}


def behavior_candidate_record(root, p, change, report, reviewer):
    """A reviewed active delta may intentionally differ from the unarchived current spec."""
    directory, metadata = change_at(root, p, change)
    if not reviewer.strip() or directory.parent.name == "archive": raise KitError("Review an actual active change")
    audits = baseline_audit_status(root, p, report)
    if audits["status"] != "PASS": raise KitError("Candidate review requires a current closed two-pass source audit")
    data = read_json(safe(root, report))
    review = data.get("behavior_change", {})
    rows = review.get("units", [])
    record, inventory = behavior_data(root, p)
    if not record or not isinstance(rows, list) or not rows: raise KitError("Review affected and newly discovered units explicitly")
    affected = set(behavior_impact(root, p, metadata["scope"])["units"])
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in rows): raise KitError("Candidate units need IDs")
    if len({row["id"] for row in rows}) != len(rows) or not affected.issubset({row["id"] for row in rows}):
        raise KitError("Candidate review must retain every affected/transitive behavior unit")
    source_scope = {name for name in capability_sources(root, p) if any(under(name, path) for path in metadata["scope"])}
    source_scope.update(e["path"] for u in inventory.get("units", []) if u["id"] in affected for e in u.get("evidence", []) if safe(root, e["path"]).is_file())
    source_scope.update(t["path"] for u in inventory.get("units", []) if u["id"] in affected for t in u.get("tests", []) if safe(root,t["path"]).is_file())
    if not source_scope.issubset(set(audits["reports"][0]["files"])): raise KitError("Candidate audit omits affected/new production sources")
    targets = review.get("targets", [])
    if not isinstance(targets, list) or not targets or not all(isinstance(path, str) and safe(root,path).is_file() and under(path, directory.relative_to(root).as_posix()) for path in targets):
        raise KitError("Candidate review needs actual native Change target artifacts")
    actual_targets = {path.relative_to(root).as_posix() for path in directory.glob('specs/**/*.md')}
    actual_targets.update((directory/name).relative_to(root).as_posix() for name in ('proposal.md','design.md','tasks.md') if (directory/name).is_file())
    if not actual_targets.issubset(set(targets)): raise KitError("Review ALL actual native proposal/design/tasks/delta targets, including newly added targets")
    required_artifacts = set(targets) | {record["document"]} | {u["spec_path"] for u in inventory.get("units", []) if u["id"] in affected and u.get("spec_path")}
    if not required_artifacts.issubset(set(audits["reports"][0]["artifacts"])): raise KitError("Audit actual targets, current affected specs and behavior inventory")
    if not str(review.get("contract_consistency", "")).strip(): raise KitError("Review current/target canonical contract differences explicitly")
    pending, evidence_sources = [], set()
    old_units={u["id"]:u for u in inventory.get("units",[])}
    deltas=[r for path in directory.glob('specs/**/*.md') for r in spec_records(path.read_text(encoding='utf-8'),path.parent.name)]
    for row in rows:
        if row.get("outcome") not in {"preserved", "intentional-change", "new", "removed", "unresolved"} or not all(isinstance(row.get(k),str) and row[k].strip() for k in ("reason", "counterexample", "assertion_review")):
            raise KitError("Candidate behavior needs preservation/target disposition, counterexample and actual assertion review")
        evidence = row.get("evidence", [])
        if not isinstance(evidence,list) or not evidence or not all(behavior_anchor(root,e) for e in evidence): raise KitError("Candidate units need actual effective-path anchors")
        roles={e["role"] for e in evidence}
        if row["outcome"]!="removed" and (not roles & {"entry","call","config-use"} or not roles & {"branch","effect"}): raise KitError("Candidate review needs actual entry/use and branch/effect evidence")
        evidence_sources.update(e["path"] for e in evidence)
        tests=row.get("tests",[])
        old=old_units.get(row["id"],{})
        if row["outcome"] in {"removed","intentional-change"} and old.get("requirement"):
            if not any(r["id"]==old["requirement"] and r["section"] in ({"REMOVED"} if row["outcome"]=="removed" else {"MODIFIED","REMOVED"}) for r in deltas):
                raise KitError("Removal/intentional change of a current promise needs its actual native delta")
        verification=row.get("verification",old.get("verification","automated"))
        if row["outcome"] == "unresolved":
            pending.append(row["id"])
            continue
        if row["outcome"] != "removed" and verification=="automated":
            if not isinstance(tests,list) or not tests or not all(behavior_assertion_valid(root,t) and any(under(t["path"],prefix) for prefix in p["test_paths"]) for t in tests):
                raise KitError("Candidate assertions need actual current test snippets, stimuli and expected outcomes")
            checks={c["name"] for c in p["checks"] if c.get("type","command")=="command" and c.get("required",True) and "delivery" in c.get("phases",["ready","delivery"])}
            if any(not isinstance(t.get("checks"),list) or not t["checks"] or not set(t["checks"]).issubset(checks) for t in tests): raise KitError("Map actual candidate assertions to required native delivery checks")
            if not {t["path"] for t in tests}.issubset(set(audits["reports"][0]["files"])): raise KitError("Audit actual candidate test sources in both passes")
        elif row["outcome"] != "removed" and verification in {"manual","external"}:
            checks={c["name"] for c in p["checks"] if c.get("type")==verification and c.get("required",True) and "delivery" in c.get("phases",["ready","delivery"])}
            if not str(row.get("verification_reason","")).strip() or not row.get("checks") or not set(row["checks"]).issubset(checks): raise KitError("Manual/external candidate review needs justified required delivery checks")
            evidence=row.get("verification_artifacts",[])
            if not isinstance(evidence,list) or not evidence or not set(evidence).issubset(set(audits["reports"][0]["artifacts"])): raise KitError("Audit actual manual/external procedure/evidence artifacts")
            if old.get("verification")=="automated":
                transition=row.get("verification_change",{})
                if not all(isinstance(transition.get(k),str) and transition[k].strip() for k in ("reason","alternatives","remaining_gap","reviewer")): raise KitError("Candidate verification downgrade needs actual reason, alternatives, remaining gap and reviewer")
        elif row["outcome"] != "removed": pending.append(row["id"])
    new_sources = (source_scope & set(capability_sources(root,p))) - set(record["production_sources"])
    if not new_sources.issubset(evidence_sources): raise KitError("Discover observable behavior in newly added sources")
    result = {"schema_version":1,"change":change,"report":report,"reviewer":reviewer,"pending_units":pending,
              "inputs":behavior_candidate_inputs(root,p,change,report),"recorded_at":now(),
              "meaning":"Declared candidate source/target/assertion review; actual delivery tests remain mandatory. Refresh current baseline after native synchronization/archive."}
    transact(root,{(directory/'behavior-review.json').relative_to(root).as_posix():dump(result)})
    return {"status":"PENDING" if pending else "PASS",**result}


def behavior_scope_findings(root, p, scope, change=None):
    record, data = behavior_data(root,p)
    if not record: return []  # Explicit upgrade/onboarding introduces this protocol; no implicit asset rewrite.
    status = behavior_status(root,p)
    affected = set(behavior_impact(root,p,scope)["units"])
    def matches(path): return any(under(path,s) for s in scope)
    production = capability_sources(root,p)
    changed_sources = {name for name in set(production)|set(record["production_sources"]) if production.get(name)!=record["production_sources"].get(name) and matches(name)}
    if change:
        directory,_=change_at(root,p,change)
        candidate=read_json(directory/'behavior-review.json',{})
        if candidate and safe(root,candidate["report"]).is_file() and not candidate.get("pending_units"):
            if candidate.get("inputs")==behavior_candidate_inputs(root,p,change,candidate["report"]) and baseline_audit_status(root,p,candidate["report"])["status"]=="PASS":
                return []
    findings = [item for item in status["findings"] if item.get("unit") in affected or item.get("path") and matches(item["path"]) or item["code"]=="behavior-evidence-invalid"]
    stale = [item for item in status["findings"] if item["code"] == "behavior-evidence-stale"]
    if changed_sources or affected and stale:
        findings.append({"status":"PENDING","code":"behavior-impact-stale","paths":sorted(changed_sources),
                         "message":"Review affected/new behavior from source. Refresh current baseline, or record a two-pass candidate target review before delivery; native archive owns current-spec synchronization."})
    return findings


def engineering_status(root, p):
    """Read-only readiness, not dependency installation or a successful build declaration."""
    inventory = inventory_files(root, p)
    stacks = {"C/C++": {".c", ".cpp", ".cc", ".cxx"}, "Java": {".java"}, "Python": {".py"}}
    ranges = []
    for name, suffixes in stacks.items():
        source = [path for path in inventory if Path(path).suffix.lower() in suffixes and not any(under(path, t) for t in p["test_paths"])]
        tests = [path for path in inventory if Path(path).suffix.lower() in suffixes and any(under(path, t) for t in p["test_paths"])]
        if source: ranges.append({"stack": name, "source_files": len(source), "test_source_files": len(tests), "test_roots": p["test_paths"]})
    commands = []
    for check in p["checks"]:
        argv = check.get("argv", [])
        executable = argv[0].replace("{python}", sys.executable) if argv else None
        location = shutil.which(executable) if executable else None
        if executable and ("/" in executable or "\\" in executable):
            cwd = root if check.get("cwd", ".") == "." else safe(root, check["cwd"])
            candidate = Path(executable) if Path(executable).is_absolute() else cwd / executable
            location = str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None
        commands.append({"name": check["name"], "type": check.get("type", "command"), "argv": argv,
                         "cwd": check.get("cwd", "."), "executable_available": bool(location),
                         "required": check.get("required", True), "execution": "NOT_RUN"})
    findings = [{"status": "PENDING", "code": "engineering-test-stack-gap", "message": f"No mapped executable test sources for {r['stack']}; inspect native/custom test roots and behavior needs"} for r in ranges if not r["test_source_files"]]
    findings += [{"status": "PENDING", "code": "engineering-command-unavailable", "message": c["name"]} for c in commands if c["type"] == "command" and not c["executable_available"]]
    if not commands: findings.append({"status": "PENDING", "code": "engineering-checks-missing", "message": "Confirm native commands; suggested commands are not verification"})
    return {"status": overall(findings, []), "ranges": ranges, "checks": commands, "findings": findings,
            "python": sys.version.split()[0], "platform": sys.platform, "execution": "NOT_RUN",
            "meaning": "Mapped source/test/tool readiness only. Redis/DB/network/native libraries, command semantics, build patches and actual execution need separate reproducible evidence."}


def openspec_applicable(root, p):
    return under(p["paths"]["specs"], "openspec") or safe(root, "openspec/config.yaml").exists()


def openspec_config_text(root, p, facts):
    """Generate the supported schema using JSON-quoted YAML scalars; no guessed product facts."""
    context = [f"Project: {root.name}"]
    for name in ("purpose", "stack", "boundaries", "constraints", "workflow", "precedence"):
        context.append(f"{name}: {facts.get(name, 'Not established; source review required.')}")
    context += [f"Current specifications: {p['paths']['specs']}", f"Engineering authority: {p['paths'].get('standard', 'docs/engineering-standard.md')}",
                "Source/Baseline are evidence. Current specifications state accepted observable behavior. Active deltas are proposed changes."]
    rules = {
        "proposal": ["Explain why, changed behavior, included/excluded scope, impact and compatibility; cite actual evidence and relevant decisions. Use the repository Change and its policy.artifact_rules with any development entry."],
        "specs": ["Preserve existing requirement IDs; state observable normative behavior with concrete normal/error/boundary scenarios.",
                  "Discover observable cross-module behavior before selecting spec boundaries; require effective source-path evidence, attempted counterexamples and actual assertion mappings. Unknowns/defects do not automatically become current promises.",
                  "Draft a concrete acceptance case from the spec alone. For existing behavior compare its predicted result with the reachable source branch for that same input. For proposed behavior use the approved target as the expected result.",
                  "Define the behavior in the current Spec or delta. Link stable Baseline contracts for provenance. Keep implementation and test line locations in Baseline or audit evidence."],
        "design": ["Document implementation for new dependencies, concurrency/data models and cross-module interfaces; preserve consequential decisions in ADRs."],
        "tasks": ["Include applicable characterization/regression/acceptance, actual verification evidence and native specification synchronization/archive; missing execution stays pending."]}
    lines = ["# Project configuration; source/content review is recorded separately.", "schema: spec-driven", "", "context: |"]
    for value in context:
        lines.extend("  " + line for line in value.splitlines())
    lines += ["", "rules:"]
    for kind, values in rules.items():
        lines.append("  " + kind + ":")
        lines.extend("    - " + json.dumps(value, ensure_ascii=False) for value in values)
    return "\n".join(lines) + "\n"


def openspec_sections(text):
    # A bounded content guard, not a general YAML parser. Native CLI validation is separate.
    lines = text.splitlines()
    keys = [(i, m.group(1)) for i, line in enumerate(lines) if (m := re.match(r"^([A-Za-z][\w-]*):", line))]
    result = {}
    for n, (start, key) in enumerate(keys):
        end = keys[n + 1][0] if n + 1 < len(keys) else len(lines)
        if key in result:
            raise KitError("Duplicate OpenSpec top-level key: " + key)
        result[key] = "\n".join(lines[start:end])
    return result


def openspec_config_findings(root, p):
    if not openspec_applicable(root, p):
        return []
    path = safe(root, "openspec/config.yaml")
    def issue(code, message):
        return {"status": "PENDING", "code": code, "path": "openspec/config.yaml", "message": message}
    if not path.is_file() or not path.read_bytes().strip():
        return [issue("openspec-config-missing", "Write project schema, context and artifact rules; an unavailable CLI does not exempt configuration content.")]
    text = path.read_text(encoding="utf-8")
    try:
        sections = openspec_sections(text)
    except KitError as exc:
        return [issue("openspec-config-content", str(exc))]
    missing = []
    for key in ("schema", "context", "rules"):
        value = sections.get(key, "").split(":", 1)[-1]
        content = "\n".join(line for line in value.splitlines() if line.strip() and not line.lstrip().startswith("#")).strip()
        if content in {"", "|", ">", "{}", "[]", "null", "~", "''", '\"\"'} or FILL in content or re.search(r"\{\{\w+\}\}|<project[-_]name>|YOUR_PROJECT", content):
            missing.append(key)
    if missing:
        return [issue("openspec-config-content", "Fill substantive project configuration: " + ", ".join(missing))]
    context_lines = sections["context"].split(":", 1)[-1].splitlines()
    substantive = [line.strip().strip("\"'") for line in context_lines
                   if line.strip() and line.strip() not in {"|", ">", "|-", ">-"} and not line.lstrip().startswith("#")]
    if substantive and all(re.match(r"(?i)^(?:language|framework|schema|locale|stack|technology|语言|框架|技术栈)\s*:", line) for line in substantive):
        return [issue("openspec-config-content", "Framework/language alone is not project context; explain actual project responsibility, boundaries and authority.")]
    findings = []
    if re.search(r"^schema:\s*['\"]?spec-driven['\"]?\s*(?:#.*)?$", sections.get("schema", ""), re.MULTILINE):
        for key in ("proposal", "specs", "design", "tasks"):
            if not re.search(r"(?m)^\s+" + key + r":\s*\n\s+-\s*\S", sections["rules"]):
                findings.append(issue("openspec-config-rules", "Review actual spec-driven artifact rules for " + key))
    record = read_json(safe(root, ".ai/openspec-review.json"), {})
    if not record:
        findings.append(issue("openspec-config-unreviewed", "Review configuration against current project facts/rules; record actual review, not merely CLI initialization."))
    elif any(not safe(root, name).is_file() or digest(safe(root, name).read_bytes()) != expected for name, expected in record.get("inputs", {}).items()):
        findings.append(issue("openspec-config-stale", "Configuration, project facts, authority or policy changed; reconcile and re-review."))
    return findings


def openspec_record(root, p, reviewer):
    if not openspec_applicable(root, p):
        raise KitError("No OpenSpec authority/configuration is established; preserve the existing mapped workflow")
    if not reviewer.strip():
        raise KitError("Name the actual configuration reviewer")
    issues = openspec_config_findings(root, p)
    blocking = [x for x in issues if x["code"] not in {"openspec-config-unreviewed", "openspec-config-stale"}]
    if blocking:
        raise KitError(blocking[0]["message"])
    entry = entry_status(root, p)
    if any(x["code"] != "project-entry-gaps" for x in entry["findings"]):
        raise KitError("Review current source-backed project facts before reviewing OpenSpec configuration")
    facts = read_json(safe(root, ".ai/project-entry.json"))
    paths = ["openspec/config.yaml", "AGENTS.md", ".ai/project-entry.json", POLICY, p["paths"].get("standard", "docs/engineering-standard.md"), *facts["source_evidence"]]
    record = {"reviewer": reviewer, "recorded_at": now(), "inputs": {name: digest(safe(root, name).read_bytes()) for name in paths},
              "level": "agent-declared-configuration-content-review", "native_validation": "NOT_ASSESSED",
              "meaning": "Actual Agent must check YAML syntax, schema compatibility, factual context and consistency with authority; bounded guards/hashes cannot certify those semantics."}
    transact(root, {".ai/openspec-review.json": dump(record)})
    return {"status": "PASS", **record}


def openspec_refresh(root, p):
    if not openspec_applicable(root, p):
        raise KitError("Preserve the established non-OpenSpec workflow; no OpenSpec configuration is applicable")
    path = safe(root, "openspec/config.yaml")
    owned = read_json(safe(root, ".ai/openspec-generated.json"), {})
    if path.exists() and path.read_bytes().strip() and digest(path.read_bytes()) != owned.get("sha256"):
        raise KitError("Existing native/human OpenSpec configuration preserved. Reconcile it in place, retaining schema/rules/comments, then use openspec record --reviewer; do not overwrite or ask a routine tooling-choice question.")
    facts = read_json(safe(root, ".ai/project-entry.json"))
    if not facts:
        raise KitError("Curate project-entry facts before configuration refresh")
    # Validate facts and their currency before writing configuration.
    if any(x["code"] != "project-entry-gaps" for x in entry_status(root, p)["findings"]):
        raise KitError("Refresh reviewed project-entry evidence first")
    text = openspec_config_text(root, p, facts)
    transact(root, {"openspec/config.yaml": text, ".ai/openspec-generated.json": dump({"sha256": digest(text.encode())})})
    return {"status": "PENDING", "path": "openspec/config.yaml", "meaning": "Configuration generated from project facts; inspect syntax/schema/context/rules against project authority, then openspec record --reviewer with the actual reviewer. Native validation is separate."}


def baseline_orphan_findings(root, p, scope=None):
    """Discover current contract files and referenced contracts independently of the registry."""
    base = p["paths"]["baseline"]
    registered = read_json(safe(root, base + "/knowledge.json"), {"documents": {}})["documents"]
    candidates, referenced = set(), set()
    for path in safe(root, base).rglob("*.md"):
        name = path.relative_to(root).as_posix()
        if under(name, base + "/raw") or under(name, evidence_root(p)) or path.name.lower() == "readme.md":
            continue
        text = safe(root, name).read_text(encoding="utf-8")
        front = re.match(r"\A---\s*\n(.*?)\n---", text.lstrip("\ufeff"), re.DOTALL)
        native_contract = bool(front and re.search(r"(?m)^kind:\s*['\"]?contract['\"]?\s*$", front.group(1)))
        if under(name, base + "/contracts") or native_contract or knowledge_sections_present(p, "contract", text):
            candidates.add(name)
    for spec in safe(root, p["paths"]["specs"]).rglob("*.md"):
        for value in re.findall(r"(?im)^(?:Baseline|Source):\s*`?([^\s`]+)", spec.read_text(encoding="utf-8")):
            value = re.sub(r":L\d+(?:-L\d+)?$", "", value.split("#", 1)[0])
            if under(value, base) and safe(root, value).is_file() and value.endswith(".md"):
                text = safe(root, value).read_text(encoding="utf-8")
                if under(value, base + "/contracts") or knowledge_sections_present(p, "contract", text):
                    candidates.add(value)
                    referenced.add(value)
    return [{"status": "FAIL" if name in referenced else "PENDING", "code": "baseline-contract-unregistered", "path": name,
             "message": "Current specification references an unregistered contract; register and source-audit it." if name in referenced else "Contract exists outside the declared knowledge registry; explain/register its scope before claiming whole coverage."}
            for name in sorted(candidates - set(registered)) if not scope or any(under(name, prefix) for prefix in scope)]


BASELINE_INDEX_START = "<!-- agent-repo-kit:baseline-index:start -->"
BASELINE_INDEX_END = "<!-- agent-repo-kit:baseline-index:end -->"


def baseline_index_text(root, p):
    documents = knowledge_status(root, p)["documents"]
    lines = [BASELINE_INDEX_START, "## Current source-backed knowledge", "", "Generated navigation from current declarations and file freshness. Static review is not business-test execution.", "", "| Document | Kind | State | Evidence freshness | Current requirements |", "| --- | --- | --- | --- | --- |"]
    for item in sorted(documents, key=lambda x: x["document"]):
        link = os.path.relpath(item["document"], p["paths"]["baseline"]).replace(os.sep, "/")
        lines.append(f"| [{Path(item['document']).name}](<{link}>) | {item['kind']} | {item['state']} | {item['freshness']} | {', '.join(item.get('promoted_to', [])) or '—'} |")
    if not documents:
        lines.append("| No knowledge registered | — | pending | — | — |")
    lines += ["", "Unregistered contract scope:"]
    lines += ["- `" + item["path"] + "`: " + item["status"] for item in baseline_orphan_findings(root, p)] or ["- None discovered by the bounded contract scan; semantic capability completeness still requires source review."]
    lines += ["", "Current specifications: `" + p["paths"]["specs"] + "`. Use baseline spec-status / coverage-status / audit-status and onboarding-status --record after final edits.", BASELINE_INDEX_END]
    return "\n".join(lines) + "\n"


def baseline_index_refresh(root, p):
    path = safe(root, p["paths"]["baseline"] + "/README.md")
    old = path.read_bytes().decode("utf-8") if path.is_file() else "# Baseline\n\n"
    scaffold = "# Baseline\n\n" + ("Existing repository: inventory is pending review. Use baseline-repo; inventory alone is not an approved baseline.\n" if p["mode"] == "existing" else "New repository: no historical system is asserted. Build specifications from real requirements.\n")
    if old == scaffold:
        old = "# Baseline\n\n"
    if old.count(BASELINE_INDEX_START) != old.count(BASELINE_INDEX_END) or old.count(BASELINE_INDEX_START) > 1:
        raise KitError("Malformed Baseline navigation markers; preserve/merge human content before refresh")
    content = baseline_index_text(root, p)
    if BASELINE_INDEX_START in old:
        updated = old[:old.index(BASELINE_INDEX_START)] + content.rstrip("\n") + old[old.index(BASELINE_INDEX_END) + len(BASELINE_INDEX_END):]
    else:
        updated = old + ("\n" if old and not old.endswith("\n") else "") + "\n" + content
    transact(root, {p["paths"]["baseline"] + "/README.md": updated})
    return {"status": "PASS", "meaning": "Navigation refreshed; no new semantic review/test execution asserted."}


def baseline_index_findings(root, p):
    path = safe(root, p["paths"]["baseline"] + "/README.md")
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    expected = baseline_index_text(root, p).strip()
    if text.count(BASELINE_INDEX_START) != 1 or text.count(BASELINE_INDEX_END) != 1 or expected not in text:
        return [{"status": "PENDING", "code": "baseline-index-stale", "message": "Refresh Baseline navigation against actual current/retired/stale and unregistered knowledge; preserve native prose."}]
    return []


def source_case_status(root, p, map_record, coverage, behaviors):
    """Reconcile declared source-side questions with independently recorded Spec readbacks."""
    findings = []
    if not map_record or any(f["code"] == "capability-map-stale" for f in coverage["findings"]):
        return {"status": "PENDING", "registered": None, "answered": None, "findings": [
            {"status": "PENDING", "code": "source-case-map-unavailable", "message": "Record a current source capability map to establish the question set."}]}
    capabilities = read_json(safe(root, map_record["document"]))["capabilities"]
    answers = {}
    unavailable = {"behavior-inventory-missing", "behavior-evidence-invalid", "behavior-evidence-stale"}
    if not any(f["code"] in unavailable for f in behaviors["findings"]):
        _, inventory = behavior_data(root, p)
        bodies = {(record["id"], path.relative_to(root).as_posix()): record["body"]
                  for path in safe(root, p["paths"]["specs"]).rglob("*.md")
                  for record in spec_records(path.read_text(encoding="utf-8"), path.parent.name)}
        for unit in inventory["units"]:
            requirement = unit.get("requirement")
            body = bodies.get((requirement, unit.get("spec_path")))
            if not body or unit["disposition"] != "current" or unit["confidence"] != "verified":
                continue
            cases = unit.get("acceptance_cases")
            if not isinstance(cases, list):
                continue
            for case in cases:
                if not isinstance(case, dict) or not isinstance(case.get("stimulus"), str):
                    continue
                valid = not any(acceptance_readback_findings({**unit, "acceptance_cases": [case]}, body))
                answers.setdefault((requirement, case["stimulus"]), []).append((case, valid))
    registered = answered = 0
    for capability in capabilities:
        if capability["kind"] != "business":
            continue
        cases = capability.get("source_cases", [])
        if not cases:
            findings.append({"status": "PENDING", "code": "source-case-sample-missing", "capability": capability["id"],
                             "message": "Capture representative observable inputs and outcomes from source for this business capability."})
        for case in cases:
            registered += 1
            matches = [answer for req in capability.get("requirements", []) for answer in answers.get((req, case["stimulus"]), [])]
            compared = [answer for answer, _ in matches if answer.get("status") == "compared"]
            outcome = dump(case["source_outcome"])
            wrong = any(dump(answer[field]) != outcome for answer in compared
                        for field in ("expected", "source_outcome") if field in answer)
            if matches and all(valid for _, valid in matches) and not wrong:
                answered += 1
                continue
            findings.append({"status": "FAIL" if wrong else "PENDING",
                             "code": "source-case-contradicted" if wrong else "source-case-unanswered",
                             "capability": capability["id"], "case": case["id"],
                             "message": "Compare this exact input using current authoritative Spec wording and the recorded source outcome."})
    return {"status": overall(findings, []) if registered or findings else "NOT_APPLICABLE",
            "registered": registered, "answered": answered, "findings": findings,
            "meaning": "Declared static answers for the recorded source sample. Sampling independence, exhaustiveness and runtime behavior require separate evidence."}


def onboarding_inputs(root, p):
    paths = {POLICY, MANIFEST, "AGENTS.md", ".ai/project-entry.json", ".ai/project-entry-review.json", ".ai/capability-coverage-review.json", ".ai/openspec-review.json", "openspec/config.yaml", p["paths"]["baseline"] + "/README.md", p["paths"]["baseline"] + "/knowledge.json", p["paths"]["baseline"] + "/audits.json"}
    paths.update(capability_sources(root, p))
    coverage_recorded = read_json(safe(root, ".ai/capability-coverage-review.json"), {})
    if coverage_recorded:
        paths.add(coverage_recorded["document"])
    behavior_review, _ = behavior_data(root, p)
    paths.add(".ai/behavior-review.json")
    paths.update(behavior_review.get("inputs", {}))
    paths.update(read_json(safe(root, MANIFEST), {}).get("files", {}))
    paths.update([p["paths"].get("standard", "docs/engineering-standard.md"), p["paths"].get("context", "docs/project-context.md")])
    for review in (".ai/project-entry-review.json", ".ai/openspec-review.json"):
        paths.update(read_json(safe(root, review), {}).get("inputs", {}))
    paths.update(path.relative_to(root).as_posix() for path in safe(root, p["paths"]["specs"]).rglob("*.md"))
    for item in knowledge_status(root, p)["documents"]:
        paths.update([item["document"], *item["sources"]])
        if item.get("decision"): paths.add(item["decision"])
    for item in baseline_orphan_findings(root, p): paths.add(item["path"])
    ledger = read_json(safe(root, p["paths"]["baseline"] + "/audits.json"), {"reports": {}})
    for report, item in ledger["reports"].items():
        paths.add(report)
        paths.update(item.get("inputs", {}))
    for name in inventory_files(root, p):
        if any(under(name, prefix) for prefix in p["test_paths"]): paths.add(name)
    return {name: digest(safe(root, name).read_bytes()) for name in sorted(paths) if safe(root, name).is_file()}


def finish_onboarding(root, p, result, record, initial_inputs):
    inputs = onboarding_inputs(root, p)
    findings = result["findings"]
    if inputs != initial_inputs:
        findings.append({"status": "PENDING", "code": "onboarding-inputs-changed", "message": "Inputs changed during the final declaration check; inspect and rerun."})
    final = read_json(safe(root, ".ai/runtime/final-onboarding.json"), {})
    if not record and (not final or final.get("inputs") != inputs):
        findings.append({"status": "PENDING", "code": "onboarding-final-check-stale" if final else "onboarding-final-check-missing", "message": "Run onboarding-status --record after final configuration, navigation, source-audit registration and artifact edits. This rechecks structure/content declarations, not business execution."})
    result["status"] = overall(findings, [])
    if "completion" in result:
        result["completion"] = "PARTIAL" if findings else "COMPLETE_DECLARED"
    result["structure_rechecked"] = True
    result["behavior_verification"] = "NOT_ASSESSED"
    if record:
        snapshot = {"created_at": now(), "kit_version": VERSION, "inputs": inputs, "result": result,
                    "scope": "Final asset/configuration/specification/registry/navigation/source-audit declaration checks; no business tests or native CLI executed."}
        transact(root, {".ai/runtime/final-onboarding.json": dump(snapshot)})
    return result


def onboarding_status(root, p, record=False):
    initial_inputs = onboarding_inputs(root, p)
    entry = entry_status(root, p)
    configuration = openspec_config_findings(root, p)
    if p["mode"] == "new":
        findings = entry["findings"] + configuration + structure_findings(root, p)
        result = {"status": overall(findings, []), "entry": entry, "configuration_status": overall(configuration, []), "findings": findings, "baseline": "NOT_APPLICABLE", "meaning": "No legacy baseline asserted; initial goals/specs/implementation require their own delivery verification."}
        return finish_onboarding(root, p, result, record, initial_inputs)
    coverage = coverage_status(root, p)
    behaviors = behavior_status(root, p)
    specs = baseline_spec_status(root, p)
    audits = baseline_audit_status(root, p)
    expected = {"AGENTS.md", p["paths"]["baseline"] + "/README.md"} | {path.relative_to(root).as_posix() for path in safe(root, p["paths"]["specs"]).glob("**/*.md")}
    if safe(root, ".ai/project-entry.json").is_file():
        expected.add(".ai/project-entry.json")
    if openspec_applicable(root, p):
        expected.add("openspec/config.yaml")
    expected.update(item["path"] for item in baseline_orphan_findings(root, p))
    for item in knowledge_status(root, p)["documents"]:
        if item["state"] != "obsolete":
            expected.add(item["document"])
            if item.get("decision"):
                expected.add(item["decision"])
    coverage_recorded = read_json(safe(root, ".ai/capability-coverage-review.json"), {})
    source_cases = source_case_status(root, p, coverage_recorded, coverage, behaviors)
    if coverage_recorded:
        expected.add(coverage_recorded["document"])
    behavior_review, _ = behavior_data(root, p)
    if behavior_review:
        expected.add(behavior_review["document"])
    audited, topics, findings = set(), set(), []
    for item in audits["reports"]:
        if any(not safe(root, name).is_file() or digest(safe(root, name).read_bytes()) != sha for name, sha in item["inputs"].items()):
            continue
        audited.update(item["artifacts"])
        report = read_json(safe(root, item["report"]))
        for check in report.get("quality_checks", []):
            if isinstance(check, dict) and check.get("status") == "PASS" and isinstance(check.get("checked"), str) and check["checked"].strip():
                topics.add(check.get("topic"))
    missing = sorted(expected - audited)
    if missing:
        findings.append({"status": "PENDING", "code": "onboarding-artifacts-unaudited", "paths": missing, "message": "Source audit must include project entry, capability map, explanations and current specs, not a token subset."})
    required_topics = {"project-entry", "capability-coverage", "spec-self-containment"}
    if required_topics - topics:
        findings.append({"status": "PENDING", "code": "onboarding-quality-unreviewed", "topics": sorted(required_topics - topics), "message": "Explicitly review project-specific entry, major capability omissions and whether specs are independently usable without Baseline."})
    verification = current_test_findings(root, p)
    overall_findings = entry["findings"] + configuration + baseline_orphan_findings(root, p) + baseline_index_findings(root, p) + structure_findings(root, p) + coverage["findings"] + behaviors["findings"] + specs["findings"] + audits["findings"] + findings + verification
    overall_findings.extend(source_cases["findings"])
    discovery = discovery_status(root, p)
    overall_findings.extend(discovery["findings"])
    readback = readback_status(root, p)
    overall_findings.extend(readback["findings"])
    result = {"status": overall(overall_findings, []), "completion": "COMPLETE_DECLARED" if not overall_findings else "PARTIAL", "source_cases": source_cases,
            "discovery": discovery, "readback": readback, "entry_status": entry["status"], "configuration_status": overall(configuration, []), "coverage": coverage, "behavior_review": behaviors, "specification_status": specs["specification_status"],
            "audit_status": audits["status"], "verification_mapping_status": overall(verification, []), "findings": overall_findings,
            "execution": "Not assessed by this quality declaration; cite actual build/test/external runs separately. Compilation is not business testing.",
            "verification_gaps": {"missing_mapping_count": len(verification), "missing_mapping_by_spec": {path: sum(item.get("path") == path for item in verification) for path in sorted({item.get("path", "") for item in verification})}},
            "structure_rechecked": True, "behavior_verification": "NOT_ASSESSED",
            "meaning": "Current declared onboarding quality and coverage, not zero defects or runtime verification. init-report.json is a historical setup snapshot."}
    return finish_onboarding(root, p, result, record, initial_inputs)


def baseline_next(root, p):
    """Derive recoverable work from existing authorities; do not create another ledger."""
    report = onboarding_status(root, p)
    stages = [
        ("project", ("project-entry", "openspec-config", "rule-source"), "Read project-entry/configuration guidance and reconcile the actual project inputs."),
        ("discover", ("discovery-", "capability-", "behavior-source"), "Run baseline discover; review contrasting paths and actual enablement, then reconcile candidates."),
        ("specify", ("behavior-", "spec-", "source-case"), "Review the affected behavior units and complete their current Requirement/Scenario outcomes."),
        ("readback", ("readback-",), "Freeze reader questions with readback-open, commit predictions, then adjudicate against source."),
        ("audit", ("source-audit", "onboarding-"), "Reopen source, record remaining findings, repair and recheck the affected scope."),
    ]
    tasks, assigned = [], set()
    for stage, prefixes, action in stages:
        selected = [item for item in report.get("findings", []) if item.get("code", "").startswith(prefixes) and dump(item) not in assigned]
        if selected:
            tasks.append({"stage": stage, "action": action, "findings": selected})
            assigned.update(dump(item) for item in selected)
    others = [item for item in report.get("findings", []) if dump(item) not in assigned]
    if others: tasks.append({"stage": "reconcile", "action": "Resolve the remaining concrete findings, retaining unavailable evidence as pending.", "findings": others})
    return {"status": report["status"], "next": tasks[0] if tasks else None, "remaining_stages": tasks,
            "meaning": "Read-only next work derived from current evidence; no automatic semantic approval or endless retry loop."}


def baseline_spec_status(root, p, scope=None):
    """Check declared contract-to-current-spec handoff; never infer semantics from code."""
    documents = [item for item in knowledge_status(root, p, scope)["documents"]
                 if item["kind"] == "contract" and item["state"] != "obsolete"]
    findings, linked = baseline_orphan_findings(root, p, scope), set()
    records = [{**item, "path": path.relative_to(root).as_posix()}
               for path in sorted(safe(root, p["paths"]["specs"]).glob("**/*.md"))
               for item in spec_records(path.read_text(encoding="utf-8"), path.parent.name)]
    current = {item["id"]: item for item in records}
    if not documents:
        findings.append({"status": "PENDING", "code": "baseline-contract-missing",
                         "message": "No registered observable contracts in scope; inventory or module prose alone does not complete baseline specification."})
    for item in documents:
        document = item["document"]
        if item["freshness"] != "current":
            findings.append({"status": "PENDING", "code": "baseline-spec-stale", "path": document,
                             "message": "Refresh source/document/decision evidence before claiming current specification coverage."})
        requirements = item.get("promoted_to", [])
        if item["state"] != "promoted" or not requirements:
            findings.append({"status": "PENDING", "code": "baseline-spec-missing", "path": document,
                             "message": "Write or reuse source-backed current requirements, record the preservation decision and promote selected promises. Record defects/unknowns separately; do not silently approve them."})
        for identity in requirements:
            record = current.get(identity)
            if not record:
                findings.append({"status": "FAIL", "code": "baseline-spec-removed", "path": document,
                                 "message": f"Missing current requirement: {identity}"})
                continue
            references = re.findall(r"(?im)^Baseline:\s*`?([^\s`]+)", record["body"])
            if not any(reference.split('#', 1)[0] == document for reference in references):
                findings.append({"status": "PENDING", "code": "baseline-spec-evidence", "path": record["path"],
                                 "message": f"{identity} must cite Baseline: {document}; preserve native IDs and add the evidence link rather than duplicating the requirement."})
            linked.add(identity)
    spec_paths = None
    if scope:
        spec_paths = [safe(root, name) for name in sorted({record["path"] for record in records if record["id"] in linked})]
    findings += specification_findings(root, p, spec_paths)
    verification = requirement_test_findings(root, p, [item for item in records if item["id"] in linked], current=True)
    return {"status": overall(findings + verification, []), "specification_status": overall(findings, []),
            "verification_status": overall(verification, []), "contracts": [item["document"] for item in documents],
            "requirements": sorted(linked), "findings": findings + verification,
            "scope": "Registered contracts plus independently discovered contract files/current-spec contract references; test mapping is not execution.",
            "meaning": "Declared contract/spec links and verification mappings only; not semantic completeness, owner approval or executed business tests."}


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
    baseline_index_refresh(root, p)
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


def proposal_field(proposal, name):
    """Read a single visible, line-oriented declaration in the native proposal."""
    visible = re.sub(r"<!--.*?(?:-->|\Z)", "", markdown_structure(proposal), flags=re.S)
    values = re.findall(rf"(?mi)^{re.escape(name)}:[ \t]*(.+?)[ \t]*$", visible)
    if len(values) > 1:
        raise KitError(f"Multiple {name}: fields in one proposal")
    return values[0].strip() if values else ""


def workflow_document(root, directory, name):
    """A native wrapper may cite one existing repository-local design or task document."""
    wrapper = safe(root, (directory / name).relative_to(root).as_posix())
    if not wrapper.is_file():
        return "", None
    content = wrapper.read_text(encoding="utf-8")
    source = proposal_field(content, "Workflow-Source").strip("`")
    if not source:
        return content, None
    path = safe(root, source)
    if not path.is_file() or path.suffix.lower() != ".md" or path == wrapper:
        raise KitError(f"{name} requires an existing distinct Markdown Workflow-Source: {source}")
    extra = path.read_text(encoding="utf-8")
    if not extra.strip() or proposal_field(extra, "Workflow-Source"):
        raise KitError(f"{name} Workflow-Source must contain the actual design or plan: {source}")
    return content + "\n" + extra, source


def file_change_metadata(root, p, directory):
    """Read ordinary change documents; no toolkit-owned lifecycle or sidecar is needed."""
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", directory.name) if directory.parent.name == "archive" else directory.name
    proposal = (directory / "proposal.md").read_text(encoding="utf-8")
    deltas = list(directory.glob("specs/**/*.md"))
    kind = proposal_field(proposal, "Kind")
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
    return {"schema_version": 1, "id": name, "kind": kind or ("feature" if deltas else "unclassified"),
            "scope": sorted(set(scope)), "scope_source": origin, "requirements": sorted({item["id"] for item in records} | set(proposal_field(proposal, "Current-Requirements").split())),
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
    allowed_kinds = {"feature", "fix", "refactor", "maintenance", "docs"}
    if not (directory / "ark.json").is_file():
        allowed_kinds.add("unclassified")
    if metadata.get("id") != change or metadata.get("kind") not in allowed_kinds:
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
    findings, seen, purposes = [], {}, {}
    paths = list(paths) if paths is not None else sorted(safe(root, p["paths"]["specs"]).glob("**/*.md"))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        text = safe(root, relative).read_text(encoding="utf-8")
        records = spec_records(text, path.parent.name)
        def issue(status, code, message, line=1):
            findings.append({"status": status, "code": code, "path": relative, "line": line, "message": f"{relative}:{line}: {message}"})
        structured = markdown_structure(text)
        if path.name == "spec.md" or records:
            for line_number, line_text in enumerate(text.splitlines(), 1):
                if SPEC_CODE_LOCATION.search(line_text):
                    issue("FAIL", "spec-source-line-reference",
                          "Move the code line citation to Baseline or audit evidence. Keep the observable behavior and stable contract link here.",
                          line_number)
        if path.name == "spec.md" and path.is_relative_to(safe(root, p["paths"]["specs"])):
            purpose = re.search(r"(?ms)^## Purpose\s*\n(.*?)(?=^## |\Z)", structured)
            value = re.sub(r"\s+", " ", purpose.group(1)).strip() if purpose else ""
            if value:
                if value in purposes and purposes[value] != relative:
                    issue("PENDING", "spec-repeated-purpose", f"Capability Purpose repeats {purposes[value]}; explain this capability's actual responsibility, not shared scope boilerplate.")
                purposes[value] = relative
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
            normative = body.split("#### Scenario:", 1)[0]
            normative = re.sub(r"(?m)^### Requirement:[^\n]*$", "", normative)
            normative = re.sub(r"(?m)^(?:Verification|Source|Baseline|Decision|Depends-On):[^\n]*$", "", normative).strip()
            pointer = re.fullmatch(r"(?is)(?:the )?(?:system|service)\s+(?:SHALL|MUST)\s+(?:follow|implement|use|preserve)\s+(?:the |all |existing )*(?:(?:behavior|rules|contract|requirements)\s+(?:described in|defined in|in|from)\s+.*(?:baseline|source document).*|(?:baseline|source document)[\w\s/`.:-]*(?:rules|contract|requirements|behavior))[.]?", normative)
            pointer = pointer or re.fullmatch(r"(?is)(?:系统|服务)\s*(?:SHALL|MUST|必须|应当|应)\s*(?:遵循|沿用|按照|按|参照|参考)\s*[^。\n]*(?:Baseline|基线|契约文档|源码说明)[^。\n]*(?:规则|约定|要求|处理|执行)[。.]?", normative)
            if pointer:
                issue("PENDING", "spec-delegated-body", f"{identifier}: state the observable rules and outcomes in the spec; Baseline is provenance, not a substitute for the promise.", line)
            if path.is_relative_to(safe(root, p["paths"]["specs"])):
                for dependencies in re.findall(r"(?im)^Depends-On:\s*(.+)$", body):
                    for dependency in REQ.findall(dependencies):
                        if dependency not in current_requirement_ids(root, p):
                            issue("PENDING", "spec-missing-owner", f"{identifier}: dependency {dependency} is not current; do not delegate a required payload/contract to an uncreated capability.", line)
            for match in re.finditer(r"(?im)^(?:Source|Baseline|Decision):\s*\x60?([^\s\x60]+)", body):
                reference = re.sub(r":L?\d+(?:[-:]L?\d+)*$", "", match.group(1).split("#", 1)[0])
                if "://" in reference:
                    continue
                try:
                    exists = safe(root, reference).is_file()
                except KitError:
                    exists = False
                if not exists:
                    issue("FAIL", "broken-evidence-link", f"Missing referenced evidence: {reference}", line)
        for section in re.split(r"(?m)^## ", structured):
            if section.startswith("RENAMED Requirements"):
                tags = re.findall(r"(?m)^\s*-?\s*(FROM|TO):", section)
                if not tags or len(tags) % 2 or any(tag != ("FROM" if i % 2 == 0 else "TO") for i, tag in enumerate(tags)):
                    issue("FAIL", "rename-pairs", "Native renames require alternating FROM and TO pairs.")
    return findings


def requirement_test_findings(root, p, records, current=False, change=None):
    """Check every effective promise, including ones absent from the selected delta."""
    findings = []
    tests = "\n".join(safe(root, name).read_text(encoding="utf-8", errors="replace")
                      for name in inventory_files(root, p) if Path(name).suffix.lower() in TEST_SOURCE_SUFFIXES
                      and any(under(name, prefix) for prefix in p["test_paths"]))
    for item in records:
        if item["section"] in {"REMOVED", "RENAMED"}:
            continue
        identifier = item["id"]
        declared = re.search(r"(?im)^Verification:\s*(automated|manual|external)\b", item["body"])
        mapping = p.get("requirements", {}).get(identifier, {})
        if not current and change:
            mapping = mapping.get("targets",{}).get(change,mapping)
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
        observations = case.get("observations", {})
        if (not isinstance(observations, dict) or set(observations) - names
                or any(not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids) for ids in observations.values())):
            raise KitError("Behavior observations map required check names to actual case/assertion identities")
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


def matching_artifact_rules(p, paths):
    return {name for name, rule in p.get("artifact_rules", {}).items()
            if any(under(path, pattern) or fnmatch.fnmatchcase(path, pattern)
                   for path in paths for pattern in rule.get("paths", []))}


def rule_record(root, p, reviewer):
    if not reviewer.strip(): raise KitError("Name the reviewer who reconciled project rules with their sources")
    rules = p.get("artifact_rules", {})
    record = {"schema_version": 1, "reviewer": reviewer, "recorded_at": now(), "rules": rules,
              "sources": {rule["source"]: digest(safe(root, rule["source"]).read_bytes()) for rule in rules.values()}}
    transact(root, {".ai/rule-review.json": dump(record), evidence_root(p) + "/rules/" + digest(dump(record).encode()) + ".json": dump(record)})
    return rule_status(root, p)


def rule_status(root, p):
    rules = p.get("artifact_rules", {})
    record = read_json(safe(root, ".ai/rule-review.json"), {})
    findings = []
    for identity, rule in rules.items():
        path = safe(root, rule["source"])
        if (record.get("rules", {}).get(identity) != rule or not path.is_file()
                or record.get("sources", {}).get(rule["source"]) != digest(path.read_bytes())):
            findings.append({"status": "PENDING", "code": "rule-source-unreviewed", "rule": identity, "path": rule["source"],
                             "message": "Reconcile the structured rule with its current source, then run rules record; existence alone does not prove equivalence."})
    return {"status": overall(findings, []), "findings": findings, "reviewer": record.get("reviewer")}


def external_record(root, p, document, reviewer):
    data = read_json(safe(root, document))
    dependencies = data.get("dependencies")
    if not reviewer.strip() or not isinstance(dependencies, list) or not dependencies:
        raise KitError("External dependencies need explicit local roots, file scopes and a reviewer")
    aliases, records, snapshots = set(), [], {}
    for dependency in dependencies:
        alias = dependency.get("alias", "")
        if not isinstance(alias, str) or not ID.fullmatch(alias) or alias in aliases:
            raise KitError("Use unique external repository aliases to disambiguate names")
        aliases.add(alias)
        source = Path(dependency.get("root", "")).expanduser()
        if not source.is_absolute() or not source.is_dir(): raise KitError("External roots must be explicit existing absolute directories")
        source = source.resolve()
        paths = dependency.get("files", [])
        if not isinstance(paths, list) or not paths: raise KitError("List explicit external contract/source files; do not scan an entire external repository")
        hashes = {}
        for path in paths:
            file = safe(source, path)
            if not file.is_file() or file.stat().st_size > 4 * 1024 * 1024: raise KitError("External snapshot file missing or over 4 MiB")
            content = file.read_bytes(); hashes[path] = digest(content)
            snapshots[evidence_root(p) + "/external/" + hashes[path] + "/" + alias + "/" + path] = content
        records.append({"alias": alias, "root": str(source), "files": hashes})
    record = {"schema_version": 1, "reviewer": reviewer, "document": document,
              "document_sha256": digest(dump(data).encode()), "recorded_at": now(), "dependencies": records}
    transact(root, {**snapshots, ".ai/external-review.json": dump(record)})
    return external_status(root, p)


def external_status(root, p):
    record = read_json(safe(root, ".ai/external-review.json"), {})
    findings, files = [], {}
    if record:
        document = safe(root, record["document"])
        if not document.is_file() or digest(dump(read_json(document)).encode()) != record["document_sha256"]:
            findings.append({"status": "PENDING", "code": "external-map-stale", "message": "External dependency mapping changed; reconcile scopes explicitly."})
    for dependency in record.get("dependencies", []):
        for path, expected in dependency["files"].items():
            file = safe(Path(dependency["root"]), path)
            actual = digest(file.read_bytes()) if file.is_file() else None
            key = dependency["alias"] + "::" + path
            files[key] = actual
            if actual != expected:
                findings.append({"status": "PENDING", "code": "external-source-stale", "source": key,
                                 "message": "External contract/source changed or is unavailable; recheck its consumers before recording again."})
    return {"status": overall(findings, []), "files": files, "findings": findings,
            "scope": "Explicit local external snapshots only; deployed compatibility, remote freshness and undeclared dependencies are NOT_ASSESSED."}


def explain(root, p, identity):
    _, inventory = behavior_data(root, p)
    units = [unit for unit in inventory.get("units", []) if identity in {unit["id"], unit.get("requirement")}]
    rules = p.get("artifact_rules", {})
    change = None
    try:
        directory, metadata = change_at(root, p, identity)
        impact = behavior_impact(root, p, metadata["scope"])
        units = [unit for unit in inventory.get("units", []) if unit["id"] in impact["units"] or unit.get("requirement") in metadata.get("requirements", [])]
        verification = read_json(directory / "verification.json", {})
        proposal = (directory / "proposal.md").read_text(encoding="utf-8") if (directory / "proposal.md").is_file() else ""
        change = {"metadata": metadata, "path": directory.relative_to(root).as_posix(), "impact": impact,
                  "target_specs": sorted(path.relative_to(root).as_posix() for path in directory.glob("specs/**/*.md")),
                  "adr": proposal_field(proposal, "ADR"), "verification": verification,
                  "verification_current": bool(verification) and verification.get("fingerprint") == fingerprint(root, p, identity)}
    except KitError:
        pass
    return {"status": "PASS" if units or identity in rules or change else "PENDING", "query": identity, "change": change,
            "units": [{"id": unit["id"], "requirement": unit.get("requirement"), "spec_path": unit.get("spec_path"),
                       "evidence": unit.get("evidence", []), "tests": unit.get("tests", []),
                       "depends_on": unit.get("depends_on", []), "disposition": unit["disposition"],
                       "confidence": unit["confidence"], "contract_facts": unit.get("contract_facts", [])} for unit in units],
            "rule": rules.get(identity), "rule_currency": rule_status(root, p),
            "behavior_currency": behavior_status(root, p), "external_currency": external_status(root, p),
            "meaning": "Read-only navigation of recorded evidence and gaps; PASS means a matching record exists, not semantic approval."}


def project_obligations(root, p, directory, metadata, phase, paths, deltas):
    """Combine actual scoped paths with the project's recorded semantic risk assessment."""
    findings = rule_status(root, p)["findings"] + external_status(root, p)["findings"]
    proposal = directory / "proposal.md"
    text = proposal.read_text(encoding="utf-8") if proposal.is_file() else ""
    kind = metadata["kind"]
    current = current_requirement_ids(root, p)
    claimed = set(proposal_field(text, "Current-Requirements").split())
    if claimed - current:
        findings.append({"status": "FAIL", "code": "unknown-current-requirement",
                         "message": f"Current-Requirements refers to missing current specifications: {sorted(claimed - current)}"})
    if kind == "unclassified" and phase in {"ready", "delivery"}:
        findings.append({"status": "PENDING", "code": "change-intent",
                         "message": "Declare the change intent in the proposal (Kind: feature/fix/refactor/maintenance/docs). Supply a delta for new behavior, or identify the preserved contract."})
    if kind == "maintenance" and metadata.get("origin") == "files" and paths and not deltas and not claimed and not proposal_field(text, "Preserves"):
        plan = behavior_plan(root, p, metadata["id"])
        if not any(case["effect"] == "preserve" for case in plan["cases"]):
            findings.append({"status": "PENDING", "code": "maintenance-rationale",
                         "message": "For production maintenance, explain the unchanged observable behavior in Preserves: or cite Current-Requirements:."})
    rules = p.get("artifact_rules", {})
    selected = set(proposal_field(text, "Risks").split())
    if selected - {"none"} - rules.keys() or ("none" in selected and len(selected) != 1):
        findings.append({"status": "FAIL", "code": "invalid-risks", "message": "Risks: must name configured project rule IDs or none alone."})
    if paths and any(not rule.get("paths") for rule in rules.values()) and not selected:
        findings.append({"status": "PENDING", "code": "risk-assessment", "message": "Assess the repository's semantic artifact rules in Risks: before delivery."})
    if selected == {"none"} and not proposal_field(text, "Risk-Reason"):
        findings.append({"status": "PENDING", "code": "risk-rationale", "message": "Explain the assessment in Risk-Reason:."})
    applicable = (selected & rules.keys()) | matching_artifact_rules(p, paths)
    required = {asset for name in applicable for asset in rules[name]["requires"]}
    if kind == "feature":
        required.add("spec")
    if "spec" in required and not any(spec_records(path.read_text(encoding="utf-8"), path.parent.name) for path in deltas):
        findings.append({"status": "PENDING", "code": "required-delta", "message": "Add the observable behavior and its scenarios to the Change delta."})
    if "design" in required:
        design, _ = workflow_document(root, directory, "design.md")
        if not design.strip() or FILL in design:
            findings.append({"status": "PENDING", "code": "required-design", "message": f"Project rules {sorted(applicable)} require a filled Change design.md."})
    if "adr" in required:
        reference = proposal_field(text, "ADR").strip("`")
        adr = safe(root, reference) if reference else None
        status = None
        if adr and under(reference, p["paths"]["adr"]) and adr.suffix == ".md" and adr.is_file():
            body = adr.read_text(encoding="utf-8")
            if FILL not in body:
                status = adr_status(body)
        if not status or status[0] not in ({"Accepted", "Proposed"} if phase == "specification" else {"Accepted"}):
            findings.append({"status": "PENDING", "code": "required-adr", "message": "Reference an applicable ADR with ADR: <repo-relative path>. Implementation requires an Accepted decision; specification can cite a Proposed one."})
    return findings


def change_findings(root, p, change, phase, changed=None):
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
        elif phase != "structure" and (FILL in (workflow_document(root, directory, name)[0]
                if name in {"design.md", "tasks.md"} else path.read_text(encoding="utf-8"))):
            findings.append({"status": "PENDING", "code": "draft-artifact", "message": f"Fill {change}/{name} or explain why its sections do not apply."})
    deltas = list(directory.glob("specs/**/*.md"))
    if phase != "structure":
        paths = metadata["scope"] if changed is None else changed
        production = [path for path in paths if path == "." or (
            any(under(path, scope) for scope in metadata["scope"])
            and is_behavior(path, p) and not excluded(path, p)
            and not any(under(path, test) for test in p["test_paths"]))]
        # Concrete paths stated in an active proposal also matter before the first edit.
        declared = [path for path in metadata["scope"] if path != "." and is_behavior(path, p) and not excluded(path, p)
                    and not any(under(path, test) for test in p["test_paths"])]
        findings += project_obligations(root, p, directory, metadata, phase, production + declared, deltas)
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
        findings += behavior_scope_findings(root, p, metadata["scope"], change)
        findings += delivery_knowledge_findings(root, p, metadata["scope"])
        tasks, _ = workflow_document(root, directory, "tasks.md")
        if re.search(r"^\s*[-*] \[ \]", markdown_structure(tasks), re.MULTILINE):
            findings.append({"status": "PENDING", "code": "unfinished-tasks", "message": "Change tasks still contain unchecked items."})
        records = [item for path in deltas for item in spec_records(path.read_text(encoding="utf-8"), path.parent.name)]
        declared = current_requirement_ids(root, p) | {item["id"] for item in records}
        for requirement in metadata.get("requirements", []):
            if requirement not in declared:
                findings.append({"status": "FAIL", "code": "requirement-spec", "message": f"{requirement} has no specification reference."})
        findings += requirement_test_findings(root, p, records, change=change)
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


def execution_cases(path, kind, run_id):
    if not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise KitError("This run did not produce a bounded test report")
    if kind == "junit":
        tree = ET.fromstring(path.read_bytes())
        cases = [{"id": (node.get("classname", "") + "::" + node.get("name", "")).strip(":"),
                  "status": "FAIL" if node.find("failure") is not None or node.find("error") is not None
                  else "NOT_RUN" if node.find("skipped") is not None else "PASS"}
                 for node in tree.iter("testcase")]
    elif kind == "ark-json":
        data = read_json(path)
        if data.get("schema_version") != 1 or data.get("run_id") != run_id:
            raise KitError("Test report must identify this exact ARK_RUN_ID")
        cases = data.get("cases")
    else:
        raise KitError("Test report format must be junit or ark-json")
    if not isinstance(cases, list):
        raise KitError("Test report needs a cases array")
    identities = set()
    for case in cases:
        if (not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"]
                or case["id"] in identities or case.get("status") not in {"PASS", "FAIL", "NOT_RUN"}):
            raise KitError("Test report case identities must be unique with PASS/FAIL/NOT_RUN states")
        identities.add(case["id"])
    return cases


def run_check(root, check, run_dir, observations=None, test_paths=None):
    result = {"name": check["name"], "type": check.get("type", "command"), "required": check.get("required", True), "started_at": now()}
    argv = [sys.executable if part == "{python}" else part for part in check["argv"]]
    cwd = root if check.get("cwd", ".") == "." else safe(root, check["cwd"])
    result.update(argv=argv, cwd=str(cwd))
    log = run_dir / (check["name"] + ".log")
    started = time.monotonic()
    report_config = check.get("case_report")
    report_path = run_dir / (check["name"] + ".cases." + ("xml" if report_config and report_config.get("format") == "junit" else "json"))
    preexisting_report = report_path.exists()
    run_id = run_dir.name
    executed_argv = [part.replace("{case_report}", str(report_path)).replace("{run_dir}", str(run_dir)) for part in argv]
    report_kind = report_config.get("format") if report_config else None
    supported_python = (bool(re.fullmatch(r"python(?:\d+(?:\.\d+)?)?(?:\.exe)?", Path(argv[0]).name.lower()))
                        and len(argv) > 1 and (argv[1] in {"-c", "-m"} and len(argv) > 2 or not argv[1].startswith("-")))
    if observations is not None and not report_config and supported_python:
        executed_argv = [argv[0], str(ASSETS / "execution_probe.py"), str(report_path), str(root), dump(argv[1:]), dump(test_paths or ["tests", "src/test"])]
        report_kind = "ark-json"
    result["executed_argv"] = executed_argv
    try:
        with log.open("wb") as stream:
            completed = subprocess.run(executed_argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=check.get("timeout", 300), check=False, env={**os.environ, "ARK_VERIFY_ACTIVE": "1", "ARK_RUN_ID": run_id, "ARK_CASE_REPORT": str(report_path), "PYTHONPYCACHEPREFIX": str(run_dir / "bytecode")})
        result.update(status="PASS" if completed.returncode == 0 else "FAIL", exit_code=completed.returncode)
        if completed.returncode < 0:
            try: result["termination"] = signal.Signals(-completed.returncode).name
            except ValueError: result["termination"] = "unknown-signal"
    except FileNotFoundError as exc:
        result.update(status="NOT_RUN", reason=str(exc))
    except subprocess.TimeoutExpired:
        result.update(status="FAIL", reason="timeout")
    except OSError as exc:
        result.update(status="NOT_RUN", reason=str(exc))
    result["command_status"] = result["status"]
    if observations is not None or report_config:
        try:
            if preexisting_report:
                raise KitError("Refusing a test report path that existed before this invocation")
            cases = execution_cases(report_path, report_kind, run_id)
            by_id = {case["id"]: case["status"] for case in cases}
            required = set((report_config or {}).get("required_cases", [])) | set((observations or {}).get("cases", []))
            missing = sorted(identity for identity in required if by_id.get(identity) != "PASS")
            fixtures = (observations or {}).get("fixtures", [])
            unobserved = [path for path in fixtures if not any(case["id"].startswith(path + ":L") and case["status"] == "PASS" for case in cases)] if not report_config else []
            failed = any(case["status"] == "FAIL" for case in cases)
            passed = sum(case["status"] == "PASS" for case in cases)
            state = "FAIL" if failed else "PENDING" if missing or unobserved or not passed else "PASS"
            result["case_execution"] = {"status": state, "cases": cases, "required": sorted(required), "missing": missing,
                                        "unobserved_fixtures": unobserved, "executed": sum(case["status"] != "NOT_RUN" for case in cases),
                                        "report": report_path.relative_to(root).as_posix(), "sha256": digest(report_path.read_bytes()),
                                        "meaning": "Observed case/assertion execution; semantic adequacy is reviewed separately."}
            result["status"] = overall([{ "status": result["status"]}, {"status": state}], [])
        except (KitError, ET.ParseError, ValueError, TypeError) as exc:
            result["case_execution"] = {"status": "PENDING", "executed": 0, "reason": str(exc)}
            if result["status"] == "PASS":
                result.update(status="PENDING", reason="Command passed, but required behavior case execution is unproven: " + str(exc))
    result.update(duration_seconds=round(time.monotonic() - started, 3), finished_at=now(), log=log.relative_to(root).as_posix(),
                  log_sha256=digest(log.read_bytes()) if log.is_file() else None,
                  environment={"platform": sys.platform, "python": sys.version.split()[0]})
    return result


def overall(findings, checks):
    statuses = [x["status"] for x in findings] + [x["status"] for x in checks if x.get("required", True)]
    if "FAIL" in statuses:
        return "FAIL"
    if any(s in {"PENDING", "NOT_RUN"} for s in statuses):
        return "PENDING"
    return "PASS"


def verify(root, p, phase="structure", change=None, base=None, selected=None, peer_scopes=None, candidate_paths=None):
    findings = structure_findings(root, p)
    metadata = None
    if change:
        _, metadata = change_at(root, p, change)
        if candidate_paths is None:
            candidate_paths = changed_files(root, base)
            if not candidate_paths and git(root, "rev-parse", "--is-inside-work-tree", optional=True) is None:
                candidate_paths = list(inventory_files(root, p))
        findings += change_findings(root, p, change, phase, candidate_paths)
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
        planned_cases = behavior_plan(root, p, change)["cases"]
        for check in p["checks"]:
            if phase not in check.get("phases", ["ready", "delivery"]):
                continue
            if before_names is not None and check["name"] not in before_names:
                continue
            if selected and check["name"] not in selected:
                checks.append({"name": check["name"], "required": check.get("required", True), "status": "NOT_RUN", "reason": "Not selected; partial execution cannot satisfy required delivery checks."})
            elif check.get("type", "command") == "command":
                relevant = [case for case in planned_cases if check["name"] in
                            (case["checks"] if phase == "delivery" or case["effect"] == "preserve" else case.get("before_checks", []))]
                observations = {"cases": sorted({identity for case in relevant for identity in case.get("observations", {}).get(check["name"], [])}),
                                "fixtures": sorted({path for case in relevant if phase == "ready" or case["effect"] == "preserve" for path in case.get("fixtures", [])})} if relevant else None
                checks.append(run_check(root, check, run_dir, observations, p["test_paths"]))
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
    if phase == "structure":
        report["scope"] = "Asset integrity and declared specification structure/mapping only; empty specifications do not establish onboarding completion."
        report["onboarding_complete"] = False
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
    if metadata.get("origin") == "files":
        return {"status": "PENDING", "change": change, "state": "native-archive-required",
                "message": "Delivery verification passed. Synchronize and archive using the repository's native workflow, then run the local check; the toolkit does not create ark.json or archive native changes."}
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
        linked = set()
        if directory.parent.name != "archive":
            for name in ("design.md", "tasks.md"):
                wrapper = directory / name
                if wrapper.is_file():
                    linked.add(proposal_field(wrapper.read_text(encoding="utf-8"), "Workflow-Source").strip("`"))
        if matched or linked.intersection(changed) or any(under(path, relative) for path in changed):
            candidates.append({"id": metadata["id"], "path": relative, "files": matched, "scope": metadata["scope"], "scope_source": metadata.get("scope_source", "declared")})
    overlaps = {path: [item["id"] for item in candidates if path in item["files"]] for path in behavior}
    overlaps = {path: names for path, names in overlaps.items() if len(names) > 1}
    return {"candidates": candidates, "catalog": catalog, "overlaps": overlaps,
            "ambiguous": bool(overlaps), "changed_files": changed, "behavior_files": behavior}


def knowledge_navigation(root, p, changed):
    index = read_json(safe(root, p["paths"]["baseline"] + "/knowledge.json"), {"documents": {}})
    return [document for document, item in index["documents"].items()
            if item.get("state") != "obsolete" and (document in changed or item.get("decision") in changed
                                                     or any(path in changed for path in item.get("sources", {})))]


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
            "behavior_impact": behavior_impact(root, p, selection["changed_files"], scan_sources=False),
            "routing": {"facts": p["paths"]["baseline"], "behavior": p["paths"]["specs"], "decisions": p["paths"]["adr"], "work": p["paths"]["changes"]},
            "workflow": "Use OpenSpec, another development tool or direct conversation. Read relevant rules/evidence; run local checks before claiming delivery. No daily toolkit Skill or activation is required.",
            "resume": f"Read {resume} and actual diff." if resume else "Inspect candidate work and actual diff; overlapping scope stays ambiguous. No task is guessed from modification time.",
            "last_check": ".ai/runtime/last-check.json", "meaning": "Navigation and diff-based association; no tests, whole-repository inventory or semantic certification on startup"}


def impact(root, p, base=None):
    selection = work_selection(root, p, changed_files(root, base))
    affected = set(knowledge_navigation(root, p, selection["changed_files"]))
    documents = [item for item in knowledge_status(root, p)["documents"] if item["document"] in affected]
    result = {"status": "PENDING" if selection["ambiguous"] or any(item["freshness"] == "stale" for item in documents) else "PASS",
              "base": base, "selection": selection, "knowledge": documents, "behavior": behavior_impact(root, p, selection["changed_files"]), "created_at": now(),
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
    result["behavior_review_candidates"] = behavior_impact(root, p, changed)
    if safe(root, ".ai/behavior-review.json").is_file() and not result.get("changes"):
        scoped = behavior_scope_findings(root, p, changed)
        result["findings"].extend(scoped)
        result["status"] = overall([{"status": result["status"]}, *scoped], [])
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


def lightweight_input_signature(root, p, base):
    """Bind candidate bytes/modes and the lightweight declarations themselves."""
    paths = set(changed_files(root, base))
    paths.update(path.relative_to(root).as_posix() for path in safe(root, ".ai/notes").glob("*.json"))
    inputs = {}
    for relative in sorted(paths):
        path = safe(root, relative)
        inputs[relative] = ({"sha256": digest(path.read_bytes()), "executable": bool(path.stat().st_mode & 0o111)}
                            if path.is_file() else None)
    return {"fingerprint": fingerprint(root, p), "inputs": inputs}


def ci_verify(root, p, base, local=False):
    """Re-execute candidate changes; never trust committed verification reports."""
    if (not base or set(base) == {"0"}) and not local:
        raise KitError("CI requires a real comparison base; configure the main-branch base for an initial push.")
    changed = changed_files(root, base)
    without_git = git(root, "rev-parse", "--is-inside-work-tree", optional=True) is None
    if local and without_git:
        changed = sorted(inventory_files(root, p))
    immutable = []
    comparison = git(root, "merge-base", base, "HEAD").decode().strip() if base else "HEAD"
    for relative in changed:
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
    ignore = safe(root, ".gitignore")
    prior_ignore = None if without_git else git(root, "show", f"{comparison}:.gitignore", optional=True)
    original_ignore = prior_ignore or b""
    setup_ignore = original_ignore + (b"\n" if original_ignore and not original_ignore.endswith(b"\n") else b"") + LOCAL_IGNORE.encode()
    if ignore.is_file() and ignore.read_bytes() == setup_ignore:
        # Only the exact known initializer append is setup. Arbitrary changes to
        # existing ignore/attributes rules still require scoped impact review.
        behavior = [x for x in behavior if x != ".gitignore"]
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
    protected = {path for path in lightweight if matching_artifact_rules(p, [path])}
    lightweight -= protected
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
            report = verify(root, p, "delivery" if affects_behavior else "specification", change, base, peer_scopes=peers,
                            candidate_paths=next(item["files"] for item in selection["candidates"] if item["id"] == change))
            executed_count += sum(item["status"] in {"PASS", "FAIL"} and "argv" in item for item in report["checks"])
            results.append({"status": report["status"], "change": change, "phase": report["phase"], "run_id": report["run_id"], "checks": report["checks"], "findings": report["findings"]})
    light_checks = []
    light_findings = []
    if lightweight:
        run_dir = safe(root, ".ai/runtime/runs/light-" + uuid.uuid4().hex[:12])
        run_dir.mkdir(parents=True)
        start_signature = lightweight_input_signature(root, p, base)
        for check in p["checks"]:
            if "delivery" not in check.get("phases", ["ready", "delivery"]):
                continue
            if check.get("type", "command") == "command":
                light_checks.append(run_check(root, check, run_dir))
            elif check.get("required", True):
                light_checks.append({"name": check["name"], "required": True, "status": "NOT_RUN", "reason": "Required outside verification needs a scoped change/evidence record."})
        if lightweight_input_signature(root, p, base) != start_signature:
            light_findings.append({"status": "FAIL", "code": "inputs-changed",
                                   "message": "Lightweight verification inputs changed while checks were running; inspect the resulting diff and rerun on the reviewed inputs."})
        results += light_findings
        atomic(run_dir / "result.json", dump({"checks": light_checks, "findings": light_findings,
                                               "fingerprint": start_signature["fingerprint"], "inputs": start_signature["inputs"],
                                               "status": overall(light_findings, light_checks)}))
    results += delivery_knowledge_findings(root, p, changed)
    return {"status": overall(results, light_checks), "execution": "local" if local else "ci", "base": base, "executed_check_count": executed_count + sum(item["status"] in {"PASS", "FAIL"} for item in light_checks), "behavior_files": behavior, "lightweight_files": sorted(lightweight), "lightweight_checks": light_checks, "lightweight_findings": light_findings, "changes": results, "control_review": "Review lightweight declarations and policy/runtime/CI/manifest changes independently; repository-controlled checks are not a security boundary."}


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
    entry = sub.add_parser("entry").add_subparsers(dest="operation", required=True)
    entry.add_parser("refresh")
    entry.add_parser("status")
    onboarding = sub.add_parser("onboarding-status")
    onboarding.add_argument("--record", action="store_true", help="Persist a fresh final declaration check after all artifact/audit edits; does not run business tests")
    openspec = sub.add_parser("openspec").add_subparsers(dest="operation", required=True)
    openspec.add_parser("refresh")
    openspec.add_parser("status")
    openspec_review = openspec.add_parser("record")
    openspec_review.add_argument("--reviewer", required=True)
    ctx = sub.add_parser("context")
    ctx.add_argument("--session", default="default")
    affected = sub.add_parser("impact")
    affected.add_argument("--base")
    explanation = sub.add_parser("explain")
    explanation.add_argument("identity")
    rules = sub.add_parser("rules").add_subparsers(dest="operation", required=True)
    rules.add_parser("status")
    rules.add_parser("record").add_argument("--reviewer", required=True)
    external = sub.add_parser("external").add_subparsers(dest="operation", required=True)
    external.add_parser("status")
    external_record_parser = external.add_parser("record")
    external_record_parser.add_argument("--document", required=True)
    external_record_parser.add_argument("--reviewer", required=True)
    sub.add_parser("install-git-hook")
    baseline = sub.add_parser("baseline").add_subparsers(dest="operation", required=True)
    baseline.add_parser("inventory")
    baseline.add_parser("discover")
    baseline.add_parser("next")
    baseline.add_parser("discovery-status")
    readback = baseline.add_parser("readback-open")
    readback.add_argument("--id", required=True)
    readback.add_argument("--document", required=True)
    readback.add_argument("--reviewer", required=True)
    readback.add_argument("--mode", choices=["same-agent-separate-pass", "separate-context-attested"], default="same-agent-separate-pass")
    for operation in ("readback-predict", "readback-judge"):
        readback = baseline.add_parser(operation)
        readback.add_argument("--id", required=True)
        readback.add_argument("--document", required=True)
        readback.add_argument("--reviewer", required=True)
    baseline.add_parser("readback-status").add_argument("--id")
    discover = baseline.add_parser("discovery-record")
    discover.add_argument("--document", required=True)
    discover.add_argument("--reviewer", required=True)
    review = baseline.add_parser("review")
    review.add_argument("--document", required=True)
    review.add_argument("--files", nargs="+", required=True)
    review.add_argument("--reviewer", required=True)
    baseline.add_parser("validate")
    baseline.add_parser("status")
    baseline.add_parser("index-refresh")
    coverage = baseline.add_parser("coverage-record")
    coverage.add_argument("--document", required=True)
    coverage.add_argument("--reviewer", required=True)
    baseline.add_parser("coverage-status")
    behavior = baseline.add_parser("behavior-record")
    behavior.add_argument("--document", required=True)
    behavior.add_argument("--reviewer", required=True)
    baseline.add_parser("behavior-status")
    candidate = baseline.add_parser("behavior-change-record")
    candidate.add_argument("--change", required=True)
    candidate.add_argument("--report", required=True)
    candidate.add_argument("--reviewer", required=True)
    spec_status = baseline.add_parser("spec-status")
    spec_status.add_argument("--scope", nargs="+", help="Limit contract source/document scope; omitted means all registered contracts")
    audit = baseline.add_parser("audit-record")
    audit.add_argument("--report", required=True)
    audit.add_argument("--files", nargs="+", required=True)
    audit.add_argument("--artifacts", nargs="+", required=True)
    audit.add_argument("--reviewer", required=True)
    audit_status = baseline.add_parser("audit-status")
    audit_status.add_argument("--report", help="Limit to one audit; otherwise inspect all recorded audit scopes")
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
    sub.add_parser("engineering-status")
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
            elif args.command == "engineering-status":
                result = engineering_status(root, p)
            elif args.command == "entry":
                with lock(root):
                    result = entry_refresh(root, p) if args.operation == "refresh" else entry_status(root, p)
            elif args.command == "onboarding-status":
                with lock(root):
                    result = onboarding_status(root, p, args.record)
            elif args.command == "openspec":
                with lock(root):
                    if args.operation == "refresh": result = openspec_refresh(root, p)
                    elif args.operation == "record": result = openspec_record(root, p, args.reviewer)
                    else:
                        findings = openspec_config_findings(root, p)
                        result = {"status": overall(findings, []), "applicable": openspec_applicable(root, p), "findings": findings, "native_validation": "NOT_ASSESSED", "meaning": "Bounded content guards and declared source-backed configuration currency; not a YAML parser or proof native CLI read/validation ran."}
            elif args.command == "context":
                result = context(root, p, args.session)
            elif args.command == "impact":
                result = impact(root, p, args.base)
            elif args.command == "explain":
                result = explain(root, p, args.identity)
            elif args.command == "rules":
                with lock(root):
                    result = rule_record(root, p, args.reviewer) if args.operation == "record" else rule_status(root, p)
            elif args.command == "external":
                with lock(root):
                    result = external_record(root, p, args.document, args.reviewer) if args.operation == "record" else external_status(root, p)
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
                    elif args.operation == "discover":
                        result = discovery_scan(root, p)
                    elif args.operation == "next":
                        result = baseline_next(root, p)
                    elif args.operation == "readback-open":
                        result = readback_open(root, p, args.id, args.document, args.reviewer, args.mode)
                    elif args.operation in {"readback-predict", "readback-judge"}:
                        result = readback_record(root, p, args.id, args.document, args.reviewer, args.operation == "readback-judge")
                    elif args.operation == "readback-status":
                        result = readback_status(root, p, args.id)
                    elif args.operation == "discovery-status":
                        result = discovery_status(root, p)
                    elif args.operation == "discovery-record":
                        result = discovery_record(root, p, args.document, args.reviewer)
                    elif args.operation == "review":
                        result = baseline_review(root, p, args.document, args.files, args.reviewer)
                    elif args.operation == "register":
                        result = baseline_review(root, p, args.document, args.files, args.reviewer) if args.kind == "module" else knowledge_record(root, p, args.kind, args.document, args.files, args.reviewer)
                    elif args.operation == "status":
                        result = knowledge_status(root, p)
                        result["orphan_findings"] = baseline_orphan_findings(root, p)
                        result["status"] = overall(result["orphan_findings"] + [{"status": result["status"]}], [])
                    elif args.operation == "index-refresh":
                        result = baseline_index_refresh(root, p)
                    elif args.operation == "coverage-record":
                        result = coverage_record(root, p, args.document, args.reviewer)
                    elif args.operation == "coverage-status":
                        result = coverage_status(root, p)
                    elif args.operation == "behavior-record":
                        result = behavior_record(root, p, args.document, args.reviewer)
                    elif args.operation == "behavior-status":
                        result = behavior_status(root, p)
                    elif args.operation == "behavior-change-record":
                        result = behavior_candidate_record(root, p, args.change, args.report, args.reviewer)
                    elif args.operation == "spec-status":
                        result = baseline_spec_status(root, p, args.scope)
                    elif args.operation == "audit-record":
                        result = baseline_audit_record(root, p, args.report, args.files, args.artifacts, args.reviewer)
                    elif args.operation == "audit-status":
                        result = baseline_audit_status(root, p, args.report)
                    elif args.operation in {"promote", "retire"}:
                        result = knowledge_transition(root, p, args.document, args.reviewer, args.decision, getattr(args, "requirements", None), obsolete=args.operation == "retire")
                    else:
                        findings = baseline_findings(root, p) + baseline_orphan_findings(root, p) + baseline_index_findings(root, p)
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
        if args.command == "change" and args.operation == "close":
            return {"FAIL": 1, "PENDING": 2}.get(result.get("status"), 0)
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
