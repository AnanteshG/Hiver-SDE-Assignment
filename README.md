# Hiver SDE Assignment

Evidence-first customer-support agent with reproducible evaluation.

## Status

Initial project scaffold. The agent, dataset processing, annotation workflow,
evaluation harness, and Streamlit review dashboard are not implemented yet.
No evaluation results are claimed.

## Stack

Python 3.11+ for data processing, retrieval, generation, and evaluation.
Streamlit is planned for the optional Trust Review dashboard.

## Run the scaffold

```sh
python -m venv .venv
python -m pip install -e .
hiver-support --help
hiver-support --version
```

Activate the virtual environment before installing: on PowerShell use
`.venv\Scripts\Activate.ps1`; on macOS/Linux use `source .venv/bin/activate`.

## Implementation order

1. Dataset audit and brand selection.
2. Conversation reconstruction and leakage-safe partitions.
3. Human annotation workflow and 200 reviewed examples.
4. Trivial and retrieval baselines.
5. Evidence-grounded agent and automation gates.
6. Evaluation harness and human-versus-judge validation.
7. Evidence stress tests and Trust Review dashboard.
8. Report, reproducibility validation, and submission preparation.

The golden labels and human reply ratings require actual human review.
Historical replies will not be treated as verified resolutions or current policy.

## Repository hygiene

Commit each completed, checked feature or fix separately. Keep API keys, raw data,
and temporary caches out of Git. Version small frozen evaluation artifacts when
available, with source attribution and applicable licence information.
