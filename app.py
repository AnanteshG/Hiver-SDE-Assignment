"""Local Trust Review dashboard. Run: streamlit run app.py."""

import json
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
from hiver_support.annotations import DIMENSIONS, validate_annotation
from hiver_support.io import read_jsonl, write_jsonl
from hiver_support.policy import INTENTS

ROOT = Path(__file__).resolve().parent
DATA, ARTIFACTS = ROOT / "data" / "processed", ROOT / "artifacts"
st.set_page_config(
    page_title="Trust Review | Support Agent", page_icon="◈", layout="wide"
)
st.markdown(
    """<style>
.stApp { background: #f5f7fb; }
h1,h2,h3 { color: #132b45; }
div[data-testid="stMetric"] {background:white;border:1px solid #dce4ee;border-radius:12px;padding:18px;}
div[data-testid="stSidebar"] {background:#eaf0f7;}
</style>""",
    unsafe_allow_html=True,
)
st.title("Trust Review")
st.caption(
    "APPLE SUPPORT · Evidence-first replies · Inspect the proof behind each decision"
)
page = st.sidebar.radio(
    "Workspace",
    [
        "Overview",
        "Try a message",
        "Case inspector",
        "Label customer messages",
        "Review replies",
        "Judge audit",
        "Evidence stress test",
    ],
)
st.sidebar.caption(
    "Historical Twitter data. This prototype does not access accounts or send messages."
)


def read_optional(path):
    return read_jsonl(path) if path.exists() else []


examples = read_optional(DATA / "candidates.jsonl")
corpus = read_optional(DATA / "corpus.jsonl")
predictions = read_optional(ARTIFACTS / "predictions.jsonl")
reviewed = sum(not validate_annotation(e.get("annotation")) for e in examples)

if page == "Overview":
    cols = st.columns(4)
    cols[0].metric("Historical cases", f"{len(corpus):,}")
    cols[1].metric("Evaluation candidates", len(examples))
    cols[2].metric("Human annotations", f"{reviewed} / {len(examples)}")
    cols[3].metric("Systems run", len({p["system"] for p in predictions}))
    if reviewed < len(examples):
        st.warning(
            "Evaluation is pending human labels. Prediction counts are operational observations, not accuracy or safety evidence."
        )
    st.subheader("What this system proves—and what remains open")
    st.write(
        "Each response has an intent, a next-step draft, and a handling decision. Inspect retrieved cases and explicit escalation reasons before judging whether an answer is trustworthy."
    )
    metrics_path = ARTIFACTS / "metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text())
        partition = st.selectbox(
            "Evaluation partition", ["representative", "challenge", "development"]
        )
        table = []
        for system, parts in metrics.items():
            m = parts[partition]
            table.append(
                {
                    "System": system,
                    "Status": m["status"],
                    "Scored examples": m["labelled_evaluated"],
                    "Intent macro-F1": m["intent_macro_f1"],
                    "Auto coverage": m["auto_coverage"]["value"],
                    "Unsafe auto rate": m["unsafe_auto_rate"]["value"],
                    "Escalation recall": m["escalation_recall"]["value"],
                }
            )
        st.dataframe(table, width="stretch", hide_index=True)
    st.info(
        "Start with Case inspector to examine actual outputs. Use Label customer messages to build the golden set yourself."
    )

elif page == "Try a message":
    st.subheader("Inspect a new support request")
    st.caption(
        "The retrieval baseline runs locally. The live agent requires the model settings in your .env file."
    )
    message = st.text_area(
        "Customer message",
        placeholder="My phone battery drains quickly after an update.",
    )
    system = st.selectbox(
        "Response system",
        ["simple", "agent"],
        format_func=lambda x: "Retrieval baseline · local"
        if x == "simple"
        else "Grounded agent · live model",
    )
    if st.button("Draft response", type="primary"):
        if not message.strip():
            st.error("Enter a message first.")
        else:
            from hiver_support.agent import predict
            from hiver_support.provider import Provider
            from hiver_support.retrieval import Retriever
            from hiver_support.data import sanitize
            from hiver_support.io import load_env

            load_env(ROOT / ".env")
            try:
                with st.spinner("Retrieving evidence and drafting..."):
                    result = predict(
                        dict(
                            id="interactive",
                            text=sanitize(message),
                            context=[],
                            context_incomplete=False,
                        ),
                        system,
                        Retriever(corpus),
                        Provider() if system == "agent" else None,
                    )
                st.write(result["draft_reply"])
                st.info(result["reason"])
                st.write("**Intent:**", result["intent"])
                st.write("**Handling:**", result["decision"])
                lookup = {e["id"]: e for e in corpus}
                for match in result["retrieved"]:
                    with st.expander(f"Evidence {match['id']} · {match['score']:.3f}"):
                        st.write(lookup[match["id"]]["text"])
                        st.caption(lookup[match["id"]]["historical_reply"])
                if result["error"]:
                    st.error(result["error"])
            except ValueError as exc:
                st.error(str(exc))

elif page == "Case inspector":
    if not predictions:
        st.info("Run the pipeline to create predictions.")
        st.stop()
    system = st.selectbox("System", sorted({p["system"] for p in predictions}))
    decision = st.selectbox("Handling", ["all", "auto_handle", "escalate"])
    filtered = [
        p
        for p in predictions
        if p["system"] == system and (decision == "all" or p["decision"] == decision)
    ]
    if not filtered:
        st.info("No matching cases.")
        st.stop()
    selected = st.selectbox("Example", [p["id"] for p in filtered])
    prediction = next(p for p in filtered if p["id"] == selected)
    example = next(e for e in examples if e["id"] == selected)
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Customer message")
        st.write(example["text"])
        with st.expander("Prior context"):
            for turn in example["context"]:
                st.write(f"{turn['role']}: {turn['text']}")
        st.subheader("Draft reply")
        st.write(prediction["draft_reply"])
        st.write("**Intent:**", prediction["intent"])
        st.write("**Handling:**", prediction["decision"])
        st.info(prediction["reason"])
        if prediction["error"]:
            st.error(prediction["error"])
    with right:
        st.subheader("Retrieved evidence")
        lookup = {e["id"]: e for e in corpus}
        for match in prediction["retrieved"]:
            e = lookup[match["id"]]
            with st.expander(
                f"{e['id']} · similarity {match['score']:.3f}", expanded=True
            ):
                st.write("**Historical customer:**", e["text"])
                st.write("**Observed brand response:**", e["historical_reply"])
                st.caption(
                    "Observed response; successful resolution has not been verified."
                )
        st.caption(prediction["support_explanation"])

elif page == "Label customer messages":
    st.subheader("Build the human-labelled golden set")
    st.caption(
        "Read the annotation guide before starting. Predictions and future brand replies are hidden here to reduce anchoring."
    )
    if not examples:
        st.info("Prepare data first.")
        st.stop()
    annotator = st.text_input("Your name or reviewer ID")
    partition = st.selectbox(
        "Partition", ["development", "representative", "challenge"]
    )
    unfinished = st.checkbox("Only unlabelled examples", value=True)
    available = [
        e
        for e in examples
        if e["partition"] == partition
        and (not unfinished or validate_annotation(e.get("annotation")))
    ]
    if not available:
        st.success("This selection is complete.")
        st.stop()
    selected = st.selectbox("Example", [e["id"] for e in available])
    example = next(e for e in available if e["id"] == selected)
    for turn in example["context"]:
        st.caption(f"{turn['role']}: {turn['text']}")
    st.write(example["text"])
    if example["context_incomplete"]:
        st.warning("Some prior context is missing.")
    if partition == "development":
        suggestions = read_optional(
            ROOT / "data" / "assistance" / "development_suggestions.jsonl"
        )
        suggestion = next((row for row in suggestions if row["id"] == selected), None)
        if suggestion:
            with st.expander("AI development hint — decide your own label"):
                st.warning(suggestion["warning"])
                st.write("**Suggested intent:**", suggestion["suggested_intent"])
                st.write("**English eligibility:**", suggestion["suggested_eligible"])
                st.write(
                    "**Human review suggested:**",
                    suggestion["suggested_human_required"],
                )
                st.write(suggestion["rationale"])
                st.write(
                    "**An acceptable response should:**",
                    suggestion["response_requirements"],
                )
                st.caption(
                    "These hints never fill or save the annotation form. Held-out examples have no hints."
                )
    existing = example.get("annotation") or {}
    with st.form("annotation_" + selected):
        eligible = st.checkbox(
            "Eligible English support message", value=existing.get("eligible", True)
        )
        intent = st.selectbox(
            "Primary intent",
            list(INTENTS),
            index=list(INTENTS).index(existing.get("intent", "other_unclear")),
        )
        st.caption(INTENTS[intent])
        handling = st.radio(
            "Does the next response require human review?",
            ["Choose a label", "Yes", "No"],
            index=0,
        )
        reason = st.text_input("Handling reason", value=existing.get("reason", ""))
        requirements = st.text_area(
            "What must an acceptable reply accomplish?",
            value=existing.get("response_requirements", ""),
        )
        prohibited = st.text_area(
            "What must the reply not claim or request?",
            value=existing.get("prohibited_claims", ""),
        )
        notes = st.text_area(
            "Ambiguity or exclusion notes", value=existing.get("notes", "")
        )
        confirmed = st.checkbox(
            "I personally reviewed this example and chose these labels."
        )
        save = st.form_submit_button("Save human annotation", type="primary")
    if save:
        annotation = dict(
            source="human",
            annotator=annotator,
            eligible=eligible,
            intent=intent,
            human_required={"Yes": True, "No": False}.get(handling),
            reason=reason,
            response_requirements=requirements,
            prohibited_claims=prohibited,
            notes=notes,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )
        errors = validate_annotation(annotation)
        if not confirmed:
            errors.append("Confirm personal review before saving")
        if errors:
            st.error("; ".join(errors))
        else:
            latest = read_jsonl(DATA / "candidates.jsonl")
            for e in latest:
                if e["id"] == selected:
                    e["annotation"] = annotation
            write_jsonl(DATA / "candidates.jsonl", latest)
            st.rerun()

elif page == "Review replies":
    st.subheader("Blinded human reply ratings")
    path = ARTIFACTS / "review_packet.jsonl"
    packet = read_optional(path)
    pending = [r for r in packet if not r.get("human_rating")]
    if not pending:
        st.info("No unrated replies. Create a review packet after running the systems.")
        st.stop()
    annotator = st.text_input("Reviewer ID")
    selected = st.selectbox("Blind review ID", [r["blind_id"] for r in pending])
    row = next(r for r in pending if r["blind_id"] == selected)
    st.write("**Customer:**", row["text"])
    st.write("**Candidate reply:**", row["draft_reply"])
    with st.expander("Context and evidence", expanded=True):
        for turn in row["context"]:
            st.write(turn["role"] + ": " + turn["text"])
        for e in row["evidence"]:
            st.write(e["text"])
            st.caption(e["historical_reply"])
    st.caption(
        "0 = fails · 1 = partial/minor concern · 2 = fully meets dimension. Consult docs/judge_rubric.md."
    )
    with st.form("rating_" + selected):
        ratings = {
            d: st.selectbox(
                d.title(),
                [None, 0, 1, 2],
                format_func=lambda v: "Choose a score" if v is None else str(v),
            )
            for d in DIMENSIONS
        }
        critical = st.checkbox(
            "Critical failure: fabricated action, private credentials, or dangerous advice"
        )
        rationale = st.text_area("Reason for your scores")
        confirmed = st.checkbox("I personally rated this reply.")
        save = st.form_submit_button("Save rating", type="primary")
    if save:
        if (
            not annotator.strip()
            or not confirmed
            or any(v is None for v in ratings.values())
            or not rationale.strip()
        ):
            st.error(
                "Complete all scores, reviewer ID, rationale, and personal-review confirmation."
            )
        else:
            latest = read_jsonl(path)
            for r in latest:
                if r["blind_id"] == selected:
                    r["human_rating"] = {
                        **ratings,
                        "critical_failure": critical,
                        "rationale": rationale,
                        "annotator": annotator,
                        "source": "human",
                    }
            write_jsonl(path, latest)
            st.rerun()

elif page == "Judge audit":
    st.subheader("Where the judge disagrees with a human")
    packet = read_optional(ARTIFACTS / "review_packet.jsonl")
    judged = read_optional(ARTIFACTS / "judge_scores.jsonl")
    from hiver_support.metrics import agreement

    result = agreement(packet, judged)
    st.metric("Paired ratings", result["paired_ratings"])
    if not result["paired_ratings"]:
        st.info(
            "Human ratings and live judge outputs are required before agreement can be measured."
        )
    else:
        st.dataframe(
            [
                {
                    "Dimension": d,
                    "Exact agreement": v["exact_agreement"]["value"],
                    "Weighted kappa": v["weighted_kappa"],
                }
                for d, v in result["dimensions"].items()
            ],
            hide_index=True,
        )
        lookup = {r["blind_id"]: r for r in judged if not r["error"]}
        for row in packet:
            human = row.get("human_rating")
            judge = lookup.get(row["blind_id"], {}).get("rating")
            if human and judge and any(human[d] != judge[d] for d in DIMENSIONS):
                with st.expander(row["blind_id"]):
                    st.write(row["draft_reply"])
                    st.json({"human": human, "judge": judge})

elif page == "Evidence stress test":
    st.subheader("Does the agent stop when its evidence disappears?")
    st.write(
        "Compare normal, removed, and deliberately unrelated evidence. These controlled variants are separate from the real-message evaluation set."
    )
    path = ARTIFACTS / "stress_summary.json"
    if not path.exists():
        st.info("Run the stress command to populate this experiment.")
    else:
        summary = json.loads(path.read_text())
        st.dataframe(
            [
                {"Evidence": mode, "System": system, **counts}
                for mode, systems in summary.items()
                for system, counts in systems.items()
            ],
            hide_index=True,
        )
        st.caption(
            "Automation counts alone do not establish reply safety. Review generated replies for unsupported claims."
        )
    curve = ARTIFACTS / "risk_curve.json"
    if curve.exists():
        st.subheader("Development threshold sweep")
        rows = json.loads(curve.read_text())
        st.dataframe(
            [
                {
                    "System": r["system"],
                    "Threshold": r["threshold"],
                    "Observed auto count": r["observed_auto_count"],
                    "Scored coverage": r["coverage"]["value"],
                    "Unsafe rate": r["unsafe_auto_rate"]["value"],
                }
                for r in rows
            ],
            hide_index=True,
        )
