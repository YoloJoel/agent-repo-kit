"""Synthetic accounting fixtures, not model-generation or holdout quality evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ASSET=Path(__file__).resolve().parents[1]/'src/agent_repo_kit/assets/quality_trial.py'
SPEC=importlib.util.spec_from_file_location('quality_trial',ASSET)
trial=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(trial)


class QualityTrialTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.manifest={'schema_version':1,'source_revision':'fixture-only','protocol':'protocol.md','reference':'reference.json',
                       'dataset':{'split':'development','case_ids':['present','absent']},'inputs':{},'runs':[],
                       'release_gate':{'minimum_entailed_ratio':1,'minimum_repeats':2}}
        self.freeze('protocol.md',json.dumps({key:self.manifest[key] for key in ('source_revision','dataset','release_gate')}))
        self.freeze('reference.json',json.dumps({'present':7,'absent':None}))
        for method in ('kit','manual'):
            self.freeze(method+'.log','Synthetic fixture only; no real generation was performed.')
            self.freeze(method+'.md','Return 7 for present, None for absent.')
            self.freeze(method+'-predictions.json',json.dumps({'answers':[{'id':'present','status':'predicted','expected':7},{'id':'absent','status':'predicted','expected':None}]}))
            self.freeze(method+'-judgments.json',json.dumps({'predictions_sha256':self.manifest['inputs'][method+'-predictions.json'],
                       'rows':[{'id':identity,'result':'entailed','observed':7 if identity=='present' else None,'reason':'Synthetic accounting fixture','evidence':'reference.json'} for identity in ('present','absent')]}))
            self.manifest['runs'].append({'method':method,'stage':'initial','repeat':1,'review_mode':'same-agent-separate-pass',
                 'settings':{'model':'fixture','model_version':'0','host':'fixture','tool_permissions':[],'context_budget':100,'generation_budget':100},
                 'spec':method+'.md','execution_log':method+'.log','predictions':method+'-predictions.json','judgments':method+'-judgments.json',
                 'cost':{field:0 for field in ('wall_seconds','input_tokens','output_tokens','manual_minutes','reminders','repair_rounds','false_blocks')}})

    def freeze(self,name,text):
        (self.root/name).write_text(text,encoding='utf-8')
        self.manifest['inputs'][name]=hashlib.sha256(text.encode()).hexdigest()

    def evaluate(self):
        path=self.root/'manifest.json';path.write_text(json.dumps(self.manifest))
        return trial.evaluate(path)

    def test_development_scores_do_not_become_holdout_qualification(self):
        result=self.evaluate();self.assertEqual(result['status'],'PASS');self.assertEqual(result['product_quality'],'PENDING')
        self.assertEqual(result['stages'][0]['denominator'],2)

    def test_source_audit_scores_cannot_replace_missing_initial_run(self):
        for run in self.manifest['runs']: run['stage']='source-audit'
        self.assertIn('initial-missing',{row['code'] for row in self.evaluate()['findings']})

    def test_denominator_mismatch_and_missing_cost_remain_pending(self):
        self.manifest['dataset']['case_ids'].append('omitted')
        del self.manifest['runs'][0]['cost']['manual_minutes']
        codes={row['code'] for row in self.evaluate()['findings']}
        self.assertTrue({'prediction-denominator','judgment-denominator','cost-incomplete'}.issubset(codes))

    def test_changed_inputs_or_model_make_the_pair_ineligible(self):
        (self.root/'kit.md').write_text('Changed after the trial.')
        self.manifest['runs'][0]['settings']['model']='different'
        self.assertTrue({'input-not-frozen','pair-confounded'}.issubset({row['code'] for row in self.evaluate()['findings']}))

    def test_retuned_stages_are_reported_separately(self):
        for run in list(self.manifest['runs']):
            revised=copy.deepcopy(run);revised['stage']='recheck';self.manifest['runs'].append(revised)
        result=self.evaluate();self.assertEqual(result['status'],'PASS')
        self.assertEqual([r['stage'] for r in result['stages']],['initial','initial','recheck','recheck'])
