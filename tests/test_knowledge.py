"""REQ-KNOWLEDGE-001: evidence lifecycle, behavior cases and a single decision ledger."""

from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class KnowledgeTests(RepositoryCase):
    def setup_app(self):
        self.write('app.py', 'def double(value):\n    return value * 2\n')
        p = self.initialize('existing')
        self.review_app(p)
        return p

    def test_static_explanation_keeps_immutable_snapshot_and_detects_source_change(self):
        p = self.setup_app()
        first = kit.knowledge_status(self.root, p)['documents'][0]
        original = (self.root / first['snapshot'] / 'document.md').read_bytes()
        self.write('app.py', 'def double(value):\n    return value + value\n')
        self.assertEqual(kit.knowledge_status(self.root, p)['status'], 'PENDING')
        kit.baseline_inventory(self.root, p)
        self.review_app(p)
        second = kit.knowledge_status(self.root, p)['documents'][0]
        self.assertNotEqual(first['snapshot'], second['snapshot'])
        self.assertEqual((self.root / first['snapshot'] / 'document.md').read_bytes(), original)
        self.assertEqual(second['freshness'], 'current')
        self.assertEqual(second['level'], 'static-declared')

    def test_contract_review_does_not_claim_whole_source_understanding(self):
        self.write('app.py', 'def double(value):\n    return value * 2\n')
        p = self.initialize('existing')
        document = 'docs/baseline/contracts/math.md'
        self.write(document, '# Contract\n## Source version and evidence\napp.py:L1-L2\n## Inputs and outputs\nA numeric input returns twice its value.\n## Timing and failure\nSynchronous; multiplication errors propagate.\n## Compatibility and promotion\nObserved contract; acceptance remains a separate choice.\n')
        kit.knowledge_record(self.root, p, 'contract', document, ['app.py'], 'reviewer')
        self.assertTrue(kit.baseline_findings(self.root, p))
        self.assertEqual(kit.knowledge_status(self.root, p)['documents'][0]['kind'], 'contract')

    def test_behavior_cases_need_real_expectations_and_keep_existing_ids(self):
        p = self.setup_app()
        document = 'docs/baseline/cases/math.md'
        header = '# Cases\n## Scope and source\napp.py:L1-L2\n## Cases\n| ID | Preconditions | Input | Expected | Source | Verification |\n| --- | --- | --- | --- | --- | --- |\n'
        self.write(document, header)
        with self.assertRaisesRegex(kit.KitError, 'actual'):
            kit.knowledge_record(self.root, p, 'cases', document, ['app.py'], 'reviewer')
        self.write(document, header + '| C1 | numeric input | 4 | 8 | app.py:L1-L2 | NOT_RUN; fixture needed |\n')
        kit.knowledge_record(self.root, p, 'cases', document, ['app.py'], 'reviewer')
        item = next(item for item in kit.knowledge_status(self.root, p)['documents'] if item['kind'] == 'cases')
        self.assertEqual(item['cases'], ['C1'])
        self.assertEqual(item['state'], 'reviewed')

    def test_promotion_requires_current_evidence_real_spec_and_decision(self):
        p = self.setup_app()
        document = 'docs/baseline/modules/app.md'
        decision = 'docs/decisions/retain-double.md'
        self.write(decision, '# Accepted compatibility choice\nRetain public doubling behavior.\n')
        with self.assertRaisesRegex(kit.KitError, 'real current'):
            kit.knowledge_transition(self.root, p, document, 'reviewer', decision, ['REQ-MATH-001'])
        self.write('openspec/specs/math/spec.md', '### Requirement: REQ-MATH-001 Double input\nThe system SHALL double input.\n#### Scenario: Four\n- WHEN 4 arrives\n- THEN 8 returns\n')
        result = kit.knowledge_transition(self.root, p, document, 'reviewer', decision, ['REQ-MATH-001'])
        self.assertEqual(result['state'], 'promoted')
        self.write('app.py', 'def double(value):\n    return value * 3\n')
        with self.assertRaisesRegex(kit.KitError, 'stale'):
            kit.knowledge_transition(self.root, p, document, 'reviewer', decision, ['REQ-MATH-001'])

    def test_decision_view_comes_from_one_ledger_and_keeps_resolution_evidence(self):
        p = self.setup_app()
        kit.decision_record(self.root, p, 'BQ-001', 'fact', 'How is input doubled?', ['app.py'])
        with self.assertRaisesRegex(kit.KitError, 'reviewer'):
            kit.decision_record(self.root, p, 'BQ-001', outcome='Multiplication', reviewer='agent')
        kit.decision_record(self.root, p, 'BQ-001', outcome='Source uses multiplication.', reviewer='agent', evidence=['app.py'])
        ledger = kit.read_json(self.root / 'docs/baseline/questions.json')
        self.assertEqual(len(ledger['questions']), 1)
        self.assertEqual(ledger['questions'][0]['status'], 'resolved')
        self.assertEqual(ledger['questions'][0]['evidence']['app.py'], kit.digest((self.root / 'app.py').read_bytes()))
        view = (self.root / 'docs/baseline/questions.md').read_text()
        self.assertIn('Generated from', view)
        self.assertIn('Source uses multiplication.', view)

    def test_existing_localized_manual_sections_can_be_reused(self):
        self.write('app.py', 'def double(value):\n    return value * 2\n')
        p = self.initialize('existing')
        document = 'manual/math.md'
        self.write(document, '# 计算模块\n## 职责\n数值翻倍。\n## 业务流程\n接收输入后返回乘二结果。\n## 状态与异常\n无持久状态；乘法异常传播。\n## 源码证据\napp.py:L1-L2\n## 未核实项\n未执行生产流量验证。\n')
        result = kit.baseline_review(self.root, p, document, ['app.py'], 'agent')
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual((self.root / document).read_text(encoding='utf-8').count('##'), 5)

    def test_native_markdown_decision_ledger_is_preserved_without_parallel_source(self):
        p = kit.default_policy('existing', ['codex'])
        p['paths']['questions'] = 'manual/open-questions.md'
        self.write(kit.POLICY, kit.dump(p))
        self.write('manual/open-questions.md', '# Existing choices\nBQ-007: retain public format.\n')
        kit.init_repo(self.root)
        self.assertFalse((self.root / 'docs/baseline/questions.json').exists())
        with self.assertRaisesRegex(kit.KitError, 'native file format'):
            kit.decision_record(self.root, p, 'BQ-008', 'fact', 'Inspect input.', ['app.py'])
        self.assertEqual((self.root / 'manual/open-questions.md').read_text(), '# Existing choices\nBQ-007: retain public format.\n')


if __name__ == '__main__':
    import unittest
    unittest.main()
