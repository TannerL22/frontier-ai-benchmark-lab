"""Local-only private task review. This is not the hosted Streamlit entry point."""
import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from frontierlab.integrity import verify_manifest
from frontierlab.presentation import (
    badge, inject_lab_theme_css, render_audit_callout,
    render_hero, render_kpi_grid, render_section,
)

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "private_pilot/artifact_private_v1"
OPTIONS = ["not_reviewed", "approve", "needs_revision", "reject"]
LABELS = {"not_reviewed": "Not reviewed", "approve": "Approve", "needs_revision": "Needs revision", "reject": "Reject"}
st.set_page_config(page_title="Frontier AI · Private pilot review", page_icon="◈", layout="wide")
inject_lab_theme_css()
if not WORKSPACE.exists():
    render_hero("Private pilot review", "Prepare the private holdout before reviewing it.", release="artifact_private_v1", status="Not prepared", tone="pending")
    st.info("Prepare the private holdout before reviewing it.")
    st.stop()
manifest = verify_manifest(WORKSPACE, WORKSPACE / "manifest.json")
tasks = [json.loads(line) for line in (WORKSPACE / "tasks.jsonl").read_text().splitlines()]
answers = json.loads((WORKSPACE / "oracle_answers.json").read_text())
review_path = WORKSPACE / "review.json"
review = json.loads(review_path.read_text())
by_id = {r["task_id"]: r for r in review["items"]}
task_ids = [t["task_id"] for t in tasks]
if review["task_sha256"] != manifest["sha256"]["tasks.jsonl"] or set(by_id) != set(task_ids) or len(review["items"]) != len(task_ids):
    st.error("The review record does not match the sealed private task set.")
    st.stop()
approved = sum(r["decision"] == "approve" for r in review["items"])
reviewed = sum(r["decision"] != "not_reviewed" for r in review["items"])
changes = sum(r["decision"] in {"needs_revision", "reject"} for r in review["items"])
accepted_overall = review.get("overall_task_validity_accepted") is True
render_hero("Review the private pilot tasks", "Inspect each synthetic task, its edge cases and the proposed answer. Record your independent decision before accepting the task set.",
            eyebrow="Frontier AI · Independent review workspace", release="artifact_private_v1",
            status="Owner review recorded" if accepted_overall else "Independent review pending", tone="verified" if accepted_overall else "pending",
            context=[("Reviewer", review["reviewer_id"]), ("Currency", "USD · integer cents"), ("Model runs", "0"), ("Storage", "Local private holdout")])
render_kpi_grid([
    {"label": "Approved tasks", "value": f"{approved} / {len(tasks)}", "status": "Human decisions", "tone": "verified" if approved == len(tasks) else "pending", "caption": "Every task needs an independent approval"},
    {"label": "Review progress", "value": f"{reviewed / len(tasks):.0%}", "status": f"{reviewed} decisions recorded", "caption": "Approvals, revision requests and rejections"},
    {"label": "Changes requested", "value": changes, "status": "Review decisions", "tone": "issue" if changes else "neutral", "caption": "Resolve these tasks before overall acceptance"},
    {"label": "Internal oracle checks", "value": manifest["independent_oracle_checks"], "status": "Prepared checks", "tone": "verified", "caption": "SQL oracle checks do not replace your review"},
])
if st.session_state.pop("review_saved_notice", False):
    st.success("Task review saved locally. Overall approval remains separate.")


def move_task(offset):
    current = st.session_state.get("task_choice", task_ids[0])
    index = task_ids.index(current)
    st.session_state["task_choice"] = task_ids[max(0, min(len(task_ids) - 1, index + offset))]


with st.sidebar:
    st.html('<div class="lab-brand"><span class="lab-mark">◈</span><span>Private review</span></div><div class="lab-eyebrow">Task navigator</div>')
    tid = st.selectbox("Task", task_ids, key="task_choice", format_func=lambda value: value.removeprefix("holdout-").replace("_", " "))
    previous, next_task = st.columns(2)
    previous.button("← Previous", on_click=move_task, args=(-1,), disabled=tid == task_ids[0], width="stretch")
    next_task.button("Next →", on_click=move_task, args=(1,), disabled=tid == task_ids[-1], width="stretch")
    st.progress(reviewed / len(tasks), text=f"{reviewed} of {len(tasks)} tasks reviewed")
    queue_status = st.selectbox("Queue status", ["All tasks"] + list(LABELS.values()))
    queue = [{"Task": t["task_id"].removeprefix("holdout-"), "Decision": LABELS[by_id[t["task_id"]]["decision"]]} for t in tasks
             if queue_status == "All tasks" or LABELS[by_id[t["task_id"]]["decision"]] == queue_status]
    st.dataframe(queue, hide_index=True, width="stretch", height=350)
    st.caption("Review decisions and private answers stay in this local workspace. Model execution remains disabled.")

task = next(t for t in tasks if t["task_id"] == tid)
input_pane, review_pane = st.columns([1.35, 1], gap="large")
with input_pane:
    render_section("Task evidence", f"{task_ids.index(tid) + 1:02d} / {len(tasks):02d}")
    render_audit_callout(task["category"].replace("_", " ").capitalize(), task["instruction"], "Synthetic holdout", "neutral")
    st.caption(tid + " · USD integer cents")
    st.dataframe(task["input_rows"], hide_index=True, width="stretch", height=390,
                 column_config={field: st.column_config.NumberColumn(format="%d") for field in task["input_rows"][0] if field.endswith("cents") or field == "quantity"})
    with st.expander("Task commitment and classification"):
        render_audit_callout("Private task input commitment", task["data_class"].replace("_", " "), "Sealed inputs", "verified", task["task_sha256"])
        st.caption("Internal checks exercise this prepared evaluator. No model has been run; approval does not establish broad benchmark validity.")

with review_pane:
    render_section("Proposed expected answer", "Oracle artifact · not a model response")
    with st.container(border=True):
        st.json(answers[tid], expanded=True)
    with st.expander("Review rubric", expanded=True):
        st.markdown("1. **Realism:** the workflow is suitable for this narrow pilot.\n2. **Clarity:** the instructions lead to one clear answer.\n3. **Edge cases:** refunds, duplicates or overpayments are handled correctly.\n4. **Artifact validity:** the expected JSON and exact integer amounts are correct.")
    st.html(badge(LABELS[by_id[tid]["decision"]], "verified" if by_id[tid]["decision"] == "approve" else "pending"))
    with st.form("task_review_" + tid):
        decision = st.radio("Your task decision", OPTIONS, index=OPTIONS.index(by_id[tid]["decision"]), format_func=LABELS.get)
        notes = st.text_area("Notes and reasons", value=by_id[tid]["notes"], placeholder="Record ambiguities, edge cases or reasons for a revision.")
        saved = st.form_submit_button("Save this task review", type="primary", width="stretch")
    if saved:
        if decision in {"needs_revision", "reject"} and not notes.strip():
            st.error("Record the reason so the task can be revised.")
        else:
            by_id[tid].update(decision=decision, notes=notes)
            review["items"] = list(by_id.values())
            review["overall_task_validity_accepted"] = False
            review["reviewed_at"] = None
            review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
            st.session_state["review_saved_notice"] = True
            st.rerun()

st.divider()
render_section("Accept the reviewed task set", "Independent sign-off · separate from individual decisions")
render_audit_callout("Overall task validity", "Acceptance requires your approval of every task. Model execution also requires actual system conditions and remains disabled in the preparation plan.",
                     "Recorded" if accepted_overall else "Pending", "verified" if accepted_overall else "pending")
with st.form("overall_review"):
    accepted = st.checkbox("I have independently checked every task and accept this task set for the narrow pilot.")
    signoff = st.form_submit_button("Record my overall review")
if signoff:
    if accepted and approved == len(tasks):
        review.update(overall_task_validity_accepted=True, reviewed_at=datetime.now(timezone.utc).isoformat(), reviewer_id="TannerL22")
        review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        st.success("Independent task review recorded. Model execution remains disabled until actual system conditions are declared.")
    else:
        st.error("Overall acceptance requires an independent approval decision for every task.")
st.download_button("Download your review record", review_path.read_text(), "private_pilot_review.json", "application/json")
with st.expander("Protocol & independent review packet"):
    protocol = ROOT / "studies/artifact_pilot_v1/protocol.json"
    packet = ROOT / "studies/artifact_pilot_v1/REVIEW_PACKET.md"
    if protocol.exists():
        st.json(json.loads(protocol.read_text(encoding="utf-8")))
    if packet.exists():
        st.markdown(packet.read_text(encoding="utf-8"))
        st.download_button("Download independent pilot review packet", packet.read_text(encoding="utf-8"), "pilot_review_packet.md", "text/markdown")
