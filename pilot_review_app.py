"""Local-only private task review. This is not the hosted Streamlit entry point."""
import json
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
from frontierlab.integrity import verify_manifest

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "private_pilot/artifact_private_v1"
st.set_page_config(page_title="Private pilot review", layout="wide")
st.title("Review the private pilot tasks")
st.write("You are the designated independent reviewer. These synthetic tasks have passed internal oracle checks; your review of realism, instructions and expected answers is still required. No model has been run.")
if not WORKSPACE.exists():
    st.info("Prepare the private holdout before reviewing it.")
    st.stop()
manifest = verify_manifest(WORKSPACE, WORKSPACE / "manifest.json")
tasks = [json.loads(line) for line in (WORKSPACE / "tasks.jsonl").read_text().splitlines()]
answers = json.loads((WORKSPACE / "oracle_answers.json").read_text())
review_path = WORKSPACE / "review.json"
review = json.loads(review_path.read_text())
by_id = {r["task_id"]: r for r in review["items"]}
task = st.selectbox("Task", tasks, format_func=lambda t: t["task_id"])
tid = task["task_id"]
st.write(task["instruction"])
st.caption("USD integer cents · " + task["data_class"].replace("_", " "))
st.dataframe(task["input_rows"], hide_index=True, width="stretch")
with st.expander("Check the proposed expected answer"):
    st.json(answers[tid])
st.write("Check that the task is realistic enough for the pilot, has one clear answer, handles its edge cases correctly, and that the expected artifact is correct. Approval does not establish broad benchmark validity.")
options = ["not_reviewed", "approve", "needs_revision", "reject"]
with st.form("task_review_" + tid):
    decision = st.radio("Your task decision", options, index=options.index(by_id[tid]["decision"]))
    notes = st.text_area("Notes and reasons", value=by_id[tid]["notes"])
    saved = st.form_submit_button("Save this task review")
if saved:
    if decision in {"needs_revision", "reject"} and not notes.strip():
        st.error("Record the reason so the task can be revised.")
    else:
        by_id[tid].update(decision=decision, notes=notes)
        review["items"] = list(by_id.values())
        review["overall_task_validity_accepted"] = False
        review["reviewed_at"] = None
        review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        st.success("Task review saved locally. Overall approval remains separate.")
approved = sum(r["decision"] == "approve" for r in review["items"])
st.metric("Approved tasks", f"{approved} / {len(tasks)}")
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
