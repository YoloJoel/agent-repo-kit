"""Retain an interrupted qualification command's evidence for the CLI consumer."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOL = Path(__file__).resolve().parents[1] / "tools/qualify_source_facts.py"


@unittest.skipUnless(sys.platform == "linux", "Source-fact native probe supports Linux")
class SourceFactProbeTests(unittest.TestCase):
    def test_timeout_keeps_partial_log_and_failure_report(self):
        spec = importlib.util.spec_from_file_location("source_fact_probe", TOOL)
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        interrupted = subprocess.TimeoutExpired(["make", "test"], 30, output=b"started case\n", stderr=b"waiting for service\n")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            with patch.object(sys, "argv", [str(TOOL), "--output", directory]), \
                 patch.object(tool.shutil, "which", return_value="available"), \
                 patch.object(tool.subprocess, "run", side_effect=interrupted):
                self.assertEqual(tool.main(), 1)
            report = json.loads((destination / "source-facts.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["remaining_execution"], "NOT_RUN")
            self.assertEqual(report["checks"][0]["reason"], "timeout")
            self.assertEqual((destination / "original-tests.log").read_text(), "started case\nwaiting for service\n")

    @unittest.skipUnless(shutil.which("cc") and shutil.which("make"), "Native example toolchain required")
    def test_later_timeout_retains_completed_observations(self):
        spec = importlib.util.spec_from_file_location("source_fact_probe", TOOL)
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        native_run = tool.subprocess.run
        make_calls = 0

        def run(argv, **kwargs):
            nonlocal make_calls
            if argv == ["make", "test"]:
                make_calls += 1
                if make_calls == 2:
                    raise subprocess.TimeoutExpired(argv, 30, output=b"mutation started\n")
            return native_run(argv, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            with patch.object(sys, "argv", [str(TOOL), "--output", directory]), \
                 patch.object(tool.subprocess, "run", side_effect=run):
                self.assertEqual(tool.main(), 1)
            report = json.loads((destination / "source-facts.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["observations"]["both_rules_enabled_route"], "global")
            self.assertEqual(report["observations"]["termination_returncode"], -15)
            self.assertEqual(report["checks"][-1]["reason"], "timeout")
            self.assertEqual((destination / "changed-rule-original-tests.log").read_text(), "mutation started\n")
