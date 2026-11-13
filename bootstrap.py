"""One-shot repository setup from a checkout; no pip, venv, PATH entry or network.

The Agent obtains this toolkit and runs this entry point. All installed resources
are copied into the target, so the toolkit checkout can be discarded afterwards.
"""

import argparse
import json
from pathlib import Path
import sys


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.version_info < (3, 11):
        print(json.dumps({"status": "FAIL", "error": "Python 3.11+ is required; let the Agent locate an available interpreter."}))
        return 1
    source = Path(__file__).resolve().parent / "src"
    if not (source / "agent_repo_kit/assets/agents.md").is_file():
        print(json.dumps({"status": "FAIL", "error": "Obtain the complete agent-repo-kit checkout, not bootstrap.py alone. Follow START_HERE.md."}))
        return 1
    sys.path.insert(0, str(source))
    from agent_repo_kit import core

    parser = argparse.ArgumentParser(description="Initialize this repository without installing agent-repo-kit.")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--agents", help="The Agent can select its own adapter; omit to preserve existing selection/defaults.")
    parser.add_argument("--mode", choices=["auto", "new", "existing"], default="auto")
    parser.add_argument("--no-hooks", action="store_true", help="Skip new hook setup; existing requested hooks are preserved/repaired.")
    parser.add_argument("--ci", choices=["auto", "github", "none"], default="none")
    parser.add_argument("--upgrade", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.path).expanduser().resolve()
    try:
        result = core.onboard_repo(root, args.mode, args.agents.split(",") if args.agents else None, not args.no_hooks, args.ci, args.upgrade)
        print(core.dump(result), end="")
        return 0 if result["status"] == "PASS" else 1
    except (core.KitError, OSError, ValueError) as exc:
        print(core.dump({"status": "FAIL", "error": str(exc)}), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
