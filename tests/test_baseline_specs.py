"""REQ-BASELINE-SPEC-001: observable onboarding handoff, not inventory-only completion."""
import json
import subprocess
import sys

from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class BaselineSpecTests(RepositoryCase):
    document = 'manual/contracts/double.md'

    def prepare(self, mapped=False):
        self.write('app.py', 'def double(value):\n    return value * 2\n')
        p = self.initialize('existing')
        if mapped:
            p['paths']['specs'] = 'requirements/current'
            self.write(kit.POLICY, kit.dump(p))
        self.write(self.document, '# Double\n## Source version and evidence\napp.py:L1-L2\n'
                   '## Inputs and outputs\nNumbers return doubled.\n## Timing and failure\n'
                   'Synchronous; Python multiplication errors propagate.\n## Compatibility and promotion\n'
                   'Retain numeric results; nonnumeric behavior is not promised.\n')
        kit.knowledge_record(self.root, p, 'contract', self.document, ['app.py'], 'agent')
        self.write('manual/preservation.md', '# Preservation analysis\nRetain verified numeric behavior; no owner approval asserted.\n')
        return p

    def promise(self, p, reference=True):
        path = p['paths']['specs'] + '/math/spec.md'
        self.write(path, '# Math\n## Purpose\nNumeric doubling.\n## Requirements\n'
                   '### Requirement: REQ-DOUBLE-001 Double\nVerification: automated\n'
                   + ('Baseline: ' + self.document + '\n' if reference else '')
                   + 'Source: app.py:L1-L2\nThe system SHALL return twice the numeric input.\n'
                   '#### Scenario: Four\n- WHEN 4 is supplied\n- THEN 8 is returned\n')
        kit.knowledge_transition(self.root, p, self.document, 'agent', 'manual/preservation.md', ['REQ-DOUBLE-001'])
        return path

    def test_bare_inventory_and_contract_are_not_specification_completion(self):
        self.write('app.py', 'value = 1\n')
        p = self.initialize('existing')
        kit.baseline_inventory(self.root, p)
        self.assertEqual(kit.baseline_spec_status(self.root, p)['status'], 'PENDING')
        p = self.prepare()
        self.assertIn('baseline-spec-missing', {x['code'] for x in kit.baseline_spec_status(self.root, p)['findings']})

    def test_created_specs_separate_missing_verification_from_specification(self):
        p = self.prepare(mapped=True)
        self.promise(p)
        before = kit.baseline_spec_status(self.root, p)
        self.assertEqual(before['specification_status'], 'PASS', before)
        self.assertEqual(before['verification_status'], 'PENDING', before)
        self.write('tests/test_double.py', 'import unittest\nfrom app import double\n'
                   'class TestDouble(unittest.TestCase):\n'
                   '    def test_double(self):\n'
                   '        # REQ-DOUBLE-001\n        self.assertEqual(double(4), 8)\n')
        result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], cwd=self.root, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(kit.baseline_spec_status(self.root, p)['status'], 'PASS')
        self.assertFalse((self.root / 'openspec/specs').exists())
        (self.root / 'tests/test_double.py').unlink()
        self.assertEqual(kit.baseline_spec_status(self.root, p)['verification_status'], 'PENDING')

    def test_promoted_id_alone_cannot_hide_missing_baseline_link_or_spec(self):
        p = self.prepare()
        path = self.promise(p, reference=False)
        self.assertIn('baseline-spec-evidence', {x['code'] for x in kit.baseline_spec_status(self.root, p)['findings']})
        (self.root / path).unlink()
        self.assertEqual(kit.baseline_spec_status(self.root, p)['status'], 'FAIL')

    def test_contract_and_decision_edits_make_handoff_stale(self):
        p = self.prepare()
        self.promise(p)
        for path in (self.document, 'app.py', 'manual/preservation.md'):
            original = (self.root / path).read_bytes()
            (self.root / path).write_bytes(original + b'\n')
            self.assertIn('baseline-spec-stale', {x['code'] for x in kit.baseline_spec_status(self.root, p)['findings']})
            (self.root / path).write_bytes(original)

    def test_scoped_vendored_cli_reports_missing_specs_without_creating_fakes(self):
        p = self.prepare()
        engine = self.root / 'hack/ai/ark.py'
        result = subprocess.run([sys.executable, str(engine), '--repo', str(self.root), 'baseline', 'spec-status', '--scope', 'app.py'], capture_output=True, text=True)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'PENDING', result.stderr)
        self.assertEqual(report['contracts'], [self.document])
        self.assertFalse((self.root / p['paths']['specs']).exists())
        self.assertEqual(kit.baseline_spec_status(self.root, p, ['other.py'])['status'], 'PENDING')
