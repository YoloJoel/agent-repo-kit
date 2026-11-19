"""Execute bounded source-fact counterexamples in the control-hub example."""

import argparse
import ctypes
import hashlib
import json
import os
import select
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


class Frame(ctypes.Structure):
    _fields_ = [("token", ctypes.c_uint32), ("value", ctypes.c_int)]


class ProbeTimeout(RuntimeError):
    pass


def qualify(output):
    output.mkdir(parents=True, exist_ok=True)
    available = {name: shutil.which(name) for name in ("cc", "make", "python3")}
    report = {"meaning": "Bounded source observations and assertion counterexample; no private-repository or model-quality certification.",
              "toolchain": available, "checks": []}
    if sys.platform != "linux" or not all(available.values()):
        report.update(status="NOT_RUN", reason="Linux with cc, make and python3 required.")
        return report

    try:
        with tempfile.TemporaryDirectory(prefix="ark-source-facts-") as temporary:
            root = Path(temporary) / "project"
            shutil.copytree(ROOT / "examples/control-hub", root,
                            ignore=shutil.ignore_patterns("build", "__pycache__"))
            report["source_hashes"] = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(root.rglob("*")) if p.is_file()}

            def command(name, argv):
                timed_out = False
                try:
                    completed = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=30,
                                               env=os.environ.copy())
                except subprocess.TimeoutExpired as error:
                    timed_out = True
                    stdout, stderr = error.stdout or "", error.stderr or ""
                    if isinstance(stdout, bytes):
                        stdout = stdout.decode(errors="replace")
                    if isinstance(stderr, bytes):
                        stderr = stderr.decode(errors="replace")
                    completed = subprocess.CompletedProcess(argv, 124, stdout, stderr)
                log = output / (name + ".log")
                log.write_text(completed.stdout + completed.stderr)
                record = {"name": name, "argv": argv, "exit_code": completed.returncode,
                          "status": "PASS" if completed.returncode == 0 else "FAIL",
                          "log": log.name, "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
                report["checks"].append(record)
                if timed_out:
                    record.update(reason="timeout", timeout_seconds=30)
                    report.update(status="FAIL", reason=f"{name} timed out.", remaining_execution="NOT_RUN")
                    raise ProbeTimeout
                return completed

            original = command("original-tests", ["make", "test"])
            if original.returncode:
                report.update(status="FAIL", reason="Original example build/tests failed.")
                return report

            hub = ctypes.CDLL(str(root / "build/libhub.so"))
            hub.hub_resource_count.restype = ctypes.c_size_t
            hub.hub_resource.argtypes = [ctypes.c_size_t]
            hub.hub_resource.restype = ctypes.c_char_p
            hub.hub_identity.restype = ctypes.c_char_p
            hub.hub_configure_filters.argtypes = [ctypes.c_size_t]
            hub.hub_configure_filters.restype = ctypes.c_int
            hub.hub_encode.argtypes = [ctypes.c_int]
            hub.hub_encode.restype = Frame
            hub.hub_receive.argtypes = [Frame]
            hub.hub_route.argtypes = [ctypes.c_int, ctypes.c_int]
            hub.hub_route.restype = ctypes.c_char_p
            observations = {}
            report["observations"] = observations
            observations["registered_resources"] = [
                hub.hub_resource(i).decode() for i in range(hub.hub_resource_count())
            ]
            observations["unknown_command_result"] = command(
                "unknown-command", [str(root / "build/hub"), "dispatch", "archive"]
            ).stdout.strip()
            observations["identity"] = hub.hub_identity().decode()
            observations["emitted_token"] = hub.hub_encode(42).token
            observations["received_arbitrary_token_value"] = hub.hub_receive(Frame(999, 42))
            observations["validator_accepts_700"] = bool(hub.hub_period_valid(700))
            observations["update_period_700"] = hub.hub_update_period(700)
            observations["both_rules_enabled_route"] = hub.hub_route(1, 1).decode()
            observations["filter_count_4"] = hub.hub_configure_filters(4)
            observations["filter_count_5"] = hub.hub_configure_filters(5)
            hub.hub_window_reset(0)
            hub.hub_window_tick(99)
            observations["reports_after_timer_tick"] = hub.hub_window_reports()
            hub.hub_window_reset(0)
            hub.hub_window_ingest(20, 0, 0)
            observations["reports_at_boundary"] = hub.hub_window_reports()
            hub.hub_window_ingest(21, 0, 0)
            observations["reports_after_next_event"] = hub.hub_window_reports()
            observations["empty_report_fields"] = hub.hub_last_report_fields()

            server = subprocess.Popen([str(root / "build/hub"), "serve"], cwd=root,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                readable, _, _ = select.select([server.stdout], [], [], 5)
                if not readable or server.stdout.readline().strip() != "ready":
                    report.update(status="FAIL", reason="Server readiness was not observed.", observations=observations)
                    return report
                server.send_signal(signal.SIGTERM)
                stdout, _ = server.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                report.update(status="FAIL", reason="Server termination timed out.", observations=observations)
                return report
            finally:
                if server.poll() is None:
                    server.kill()
                    server.communicate()
            observations["termination_returncode"] = server.returncode
            observations["termination_flushed"] = "flushed" in stdout

            source = root / "hub.c"
            original_source = source.read_text()
            original_branch = '    if (global_enabled) {\n        return "global";\n    }'
            assert original_source.count(original_branch) == 1
            source.write_text(original_source.replace(original_branch, '    if (global_enabled) {\n        return "local";\n    }'))
            try:
                unrelated = command("changed-rule-original-tests", ["make", "test"])
            finally:
                source.write_text(original_source)
            restored = command("restored-original-tests", ["make", "test"])
            observations["wrong_rule_still_passes_original_tests"] = unrelated.returncode == 0
            observations["restored_original_tests_pass"] = restored.returncode == 0

            expected = {"registered_resources": ["stream", "probe"], "unknown_command_result": "-1", "identity": "hub.v2",
                        "emitted_token": 0, "received_arbitrary_token_value": 42, "validator_accepts_700": False,
                        "update_period_700": 700, "both_rules_enabled_route": "global", "reports_after_timer_tick": 0,
                        "reports_at_boundary": 0, "reports_after_next_event": 1, "empty_report_fields": 0,
                        "termination_returncode": -signal.SIGTERM, "termination_flushed": False,
                        "filter_count_4": 0, "filter_count_5": -2,
                        "wrong_rule_still_passes_original_tests": True, "restored_original_tests_pass": True}
            report["mismatches"] = {key: {"expected": value, "actual": observations.get(key)}
                                    for key, value in expected.items() if observations.get(key) != value}
            report["status"] = "FAIL" if report["mismatches"] else "PASS"
            return report

    except ProbeTimeout:
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.output.resolve())
    path = args.output.resolve() / "source-facts.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "report": str(path)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
