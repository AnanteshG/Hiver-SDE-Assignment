# Decision log

1. Use Python with a standard-library core so data processing and cached metric reproduction do not depend on a large ML installation.
2. Keep Streamlit optional; the reviewer can run evaluation without opening a dashboard.
3. Choose AppleSupport after a brand-count audit and initial response inspection: a focused technical domain with public clarifications and human handoffs.
4. Use a small 5,000-case retrieval sample to keep reproduction fast; this limits rare-issue coverage.
5. Reconstruct observed parent paths and mark missing context rather than inventing intermediate messages.
6. Group conversation components and normalized-identical text before partitioning to reduce leakage; semantic paraphrase leakage remains a limitation.
7. Sample one candidate per group and separate representative from intentionally difficult challenge cases; their distributions should not be mixed into one headline.
8. Require actual human provenance for labels and ratings; unreviewed examples receive no correctness scores.
9. Define auto-handling as permission for the next public reply, not issue resolution or execution of account actions.
10. Begin with inspectable lexical retrieval; add semantic retrieval only if development failures justify the added dependency and complexity.
11. Treat historical replies as observed behaviour, never current policy or verified outcomes.
12. Gate sensitive intents, missing context, weak evidence, unsupported generation, and private-channel requests separately; the generator cannot override a failed gate.
13. Use fixed-taxonomy macro-F1 and explicit fraction denominators; absent intent classes contribute zero, and zero auto-handled cases yield undefined unsafe-auto rate.
14. Blind human reply review, validate the judge against it, and treat undefined kappa honestly rather than implying perfect agreement.
15. Version cached predictions and manifests while excluding raw data, secrets, and transient model caches. Each verified feature or fix receives a focused commit.
