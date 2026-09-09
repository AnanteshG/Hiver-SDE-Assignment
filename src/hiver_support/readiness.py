"""Submission gates: implemented machinery is not measured scientific evidence."""
from pathlib import Path
from .annotations import validate_annotation
from .metrics import agreement
from .io import read_jsonl


def status(data, artifacts):
    data, artifacts = Path(data), Path(artifacts)
    def read(path):
        return read_jsonl(path) if path.exists() else []
    examples = read(data/'candidates.jsonl')
    valid = [e for e in examples if not validate_annotation(e.get('annotation')) and e['annotation']['eligible']]
    predictions=read(artifacts/'predictions.jsonl')
    packet=read(artifacts/'review_packet.jsonl')
    judged=read(artifacts/'judge_scores.jsonl')
    agree=agreement(packet,judged)
    heldout={e['id'] for e in valid if e['partition']!='development'}
    complete_systems={system: bool(heldout) and heldout <= {p['id'] for p in predictions if p['system']==system and not p['error']}
                      for system in ['trivial','simple','agent']}
    blockers=[]
    if not 150<=len(valid)<=250: blockers.append('Complete 150–250 eligible human-labelled examples.')
    if not all(complete_systems.values()): blockers.append('Run both baselines and the live agent on every eligible held-out input.')
    if agree['paired_ratings']<120: blockers.append('Complete 120 paired human/judge reply ratings across the three systems.')
    if not (artifacts/'reply_metrics.json').exists(): blockers.append('Run held-out reply judging and aggregate its metrics.')
    return {'ready_for_final_report_review':not blockers,'eligible_human_labels':len(valid),
            'complete_systems':complete_systems,'paired_reply_ratings':agree['paired_ratings'],'blockers':blockers,
            'note':'Manual report, failure-analysis, attribution and access checks remain necessary even after these gates pass.'}
