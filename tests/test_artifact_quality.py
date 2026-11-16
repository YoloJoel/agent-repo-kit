"""REQ-ARTIFACT-QUALITY-001: project entrance, whole-scope coverage and standalone promises."""
import json
import subprocess
import sys

from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class ArtifactQualityTests(RepositoryCase):
    def entry_data(self):
        return {'language': 'zh', 'purpose': '整数读取服务，缺失键报告错误。',
                'stack': 'Python 标准库；无外部服务。', 'boundaries': 'app.py 提供同步字典读取；无后台任务。',
                'constraints': '读取不修改存储，保留缺失错误。', 'workflow': '修改前补齐旧行为断言；本地验证；无已配置发布流程。',
                'precedence': '用户要求优先；规格约束行为，决策约束设计，工程规范约束流程；冲突显式记录。',
                'source_evidence': {'app.py': 'app.py:L1-L2'}, 'reviewer': 'agent', 'gaps': []}

    def prepare(self):
        self.write('app.py', 'def lookup(values, key):\n    return values[key]\n')
        p = self.initialize('existing')
        p['source_paths'] = ['app.py']
        self.configure(p, [{'name': 'unit', 'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']}])
        return p

    def test_large_manifest_inventory_does_not_spill_into_project_entrance(self):
        for i in range(92):
            self.write(f'modules/m{i}/pom.xml', '<project/>\n')
        p = self.initialize('existing')
        text = (self.root / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('# AGENTS.md', text)
        self.assertEqual(sum(line.startswith('## ') for line in text.splitlines()), 7)
        self.assertNotIn('m91/pom.xml', text)
        self.assertLess(len(text.splitlines()), 90)
        self.assertEqual(kit.entry_status(self.root, p)['status'], 'PENDING')
        self.assertIn('m91/pom.xml', (self.root / 'docs/project-context.md').read_text(encoding='utf-8'))

    def test_curated_entry_uses_project_facts_and_confirmed_commands_and_detects_staleness(self):
        p = self.prepare()
        self.write('.ai/project-entry.json', kit.dump(self.entry_data()))
        self.assertEqual(kit.entry_refresh(self.root, p)['status'], 'PASS')
        text = (self.root / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('整数读取服务', text)
        self.assertIn('项目定位与技术栈', text)
        self.assertIn('代码与模块边界', text)
        self.assertIn('unittest discover', text)
        self.assertNotIn('Agent Repo Kit workflow', text)
        self.assertEqual(kit.init_repo(self.root)['changed'], [])
        self.write('app.py', 'def lookup(values, key):\n    return values.get(key)\n')
        self.assertEqual(kit.entry_status(self.root, p)['status'], 'PENDING')

    def test_human_native_entrance_is_preserved_without_a_second_project_outline(self):
        human = b'# Project instructions\r\n## Project scope\r\nKeep human decisions.  \r\n'
        (self.root / 'AGENTS.md').write_bytes(human)
        p = self.prepare()
        self.write('.ai/project-entry.json', kit.dump(self.entry_data()))
        kit.entry_refresh(self.root, p)
        text = (self.root / 'AGENTS.md').read_bytes()
        self.assertTrue(text.startswith(human))
        self.assertNotIn(b'## 1.', text)
        self.assertEqual(text.count('工程工具接入'.encode()), 1)

    def test_lifecycle_only_map_cannot_hide_uncovered_business_sources(self):
        p = self.prepare()
        p['source_paths'] = ['app.py', 'protocol.py']
        self.write(kit.POLICY, kit.dump(p))
        self.write('protocol.py', 'def decode(text):\n    return int(text)\n')
        self.write('manual/capabilities.json', kit.dump({'capabilities': [{'id': 'lifecycle', 'kind': 'business', 'purpose': 'Lookup lifecycle only.', 'sources': ['app.py'], 'status': 'pending', 'requirements': []}]}))
        report = kit.coverage_record(self.root, p, 'manual/capabilities.json', 'agent')
        self.assertEqual(report['production_files'], 2)
        self.assertEqual(report['mapped_files'], 1)
        self.assertEqual(report['status'], 'PENDING')
        self.assertIn('protocol.py', next(x for x in report['findings'] if x['code'] == 'capability-unmapped-sources')['sample'])
        self.assertEqual(kit.onboarding_status(self.root, p)['completion'], 'PARTIAL')

    def test_exclusions_require_rationale_and_do_not_hide_business_scope(self):
        p = self.prepare()
        item = {'id': 'lookup', 'kind': 'business', 'purpose': 'Lookup.', 'sources': ['app.py'], 'status': 'excluded'}
        self.write('manual/capabilities.json', kit.dump({'capabilities': [item]}))
        with self.assertRaisesRegex(kit.KitError, 'rationale'):
            kit.coverage_record(self.root, p, 'manual/capabilities.json', 'agent')
        item['reason'] = 'Not analyzed in this partial pass.'
        self.write('manual/capabilities.json', kit.dump({'capabilities': [item]}))
        result = kit.coverage_record(self.root, p, 'manual/capabilities.json', 'agent')
        self.assertEqual(result['mapped_files'], 1)
        self.assertEqual(result['status'], 'PENDING')

    def test_reference_only_promise_is_pending_but_provenance_does_not_replace_or_invalidate_real_rules(self):
        p = self.prepare()
        path = 'openspec/specs/lookup/spec.md'
        self.write('manual/contract.md', '# Observation\nDictionary lookup.\n')
        header = '# Lookup\n## Requirements\n### Requirement: REQ-LOOKUP-001 Lookup\nVerification: automated\nBaseline: manual/contract.md\n'
        scenario = '\n#### Scenario: Known key\n- WHEN an existing key is read\n- THEN its stored value is returned\n'
        self.write(path, header + 'The system SHALL follow Baseline contract.' + scenario)
        self.assertIn('spec-delegated-body', {x['code'] for x in kit.specification_findings(self.root, p)})
        self.write(path, header + 'The system SHALL return the stored value and raise KeyError on a missing key without changing values.' + scenario)
        self.assertEqual(kit.specification_findings(self.root, p), [])
        self.write(path, header + 'The system SHALL preserve immutable Baseline snapshots.' + scenario)
        self.assertEqual(kit.specification_findings(self.root, p), [])

    def test_current_spec_cannot_delegate_to_a_nonexistent_requirement_owner(self):
        p = self.prepare()
        self.write('openspec/specs/lookup/spec.md', '# Lookup\n## Requirements\n### Requirement: REQ-LOOKUP-001 Lookup\nVerification: automated\nDepends-On: REQ-PAYLOAD-001\nThe system SHALL return the decoded stored value.\n#### Scenario: Known key\n- WHEN a stored key is read\n- THEN its decoded value is returned\n')
        self.assertIn('spec-missing-owner', {x['code'] for x in kit.specification_findings(self.root, p)})

    def test_distinct_capabilities_cannot_share_only_a_generic_purpose(self):
        p = self.prepare()
        for name, action in (('read', 'return a stored value'), ('write', 'store the supplied value')):
            self.write(f'openspec/specs/{name}/spec.md', f'# {name}\n## Purpose\nCurrent source snapshot behavior.\n## Requirements\n### Requirement: REQ-{name.upper()}-001 {name}\nVerification: automated\nThe system SHALL {action}.\n#### Scenario: Request\n- WHEN the operation is called\n- THEN it produces its defined result\n')
        self.assertIn('spec-repeated-purpose', {x['code'] for x in kit.specification_findings(self.root, p)})
        path = self.root / 'openspec/specs/read/spec.md'
        path.write_text(path.read_text(encoding='utf-8').replace('Current source snapshot behavior.', 'Read the current value without changing stored records.'), encoding='utf-8')
        self.assertEqual(kit.specification_findings(self.root, p), [])

    def test_historical_setup_pass_is_not_current_onboarding_completion(self):
        self.prepare()
        report = kit.read_json(self.root / '.ai/init-report.json')
        self.assertEqual(report['report_kind'], 'initialization_snapshot')
        self.assertIn('created_at', report)
        result = subprocess.run([sys.executable, str(self.root / 'hack/ai/ark.py'), '--repo', str(self.root), 'onboarding-status'], capture_output=True, text=True)
        current = json.loads(result.stdout)
        self.assertEqual(current['completion'], 'PARTIAL')
        self.assertEqual(current['status'], 'PENDING')
        self.assertIn('Compilation is not business testing', current['execution'])
        self.assertIn('onboarding-quality-unreviewed', {x['code'] for x in current['findings']})

    def test_complete_declared_quality_requires_all_artifacts_and_explicit_semantic_questions(self):
        p = self.prepare()
        self.write('.ai/project-entry.json', kit.dump(self.entry_data()))
        kit.entry_refresh(self.root, p)
        kit.baseline_inventory(self.root, p)
        self.write('docs/baseline/module.md', '# Lookup\n## Purpose\nRead a stored value.\n## Flow\nIndex the dictionary.\n## State and failure\nNo writes; missing key raises KeyError.\n## Evidence\napp.py:L1-L2\n## Gaps\nNo external runtime tested.\n')
        kit.baseline_review(self.root, p, 'docs/baseline/module.md', ['app.py'], 'agent')
        contract = 'docs/baseline/contract.md'
        self.write(contract, '# Contract\n## Source version and evidence\napp.py:L1-L2\n## Inputs and outputs\nExisting key returns its stored value.\n## Timing and failure\nMissing key raises KeyError synchronously without writes.\n## Compatibility and promotion\nPreserve direct lookup behavior.\n')
        kit.knowledge_record(self.root, p, 'contract', contract, ['app.py'], 'agent')
        self.write('manual/preserve.md', '# Preservation\nRetain dictionary lookup result and missing-key failure. Agent analysis, not owner approval.\n')
        spec = 'openspec/specs/lookup/spec.md'
        self.write(spec, '# Lookup\n## Requirements\n### Requirement: REQ-LOOKUP-001 Lookup\nVerification: automated\nBaseline: ' + contract + '\nSource: app.py:L1-L2\nThe system SHALL return the stored value for an existing key and raise KeyError for a missing key without changing the dictionary.\n#### Scenario: Lookup\n- WHEN an existing key is requested\n- THEN its stored value is returned\n#### Scenario: Missing\n- WHEN an absent key is requested\n- THEN KeyError is raised and the dictionary is unchanged\n')
        kit.knowledge_transition(self.root, p, contract, 'agent', 'manual/preserve.md', ['REQ-LOOKUP-001'])
        self.write('tests/test_lookup.py', 'import unittest\nfrom app import lookup\nclass TestLookup(unittest.TestCase):\n    def test_lookup(self):\n        # REQ-LOOKUP-001\n        values = {"a": 2}\n        self.assertEqual(lookup(values, "a"), 2)\n        with self.assertRaises(KeyError): lookup(values, "b")\n        self.assertEqual(values, {"a": 2})\n')
        run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], cwd=self.root, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        mapping = 'manual/capabilities.json'
        self.write(mapping, kit.dump({'capabilities': [{'id': 'lookup', 'kind': 'business', 'purpose': 'Existing-key result and missing-key error.', 'sources': ['app.py'], 'status': 'specified', 'requirements': ['REQ-LOOKUP-001']}]}))
        self.assertEqual(kit.coverage_record(self.root, p, mapping, 'agent')['status'], 'PASS')
        artifacts = ['AGENTS.md', '.ai/project-entry.json', mapping, spec, contract, 'docs/baseline/module.md', 'manual/preserve.md']
        sources = [{'path': 'app.py', 'evidence': 'app.py:L1-L2', 'checked': 'Stored result, missing-key exception and no mutation confirmed from direct indexing.'}]
        reviewed = [{'path': name, 'checked': 'Reviewed against dictionary lookup scope, explicit outputs/errors and current project facts.'} for name in artifacts]
        report = {'review_mode': 'same-agent-separate-pass', 'passes': [
            {'kind': kind, 'sources': sources, 'artifacts': reviewed, 'findings': []} for kind in ('source-first', 'source-recheck')]}
        self.write('manual/audit.json', kit.dump(report))
        kit.baseline_audit_record(self.root, p, 'manual/audit.json', ['app.py'], artifacts, 'agent')
        result = kit.onboarding_status(self.root, p)
        self.assertEqual(result['completion'], 'PARTIAL')
        self.assertIn('onboarding-quality-unreviewed', {x['code'] for x in result['findings']})
        report['quality_checks'] = [{'topic': topic, 'status': 'PASS', 'checked': 'Project facts match the source; all lookup responsibility is mapped; spec alone describes concrete return/error/state cases.'} for topic in ('project-entry', 'capability-coverage', 'spec-self-containment')]
        self.write('manual/audit.json', kit.dump(report))
        kit.baseline_audit_record(self.root, p, 'manual/audit.json', ['app.py'], artifacts, 'agent')
        result = kit.onboarding_status(self.root, p)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['completion'], 'COMPLETE_DECLARED')
        self.assertIn('Not assessed', result['execution'])
