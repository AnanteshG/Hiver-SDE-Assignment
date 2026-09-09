"""Metrics with explicit denominators and undefined values preserved."""
import math
import statistics
from collections import Counter
from .annotations import DIMENSIONS, acceptable, validate_annotation, validate_rating
from .policy import INTENTS


def fraction(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator, 'value': numerator/denominator if denominator else None}


def wilson(successes, total):
    if not total:
        return None
    z = 1.96
    p = successes/total
    center = (p + z*z/(2*total))/(1+z*z/total)
    margin = z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/(1+z*z/total)
    return [max(0, center-margin), min(1, center+margin)]


def evaluate(examples, predictions):
    lookup = {e['id']: e for e in examples}
    unknown = {p['id'] for p in predictions} - set(lookup)
    if unknown:
        raise ValueError('Predictions contain unknown example IDs')
    results = {}
    for system in sorted({p['system'] for p in predictions}):
        results[system] = {}
        for partition in ['development', 'representative', 'challenge']:
            expected = [e for e in examples if e['partition'] == partition]
            selected = [p for p in predictions if p['system'] == system and p['id'] in lookup and lookup[p['id']]['partition'] == partition]
            if len({p['id'] for p in selected}) != len(selected):
                raise ValueError('Duplicate predictions for a system and example')
            labelled = [p for p in selected if not validate_annotation(lookup[p['id']].get('annotation')) and lookup[p['id']]['annotation']['eligible']]
            correct = sum(p['intent'] == lookup[p['id']]['annotation']['intent'] for p in labelled)
            confusion = Counter((lookup[p['id']]['annotation']['intent'], p['intent']) for p in labelled)
            per_intent = {}
            f1s = []
            for intent in INTENTS:
                tp = confusion[intent, intent]
                support = sum(v for (gold, _), v in confusion.items() if gold == intent)
                predicted = sum(v for (_, pred), v in confusion.items() if pred == intent)
                f1 = 2*tp/(support+predicted) if support+predicted else 0
                # Fixed taxonomy macro-F1: absent classes contribute zero, stated in report.
                f1s.append(f1)
                per_intent[intent] = {'support': support, 'predicted': predicted, 'f1': f1}
            auto = [p for p in labelled if p['decision'] == 'auto_handle']
            required = [p for p in labelled if lookup[p['id']]['annotation']['human_required']]
            unsafe = sum(lookup[p['id']]['annotation']['human_required'] for p in auto)
            latencies = sorted(p['latency_seconds'] for p in selected)
            results[system][partition] = {
                'status': 'measured' if labelled else 'pending_human_labels',
                'expected_examples': len(expected), 'predictions': len(selected), 'labelled_evaluated': len(labelled),
                'missing_predictions': len(expected)-len(selected),
                'intent_accuracy': fraction(correct, len(labelled)), 'intent_macro_f1': sum(f1s)/len(f1s) if labelled else None,
                'per_intent': per_intent, 'confusion': [{'gold':g, 'predicted':p, 'count':v} for (g,p),v in sorted(confusion.items())],
                'auto_coverage': fraction(len(auto), len(labelled)),
                'unsafe_auto_rate': fraction(unsafe, len(auto)), 'unsafe_auto_wilson_95': wilson(unsafe,len(auto)),
                'escalation_recall': fraction(sum(p['decision']=='escalate' for p in required),len(required)),
                'processing_error_rate': fraction(sum(p['error'] is not None for p in selected), len(selected)),
                'unlabelled_auto_count': sum(p['decision']=='auto_handle' for p in selected),
                'latency_p50_seconds': statistics.median(latencies) if latencies else None,
                'latency_p95_seconds': latencies[max(0, math.ceil(.95*len(latencies))-1)] if latencies else None,
                'total_tokens': sum(p.get('provider',{}).get('usage',{}).get('total_tokens',0) for p in selected),
                'cost_usd': None,
            }
    return results


def weighted_kappa(human, judge):
    n = len(human)
    if not n:
        return None
    observed = sum(((a-b)/2)**2 for a,b in zip(human,judge))/n
    a, b = Counter(human), Counter(judge)
    expected = sum(a[i]*b[j]*((i-j)/2)**2 for i in range(3) for j in range(3))/(n*n)
    return 1-observed/expected if expected else None


def agreement(packet, judged):
    judges = {r['blind_id']:r for r in judged if not r.get('error')}
    pairs = [(r['human_rating'],judges[r['blind_id']]['rating']) for r in packet
             if r.get('human_rating') and r['human_rating'].get('source')=='human'
             and str(r['human_rating'].get('annotator','')).strip() and r['blind_id'] in judges
             and validate_rating(r['human_rating']) and validate_rating(judges[r['blind_id']]['rating'])]
    output = {'paired_ratings':len(pairs), 'status':'measured' if pairs else 'pending_human_ratings', 'dimensions':{}}
    for dimension in DIMENSIONS:
        human = [h[dimension] for h,j in pairs]
        judge = [j[dimension] for h,j in pairs]
        output['dimensions'][dimension] = {'exact_agreement':fraction(sum(a==b for a,b in zip(human,judge)),len(pairs)),
                                            'weighted_kappa':weighted_kappa(human,judge)}
    confusion = Counter((acceptable(h),acceptable(j)) for h,j in pairs)
    output['acceptability_confusion'] = {f'human_{h}_judge_{j}':confusion[h,j] for h in (False,True) for j in (False,True)}
    output['false_approval_rate_among_human_rejected'] = fraction(confusion[False,True], sum(not acceptable(h) for h,j in pairs))
    return output


def reply_summary(mapping, judged, examples):
    """Judge acceptability by system and partition, including failed grades."""
    lookup = {e['id']:e for e in examples}
    scores = {r['blind_id']:r for r in judged}
    output = {}
    for system in sorted({r['system'] for r in mapping}):
        output[system] = {}
        for partition in ['development','representative','challenge']:
            selected = [r for r in mapping if r['system']==system and lookup[r['id']]['partition']==partition]
            valid = [scores[r['blind_id']]['rating'] for r in selected if r['blind_id'] in scores
                     and not scores[r['blind_id']].get('error') and validate_rating(scores[r['blind_id']]['rating'])]
            output[system][partition] = {'requested':len(selected),'valid_ratings':len(valid),
                'missing_or_failed':len(selected)-len(valid),'pass_rate':fraction(sum(acceptable(r) for r in valid),len(valid)),
                'dimension_means':{d:statistics.mean(r[d] for r in valid) if valid else None for d in DIMENSIONS}}
    return output
