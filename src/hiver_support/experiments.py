"""Development-only threshold analysis on fixed generated replies."""
from .metrics import evaluate


def risk_curve(examples,predictions):
    development=[e for e in examples if e['partition']=='development']
    ids={e['id'] for e in development}
    result=[]
    for threshold in [.0,.2,.3,.4,.5,.6,.8,1.0]:
        changed=[]
        for prediction in predictions:
            if prediction['id'] not in ids: continue
            reasons=[r for r in prediction['reason_codes'] if r not in ['evidence_insufficient','supported_low_risk_response']]
            cited=[r['score'] for r in prediction['retrieved'] if r['id'] in prediction['evidence_ids']]
            if not cited or max(cited)<threshold: reasons.append('evidence_insufficient')
            changed.append({**prediction,'decision':'escalate' if reasons else 'auto_handle'})
        metrics=evaluate(development,changed)
        for system,parts in metrics.items():
            m=parts['development']
            result.append({'threshold':threshold,'system':system,'status':m['status'],
                'coverage':m['auto_coverage'],'unsafe_auto_rate':m['unsafe_auto_rate'],
                'unsafe_auto_wilson_95':m['unsafe_auto_wilson_95'],
                'observed_auto_count':m['unlabelled_auto_count'],
                'note':'Fixed drafts; sweep changes only the evidence-similarity gate. Choose on development data only.'})
    return result
