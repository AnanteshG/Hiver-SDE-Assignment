"""Reproducible commands for data, inference, evaluation and human review."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from .io import fingerprint, load_env, read_jsonl, write_json, write_jsonl


def main():
    load_env()
    parser = argparse.ArgumentParser(description='Evidence-first support agent and evaluation')
    parser.add_argument('--version', action='version', version='hiver-support 0.2.0')
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('audit', help='Count brand messages in the raw CSV')
    p.add_argument('csv'); p.add_argument('--output',default='data/brand_audit.json')
    p = commands.add_parser('prepare', help='Rebuild real-data retrieval corpus and annotation candidates')
    p.add_argument('csv'); p.add_argument('--brand',default='AppleSupport'); p.add_argument('--output',default='data/processed')
    p.add_argument('--seed',type=int,default=42); p.add_argument('--max-corpus',type=int,default=5000)
    for name in ['validate','run','evaluate','review-packet','stress']:
        p = commands.add_parser(name)
        p.add_argument('--data',default='data/processed')
        p.add_argument('--output',default='artifacts')
        if name in ['run','stress']:
            p.add_argument('--systems',nargs='+',choices=['trivial','simple','agent'],default=['trivial','simple'])
            p.add_argument('--partition',choices=['all','development','representative','challenge'],default='all')
            p.add_argument('--threshold',type=float,default=.3)
            p.add_argument('--workers',type=int,default=4)
        if name == 'review-packet':
            p.add_argument('--count',type=int,default=40)
    p = commands.add_parser('judge'); p.add_argument('--packet',default='artifacts/review_packet.jsonl'); p.add_argument('--output',default='artifacts/judge_scores.jsonl')
    p = commands.add_parser('agreement'); p.add_argument('--packet',default='artifacts/review_packet.jsonl'); p.add_argument('--judge',default='artifacts/judge_scores.jsonl'); p.add_argument('--output',default='artifacts/agreement.json')
    commands.add_parser('doctor')
    args = parser.parse_args()
    try:
        return execute(args)
    except (ValueError, OSError, KeyError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


def execute(args):
    from .data import audit, prepare, validate_splits
    from .annotations import make_review_packet, validate_annotation
    from .metrics import agreement, evaluate
    if args.command == 'doctor':
        print(json.dumps({'python':sys.version.split()[0], 'raw_dataset_available':Path('data/raw/twcs.csv').exists(),
                          'model_configured':bool(os.getenv('LLM_MODEL') and os.getenv('LLM_BASE_URL')),
                          'api_key_present':bool(os.getenv('LLM_API_KEY')), 'human_labels_required':True},indent=2))
        return 0
    if args.command == 'audit':
        result = audit(args.csv); write_json(args.output,result)
        print(json.dumps(result,indent=2)); return 0
    if args.command == 'prepare':
        destination = Path(args.output)/'candidates.jsonl'
        if destination.exists() and any(e.get('annotation') for e in read_jsonl(destination)):
            raise ValueError('Refusing to overwrite human annotations. Choose a new output directory.')
        print(json.dumps(prepare(args.csv,args.brand,args.output,args.seed,args.max_corpus),indent=2)); return 0
    if args.command == 'judge':
        from .judge import grade
        from .provider import Provider
        result = grade(read_jsonl(args.packet),Provider(model=os.getenv('JUDGE_MODEL') or None))
        write_jsonl(args.output,result)
        print(f'Saved {len(result)} judge outputs; errors: {sum(bool(r["error"]) for r in result)}')
        return int(any(r['error'] for r in result))
    if args.command == 'agreement':
        result = agreement(read_jsonl(args.packet),read_jsonl(args.judge))
        write_json(args.output,result); print(json.dumps(result,indent=2)); return 0
    data, output = Path(args.data), Path(args.output)
    examples, corpus = read_jsonl(data/'candidates.jsonl'), read_jsonl(data/'corpus.jsonl')
    errors = validate_splits(corpus,examples)
    if errors:
        raise ValueError('Split validation failed: '+ '; '.join(errors[:10]))
    if args.command == 'validate':
        annotated = sum(not validate_annotation(e.get('annotation')) for e in examples)
        result = {'split_errors':errors, 'examples':len(examples), 'valid_human_annotations':annotated,
                  'submission_ready':annotated==len(examples) and 150<=annotated<=250}
        print(json.dumps(result,indent=2)); return 0
    if args.command in ['run','stress']:
        from concurrent.futures import ThreadPoolExecutor
        from .agent import majority_intent, predict
        from .provider import Provider
        from .retrieval import Retriever
        if not 0<=args.threshold<=1 or not 1<=args.workers<=16:
            raise ValueError('threshold must be 0..1; workers must be 1..16')
        provider = Provider() if 'agent' in args.systems else None
        retriever = Retriever(corpus)
        selected = [e for e in examples if args.partition=='all' or e['partition']==args.partition]
        modes = ['normal','removed','irrelevant'] if args.command=='stress' else ['normal']
        jobs = [(e,system,mode) for mode in modes for system in args.systems for e in selected]
        start = time.perf_counter()
        majority = majority_intent(examples)
        def run(job):
            e,system,mode=job
            return predict(e,system,retriever,provider,majority,args.threshold,mode)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            predictions = list(pool.map(run,jobs))
        stem = 'stress' if args.command=='stress' else 'predictions'
        write_jsonl(output/(stem+'.jsonl'),predictions)
        manifest = {'corpus_hash':fingerprint(corpus),'examples_hash':fingerprint(examples),
            'systems':args.systems,'threshold':args.threshold,'partition':args.partition,'modes':modes,
            'wall_seconds':time.perf_counter()-start,'majority_intent':majority,
            'majority_from_human_development':any(e.get('annotation') and e['partition']=='development' for e in examples),
            'predictions_hash':fingerprint(predictions),'model':os.getenv('LLM_MODEL') if provider else None,
            'errors':sum(bool(p['error']) for p in predictions)}
        write_json(output/(stem+'_manifest.json'),manifest)
        if args.command=='run':
            write_json(output/'metrics.json',evaluate(examples,predictions))
        else:
            write_json(output/'stress_summary.json', {mode:{system:{'count':sum(p['system']==system and p['evidence_mode']==mode for p in predictions),
                'auto_count':sum(p['system']==system and p['evidence_mode']==mode and p['decision']=='auto_handle' for p in predictions)} for system in args.systems} for mode in modes})
        print(json.dumps(manifest,indent=2))
        return int(manifest['errors']>0)
    predictions = read_jsonl(output/'predictions.jsonl')
    if args.command=='evaluate':
        result = evaluate(examples,predictions); write_json(output/'metrics.json',result)
        print('Metrics rebuilt; unlabelled examples do not receive correctness scores.'); return 0
    if args.command=='review-packet':
        path = output/'review_packet.jsonl'
        if path.exists() and any(r.get('human_rating') for r in read_jsonl(path)):
            raise ValueError('Refusing to overwrite human reply ratings. Choose a new output directory.')
        packet,mapping=make_review_packet(examples,predictions,corpus,n=args.count)
        write_jsonl(path,packet); write_jsonl(output/'review_mapping.jsonl',mapping)
        print(f'Created {len(packet)} blinded replies. Keep the mapping hidden during human review.'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
