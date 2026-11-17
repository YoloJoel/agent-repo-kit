"""REQ-ONBOARDING-CONTENT-001: content and final-state counterexamples from source audits."""
import json
from unittest.mock import patch
from pathlib import Path
from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class OnboardingCompletenessTests(RepositoryCase):
    def prepare(self):
        self.write('app.py', 'def lookup(values, key):\n    return values[key]\n')
        p = self.initialize('existing')
        p['source_paths'] = ['app.py']
        self.configure(p, [])
        facts = {'purpose': 'Lookup existing values and report missing keys.', 'stack': 'Python standard library.',
                 'boundaries': 'app.py has synchronous dictionary lookup.', 'constraints': 'Lookup must not mutate input.',
                 'workflow': 'Preserve lookup behavior; characterize before changing it.',
                 'precedence': 'Explicit instructions, current specs, decisions, engineering standard.',
                 'source_evidence': {'app.py': 'app.py:L1-L2'}, 'reviewer': 'source reviewer', 'gaps': []}
        self.write('.ai/project-entry.json', kit.dump(facts))
        kit.entry_refresh(self.root, p)
        return p

    def contract(self, p, path='docs/baseline/contracts/lookup.md'):
        self.write(path, '# Lookup contract\n## Source version and evidence\napp.py:L1-L2\n## Inputs and outputs\nReturns existing values.\n## Timing and failure\nMissing keys raise KeyError; no mutation.\n## Compatibility and promotion\nPreserve lookup and missing-key behavior.\n')
        return path

    def spec(self, contract, identity='REQ-LOOKUP-001', capability='lookup'):
        return self.write(f'openspec/specs/{capability}/spec.md', f'# {capability}\n## Purpose\nThe {capability} contract.\n## Requirements\n### Requirement: {identity} Lookup\nVerification: automated\nBaseline: {contract}\nSource: app.py:L1-L2\nThe system SHALL return a stored value and raise KeyError for a missing key without mutation.\n#### Scenario: Stored key\n- WHEN a stored key is queried\n- THEN its value is returned\n')

    def test_initializer_generates_content_but_does_not_claim_review_or_cli_execution(self):
        p = self.prepare()
        text = (self.root/'openspec/config.yaml').read_text(encoding='utf-8')
        self.assertIn('context: |', text)
        self.assertIn('rules:', text)
        self.assertIn('openspec-config-unreviewed', {x['code'] for x in kit.openspec_config_findings(self.root,p)})
        self.assertEqual(kit.openspec_refresh(self.root,p)['status'], 'PENDING')
        generated = (self.root/'openspec/config.yaml').read_text(encoding='utf-8')
        self.assertIn('Lookup existing values', generated)
        reviewed = kit.openspec_record(self.root,p,'configuration reviewer')
        self.assertEqual(reviewed['status'], 'PASS')
        self.assertEqual(reviewed['native_validation'], 'NOT_ASSESSED')
        self.assertEqual(kit.openspec_config_findings(self.root,p), [])
        self.write('app.py', 'def lookup(values, key):\n    return values.get(key)\n')
        self.assertIn('openspec-config-stale', {x['code'] for x in kit.openspec_config_findings(self.root,p)})

    def test_empty_schema_only_and_language_only_configuration_cannot_pass(self):
        p = self.prepare()
        for text in ('', '# empty\n', 'schema: spec-driven\n', 'schema: spec-driven\ncontext: |\n  Language: Chinese\nrules: {}\n'):
            self.write('openspec/config.yaml',text)
            self.assertTrue(kit.openspec_config_findings(self.root,p))
            with self.assertRaises(kit.KitError): kit.openspec_record(self.root,p,'reviewer')

    def test_framework_language_context_is_not_project_specific_even_with_rules(self):
        p=self.prepare()
        kit.openspec_refresh(self.root,p)
        path=self.root/'openspec/config.yaml'
        text=path.read_text(encoding='utf-8')
        section=kit.openspec_sections(text)['context']
        path.write_text(text.replace(section,'context: |\n  Framework: Python stdlib\n  Language: Chinese\n'),encoding='utf-8')
        self.assertIn('openspec-config-content',{item['code'] for item in kit.openspec_config_findings(self.root,p)})
        with self.assertRaises(kit.KitError): kit.openspec_record(self.root,p,'reviewer')

    def test_native_schema_comments_and_edited_generated_rules_are_never_overwritten(self):
        p = self.prepare()
        native = '# Native owner rule\nschema: special-team-schema\ncontext: |\n  Preserve the accepted local authority.\nrules:\n  checklist:\n    - "Keep native checklist rules"\n'
        self.write('openspec/config.yaml',native)
        with self.assertRaisesRegex(kit.KitError,'preserved'): kit.openspec_refresh(self.root,p)
        self.assertEqual((self.root/'openspec/config.yaml').read_text(encoding='utf-8'),native)
        kit.openspec_record(self.root,p,'actual native schema reviewer')
        self.assertEqual(kit.openspec_config_findings(self.root,p),[])
        self.assertEqual(kit.init_repo(self.root)['changed'], [])
        self.assertEqual((self.root/'openspec/config.yaml').read_text(encoding='utf-8'),native)

    def test_duplicate_top_keys_and_missing_artifact_rules_are_detected(self):
        p = self.prepare()
        kit.openspec_refresh(self.root,p)
        path = self.root/'openspec/config.yaml'
        text=path.read_text(encoding='utf-8')
        path.write_text(text+'context: "competing context"\n',encoding='utf-8')
        self.assertIn('openspec-config-content',{x['code'] for x in kit.openspec_config_findings(self.root,p)})
        path.write_text(text.replace('  tasks:', '  forgotten-tasks:'),encoding='utf-8')
        self.assertIn('openspec-config-rules',{x['code'] for x in kit.openspec_config_findings(self.root,p)})

    def test_mapped_non_openspec_authority_does_not_acquire_a_competing_config(self):
        p = self.initialize('existing',path_overrides={'specs':'planning/current','changes':'planning/work'})
        self.assertFalse((self.root/'openspec/config.yaml').exists())
        self.assertEqual(kit.openspec_config_findings(self.root,p),[])
        with self.assertRaises(kit.KitError): kit.openspec_refresh(self.root,p)
        self.assertFalse((self.root/'openspec/config.yaml').exists())

    def test_referenced_contract_outside_registry_is_found_without_a_review_declaration(self):
        p = self.prepare()
        path=self.contract(p)
        self.spec(path)
        findings=kit.baseline_orphan_findings(self.root,p)
        self.assertEqual([(x['path'],x['status']) for x in findings],[(path,'FAIL')])
        self.assertIn('baseline-contract-unregistered',{x['code'] for x in kit.baseline_spec_status(self.root,p)['findings']})
        result=kit.onboarding_status(self.root,p)
        self.assertIn(path,next(x['paths'] for x in result['findings'] if x['code']=='onboarding-artifacts-unaudited'))
        kit.knowledge_record(self.root,p,'contract',path,['app.py'],'reviewer')
        self.assertEqual(kit.baseline_orphan_findings(self.root,p),[])
        result=kit.onboarding_status(self.root,p)
        self.assertIn(path,next(x['paths'] for x in result['findings'] if x['code']=='onboarding-artifacts-unaudited'))

    def test_native_contract_metadata_outside_default_directory_is_discovered(self):
        p=self.prepare()
        path='docs/baseline/native-interface.md'
        self.write(path,'---\nkind: contract\nstatus: reviewed\n---\n# Interface\nObserved input/output is documented using native sections.\n')
        self.assertIn(path,{item['path'] for item in kit.baseline_orphan_findings(self.root,p)})

    def test_final_check_detects_inputs_changing_while_it_is_running(self):
        p=self.prepare()
        original=kit.structure_findings
        def mutate(root, policy):
            result=original(root,policy)
            self.write('openspec/config.yaml','# changed while evaluating final declarations\n')
            return result
        with patch.object(kit,'structure_findings',side_effect=mutate):
            result=kit.onboarding_status(self.root,p,record=True)
        self.assertIn('onboarding-inputs-changed',{item['code'] for item in result['findings']})

    def test_new_repository_final_record_does_not_assert_a_historical_baseline(self):
        p=self.initialize('new')
        result=kit.onboarding_status(self.root,p,record=True)
        self.assertEqual(result['baseline'],'NOT_APPLICABLE')
        self.assertTrue((self.root/'.ai/runtime/final-onboarding.json').is_file())
        self.assertEqual(result['behavior_verification'],'NOT_ASSESSED')

    def test_unreferenced_contract_is_pending_not_silently_ignored(self):
        p=self.prepare(); path=self.contract(p)
        findings=kit.baseline_orphan_findings(self.root,p)
        self.assertEqual(findings[0]['status'],'PENDING')
        self.assertEqual(findings[0]['path'],path)

    def test_index_refresh_replaces_only_known_scaffold_and_tracks_promotions_staleness(self):
        p=self.prepare(); path=self.contract(p)
        kit.knowledge_record(self.root,p,'contract',path,['app.py'],'reviewer')
        readme=self.root/'docs/baseline/README.md'
        text=readme.read_text(encoding='utf-8')
        self.assertNotIn('inventory is pending review',text)
        self.assertIn('contracts/lookup.md',text)
        self.assertIn('reviewed',text)
        prefix='---\r\ntitle: Native Baseline\r\n---\r\n# Human baseline\r\nKeep this navigation note.\r\n'
        readme.write_bytes((prefix+text).encode('utf-8'))
        self.spec(path)
        self.write('decisions/preserve.md','Preserve the actual lookup result and missing-key error; actual Agent analysis.\n')
        kit.knowledge_transition(self.root,p,path,'reviewer','decisions/preserve.md',['REQ-LOOKUP-001'])
        self.assertTrue(readme.read_bytes().startswith(prefix.encode('utf-8')))
        self.assertIn('promoted',readme.read_text(encoding='utf-8'))
        self.assertIn('REQ-LOOKUP-001',readme.read_text(encoding='utf-8'))
        self.write('app.py','def lookup(values, key):\n    return values.get(key)\n')
        self.assertTrue(kit.baseline_index_findings(self.root,p))
        kit.baseline_index_refresh(self.root,p)
        self.assertIn('stale',readme.read_text(encoding='utf-8'))
        self.assertEqual(kit.baseline_index_findings(self.root,p),[])
        before=readme.read_bytes();kit.baseline_index_refresh(self.root,p)
        self.assertEqual(readme.read_bytes(),before)

    def test_final_record_is_invalidated_by_content_or_audit_registration_not_mtime(self):
        p=self.prepare()
        kit.onboarding_status(self.root,p,record=True)
        self.assertNotIn('onboarding-final-check-stale',{x['code'] for x in kit.onboarding_status(self.root,p)['findings']})
        (self.root/'AGENTS.md').touch()
        self.assertNotIn('onboarding-final-check-stale',{x['code'] for x in kit.onboarding_status(self.root,p)['findings']})
        self.write('docs/baseline/audits.json',kit.dump({'schema_version':1,'reports':{}}))
        self.assertIn('onboarding-final-check-stale',{x['code'] for x in kit.onboarding_status(self.root,p)['findings']})
        kit.onboarding_status(self.root,p,record=True)
        self.write('openspec/config.yaml','# erased configuration\n')
        self.assertIn('onboarding-final-check-stale',{x['code'] for x in kit.onboarding_status(self.root,p)['findings']})

    def test_empty_structure_pass_cannot_imply_onboarding_complete(self):
        p=self.prepare()
        report=kit.verify(self.root,p,'structure')
        self.assertEqual(report['status'],'PASS',report)
        self.assertFalse(report['onboarding_complete'])
        self.assertIn('empty specifications',report['scope'])
        result=kit.onboarding_status(self.root,p,record=True)
        self.assertEqual(result['completion'],'PARTIAL')
        self.assertEqual(result['specification_status'],'PENDING')

    def test_missing_test_stacks_are_explicitly_counted_and_cannot_be_verified(self):
        p=self.prepare();self.write('protocol.c','int value(void) { return 1; }\n')
        self.spec('docs/baseline/contract-a.md','REQ-PY-001','python-lookup')
        self.spec('docs/baseline/contract-b.md','REQ-C-001','c-protocol')
        result=kit.onboarding_status(self.root,p,record=True)
        self.assertEqual(result['verification_gaps']['missing_mapping_count'],2)
        self.assertEqual(result['verification_mapping_status'],'PENDING')
        self.assertEqual(result['behavior_verification'],'NOT_ASSESSED')
        self.write('tests/test_lookup.py','import unittest\nfrom app import lookup\n# REQ-PY-001\nclass LookupTest(unittest.TestCase):\n    def test_value(self):\n        values = {"a": 3}\n        self.assertEqual(lookup(values, "a"), 3)\n        with self.assertRaises(KeyError): lookup(values, "b")\n        self.assertEqual(values, {"a": 3})\n')
        result=kit.onboarding_status(self.root,p,record=True)
        self.assertEqual(result['verification_gaps']['missing_mapping_count'],1)
        self.assertIn('openspec/specs/c-protocol/spec.md',result['verification_gaps']['missing_mapping_by_spec'])
