import unittest
from hiver_support.metrics import agreement, evaluate, weighted_kappa, wilson
from hiver_support.annotations import validate_annotation, acceptable


class MetricTests(unittest.TestCase):
    def test_no_humans_no_claim(self):
        example = dict(id='a',partition='representative',annotation=None)
        prediction = dict(id='a',system='trivial',intent='other_unclear',decision='escalate',latency_seconds=0,error=None)
        result = evaluate([example],[prediction])['trivial']['representative']
        self.assertIsNone(result['intent_accuracy']['value'])
        self.assertIsNone(result['unsafe_auto_rate']['value'])

    def test_kappa(self):
        self.assertEqual(weighted_kappa([0,1,2],[0,1,2]),1)
        self.assertLess(weighted_kappa([0,2],[2,0]),0)
        self.assertIsNone(weighted_kappa([2,2],[2,2]))

    def test_zero_failures_not_certainty(self):
        self.assertGreater(wilson(0,8)[1],.2)

    def test_human_provenance_required(self):
        self.assertTrue(validate_annotation({'source':'model'}))

    def test_critical_failure_overrides_average(self):
        self.assertFalse(acceptable(dict(grounding=2,relevance=2,helpfulness=2,safety=2,critical_failure=True)))

    def test_no_agreement_without_humans(self):
        self.assertEqual(agreement([],[])['status'],'pending_human_ratings')
