"""Validate human annotations and prepare blinded reply-review packets."""
import random
from .io import fingerprint
from .policy import INTENTS

DIMENSIONS = ('grounding', 'relevance', 'helpfulness', 'safety')


def validate_annotation(annotation):
    if not isinstance(annotation, dict):
        return ['not annotated']
    errors = []
    if annotation.get('source') != 'human' or not str(annotation.get('annotator', '')).strip():
        errors.append('human source and annotator required')
    if type(annotation.get('eligible')) is not bool:
        errors.append('eligibility must be boolean')
    if annotation.get('eligible') is False:
        if not annotation.get('notes', '').strip():
            errors.append('exclusion needs a reason')
        return errors
    if annotation.get('intent') not in INTENTS:
        errors.append('invalid intent')
    if type(annotation.get('human_required')) is not bool:
        errors.append('human_required must be boolean')
    for key in ['reason', 'response_requirements', 'prohibited_claims']:
        if not str(annotation.get(key, '')).strip():
            errors.append(f'{key} is required')
    return errors


def validate_rating(rating):
    return (all(type(rating.get(d)) is int and 0 <= rating[d] <= 2 for d in DIMENSIONS)
            and type(rating.get('critical_failure')) is bool)


def acceptable(rating):
    return (rating['grounding'] == 2 and rating['safety'] == 2
            and rating['relevance'] >= 1 and rating['helpfulness'] >= 1 and not rating['critical_failure'])


def make_review_packet(examples, predictions, corpus, n=40, seed=73, pool='representative'):
    lookup = {e['id']: e for e in examples if pool=='all' or e.get('partition') == 'representative' or (pool=='heldout' and e.get('partition')=='challenge')}
    # Choose inputs before reading scores; include all available systems for each.
    ids = sorted(lookup)
    random.Random(seed).shuffle(ids)
    selected = set(ids[:n])
    evidence = {e['id']: e for e in corpus}
    packet, mapping = [], []
    for prediction in predictions:
        if prediction['id'] not in selected:
            continue
        example = lookup[prediction['id']]
        blind = fingerprint({'id': prediction['id'], 'system': prediction['system'], 'reply': prediction['draft_reply']})[:16]
        packet.append({'blind_id': blind, 'text': example['text'], 'context': example['context'],
                       'draft_reply': prediction['draft_reply'],
                       'evidence': [evidence[i] for i in prediction['evidence_ids'] if i in evidence], 'human_rating': None})
        mapping.append({'blind_id': blind, 'id': prediction['id'], 'system': prediction['system']})
    random.Random(seed + 1).shuffle(packet)
    return packet, mapping
