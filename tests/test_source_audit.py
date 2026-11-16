"""REQ-SOURCE-AUDIT-001: missing/stale/open semantic audit declarations cannot close onboarding."""
import copy
import json
import subprocess
import sys

from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class SourceAuditTests(RepositoryCase):
    def prepare(self):
        self.write('app.py', 'def lookup(values, key):\n    return values[key]\n')
        p = self.initialize('existing')
        self.write('manual/current.md', '# Current behavior\nMissing keys raise KeyError without changing values.\n')
        source = [{'path': 'app.py', 'evidence': 'app.py:L1-L2', 'checked': 'Direct dictionary lookup; absent key raises KeyError before any write.'}]
        artifacts = [{'path': 'manual/current.md', 'checked': 'Checked existing-key result and missing-key error/no-write claim.'}]
        finding = {'id': 'AUD-001', 'issue': 'Generated description previously claimed None for a missing key.', 'evidence': 'app.py:L2', 'status': 'open'}
        report = {'review_mode': 'same-agent-separate-pass', 'passes': [
            {'kind': 'source-first', 'sources': source, 'artifacts': artifacts, 'findings': [finding]},
            {'kind': 'source-recheck', 'sources': copy.deepcopy(source), 'artifacts': copy.deepcopy(artifacts),
             'findings': [{**finding, 'status': 'fixed', 'resolution': 'Corrected to KeyError; reread direct indexing and checked no state mutation.'}]}]}
        return p, report

    def record(self, p, report):
        self.write('manual/audit.json', kit.dump(report))
        return kit.baseline_audit_record(self.root, p, 'manual/audit.json', ['app.py'], ['manual/current.md'], 'agent')

    def test_missing_or_only_one_source_pass_cannot_complete(self):
        p, report = self.prepare()
        self.assertEqual(kit.baseline_audit_status(self.root, p)['status'], 'PENDING')
        report['passes'].pop()
        with self.assertRaisesRegex(kit.KitError, 'source-recheck'):
            self.record(p, report)

    def test_dropped_findings_or_unreviewed_artifacts_are_rejected(self):
        p, report = self.prepare()
        report['passes'][1]['findings'] = []
        with self.assertRaisesRegex(kit.KitError, 'retain every'):
            self.record(p, report)
        p, report = self.prepare()
        report['passes'][1]['artifacts'] = []
        with self.assertRaisesRegex(kit.KitError, 'complete selected'):
            self.record(p, report)

    def test_open_findings_stay_pending_and_resolved_snapshot_is_immutable(self):
        p, report = self.prepare()
        report['passes'][1]['findings'][0]['status'] = 'open'
        self.assertEqual(self.record(p, report)['status'], 'PENDING')
        snapshots = {path: path.read_bytes() for path in (self.root / kit.evidence_root(p) / 'audits').rglob('*') if path.is_file()}
        report['passes'][1]['findings'][0]['status'] = 'fixed'
        result = self.record(p, report)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['reports'][0]['review_mode'], 'same-agent-separate-pass')
        for path, content in snapshots.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertIn('cannot prove', result['meaning'])

    def test_each_input_change_invalidates_the_record_and_recheck_restores_currency(self):
        p, report = self.prepare()
        self.record(p, report)
        for name in ('app.py', 'manual/current.md', 'manual/audit.json'):
            original = (self.root / name).read_bytes()
            (self.root / name).write_bytes(original + b'\n')
            result = kit.baseline_audit_status(self.root, p, 'manual/audit.json')
            self.assertEqual(result['status'], 'PENDING')
            self.assertIn(name, result['findings'][0]['changed'])
            (self.root / name).write_bytes(original)
        self.assertEqual(self.record(p, report)['status'], 'PASS')

    def test_invalid_source_evidence_or_empty_disposition_is_not_accepted(self):
        p, report = self.prepare()
        report['passes'][1]['sources'][0]['evidence'] = 'app.py:L99'
        with self.assertRaisesRegex(kit.KitError, 'source evidence'):
            self.record(p, report)
        p, report = self.prepare()
        report['passes'][1]['findings'][0]['resolution'] = ''
        with self.assertRaisesRegex(kit.KitError, 'resolution'):
            self.record(p, report)

    def test_new_recheck_findings_cannot_be_silently_closed_without_another_review(self):
        p, report = self.prepare()
        report['passes'][1]['findings'].append({**report['passes'][1]['findings'][0], 'id': 'AUD-002'})
        with self.assertRaisesRegex(kit.KitError, 'New recheck findings'):
            self.record(p, report)
        report['passes'][1]['findings'][1]['status'] = 'open'
        self.assertEqual(self.record(p, report)['status'], 'PENDING')

    def test_clean_two_pass_vendored_cli_and_scoped_report_selection(self):
        p, report = self.prepare()
        for audit in report['passes']:
            audit['findings'] = []
        self.write('manual/audit.json', kit.dump(report))
        engine = str(self.root / 'hack/ai/ark.py')
        result = subprocess.run([sys.executable, engine, '--repo', str(self.root), 'baseline', 'audit-record', '--report', 'manual/audit.json', '--files', 'app.py', '--artifacts', 'manual/current.md', '--reviewer', 'agent'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'PASS')
        self.assertEqual(kit.baseline_audit_status(self.root, p, 'manual/absent.json')['status'], 'PENDING')
