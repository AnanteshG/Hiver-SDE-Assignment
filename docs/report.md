# Evidence-first AppleSupport agent — report draft

**Status: implementation and baseline smoke runs complete; human and live-model
evaluation pending. This is not yet a submission-ready results report.**

## Problem framing: what good means

The system produces the next public support reply for an AppleSupport customer
message. Good means correctly identifying the request, providing a relevant next
step supported by historical evidence, and refusing automation when account access,
sensitive information, uncertain evidence, or safety concerns require a person.
An automatically permitted reply does not mean the customer's issue was resolved.

There are no live account actions, public posting, refund execution, current-policy
verification, or production deployment. Historical responses are observed behaviour,
not verified resolutions. The review dashboard is optional to the pipeline.

## Data and labels

The source is Thought Vector's Customer Support on Twitter, attributed in the data
card under CC BY-NC-SA 4.0. The brand audit found 106,860 AppleSupport outbound
tweets. Preparation produced 106,625 linked customer turns, 8,162 with incomplete
observed context. The checked-in retrieval corpus has 5,000 cases; candidates are
50 development, 120 representative, and 30 deliberately difficult examples.

Connected conversations and normalized-identical messages are grouped before
seeded partitioning. Each candidate comes from a distinct group. The representative
population is these observed groups, not all customer messages. Challenge cases
are enriched using missing-context, short-text and keyword heuristics; their results
must be separate. Only prior context reaches inference. The validator reports no
direct group or normalized-text overlap between corpus and candidates.

The candidate file currently contains **zero human annotations**. English eligibility
requires manual review, and the provisional eight-intent guide must be refined on
development data. Consequently no classification or handling accuracy is reported.
The UI hides future brand replies and predictions during customer-message labelling.

## System and comparisons

| System | Intent | Reply | Handling |
|---|---|---|---|
| Trivial | Development majority after labelling; current fallback is other_unclear | Fixed acknowledgement | Always escalate |
| Simple | Keyword rules | Nearest sanitized historical response using TF-IDF | Deterministic gates |
| Proposed | Configurable LLM | Draft from three historical cases, with evidence IDs | Independent gates after generation |

The gates cover unclear intent, missing context, account/specialist work, sensitive
issues, weak evidence, absent support, prohibited actions/requests, private-channel
instructions, and time-sensitive advice. A model support flag is not independent
proof of grounding. Evidence references are validated; the model cannot cite an
invented case. Malformed outputs and API failures become visible escalations.

## Current results and planned evaluation

The two baseline smoke runs produced 400 predictions across 200 candidates, with
zero processing errors. The saved run manifest records approximately 1.61 seconds
for prediction after retriever construction. This is a local operational timing,
not end-to-end setup time or an estimate of live LLM latency.

| System | Predictions | Intent macro-F1 | Escalation recall | Unsafe-auto rate | Reply quality |
|---|---:|---|---|---|---|
| Trivial | 200 | Pending human labels | Pending | Undefined: no automation | Pending ratings |
| Simple | 200 | Pending human labels | Pending | Pending human labels | Pending ratings |
| Proposed | Not run live | Pending | Pending | Pending | Pending |

The development stress experiment changed simple-baseline automation from 4/50
with normal evidence to 0/50 with removed or deliberately unrelated evidence.
These are observed decision counts, **not measured safe automation**. The unrelated
condition sets similarity to zero, so this primarily verifies the gate; it does not
demonstrate that the model detects plausible-looking but incorrect evidence.

Final intent metrics will include fixed-eight-class macro-F1, accuracy and confusion.
Absent classes contribute zero to macro-F1. Handling metrics use explicit denominators:
coverage is auto/all, unsafe-auto is human-required among auto, and escalation recall
is escalated among human-required. Wilson intervals expose uncertainty in small
automated subsets. Failed requests stay in scored outputs as failure escalations;
missing predictions are reported separately. No observed zero is a safety guarantee.

## Judge validation

The rubric scores grounding, relevance, helpfulness and safety from 0 to 2, with a
separate critical-failure flag. Acceptability requires full grounding/safety, at
least partial relevance/helpfulness, and no critical failure. The judge sees context,
reply and evidence, but not human scores or system identity.

Forty representative inputs are selected deterministically before inspecting scores.
Three systems will yield 120 blinded human ratings. The current two-system packet
has 80 unrated replies. Full held-out judge packets are supported separately. Exact
agreement, quadratic-weighted kappa, acceptability confusion and false approval among
human-rejected replies are implemented. **No agreement claim is currently supported**:
the model endpoint and actual human reply ratings are absent. A shared generator/judge
family, if used, must be disclosed because its errors may correlate.

## Five observed development failure modes

These are qualitative inspections of actual development outputs, not the final top
five held-out failures. They must be replaced or quantified after the frozen evaluation.

1. **Similar words, wrong issue — tw_1712989.** A customer describes an iPhone
   restarting during a song. The nearest reply talks about a phishing email
   (evidence tw_967315, similarity 0.231). The draft is irrelevant even though
   escalation blocks automation. Hypothesis: weak lexical matches and a small corpus.
   Next test: retrieval relevance ratings before adding semantic retrieval.
2. **Specific issue replaced by a generic assumption — tw_37662.** Bose headphone
   controls stopped working after an update; the draft assumes an Apple Music issue
   (tw_2476113, similarity 0.386) and is auto-permitted. This demonstrates that a
   similarity threshold does not ensure relevance. Test evidence-grounded generation
   against this baseline and audit automated replies manually.
3. **Accessory versus device confusion — tw_563102.** The request is about replacing
   a scratched screen protector. The retrieved answer asks whether the display lights
   up (tw_1961156, similarity 0.238). Human escalation is appropriate, but the draft
   does not answer the request. Hypothesis: common product words overwhelm the action.
4. **Historical advice sounds current — tw_326663.** The copied reply says iOS 11.0.2
   was released "earlier this week" (tw_330464). A development fix added a time-sensitive
   gate; the final stored output escalates. The old wording remains visible for human
   review. The rule is incomplete; a curated current knowledge source would be needed
   to make stronger present-day advice claims.
5. **Out-of-scope language enters the sample — tw_2012120.** A French macOS complaint
   retrieves a language-support handoff. English-only performance would be misleading
   if this were silently counted as an unclear intent. Manually mark eligibility and
   report excluded counts; do not pretend the sampling filter detects English.

## What is misleading about my headline number?

At present the only headline is that the pipeline ran without processing errors.
That establishes execution, not usefulness. A generated reply can be fluent and
irrelevant; an always-escalate policy can look safe while providing no automation.
The representative sample is small and group-based, and challenge enrichment changes
its distribution. Missing images, links and private resolutions remove useful context.
Public historical replies may be poor, obsolete or present in model pretraining.
Normalized duplicate checks do not remove semantic paraphrases. The random split is not a prospective temporal evaluation; retrieved conversations can postdate a benchmark query. A single annotator's
labels are subjective. Judge scores need human validation, and cached reproduction
does not establish repeatability of future hosted-model responses. The threshold 0.3
is a provisional default, not a calibrated safety probability.

## One more week

First complete independent human annotation and judge agreement; prioritize false
approvals over raising a mean score. Then rate retrieval relevance on development
cases and compare semantic retrieval only if the evidence supports it. Add targeted
tests for plausible but wrong evidence, multilingual routing and context-dependent
requests. Expand rare high-risk examples and use a fresh hold-out after changes.
Finally, separate verified current support guidance from historical stylistic examples.
