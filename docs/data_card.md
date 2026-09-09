# AppleSupport sample data card

Source: [Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)
by Thought Vector and collaborators, dataset identifier
`thoughtvector/customer-support-on-twitter`.

The source lists [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The derived data in `data/processed/` retains that licence. Code and data are
separate works; no claim of exclusive ownership of the customer conversations is made.

This repository contains a small transformed subset, not the raw download. Handles,
URLs, email patterns and long phone-like numbers are replaced; HTML entities are
decoded. This is not a guarantee of complete de-identification. Avoid attempts to
re-identify customers. Do not use this historical material as current brand policy.

## Brand selection

The audit found 106,860 AppleSupport outbound messages versus 169,840 AmazonHelp
and 43,265 SpotifyCares. Initial examples showed technical clarifications alongside
private-channel handoffs. AppleSupport provides a focused troubleshooting domain
and enough data for independent partitions. The selection was based on a small
exploratory sample, not a systematic brand-quality comparison.

## Construction

- Stream the raw CSV twice; collect target-brand turns and directly linked inbound turns.
- Link known parent relationships; missing ancestors are marked explicitly.
- Use up to eight most recent ancestors; never include descendants in model input.
- Group connected conversations and normalized-identical customer text together.
- Assign groups with seeded SHA-256 buckets: 70% retrieval, 10% development, 20% test.
- Shuffle deterministically. Keep 5,000 retrieval cases, 50 development examples,
  120 representative examples, and 30 separate challenge examples.
- Choose at most one candidate per group. The representative population is unique
  observed groups, not all tweets or customers. Larger conversations are not sampled
  proportionally to their number of tweets.
- Rank challenge candidates using incomplete context, short text, and keywords.
- Label all brand replies as observed_response; public resolution is not established.

Actual counts and content hashes are in `audit.json`. Seeds and preprocessing are
in source. Semantic paraphrases and recurring-user leakage may remain. Eligibility
for the English-only evaluation requires human review. Linked context outside the
selected brand/customer subgraph may be absent. The source is historical (2017-era
examples occur), so successful retrieval does not validate advice for current devices.

The 200 records are annotation candidates, not a completed golden set. Their
annotation fields intentionally remain null until a human reviews them.

The split is random by group, not chronological. Retrieval cases can postdate benchmark inputs; this is not a prospective deployment evaluation.
