import json
import tempfile
import unittest
from pathlib import Path
from hiver_support.annotations import make_review_packet
from hiver_support.judge import grade
from hiver_support.metrics import evaluate, reply_summary
from hiver_support.readiness import status


class WorkflowTests(unittest.TestCase):
    def test_pending_readiness(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(status(folder,folder)['ready_for_final_report_review'])

    def test_judge_schema_failure_recorded(self):
        class Fake:
            def complete(self,*args): return {'output':{'grounding':9}}
        result=grade([dict(blind_id='a',text='help',context=[],draft_reply='reply',evidence=[])],Fake())
        self.assertIsNotNone(result[0]['error'])

    def test_blinding_removes_labels_and_system(self):
        example=dict(id='a',partition='representative',text='help',context=[],annotation={'intent':'secret'},historical_reply='future')
        prediction=dict(id='a',system='simple',draft_reply='hello',evidence_ids=[])
        packet,mapping=make_review_packet([example],[prediction],[])
        self.assertNotIn('system',packet[0])
        self.assertNotIn('future',json.dumps(packet))
        self.assertEqual(mapping[0]['system'],'simple')

    def test_known_denominators_and_errors(self):
        annotation=dict(source='human',annotator='test fixture',eligible=True,intent='battery_power',human_required=True,
                        reason='test',response_requirements='test',prohibited_claims='test')
        examples=[dict(id='a',partition='representative',annotation=annotation)]
        predictions=[dict(id='a',system='simple',intent='battery_power',decision='auto_handle',error=None,latency_seconds=1)]
        result=evaluate(examples,predictions)['simple']['representative']
        self.assertEqual(result['unsafe_auto_rate']['value'],1)
        self.assertEqual(result['escalation_recall']['value'],0)
        self.assertEqual(result['intent_accuracy']['value'],1)
        with self.assertRaises(ValueError): evaluate(examples,predictions*2)

    def test_reply_metric_denominators(self):
        result=reply_summary([dict(blind_id='a',id='x',system='simple')],[],[dict(id='x',partition='representative')])
        self.assertEqual(result['simple']['representative']['missing_or_failed'],1)
        self.assertIsNone(result['simple']['representative']['pass_rate']['value'])
