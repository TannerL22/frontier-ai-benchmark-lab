"""Private holdout preparation and an explicit independent-review gate."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sqlite3

from .integrity import digest, verify_manifest
from .pilot import object_hash, grade


def independent_answers(task):
    """A separate SQL calculation checks the generator's imperative oracle."""
    db = sqlite3.connect(":memory:")
    try:
        if task["category"] == "department_totals":
            db.execute("CREATE TABLE rows(department TEXT, quantity INTEGER, unit_cents INTEGER)")
            db.executemany("INSERT INTO rows VALUES(?,?,?)", [(r["department"], r["quantity"], r["unit_cents"]) for r in task["input_rows"]])
            return {"totals_cents": dict(db.execute("SELECT department, SUM(quantity * unit_cents) FROM rows GROUP BY department"))}
        if task["category"] == "duplicate_invoices":
            db.execute("CREATE TABLE rows(invoice_id TEXT, amount_cents INTEGER)")
            db.executemany("INSERT INTO rows VALUES(?,?)", [(r["invoice_id"], r["amount_cents"]) for r in task["input_rows"]])
            duplicate = [r[0] for r in db.execute("SELECT invoice_id FROM rows GROUP BY invoice_id HAVING COUNT(*) > 1 ORDER BY invoice_id")]
            total = db.execute("SELECT SUM(amount_cents) FROM (SELECT invoice_id, MAX(amount_cents) AS amount_cents FROM rows GROUP BY invoice_id)").fetchone()[0]
            return {"duplicate_ids": duplicate, "unique_total_cents": total}
        db.execute("CREATE TABLE rows(account TEXT, billed_cents INTEGER, paid_cents INTEGER)")
        db.executemany("INSERT INTO rows VALUES(?,?,?)", [(r["account"], r["billed_cents"], r["paid_cents"]) for r in task["input_rows"]])
        return {"balance_cents": dict(db.execute("SELECT account, billed_cents - paid_cents FROM rows"))}
    finally:
        db.close()


def prepare_holdout(destination, per_category=8):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Refusing to overwrite a private holdout")
    rng = random.SystemRandom()
    tasks, answers = [], {}
    for category in ("department_totals", "duplicate_invoices", "account_reconciliation"):
        for number in range(per_category):
            tid = f"holdout-{category}-{number + 1:02}"
            if category == "department_totals":
                rows = [{"department": rng.choice(["Research", "Operations", "Support"]),
                         "quantity": rng.randint(1, 8), "unit_cents": rng.randint(100, 9999)} for _ in range(rng.randint(10, 22))]
                rows.extend([{"department": "Support", "quantity": 1, "unit_cents": -rng.randint(100, 9999)},
                             {"department": "Research", "quantity": 0, "unit_cents": rng.randint(100, 9999)}])
                totals = defaultdict(int)
                for row in rows:
                    totals[row["department"]] += row["quantity"] * row["unit_cents"]
                answer = {"totals_cents": dict(totals)}
                instruction = "Sum quantity times unit_cents by department. Negative unit_cents are refunds and zero quantities contribute zero. Return only JSON totals_cents mapping every present department to its signed integer-cent net total."
            elif category == "duplicate_invoices":
                rows = [{"invoice_id": f"INV-{number:02}-{i:03}", "amount_cents": rng.randint(100, 99999)} for i in range(rng.randint(8, 18))]
                duplicates = rng.sample(rows, rng.randint(2, 5))
                answer = {"duplicate_ids": sorted(r["invoice_id"] for r in duplicates), "unique_total_cents": sum(r["amount_cents"] for r in rows)}
                rows += [dict(r) for r in duplicates] + [dict(duplicates[0])]
                rng.shuffle(rows)
                instruction = "Return JSON duplicate_ids, the sorted invoice IDs appearing more than once, and unique_total_cents. Repeated invoices have identical amounts and must count once, including IDs appearing three times."
            else:
                rows = [{"account": f"AC-{number:02}-{i:02}", "billed_cents": rng.randint(10000, 99999)} for i in range(rng.randint(6, 12))]
                for row in rows:
                    row["paid_cents"] = rng.randint(0, row["billed_cents"] + 10000)
                rows[0]["paid_cents"] = rows[0]["billed_cents"] + rng.randint(100, 10000)
                rows[1]["paid_cents"] = 0
                answer = {"balance_cents": {r["account"]: r["billed_cents"] - r["paid_cents"] for r in rows}}
                instruction = "Return JSON balance_cents mapping each account to billed_cents minus paid_cents. Keep overpayments as negative balances; do not clamp them to zero."
            task = {"task_id": tid, "category": category, "instruction": instruction, "input_rows": rows,
                    "currency": "USD", "data_class": "private_synthetic_holdout_pending_independent_review"}
            task["task_sha256"] = object_hash(task)
            if independent_answers(task) != answer:
                raise ValueError("Independent oracle check failed")
            tasks.append(task)
            answers[tid] = answer
    destination.mkdir(parents=True)
    (destination / "tasks.jsonl").write_text("".join(json.dumps(t, sort_keys=True) + "\n" for t in tasks), encoding="utf-8")
    (destination / "oracle_answers.json").write_text(json.dumps(answers, indent=2) + "\n", encoding="utf-8")
    manifest = {"holdout_id": "artifact_private_v1", "prepared_at": datetime.now(timezone.utc).isoformat(),
                "task_count": len(tasks), "per_category": per_category, "independent_oracle_checks": len(tasks),
                "sha256": {name: digest(destination / name) for name in ("tasks.jsonl", "oracle_answers.json")},
                "scope": "Private synthetic fixtures, generated with system randomness; not a validated population sample"}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    review = {"reviewer_id": "TannerL22", "reviewer_role": "independent review designated by project owner",
              "task_sha256": manifest["sha256"]["tasks.jsonl"], "reviewed_at": None,
              "overall_task_validity_accepted": False, "items": [{"task_id": t["task_id"], "decision": "not_reviewed", "notes": ""} for t in tasks]}
    (destination / "review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_review(destination, reviewer_id="TannerL22"):
    destination = Path(destination)
    manifest = verify_manifest(destination, destination / "manifest.json")
    review = json.loads((destination / "review.json").read_text())
    expected_ids = {t["task_id"] for t in map(json.loads, (destination / "tasks.jsonl").read_text().splitlines())}
    rows = review["items"]
    if review["reviewer_id"] != reviewer_id or review["task_sha256"] != manifest["sha256"]["tasks.jsonl"]:
        raise ValueError("Review identity or reviewed task digest mismatch")
    if {r["task_id"] for r in rows} != expected_ids or len(rows) != len(expected_ids):
        raise ValueError("Every task needs exactly one review decision")
    if not review.get("reviewed_at") or review.get("overall_task_validity_accepted") is not True or any(r["decision"] != "approve" for r in rows):
        raise ValueError("Independent task review is incomplete or requests changes")
    return review


def grade_controlled(destination, responses, systems, execution):
    verify_review(destination)
    if execution.get("execution_enabled") is not True:
        raise ValueError("Model execution/reporting is disabled in the preparation plan")
    if execution.get("max_paid_spend_usd") != 0:
        raise ValueError("This project preparation permits no paid model runs")
    for system in systems:
        if any(system.get(k) in (None, "", "unknown", "pending") for k in (
                "model_snapshot", "endpoint", "reasoning_effort", "harness", "fallback_policy", "resource_budget", "evaluation_date")):
            raise ValueError("Actual system conditions must be declared before controlled grading")
    for response in responses:
        if response.get("cost_usd") != 0 or response.get("elapsed_seconds") is None or response["elapsed_seconds"] > execution["max_seconds_per_attempt"]:
            raise ValueError("Actual responses need known zero paid cost and elapsed time within the budget")
    return grade(destination, responses, systems, execution["attempts_per_task"])
