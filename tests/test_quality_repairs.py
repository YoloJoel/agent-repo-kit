"""Reproduce the November audit counterexamples against public disposable consumers."""
import json
import subprocess
import sys
import copy
import tempfile
from pathlib import Path

from agent_repo_kit import core as kit
import test_behavior_quality as fixtures
import test_behavior_verification as verification_fixtures
from test_workflows import RepositoryCase


class ClaimRepairTests(fixtures.BehaviorQualityTests):
    # Run only these new cases; the base fixture's own tests run in its module.
    def test_one_declared_failure_case_cannot_complete_source_discovery(self):
        p,data=self.prepare();self.record(p,data)
        self.record_sample(p,self.source_sample([{'id':'offline','stimulus':'send("offline")','path':'transport.py',
                                                 'reference':'transport.py:L1-L2','source_outcome':False}]))
        result=kit.onboarding_status(self.root,p)
        self.assertEqual(result['source_cases']['status'],'PASS')
        self.assertEqual(result['status'],'PENDING')
        self.assertTrue(any(item.get('path')=='transport.py' and item.get('kind')=='return-true'
                            for item in result['discovery']['findings']))

    def test_added_wrong_scenario_is_not_silently_outside_review(self):
        p, data = self.prepare()
        spec = self.root / data['units'][0]['spec_path']
        spec.write_text(spec.read_text() + '\n#### Scenario: Success\n- WHEN send("ok")\n- THEN return 42\n')
        result = self.record(p, data)
        self.assertIn('behavior-scenario-unmapped', self.codes(result))
        self.assertEqual(result['status'], 'PENDING')

    def test_condition_changes_invalidate_scenario_review(self):
        p, data = self.prepare()
        spec = self.root / data['units'][0]['spec_path']
        spec.write_text(spec.read_text().replace('WHEN value is absent', 'WHEN value is present'))
        self.assertIn('behavior-scenario-unmapped', self.codes(self.record(p, data)))

    def test_fenced_output_is_bound_but_fake_fenced_headings_are_not_scenarios(self):
        p,data=self.prepare();spec=self.root/data['units'][0]['spec_path']
        spec.write_text(spec.read_text()+'\n```json\n{"status": false}\n#### Scenario: example only\n```\n')
        scenarios=kit.spec_scenarios(spec.read_text());self.assertEqual(len(scenarios),1)
        data['units'][0]['acceptance_cases'][0]['scenarios']=[{k:v for k,v in s.items() if k!='body'} for s in scenarios]
        self.assertNotIn('behavior-scenario-unmapped',self.codes(self.record(p,data)))
        spec.write_text(spec.read_text().replace('"status": false','"status": true'))
        self.assertIn('behavior-scenario-unmapped',self.codes(self.record(p,data)))

    def test_undefined_result_cannot_reuse_old_deciding_premises(self):
        p, data = self.prepare()
        unit = data['units'][0]
        spec = self.root / unit['spec_path']
        spec.write_text(spec.read_text().replace(unit['normative_quote'], 'The sender SHALL return the configured result.')
                        .replace('- THEN return false', '- THEN return the configured result.'))
        unit['normative_quote'] = 'The sender SHALL return the configured result.'
        unit['acceptance_cases'][0]['spec_quote'] = '- THEN return the configured result.'
        self.assertIn('behavior-case-premises', self.codes(self.record(p, data)))

    def test_call_substring_is_not_an_assertion(self):
        _, data = self.prepare()
        test = dict(data['units'][0]['tests'][0])
        test['assertion'] = 'send("offline")'
        self.assertFalse(kit.behavior_assertion_valid(self.root, test))
        test['assertion'] = 'assert send("offline") is False'
        self.assertTrue(kit.behavior_assertion_valid(self.root, test))

    def test_unrelated_unit_retains_evidence_after_source_change(self):
        p, data = self.prepare()
        unit = copy.deepcopy(data['units'][0]); unit['id'] = 'BEH-OTHER-001'; unit['requirement'] = 'REQ-OTHER-001'
        unit['spec_path'] = 'openspec/specs/other/spec.md'
        self.write(unit['spec_path'], (self.root/'openspec/specs/send/spec.md').read_text().replace('REQ-SEND-001','REQ-OTHER-001'))
        self.write('other.py', (self.root/'app.py').read_text())
        self.write('tests/test_other.py', (self.root/'tests/test_send.py').read_text().replace('from app','from other'))
        for anchor in unit['evidence'] + unit['tests']:
            anchor['path'] = anchor['path'].replace('app.py','other.py').replace('test_send.py','test_other.py')
            anchor['reference'] = anchor['reference'].replace('app.py','other.py').replace('test_send.py','test_other.py')
        p['source_paths'].append('other.py'); self.configure(p,p['checks']);data['sources'].append('other.py');data['units'].append(unit)
        self.assertEqual(self.record(p,data)['coverage']['reviewed_units'],2)
        self.write('app.py',(self.root/'app.py').read_text()+'\n# source changed\n')
        status=kit.behavior_status(self.root,p)
        self.assertEqual(status['stale_units'],['BEH-SEND-001'])
        self.assertEqual(status['coverage']['reviewed_units'],1)

    def test_explain_is_read_only_and_shows_actual_evidence(self):
        p,data=self.prepare();self.record(p,data)
        before={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        result=kit.explain(self.root,p,'REQ-SEND-001')
        self.assertEqual(result['units'][0]['tests'][0]['assertion'],'assert send("offline") is False')
        after={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(before,after)

    def test_canonical_aliases_detect_conflicting_shared_contracts(self):
        p,data=self.prepare();other=copy.deepcopy(data['units'][0]);other['id']='BEH-SECOND-001'
        other['contract_facts']=[{'key':'delivery.retries','condition':'sync','value':3}]
        data['units'].append(other)
        data['contract_catalog']={'delivery.retries':{'aliases':['publish.retries'],'conditions':{'send current synchronous path':'sync'}}}
        self.assertIn('behavior-contract-conflict',self.codes(self.record(p,data)))


# Reuse setup helpers without duplicating the parent's regression suite.
for _name in tuple(dir(fixtures.BehaviorQualityTests)):
    if _name.startswith('test_') and _name not in ClaimRepairTests.__dict__:
        setattr(ClaimRepairTests, _name, None)


class ExecutionRepairTests(verification_fixtures.BehaviorVerificationTests):
    def test_never_called_regression_cannot_anchor_or_deliver(self):
        p = self.prepare()
        self.write('tests/preserve.py', 'def test_should_fail():\n    assert False\n')
        ready = kit.verify(self.root, p, 'ready', 'refactor')
        self.assertEqual(ready['status'], 'PENDING', ready)
        self.assertEqual(ready['checks'][0]['command_status'], 'PASS')
        self.assertEqual(ready['checks'][0]['case_execution']['executed'], 0)
        self.assertFalse((self.root / 'openspec/changes/refactor/baseline-anchor.json').exists())
        self.assertNotEqual(kit.verify(self.root, p, 'delivery', 'refactor')['status'], 'PASS')

    def test_actual_regression_fails_and_restores(self):
        p = self.prepare()
        self.assertEqual(kit.verify(self.root, p, 'ready', 'refactor')['status'], 'PASS')
        original = (self.root / 'app.py').read_text()
        self.write('app.py', original.replace('return x * 2', 'return 99'))
        bad = kit.verify(self.root, p, 'delivery', 'refactor')
        self.assertEqual(bad['checks'][0]['case_execution']['status'], 'FAIL')
        self.write('app.py', original)
        self.assertEqual(kit.verify(self.root, p, 'delivery', 'refactor')['status'], 'PASS')


for _name in tuple(dir(verification_fixtures.BehaviorVerificationTests)):
    if _name.startswith('test_') and _name not in ExecutionRepairTests.__dict__:
        setattr(ExecutionRepairTests, _name, None)


class ReportAdapterTests(RepositoryCase):
    def test_unsupported_python_flags_keep_actual_command_semantics(self):
        run=self.root/'.ai/runtime/runs/isolated';run.mkdir(parents=True)
        command=['{python}','-I','-c','from pathlib import Path; Path("actually-ran").write_text("yes")']
        result=kit.run_check(self.root,{'name':'isolated','argv':command},run,{'cases':[],'fixtures':[]})
        self.assertEqual(result['command_status'],'PASS')
        self.assertEqual((self.root/'actually-ran').read_text(),'yes')
        self.assertEqual(result['status'],'PENDING')

    def report(self, xml, required=('Suite::target',)):
        run = self.root / '.ai/runtime/runs' / kit.uuid.uuid4().hex
        run.mkdir(parents=True)
        code = 'import os; from pathlib import Path; Path(os.environ["ARK_CASE_REPORT"]).write_text(' + repr(xml) + ')'
        return kit.run_check(self.root, {'name':'junit', 'argv':['{python}', '-c', code],
                                        'case_report':{'format':'junit','required_cases':list(required)}}, run)

    def test_selected_skipped_missing_and_failed_cases(self):
        for body, expected in [('<testcase classname="Suite" name="target"/>','PASS'),
                               ('<testcase classname="Suite" name="target"><skipped/></testcase>','PENDING'),
                               ('<testcase classname="Suite" name="other"/>','PENDING'),
                               ('<testcase classname="Suite" name="target"><failure/></testcase>','FAIL'),
                               ('','PENDING')]:
            with self.subTest(body=body):
                result=self.report('<testsuite>'+body+'</testsuite>')
                self.assertEqual(result['command_status'],'PASS')
                self.assertEqual(result['status'],expected,result)

    def test_old_run_id_and_duplicate_cases_rejected(self):
        path=self.write('report.json',json.dumps({'schema_version':1,'run_id':'old','cases':[{'id':'a','status':'PASS'}]}))
        with self.assertRaises(kit.KitError): kit.execution_cases(path,'ark-json','new')
        xml='<testsuite><testcase classname="Suite" name="target"/><testcase classname="Suite" name="target"/></testsuite>'
        self.assertEqual(self.report(xml)['status'],'PENDING')

    def test_command_only_check_keeps_its_existing_contract(self):
        run=self.root/'.ai/runtime/runs/command';run.mkdir(parents=True)
        result=kit.run_check(self.root,{'name':'build','argv':['{python}','-c','pass']},run)
        self.assertEqual(result['status'],'PASS')
        self.assertNotIn('case_execution',result)


class DiscoveryRepairTests(RepositoryCase):
    def prepare(self):
        self.write('transport.py','def publish(value):\n    return value != "offline"\n')
        self.write('consumer.py','from transport import publish\ndef submit(value):\n    return publish(value)\n')
        p=self.initialize('existing');p['source_paths']=['transport.py','consumer.py'];self.configure(p,[])
        return p

    def test_source_only_scan_keeps_both_undeclared_return_alternatives(self):
        p=self.prepare()
        scan=kit.discovery_scan(self.root,p)
        branches=[row for row in scan['candidates'] if row['path']=='transport.py']
        self.assertTrue({'return-true','return-false'}.issubset({row['kind'] for row in branches}))
        self.assertGreater(kit.discovery_status(self.root,p)['unreviewed'],0)
        rows=[{**row,'disposition':'baseline','reason':'Keep observed behavior as unpromoted evidence.'}
              for row in scan['candidates'] if row['kind']!='return-true']
        self.write('docs/discovery.json',kit.dump({'schema_version':1,'candidates':rows}))
        result=kit.discovery_record(self.root,p,'docs/discovery.json','source reviewer')
        self.assertEqual(result['unreviewed'],1)
        self.assertEqual(result['findings'][0]['kind'],'return-true')

    def test_missing_dependency_surfaces_consumer_without_inventory_edge(self):
        p=self.prepare()
        result=kit.behavior_impact(self.root,p,['transport.py'])
        self.assertIn('consumer.py',result['source_candidates'])
        self.assertEqual(result['candidate_edges'][0]['producer'],'transport.py')

    def test_new_source_and_source_changes_invalidate_only_own_dispositions(self):
        p=self.prepare();scan=kit.discovery_scan(self.root,p)
        self.write('docs/discovery.json',kit.dump({'schema_version':1,'candidates':[
            {**row,'disposition':'baseline','reason':'Static behavior retained without a current promise.'} for row in scan['candidates']]}))
        self.assertEqual(kit.discovery_record(self.root,p,'docs/discovery.json','reviewer')['status'],'PASS')
        self.write('transport.py','def publish(value):\n    return value == "offline"\n')
        result=kit.discovery_status(self.root,p)
        self.assertEqual({f['path'] for f in result['findings']},{'transport.py'})


class FrozenReadbackTests(RepositoryCase):
    def prepare(self, identity='first'):
        self.write('app.py','def value():\n    return 7\n')
        p=self.initialize('existing');p['source_paths']=['app.py'];self.configure(p,[])
        self.spec='openspec/specs/value/spec.md'
        self.write(self.spec,'# Value\n### Requirement: REQ-VALUE-001\nThe value SHALL be 7.\n#### Scenario: Read\n- WHEN value() is called\n- THEN return 7\n')
        self.write('questions.json',kit.dump({'questions':[{'id':'read','stimulus':'value()'}]}))
        kit.readback_open(self.root,p,identity,'questions.json','examiner')
        self.write('predictions.json',kit.dump({'answers':[{'id':'read','status':'predicted','expected':7,
                                                        'premises':[{'path':self.spec,'quote':'The value SHALL be 7.'}]}]}))
        self.write('judgment.json',kit.dump({'answers':[{'id':'read','status':'entailed','observed':7,'reason':'The literal return is 7; the Spec gives this exact output.',
                                                     'evidence':[{'path':'app.py','reference':'app.py:L1-L2','role':'effect','explains':'returns literal 7'}]}]}))
        return p

    def test_predictions_precede_judgment_and_cannot_be_overwritten(self):
        p=self.prepare()
        with self.assertRaises(kit.KitError): kit.readback_record(self.root,p,'first','judgment.json','judge',True)
        self.assertEqual(kit.readback_record(self.root,p,'first','predictions.json','reader')['status'],'PENDING')
        with self.assertRaises(kit.KitError): kit.readback_record(self.root,p,'first','predictions.json','reader')
        self.assertEqual(kit.readback_record(self.root,p,'first','judgment.json','judge',True)['status'],'PASS')
        reader=kit.read_json(kit.readback_directory(self.root,p,'first')/'reader.json')
        self.assertEqual(set(reader),{'schema_version','questions','specs'})

    def test_stale_round_is_retained_without_blocking_a_new_completed_round(self):
        p=self.prepare();kit.readback_record(self.root,p,'first','predictions.json','reader')
        self.write('app.py','def value():\n    return 7  # rechecked\n')
        with self.assertRaises(kit.KitError): kit.readback_record(self.root,p,'first','judgment.json','judge',True)
        kit.readback_open(self.root,p,'second','questions.json','examiner')
        kit.readback_record(self.root,p,'second','predictions.json','reader')
        result=kit.readback_record(self.root,p,'second','judgment.json','judge',True)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(kit.readback_status(self.root,p)['active'],'second')
        self.assertEqual(kit.readback_status(self.root,p,'first')['status'],'PENDING')

    def test_ambiguous_prediction_cannot_be_closed_by_matching_source_value(self):
        p=self.prepare()
        self.write('predictions.json',kit.dump({'answers':[{'id':'read','status':'ambiguous','missing':'No deciding premise.'}]}))
        kit.readback_record(self.root,p,'first','predictions.json','reader')
        with self.assertRaises(kit.KitError): kit.readback_record(self.root,p,'first','judgment.json','judge',True)


class ProvenanceRepairTests(RepositoryCase):
    def test_rule_source_changes_reopen_obligations(self):
        p=self.initialize();self.write('rules.md','Schema changes require an accepted ADR.\n')
        p['artifact_rules']={'schema':{'source':'rules.md','requires':['adr'],'paths':['db.py']}}
        self.assertEqual(kit.rule_status(self.root,p)['status'],'PENDING')
        self.assertEqual(kit.rule_record(self.root,p,'reviewer')['status'],'PASS')
        self.write('rules.md','Schema changes require an accepted ADR and a migration test.\n')
        self.assertEqual(kit.rule_status(self.root,p)['findings'][0]['code'],'rule-source-unreviewed')

    def test_external_aliases_disambiguate_and_changes_invalidate_fingerprint(self):
        p=self.initialize()
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            for directory in (first,second): (Path(directory)/'spec.md').write_text('response is 7')
            self.write('external.json',kit.dump({'dependencies':[{'alias':alias,'root':directory,'files':['spec.md']} for alias,directory in [('alpha',first),('beta',second)]]}))
            result=kit.external_record(self.root,p,'external.json','reviewer')
            self.assertEqual(set(result['files']),{'alpha::spec.md','beta::spec.md'})
            original=kit.fingerprint(self.root,p)
            (Path(second)/'spec.md').write_text('response is 9')
            self.assertEqual(kit.external_status(self.root,p)['findings'][0]['source'],'beta::spec.md')
            self.assertNotEqual(kit.fingerprint(self.root,p),original)
