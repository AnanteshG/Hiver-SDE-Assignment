import unittest
from hiver_support.agent import predict
from hiver_support.policy import gates
from hiver_support.retrieval import Retriever


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(id='one', group_id='g1', text='phone battery draining very fast', historical_reply='Which software version are you using?', evidence_type='observed_response')
        self.retriever = Retriever([self.case])
        self.example = dict(id='two', group_id='g2', text='my phone battery is draining very fast', context=[])

    def test_self_group_excluded(self):
        self.assertEqual(self.retriever.search(self.case['text'], excluded_group='g1'), [])

    def test_account_gate(self):
        result = gates(self.example, 'account_access', [{**self.case, 'score':1}], 'Please clarify.', True)
        self.assertEqual(result['decision'], 'escalate')

    def test_missing_provider_is_visible_failure(self):
        result = predict(self.example, 'agent', self.retriever)
        self.assertIsNotNone(result['error'])
        self.assertEqual(result['decision'], 'escalate')

    def test_future_reply_not_sent_and_bad_citation_rejected(self):
        example = {**self.example, 'historical_reply':'SECRET FUTURE', 'annotation': {'intent':'battery_power'}}
        class Fake:
            def complete(self, prompt, payload):
                assert 'SECRET FUTURE' not in str(payload)
                assert 'annotation' not in payload['incoming']
                return {'output':dict(intent='battery_power', draft_reply='Try this', evidence_ids=['invented'], support_established=True)}
        result = predict(example, 'agent', self.retriever, Fake())
        self.assertIn('Invalid evidence', result['error'])

    def test_missing_evidence_abstains(self):
        result = predict(self.example, 'simple', self.retriever, evidence_mode='removed')
        self.assertEqual(result['decision'], 'escalate')
