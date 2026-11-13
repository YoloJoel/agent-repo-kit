"""REQ-PORTABLE-001: native assets, alternative tools and local-only delivery."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class PortableWorkflowTests(RepositoryCase):
    def native(self, mapped=False):
        self.git_start()
        p = self.initialize()
        if mapped:
            p['paths']['changes'] = 'planning/work'
            p['paths']['specs'] = 'planning/current'
        self.configure(p, [{'name': 'unit', 'argv': ['{python}', '-m', 'unittest', 'discover', '-s', 'tests']}])
        base = self.commit()
        self.write('app.py', 'def scale(value):\n    return value * 3\n')
        self.write('tests/test_app.py', 'import unittest\nfrom app import scale\n# REQ-MATH-001\nclass MathTests(unittest.TestCase):\n    def test_positive_and_negative(self):\n        self.assertEqual(scale(4), 12)\n        self.assertEqual(scale(-2), -6)\n')
        block = '### Requirement: REQ-MATH-001 Scale a value\nThe system SHALL multiply the input by three.\n\n#### Scenario: Positive input\n- WHEN input is 4\n- THEN output is 12\n'
        directory = p['paths']['changes'] + '/add-scale'
        self.write(directory + '/proposal.md', '# Why\nAdd scaling.\n\n## Impact\n- `app.py` and `tests/`\n')
        self.write(directory + '/tasks.md', '# Tasks\n- [x] Implement and test the positive and negative values.\n')
        self.write(directory + '/specs/math/spec.md', '## ADDED Requirements\n\n' + block)
        self.write(p['paths']['specs'] + '/math/spec.md', '# Math\n\n' + block)
        return p, base, directory

    def test_native_files_and_mapped_other_tool_need_no_toolkit_sidecar_or_lifecycle(self):
        p, base, directory = self.native(mapped=True)
        report = kit.ci_verify(self.root, p, base, local=True)
        self.assertEqual(report['status'], 'PASS', report)
        self.assertEqual(report['execution'], 'local')
        self.assertFalse((self.root / directory / 'ark.json').exists())
        self.assertEqual(kit.active(self.root), None)
        verification = kit.read_json(self.root / directory / 'verification.json')
        self.assertEqual(verification['checks'][0]['status'], 'PASS')

    def test_native_archive_is_recognized_after_the_selected_tool_moves_it(self):
        p, base, directory = self.native()
        self.assertEqual(kit.ci_verify(self.root, p, base, local=True)['status'], 'PASS')
        target = self.root / p['paths']['changes'] / 'archive/2026-11-13-add-scale'
        target.parent.mkdir(parents=True)
        shutil.move(self.root / directory, target)
        self.assertEqual(kit.ci_verify(self.root, p, base, local=True)['status'], 'PASS')
        self.assertEqual(kit.change_at(self.root, p, 'add-scale')[0], target)
        self.assertFalse((target / 'ark.json').exists())

    def test_native_unsynchronized_behavior_cannot_pass(self):
        p, base, directory = self.native()
        self.write(p['paths']['specs'] + '/math/spec.md', '# Math\nNo accepted scaling behavior yet.\n')
        target = self.root / p['paths']['changes'] / 'archive/2026-11-13-add-scale'
        target.parent.mkdir(parents=True)
        shutil.move(self.root / directory, target)
        report = kit.ci_verify(self.root, p, base, local=True)
        self.assertEqual(report['status'], 'PENDING')
        details = kit.read_json(target / 'verification.json')
        self.assertIn('spec-sync', [item['code'] for item in details['findings']])

    def test_multiple_unassociated_native_changes_are_not_guessed(self):
        p, base, directory = self.native()
        self.write(directory + '/proposal.md', '# Why\nAdd scaling.\n')
        self.write(p['paths']['changes'] + '/other/proposal.md', '# Why\nOther unfinished work.\n')
        self.write(p['paths']['changes'] + '/other/tasks.md', '- [ ] Investigate.\n')
        result = kit.ci_verify(self.root, p, base, local=True)
        self.assertEqual(result['code'], 'ambiguous-change')
        self.assertEqual(result['status'], 'PENDING')

    def test_local_cli_runs_without_remote_or_hosted_ci(self):
        p, base, directory = self.native()
        result = subprocess.run([sys.executable, str(Path(kit.__file__)), '--repo', str(self.root), 'check', '--base', base], capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'PASS')
        self.assertFalse((self.root / '.github').exists())
        self.assertEqual(self.run_git('remote'), '')

    def test_local_directory_without_git_still_executes_business_checks(self):
        p, base, directory = self.native()
        detached = tempfile.TemporaryDirectory()
        self.addCleanup(detached.cleanup)
        (self.root / '.git').rename(Path(detached.name) / 'detached-git')
        report = kit.ci_verify(self.root, p, None, local=True)
        self.assertEqual(report['status'], 'PASS', report)
        details = kit.read_json(self.root / directory / 'verification.json')
        self.assertEqual(details['checks'][0]['status'], 'PASS')
        self.assertIsNone(details['source_ref'])


if __name__ == '__main__':
    import unittest
    unittest.main()
