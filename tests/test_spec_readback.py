"""Calibrate Spec-only scoring on frozen candidate answers and actual native observations."""
import json
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'docs/evidence/source-facts-review'


class SpecReadbackTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'linux' and all(shutil.which(tool) for tool in ('cc', 'make', 'python3')),
                         'Native control-hub qualification requires Linux, cc, make and python3')
    def test_flawed_spec_receives_mixed_scores_even_when_native_probe_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'scored'
            subprocess.run([sys.executable, str(ROOT / 'tools/score_spec_readback.py'),
                            '--spec', str(SAMPLE / 'spec.md'), '--answers', str(SAMPLE / 'example-answers.json'),
                            '--output', str(output)], check=True, capture_output=True)
            report = json.loads((output / 'readback.json').read_text())
            self.assertEqual(report['native_status'], 'PASS')
            self.assertEqual(report['counts'], {'matches': 1, 'contradicts': 2, 'unclear': 5})
            self.assertEqual([row['id'] for row in report['rows'] if row['result'] == 'contradicts'], ['Q1', 'Q2'])

    @unittest.skipUnless(sys.platform == 'linux' and all(shutil.which(tool) for tool in ('cc', 'make', 'python3')),
                         'Native control-hub qualification requires Linux, cc, make and python3')
    def test_readback_of_first_handler_disagrees_with_running_final_handler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / 'spec.md'
            answers = root / 'answers.json'
            quote = 'After readiness a termination request SHALL flush and return 0.'
            spec.write_text(quote, encoding='utf-8')
            answers.write_text(json.dumps({'L1': {'status': 'predicted', 'quote': quote,
                                                   'value': {'returncode': 0, 'flushed': True}}}), encoding='utf-8')
            output = root / 'scored'
            subprocess.run([sys.executable, str(ROOT / 'tools/score_spec_readback.py'), '--suite', 'lifecycle',
                            '--spec', str(spec), '--answers', str(answers), '--output', str(output)],
                           check=True, capture_output=True)
            report = json.loads((output / 'readback.json').read_text())
            self.assertEqual(report['counts'], {'matches': 0, 'contradicts': 1, 'unclear': 0})
            self.assertEqual(report['rows'][0]['observed'], {'returncode': -signal.SIGTERM, 'flushed': False})
