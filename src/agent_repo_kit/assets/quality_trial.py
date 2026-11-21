"""Validate frozen paired trials; never generate scores from structural checks.

Run: python hack/ai/assets/quality_trial.py MANIFEST.json [--output REPORT.json]
All referenced paths are relative to the manifest directory. Raw files must be frozen
in inputs before scoring. The validator checks evidence accounting, not judge truth.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def evaluate(manifest_path):
    path = Path(manifest_path).resolve()
    data = json.loads(path.read_text(encoding='utf-8'))
    findings, summaries = [], []
    def fail(code, message): findings.append({'status':'PENDING','code':code,'message':message})
    def read(name):
        if not isinstance(name,str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Evidence paths must stay inside the trial directory')
        source = path.parent / name
        if not source.resolve().is_relative_to(path.parent): raise ValueError('Evidence symlink escapes trial')
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != data.get('inputs',{}).get(name):
            fail('input-not-frozen',name)
        return content
    if data.get('schema_version') != 1: raise ValueError('Trial schema_version must be 1')
    dataset = data.get('dataset',{})
    case_ids = dataset.get('case_ids',[])
    if not case_ids or any(not isinstance(x,str) or not x for x in case_ids) or len(set(case_ids)) != len(case_ids):
        raise ValueError('Freeze a nonempty independent case denominator with unique IDs')
    if dataset.get('split') not in {'development','holdout'}: raise ValueError('Declare development or holdout')
    if not data.get('source_revision') or not data.get('protocol') or not data.get('reference'):
        raise ValueError('Freeze the source revision, evaluation protocol and independent reference')
    protocol=json.loads(read(data['protocol']));read(data['reference'])
    for field in ('source_revision','dataset','release_gate'):
        if protocol.get(field)!=data.get(field): fail('protocol-drift',field)
    for name in data.get('inputs',{}): read(name)
    pairs = {}
    for run in data.get('runs',[]):
        key=(run.get('stage'),run.get('repeat'),run.get('method'))
        if key[0] not in {'initial','source-audit','recheck'} or not isinstance(key[1],int) or key[1]<1 or key[2] not in {'manual','kit'} or key in pairs:
            raise ValueError('Use unique stage/repeat/method; keep initial, source-audit and recheck separate')
        pairs[key]=run
        settings=run.get('settings',{})
        if any(field not in settings for field in ('model','model_version','host','tool_permissions','context_budget','generation_budget')):
            fail('settings-incomplete',str(key))
        read(run['spec']); read(run['execution_log']); prediction_bytes=read(run['predictions'])
        predictions=json.loads(prediction_bytes)
        judgment=json.loads(read(run['judgments']))
        if judgment.get('predictions_sha256') != hashlib.sha256(prediction_bytes).hexdigest():
            fail('predictions-not-bound',str(key))
        answers=predictions.get('answers',[]);rows=judgment.get('rows',[])
        if len(answers)!=len(case_ids) or {row.get('id') for row in answers}!=set(case_ids): fail('prediction-denominator',str(key))
        if len(rows)!=len(case_ids) or {row.get('id') for row in rows}!=set(case_ids): fail('judgment-denominator',str(key))
        if run.get('review_mode') not in {'same-agent-separate-pass','separate-context-attested'}:
            fail('review-mode-missing',str(key))
        counts=Counter();critical=0
        by_prediction={row.get('id'):row for row in answers}
        for row in rows:
            result=row.get('result')
            if result not in {'entailed','contradicted','ambiguous','unasked','source-unknown'}:
                raise ValueError('Invalid judgment result')
            if not row.get('reason') or not row.get('evidence'):
                fail('judgment-evidence-missing',str(row.get('id')))
            if result=='entailed' and (by_prediction.get(row.get('id'),{}).get('status')!='predicted'
                    or 'observed' not in row or 'expected' not in by_prediction.get(row.get('id'),{})
                    or json.dumps(row['observed'],sort_keys=True)!=json.dumps(by_prediction[row['id']]['expected'],sort_keys=True)):
                fail('judgment-disagrees',str(row.get('id')))
            counts[result]+=1
            if row.get('critical') and result!='entailed': critical+=1
        metrics=run.get('cost',{})
        if any(not isinstance(metrics.get(field),(float,int)) or isinstance(metrics.get(field),bool) or metrics[field]<0
               for field in ('wall_seconds','input_tokens','output_tokens','manual_minutes','reminders','repair_rounds','false_blocks')):
            fail('cost-incomplete',str(key))
        summaries.append({'stage':key[0],'repeat':key[1],'method':key[2], 'review_mode':run.get('review_mode'),
                          'denominator':len(case_ids),'counts':dict(counts),'critical_gaps':critical,
                          'entailed_ratio':counts['entailed']/len(case_ids),'cost':metrics})
    if not pairs: fail('trials-missing','No actual paired runs recorded')
    for (stage,repeat,method),run in pairs.items():
        opposite=pairs.get((stage,repeat,'kit' if method=='manual' else 'manual'))
        if not opposite: fail('pair-missing',str((stage,repeat)))
        elif opposite.get('settings')!=run.get('settings'): fail('pair-confounded',str((stage,repeat)))
        if stage!='initial' and (('initial',repeat,method) not in pairs): fail('initial-missing',str((repeat,method)))
    threshold=data.get('release_gate',{}).get('minimum_entailed_ratio')
    minimum_repeats=data.get('release_gate',{}).get('minimum_repeats')
    quality='PENDING'
    if not isinstance(threshold,(float,int)) or isinstance(threshold,bool) or not 0<=threshold<=1 or not isinstance(minimum_repeats,int) or minimum_repeats<1:
        fail('release-criteria-missing','Predeclare minimum ratio and repeats; do not choose thresholds after observing scores')
    elif not findings:
        selected=[row for row in summaries if row['method']=='kit' and row['stage']=='initial']
        if dataset['split']=='holdout' and len(selected)>=minimum_repeats and all(row['review_mode']=='separate-context-attested' for row in selected):
            quality='PASS' if all(row['entailed_ratio']>=threshold and row['critical_gaps']==0 for row in selected) else 'FAIL'
    comparisons=[]
    for row in summaries:
        if row['method']!='kit': continue
        other=next((candidate for candidate in summaries if candidate['method']=='manual' and candidate['stage']==row['stage'] and candidate['repeat']==row['repeat']),None)
        if other: comparisons.append({'stage':row['stage'],'repeat':row['repeat'],'kit_minus_manual_entailed_ratio':row['entailed_ratio']-other['entailed_ratio']})
    return {'schema_version':1,'status':'PENDING' if findings else 'PASS','findings':findings,'stages':summaries,'paired_differences':comparisons,
            'product_quality':quality,'split':dataset.get('split'),
            'meaning':'PASS validates supplied trial accounting only. Scores depend on adjudicators; context isolation is attested. Development/retuned results cannot qualify initial holdout quality.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest');parser.add_argument('--output')
    args=parser.parse_args()
    try: report=evaluate(args.manifest)
    except (ValueError,KeyError,TypeError,OSError) as error:
        report={'status':'PENDING','product_quality':'PENDING','error':str(error)}
    rendered=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output: Path(args.output).write_text(rendered,encoding='utf-8')
    print(rendered,end='')
    return 0 if report['status']=='PASS' and report['product_quality']!='FAIL' else 2


if __name__=='__main__': raise SystemExit(main())
