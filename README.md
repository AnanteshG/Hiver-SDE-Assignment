# Trust Review — Hiver SDE Assignment

An evidence-first AppleSupport agent: classify a message, draft its next public
reply from historical cases, and explain whether a human must review it.

**Current evidence status:** working software and real-data baseline artifacts.
The 200 candidate examples still need human annotation. Live agent/judge results
require a configured model endpoint. No accuracy, safety, or judge-agreement claim
is made before those steps. Run `hiver-support readiness` to see the remaining gates.

## Quick reproduction — no API key or raw download

Python 3.12+ is required (the pinned dashboard uses NumPy 2.5). The checked-in sample is about 3.5 MB.

```sh
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`
- If PowerShell activation is restricted, invoke `.venv\Scripts\python.exe` directly.

```sh
python -m pip install -e .
python scripts/reproduce.py
```

This recomputes metrics from frozen predictions. It does **not** run fresh model
inference. With unlabelled data it correctly reports pending correctness metrics.
It uses the included sample, not the full Kaggle dataset, and is designed to finish
well within the assignment's 15-minute reproduction budget. Measured timing is in
`artifacts/reproduction_check.json` when available.

## Open the dashboard

```sh
python -m pip install -r requirements-dashboard.lock.txt
python -m streamlit run app.py
```

On the prepared Windows checkout, double-click `run_dashboard.cmd`.

The dashboard contains:

- Overview with explicit evidence status.
- A new-message playground with local retrieval and optional live generation.
- A case inspector showing historical evidence and escalation reasons.
- Customer-message annotation without model predictions or future answers.
- Blinded human reply scoring.
- Human-versus-judge disagreements.
- Evidence-removal experiments and development threshold sweeps.

## Run the pipeline

```sh
hiver-support validate
hiver-support run --systems trivial simple
hiver-support respond "My phone battery drains quickly after an update."
hiver-support sweep
hiver-support stress --partition development
```

The trivial system uses the most common **human-labelled development intent**.
Until development labels exist, it explicitly falls back to `other_unclear`; its
current output is a smoke run, not a finalized majority-class baseline.

The simple system uses keyword intents and the nearest historical customer/reply
pair. Both baselines share the output schema and deterministic safety checks.
The proposed agent uses the model to classify and draft from the top three cases,
then applies independent handling gates. Its evidence-support flag is an LLM
assessment, not a calibrated probability or independent grounding guarantee.

## Complete the real evaluation

1. Read [the annotation guide](docs/annotation_guide.md). Personally review the 50
   development examples, refine intent boundaries, and freeze the guide.
2. Complete the 120 representative and 30 challenge labels. Exclude non-English
   examples with a reason; preserve 150–250 eligible labelled examples overall.
3. Copy `.env.example` to `.env`. Set `LLM_BASE_URL`, `LLM_MODEL`, and, for hosted
   providers, `LLM_API_KEY`. The endpoint must support chat completions and JSON
   object responses. Use `JUDGE_MODEL` to select another judge model if available.
4. Run:

```sh
python scripts/live_evaluation.py
```

This runs all three systems, prepares 40 representative inputs for blinded human
review (120 replies), prepares all 150 held-out inputs for judging, runs the judge,
aggregates reply metrics, and runs the agent's development evidence stress test.
Excluded examples remain visible in prediction artifacts; intent/handling metrics
and newly created reply-review packets omit them. Report their counts explicitly.

5. Personally score the 120 replies in the dashboard using [the rubric](docs/judge_rubric.md).
6. Finish:

```sh
hiver-support agreement
hiver-support evaluate
hiver-support readiness
```

Live timing and cost depend on the selected provider. Four concurrent requests,
bounded retries, and request caching are implemented. Token usage is recorded;
USD cost remains null unless computed from the actual provider's applicable rates.
No model is silently substituted. No credentials are stored in Git.

If a review packet already contains human ratings, the command refuses to overwrite
it. Preserve it and choose another `--output` directory for a new experiment.
Do not retune on held-out failures and then present them as fresh test results.

## Rebuild the real sample (optional)

```sh
python scripts/download_data.py
hiver-support audit data/raw/twcs.csv
hiver-support prepare data/raw/twcs.csv --brand AppleSupport
```

Preparation refuses to overwrite existing human annotations. Use a new output
directory for changes to sampling. Raw download and full preprocessing are outside
the short reproduction path. Attribution, sampling, masking, and limitations are
described in [the data card](docs/data_card.md).

## Evaluation and trust boundaries

Intent metrics: fixed-eight-class macro-F1, accuracy, class support and confusion.
Handling metrics: escalation recall, automation coverage, unsafe-auto rate with
numerators/denominators and a Wilson interval. Zero automation yields an undefined
unsafe-auto rate. Missing predictions, API failures, and absent human labels remain
visible; there is no fabricated score fallback.

Reply quality: grounding, relevance, helpfulness, safety, critical failure, and
acceptability. Judge validation: exact agreement, quadratic-weighted kappa, and
false approval among human-rejected replies. Failed/missing judge results are
counted separately. This measures reply quality, not actual customer resolution.

The retrieval corpus is isolated from evaluation conversation groups and
normalized-identical customer messages. Semantic paraphrases may remain. Only
prior context reaches the agent; future brand replies and gold labels do not.

## Tests

```sh
python -m pip install -e ".[dashboard]"
python -m unittest discover -s tests -v
```

Checks cover leakage, private claims, obsolete advice, evidence references,
missing-model failure, metric denominators, judge schemas, a local HTTP model
transport, caching, all dashboard screens, and interactive baseline generation.
Test fixtures are not human golden labels. CI runs the tests and metric reproduction.

## Repository map

```text
src/hiver_support/     data, retrieval, agent, policy, evaluation, judge, CLI
app.py                local review and annotation dashboard
data/processed/       attributed corpus and unlabelled evaluation candidates
artifacts/            frozen predictions, manifests, review packets and metrics
tests/                functional and integration checks
docs/report.md        report draft with real development failures
docs/decision_log.md  15 implementation decisions
scripts/              reproduction, download and final-evaluation entry points
```

## Submission

Finish the human and live evaluation gates, update [the report](docs/report.md)
with measured results and top held-out failures, and verify repository access.
Submit the repository link and report through the
[assignment form](https://intelligent-bar-256.notion.site/39492cbf0da2800682cfc78a600a745f?pvs=105).
Do not email the submission.

## Attribution

Data: Thought Vector and collaborators, [Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter),
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
Dashboard: [Streamlit](https://docs.streamlit.io/).
The core implements standard unigram TF-IDF/cosine retrieval and standard metric
formulae directly; no third-party model weights or borrowed application source are
bundled. Model identity, prompt hash, and request usage are captured for live runs.
