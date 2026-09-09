import unittest
from hiver_support.data import sanitize, validate_splits


class DataTests(unittest.TestCase):
    def test_sanitize_preserves_negation(self):
        self.assertEqual(sanitize('@Bob I cannot log in! https://x.com'), '@user I cannot log in! [link]')

    def test_email_and_html_are_normalized(self):
        self.assertEqual(sanitize('me@example.com &gt; @support'), '[email] > @user')

    def test_overlap_and_future_detected(self):
        example = dict(id='a', group_id='g', text='broken phone', partition='representative', tweet_id='1', reply_id='2', context=[{'tweet_id': '2'}])
        self.assertEqual(len(validate_splits([example], [example])), 2)

    def test_safe_split(self):
        corpus = [dict(id='a', group_id='g', text='old message')]
        example = dict(id='b', group_id='h', text='new message', partition='representative', tweet_id='3', reply_id='4', context=[])
        self.assertEqual(validate_splits(corpus, [example]), [])
