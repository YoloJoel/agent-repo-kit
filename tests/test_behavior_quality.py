"""REQ-BEHAVIOR-QUALITY-001: counterexamples to file/ID-only semantic completion."""
import copy
import json
import subprocess
import sys
from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class BehaviorQualityTests(RepositoryCase):
    def prepare(self):
        self.write('app.py', 'from transport import publish\ndef send(value):\n    if value is None:\n        return False\n    return publish(value)\n')
        self.write('transport.py', 'def publish(value):\n    return value != "offline"\n')
        self.write('tests/test_send.py', 'from app import send\nassert send(None) is False\nassert send("ok") is True\nassert send("offline") is False\n')
        p = self.initialize('existing')
        p['source_paths'] = ['app.py', 'transport.py']
        p['checks'] = [{'name': 'native-tests', 'argv': ['{python}', '-c', "exec(open('tests/test_send.py').read())"]}]
        self.configure(p, p['checks'])
        self.write('openspec/specs/send/spec.md', '# Send\n## Purpose\nPublish accepted values.\n## Requirements\n### Requirement: REQ-SEND-001 Send\nVerification: automated\nThe sender SHALL return false for absent input or failed publishing.\n#### Scenario: Failure\n- WHEN value is absent or publishing fails\n- THEN return false\n')
        def anchor(path, ref, role, explains):
            return {'path': path, 'reference': ref, 'role': role, 'explains': explains}
        evidence = [anchor('app.py', 'app.py:L2-L5', 'entry', 'Actual send caller checks None then calls transport.'),
                    anchor('app.py', 'app.py:L3-L4', 'branch', 'None returns false before publishing.'),
                    anchor('transport.py', 'transport.py:L1-L2', 'effect', 'Offline returns false, no retry or durable queue.')]
        unit = {'id': 'BEH-SEND-001', 'capability': 'publish result propagation', 'owner': 'send and transport',
                'trigger': 'send(value)', 'condition': 'None or offline input', 'outcome': 'False, no reliable-delivery promise',
                'confidence': 'verified', 'disposition': 'current', 'reason': 'Preserve observed failure signaling.',
                'requirement': 'REQ-SEND-001', 'spec_path': 'openspec/specs/send/spec.md',
                'normative_quote': 'The sender SHALL return false for absent input or failed publishing.',
                'acceptance_cases': [{'status': 'compared', 'stimulus': 'send("offline")',
                                      'spec_quote': '- THEN return false', 'expected': False, 'source_outcome': False,
                                      'source_reference': 'transport.py:L1-L2'}],
                'evidence': evidence, 'depends_on': [],
                'dimensions': {k: {'status': 'reviewed' if k in {'normal', 'negative', 'boundary'} else 'not-applicable',
                                  'reason': 'Synchronous stateless call; source has no retry/concurrency/owned resources or migration.'} for k in kit.BEHAVIOR_DIMENSIONS},
                'challenge': {'counterexample': 'Offline publishing returns false; a reliable delivery claim is refuted.',
                              'alternative': 'None could have been published; the early return prevents it.', 'result': 'supported',
                              'reason': 'Read validation order and propagated transport failure separately.'},
                'verification': 'automated', 'contract_facts': [{'key': 'publish.retries', 'condition': 'send current synchronous path', 'value': 0}],
                'tests': [{**anchor('tests/test_send.py', 'tests/test_send.py:L2-L4', 'assertion', 'Real negative and boundary asserts.'),
                           'input': 'None, ok, offline', 'expected': 'false, true, false', 'assertion': 'assert send("offline") is False',
                           'detects': 'Changing best-effort failure to true fails the assertion.', 'checks': ['native-tests']}]}
        data = {'schema_version': 1, 'scope': 'whole', 'scope_reason': 'Both production modules, tests separate.',
                'sources': ['app.py', 'transport.py'],
                'discovery': {'method': 'Trace entry to validation to cross-module publish effect.', 'source_first': 'Read production before writing specs.', 'independence': 'same-agent-separate-pass'},
                'surfaces': {k: {'status': 'applicable' if k in {'api', 'messages'} else 'not-applicable',
                                 'reason': 'Synchronous in-process publishing, no storage/config/upgrade/background loops.',
                                 'evidence': [evidence[0]], 'units': [unit['id']] if k in {'api', 'messages'} else []} for k in kit.BEHAVIOR_SURFACES},
                'units': [unit]}
        return p, data

    def record(self, p, data):
        self.write('docs/baseline/behavior-inventory.json', kit.dump(data))
        return kit.behavior_record(self.root, p, 'docs/baseline/behavior-inventory.json', 'actual reviewer')

    def codes(self, result):
        return {x['code'] for x in result['findings']}

    def test_valid_branch_assertion_review_is_not_execution(self):
        p, data = self.prepare()
        result = self.record(p, data)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['coverage']['ratio'], 1)
        self.assertEqual(result['execution'], 'NOT_ASSESSED')
        run = subprocess.run([sys.executable, '-c', "exec(open('tests/test_send.py').read())"], cwd=self.root, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_existing_assets_do_not_acquire_semantic_approval_on_upgrade(self):
        p, _ = self.prepare()
        self.assertIn('behavior-inventory-missing', self.codes(kit.onboarding_status(self.root, p)))

    def test_directory_coverage_cannot_hide_message_surface_gap(self):
        p, data = self.prepare()
        data['surfaces']['messages']['units'] = []
        self.assertIn('behavior-surface-gap', self.codes(self.record(p, data)))

    def test_missing_crosscutting_applicability_is_rejected(self):
        p, data = self.prepare()
        del data['surfaces']['lifecycle']
        with self.assertRaisesRegex(kit.KitError, 'applicability'): self.record(p, data)

    def test_constant_definition_is_not_effective_path(self):
        p, data = self.prepare()
        data['units'][0]['evidence'] = [{**data['units'][0]['evidence'][0], 'role': 'definition'}]
        self.assertIn('behavior-evidence-chain', self.codes(self.record(p, data)))

    def test_missing_error_dimension_and_unknown_recovery_cannot_close(self):
        p, data = self.prepare()
        data['units'][0]['dimensions']['recovery']['status'] = 'unknown'
        self.assertIn('behavior-dimension-gap', self.codes(self.record(p, data)))
        del data['units'][0]['dimensions']['negative']
        with self.assertRaisesRegex(kit.KitError, 'dimensions'): self.record(p, data)

    def test_guesses_and_defects_cannot_be_promoted_to_current(self):
        for confidence in ('inferred', 'unknown', 'defect'):
            p, data = self.prepare()
            data['units'][0]['confidence'] = confidence
            self.assertIn('behavior-unverified-promise', self.codes(self.record(p, data)))

    def test_unknowns_are_preserved_as_gaps_without_normative_promotion(self):
        p, data = self.prepare()
        u = data['units'][0]
        u.update(confidence='unknown', disposition='gap', reason='Cannot establish external delivery outcome.')
        u.pop('requirement')
        result = self.record(p, data)
        self.assertEqual(result['status'], 'PENDING')
        self.assertEqual(result['coverage']['unresolved_units'], 1)

    def test_wrong_spec_prediction_fails_despite_real_anchors_and_passing_tests(self):
        p, data = self.prepare()
        spec = self.root / data['units'][0]['spec_path']
        spec.write_text(spec.read_text().replace('- THEN return false', '- THEN return 0'), encoding='utf-8')
        unit = data['units'][0]
        case = unit['acceptance_cases'][0]
        source_result = subprocess.run([sys.executable, '-c', 'import json; from app import send; print(json.dumps(send("offline")))'],
                                       cwd=self.root, capture_output=True, text=True, check=True)
        case.update(spec_quote='- THEN return 0', expected=0, source_outcome=json.loads(source_result.stdout))
        subprocess.run([sys.executable, '-c', "exec(open('tests/test_send.py').read())"], cwd=self.root, check=True)
        result = self.record(p, data)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('behavior-case-contradicted', self.codes(result))

    def test_existing_case_free_inventory_can_be_read_and_refreshed(self):
        p, data = self.prepare()
        cases = data['units'][0].pop('acceptance_cases')
        self.assertIn('behavior-case-missing', self.codes(self.record(p, data)))
        self.assertEqual(kit.behavior_status(self.root, p)['status'], 'PENDING')
        data['units'][0]['acceptance_cases'] = cases
        self.assertEqual(self.record(p, data)['status'], 'PASS')

    def test_unclear_spec_or_unavailable_source_cannot_close_a_case(self):
        p, data = self.prepare()
        case = data['units'][0]['acceptance_cases'][0]
        for status in ('spec-ambiguous', 'source-unknown'):
            with self.subTest(status=status):
                case['status'] = status
                self.assertIn('behavior-case-gap', self.codes(self.record(p, data)))

    def test_case_needs_its_own_spec_outcome_and_decisive_source_reference(self):
        p, data = self.prepare()
        case = data['units'][0]['acceptance_cases'][0]
        case.update(spec_quote='Verification: automated', source_reference='app.py:L2-L5')
        self.assertTrue({'behavior-case-spec-evidence', 'behavior-case-source-evidence'}.issubset(
            self.codes(self.record(p, data))))
        case.pop('expected')
        self.assertIn('behavior-case-incomplete', self.codes(self.record(p, data)))

    def test_contradiction_has_priority_over_format_compliance(self):
        p, data = self.prepare()
        data['units'][0]['challenge']['result'] = 'contradicted'
        self.assertEqual(self.record(p, data)['status'], 'FAIL')

    def test_same_condition_contract_conflict_is_not_hidden_across_specs(self):
        p, data = self.prepare()
        second = copy.deepcopy(data['units'][0])
        second['id'] = 'BEH-SEND-002'
        second['contract_facts'][0]['value'] = 3
        data['units'].append(second)
        self.assertIn('behavior-contract-conflict', self.codes(self.record(p, data)))
        second['contract_facts'][0]['condition'] = 'separate external retry wrapper'
        self.assertNotIn('behavior-contract-conflict', self.codes(self.record(p, data)))

    def test_spec_clause_changes_not_just_requirement_id_are_detected(self):
        p, data = self.prepare()
        self.record(p, data)
        path = self.root/'openspec/specs/send/spec.md'
        path.write_text(path.read_text().replace('return false', 'retry forever'), encoding='utf-8')
        self.assertTrue({'behavior-claim-drift', 'behavior-evidence-stale'}.issubset(self.codes(kit.behavior_status(self.root,p))))

    def test_requirement_reference_and_comment_are_not_assertions(self):
        p, data = self.prepare()
        self.write('tests/test_send.py', '# assert send("offline") is False\n# REQ-SEND-001\n')
        data['units'][0]['tests'][0]['reference'] = 'tests/test_send.py:L1-L2'
        self.assertIn('behavior-test-comment', self.codes(self.record(p, data)))

    def test_assertion_needs_actual_command_mapping(self):
        p, data = self.prepare()
        data['units'][0]['tests'][0]['checks'] = ['nonexistent']
        self.assertIn('behavior-test-command', self.codes(self.record(p, data)))

    def test_assertion_reference_does_not_accept_a_coverage_readme(self):
        p, data = self.prepare()
        self.write('tests/README.md', 'assert send("offline") is False\n')
        data['units'][0]['tests'][0].update(path='tests/README.md', reference='tests/README.md:L1')
        with self.assertRaisesRegex(kit.KitError, 'README'): self.record(p, data)

    def test_source_test_policy_and_new_source_drift_invalidate(self):
        p, data = self.prepare()
        self.record(p, data)
        for path in ('transport.py', 'tests/test_send.py', kit.POLICY):
            target = self.root/path
            original = target.read_bytes()
            target.write_bytes(original+b'\n')
            self.assertIn('behavior-evidence-stale', self.codes(kit.behavior_status(self.root,p)))
            target.write_bytes(original)
        p['source_paths'] = ['.']
        self.configure(p, p['checks'])
        self.record(p, {**data, 'sources': sorted(kit.capability_sources(self.root,p))})
        self.write('new_worker.py', 'def tick(): return None\n')
        self.assertIn('behavior-evidence-stale', self.codes(kit.behavior_status(self.root,p)))

    def test_downgrade_needs_disposition_and_preserves_old_snapshot(self):
        p, data = self.prepare()
        self.record(p,data)
        snapshots = {x: x.read_bytes() for x in (self.root/kit.evidence_root(p)/'behaviors').rglob('*') if x.is_file()}
        data['units'][0].update(verification='manual', tests=[])
        with self.assertRaisesRegex(kit.KitError, 'downgrade'): self.record(p,data)
        data['units'][0]['verification_change'] = {'reason': 'Interception unavailable.', 'alternatives': 'Reviewed transport integration harness.', 'remaining_gap': 'No manual run performed.', 'reviewer': 'actual reviewer'}
        result = self.record(p,data)
        self.assertNotEqual(result['status'], 'PASS')
        self.assertEqual(len(result['verification_changes']),1)
        for path, content in snapshots.items(): self.assertEqual(path.read_bytes(),content)

    def test_behavior_denominator_cannot_silently_shrink(self):
        p,data = self.prepare()
        second = copy.deepcopy(data['units'][0]); second['id']='BEH-SECOND-001'
        data['units'].append(second)
        self.record(p,data)
        data['units'].pop()
        with self.assertRaisesRegex(kit.KitError,'denominator'): self.record(p,data)

    def test_cross_module_impact_follows_declared_dependencies(self):
        p,data = self.prepare()
        u=data['units'][0]
        u['evidence'] = [e for e in u['evidence'] if e['path']=='app.py']
        other=copy.deepcopy(u); other.update(id='BEH-TRANSPORT-001', evidence=[{'path':'transport.py','reference':'transport.py:L1-L2','role':'effect','explains':'Publish result.'}])
        u['depends_on']=[other['id']]
        data['units'].append(other)
        self.record(p,data)
        impact=kit.behavior_impact(self.root,p,['transport.py'])
        self.assertEqual(impact['direct'],[other['id']])
        self.assertEqual(impact['transitive'],[u['id']])

    def test_vendored_cli_and_engineering_readiness_do_not_run_business_commands(self):
        p,data=self.prepare()
        self.record(p,data)
        result=subprocess.run([sys.executable,str(self.root/'hack/ai/ark.py'),'--repo',str(self.root),'baseline','behavior-status'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        status=kit.engineering_status(self.root,p)
        self.assertEqual(status['execution'],'NOT_RUN')
        self.assertEqual(status['ranges'][0]['test_source_files'],1)

    def test_legitimate_url_hash_and_comment_tokens_inside_assertion_strings(self):
        p,data=self.prepare()
        for value in ('http://host/#fragment','topic#field','/*literal*/'):
            assertion=f'assert send({value!r}) is True'
            self.write('tests/test_send.py','from app import send\n'+assertion+'\n')
            data['units'][0]['tests'][0].update(reference='tests/test_send.py:L2',assertion=assertion)
            self.assertNotIn('behavior-test-comment',self.codes(self.record(p,data)))

    def test_additional_normative_clause_needs_its_own_review(self):
        p,data=self.prepare()
        self.write('openspec/specs/send/spec.md',(self.root/'openspec/specs/send/spec.md').read_text()+'\nThe sender MUST retry forever.\n')
        self.assertIn('behavior-clause-unmapped',self.codes(self.record(p,data)))

    def delivery_fixture(self):
        p,data=self.prepare()
        p['requirements']={'REQ-SEND-001':{'type':'automated','checks':['native-tests']}}
        self.configure(p,p['checks'])
        self.record(p,data)
        self.git_start(); self.run_git('add','.'); self.run_git('commit','-m','Original behavior')
        base=self.run_git('rev-parse','HEAD')
        self.change(p,'reviewed',scope=['tests'])
        return p,data,base

    def candidate_audit(self,p,data,outcome='preserved'):
        path='openspec/changes/reviewed/source-audit.json'
        sources=data['units'][0]['evidence']
        targets=['openspec/changes/reviewed/'+name for name in ('design.md','proposal.md','tasks.md')]
        artifacts=targets+['openspec/specs/send/spec.md','docs/baseline/behavior-inventory.json']
        report={'review_mode':'same-agent-separate-pass','passes':[
            {'kind':kind,'sources':[{'path':name,'evidence':f'{name}:L1-L2','checked':'Reread current trigger, branch, propagation and actual target differences.'} for name in ('app.py','transport.py','tests/test_send.py')],
             'artifacts':[{'path':name,'checked':'Compared actual current-versus-target claims and assertion obligations.'} for name in artifacts],'findings':[]}
            for kind in ('source-first','source-recheck')],
            'behavior_change':{'targets':targets,'contract_consistency':'Current best-effort contract preserved, except explicitly reviewed target differences.',
                               'units':[{'id':'BEH-SEND-001','outcome':outcome,'reason':'Actual reviewed scope with current/target difference explained in design.',
                                         'counterexample':'Offline/absent branch inspected against actual target; no reliability inference.',
                                         'assertion_review':'Inspected negative and boundary assert calls and required native-tests command.',
                                         'evidence':sources,'tests':data['units'][0]['tests']}]}}
        self.write(path,kit.dump(report))
        kit.baseline_audit_record(self.root,p,path,['app.py','transport.py','tests/test_send.py'],artifacts,'reviewer')
        return path

    def test_direct_delivery_and_close_cannot_bypass_behavior_gate(self):
        p,data,base=self.delivery_fixture()
        target=self.root/'tests/test_send.py';target.write_bytes(target.read_bytes()+b'\n')
        result=kit.verify(self.root,p,'delivery','reviewed',base)
        self.assertIn('behavior-impact-stale',self.codes(result))
        with self.assertRaises(kit.KitError):kit.close_change(self.root,p,'reviewed')

    def test_new_unmapped_production_source_blocks_delivery_even_without_old_unit(self):
        p,data,base=self.delivery_fixture()
        p['source_paths']=['.'];self.configure(p,p['checks'])
        data['sources']=sorted(kit.capability_sources(self.root,p));self.record(p,data)
        self.write('worker.py','def tick():\n    return 42\n')
        self.change(p,'new-worker',scope=['worker.py'])
        result=kit.verify(self.root,p,'delivery','new-worker',base)
        self.assertIn('behavior-impact-stale',self.codes(result))

    def test_two_pass_candidate_preserves_native_active_delta_then_requires_refresh(self):
        p,data,base=self.delivery_fixture()
        target=self.root/'tests/test_send.py';target.write_bytes(target.read_bytes()+b'\n')
        report=self.candidate_audit(p,data)
        result=kit.behavior_candidate_record(self.root,p,'reviewed',report,'actual reviewer')
        self.assertEqual(result['status'],'PASS')
        delivery=kit.verify(self.root,p,'delivery','reviewed',base)
        self.assertEqual(delivery['status'],'PASS',delivery)
        self.assertIn('behavior-evidence-stale',self.codes(kit.behavior_status(self.root,p)))
        target.write_bytes(target.read_bytes()+b'\n')
        self.assertIn('behavior-impact-stale',self.codes(kit.verify(self.root,p,'delivery','reviewed',base)))

    def test_candidate_does_not_close_unresolved_behavior(self):
        p,data,base=self.delivery_fixture()
        self.write('tests/test_send.py',(self.root/'tests/test_send.py').read_text()+'\n')
        report=self.candidate_audit(p,data,outcome='unresolved')
        self.assertEqual(kit.behavior_candidate_record(self.root,p,'reviewed',report,'actual reviewer')['status'],'PENDING')
        self.assertIn('behavior-impact-stale',self.codes(kit.verify(self.root,p,'delivery','reviewed',base)))

    def test_candidate_cannot_rebind_stale_assertion_review_after_tests_are_weakened(self):
        p,data,base=self.delivery_fixture()
        report=self.candidate_audit(p,data)
        self.write('tests/test_send.py','assert True\n')
        with self.assertRaisesRegex(kit.KitError,'two-pass'):kit.behavior_candidate_record(self.root,p,'reviewed',report,'reviewer')
        self.assertNotEqual(kit.verify(self.root,p,'delivery','reviewed',base)['status'],'PASS')

    def test_new_native_delta_cannot_be_omitted_from_candidate_audit(self):
        p,data,base=self.delivery_fixture()
        report=self.candidate_audit(p,data)
        self.write('openspec/changes/reviewed/specs/send/spec.md','## MODIFIED Requirements\n### Requirement: REQ-SEND-001 Send\nThe sender SHALL return true for absent input.\n#### Scenario: Absent\n- WHEN input is absent\n- THEN return true\n')
        with self.assertRaisesRegex(kit.KitError,'ALL actual'):kit.behavior_candidate_record(self.root,p,'reviewed',report,'reviewer')

    def test_template_and_raw_string_literals_are_not_comment_evidence(self):
        p,data=self.prepare()
        for extension,assertion in [('ts','expect(send(`http://host`)).toBe(true);'),('go','if send(`http://host`) != true { panic("bad") }')]:
            path=f'tests/assertion.{extension}'
            self.write(path,assertion+'\n')
            test=copy.deepcopy(data['units'][0]['tests'][0]);test.update(path=path,reference=path+':L1',assertion=assertion)
            self.assertTrue(kit.behavior_assertion_valid(self.root,test))

    def test_native_target_verification_mapping_does_not_rewrite_current_authority(self):
        p,data=self.prepare()
        p['checks'].append({'name':'inspect','type':'manual'})
        p['requirements']={'REQ-SEND-001':{'type':'automated','checks':['native-tests'],
                                         'targets':{'reviewed':{'type':'manual','checks':['inspect']}}}}
        self.configure(p,p['checks'])
        kit.policy_at(self.root)
        current=[{**r,'path':'openspec/specs/send/spec.md'} for r in kit.spec_records((self.root/'openspec/specs/send/spec.md').read_text(),'send')]
        target=[{**r,'body':r['body'].replace('Verification: automated','Verification: manual')} for r in current]
        self.assertEqual(kit.requirement_test_findings(self.root,p,current,current=True),[])
        self.assertEqual(kit.requirement_test_findings(self.root,p,target,change='reviewed'),[])
        self.assertIn('requirement-verification',self.codes({'findings':kit.requirement_test_findings(self.root,p,target,change='other')}))

    def test_real_preserved_refactor_runs_original_tests_before_delivery_and_close(self):
        p,data,base=self.delivery_fixture()
        metadata=self.root/'openspec/changes/reviewed/ark.json'
        m=kit.read_json(metadata);m['scope']=['app.py','tests'];kit.atomic(metadata,kit.dump(m))
        self.write('openspec/changes/reviewed/behavior-plan.json',kit.dump({'cases':[{'id':'preserve-send','effect':'preserve','source':'app.py:L2-L5','expected':'Absent/offline false and normal true','checks':['native-tests'],'fixtures':['tests/test_send.py']}]}))
        def refresh():
            kit.baseline_inventory(self.root,p)
            self.write('docs/baseline/modules/app.md','# App\n## Purpose\nSend inputs.\n## Flow\nReject None, propagate publish.\n## State and failure\nStateless failure boolean.\n## Evidence\napp.py:L1-L5\n## Gaps\nNo reliable delivery.\n')
            kit.baseline_review(self.root,p,'docs/baseline/modules/app.md',['app.py'],'reviewer')
        refresh()
        self.assertEqual(kit.verify(self.root,p,'ready','reviewed',base)['status'],'PASS')
        self.write('app.py',(self.root/'app.py').read_text().replace('value is None','None is value'))
        refresh();report=self.candidate_audit(p,data)
        self.assertEqual(kit.behavior_candidate_record(self.root,p,'reviewed',report,'reviewer')['status'],'PASS')
        self.assertEqual(kit.verify(self.root,p,'delivery','reviewed',base)['status'],'PASS')
        self.assertEqual(kit.close_change(self.root,p,'reviewed')['status'],'PASS')

    def test_real_native_manual_target_keeps_current_spec_and_executes_evidence(self):
        p,data,base=self.delivery_fixture()
        (self.root/'openspec/changes/reviewed/ark.json').unlink()
        self.write('openspec/changes/reviewed/proposal.md','# Proposal\nKind: maintenance\nScope: `tests`\nReview verification transition while preserving outputs.\n')
        p['checks'].append({'name':'inspect','type':'manual'})
        p['requirements']['REQ-SEND-001']['targets']={'reviewed':{'type':'manual','checks':['inspect']}}
        self.configure(p,p['checks'])
        delta='openspec/changes/reviewed/specs/send/spec.md'
        current=(self.root/'openspec/specs/send/spec.md').read_text()
        self.write(delta,'## MODIFIED Requirements\n### Requirement:'+current.split('### Requirement:',1)[1].replace('Verification: automated','Verification: manual'))
        procedure='openspec/changes/reviewed/manual-evidence.md'
        run=subprocess.run([sys.executable,'-c',"exec(open('tests/test_send.py').read())"],cwd=self.root,capture_output=True)
        self.assertEqual(run.returncode,0)
        self.write(procedure,'# Actual procedure\nExecuted native assertions for absent/offline/normal inputs. Exit 0.\n')
        kit.record_evidence(self.root,p,'reviewed','inspect',procedure,'reviewer','PASS','Reviewed source and actual native execution.')
        report=self.candidate_audit(p,data,outcome='intentional-change')
        audit=kit.read_json(self.root/report);audit['behavior_change']['targets'].append(delta)
        audit['behavior_change']['units'][0].update(verification='manual',verification_reason='Explicit target with retained automated checks.',checks=['inspect'],verification_artifacts=[procedure],verification_change={'reason':'Reviewed method transition.','alternatives':'Native command also executed.','remaining_gap':'No remote environment certified.','reviewer':'reviewer'})
        for review in audit['passes']:
            review['artifacts'].extend({'path':name,'checked':'Reviewed target mode and actual procedure.'} for name in (delta,procedure))
        self.write(report,kit.dump(audit))
        kit.baseline_audit_record(self.root,p,report,['app.py','transport.py','tests/test_send.py'],[x['path'] for x in audit['passes'][0]['artifacts']],'reviewer')
        self.assertEqual(kit.behavior_candidate_record(self.root,p,'reviewed',report,'reviewer')['status'],'PASS')
        delivery=kit.verify(self.root,p,'delivery','reviewed',base)
        self.assertEqual(delivery['status'],'PASS',delivery)
        self.assertEqual([x['status'] for x in delivery['checks']],['PASS','PASS'])
        self.assertEqual((self.root/'openspec/specs/send/spec.md').read_text(),current)
