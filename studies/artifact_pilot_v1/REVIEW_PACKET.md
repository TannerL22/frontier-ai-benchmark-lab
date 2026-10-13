# Independent pilot review packet

Reviewer: the project owner, TannerL22, as designated in this conversation. Status: pending actual review. Codex's internal checks are not recorded as your independent review.

The private holdout contains 24 synthetic tasks: eight department-total tasks, eight duplicate-invoice tasks and eight account-reconciliation tasks. The public demonstration tasks remain separate. Private prompts, rows and oracle answers are ignored by Git; only their digests and counts are published. System randomness generated the holdout, and a separate SQL implementation checks each expected answer.

Start the local review page with:

```bash
streamlit run pilot_review_app.py --server.address 127.0.0.1 --server.port 8503
```

For each task, inspect the inputs and instructions, then check the proposed expected answer. Decide whether it is suitable for the narrow pilot or needs revision. The review page records each decision locally and requires every task's approval before overall acceptance. Approval of this small synthetic set is not a claim about a representative population of professional workflows.

Review these points:

1. Does the task represent a coherent professional data-reconciliation operation, with enough difficulty to reveal relevant mistakes?
2. Is its instruction unambiguous about integer cents, refunds, zero quantities, repeated invoices and negative account balances?
3. Does the proposed expected answer follow from the supplied rows? Check the edge cases rather than merely accepting the internal oracle check.
4. Is strict JSON correctness a useful primary outcome for this task? Note any quality/recovery outcomes needing a separate human rubric.
5. Does the proposed three-attempt, five-minute budget make sense for the systems eventually selected?

After review, run `python scripts/private_pilot.py verify-review`. Actual model grading is gated on the reviewed task digest and explicit real system conditions. The execution plan is disabled and limits paid spend to zero. No actual model endpoint, run or model-performance result has been invented.
