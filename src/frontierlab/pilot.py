"""Public synthetic artifact-workflow pilot; no provider calls or credentials."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import math
import random

from .integrity import digest, verify_manifest


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def prepare(destination, seed=20261013):
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Refusing to overwrite a pilot workspace")
    rng = random.Random(seed)
    tasks, answers = [], {}
    for category in ("department_totals", "duplicate_invoices", "account_reconciliation"):
        for number in range(4):
            tid = f"{category}-{number + 1:02}"
            if category == "department_totals":
                rows = [{"department": rng.choice(["Research", "Operations", "Support"]),
                         "quantity": rng.randint(1, 8), "unit_cents": rng.randint(100, 9999)} for _ in range(10)]
                expected = defaultdict(int)
                for row in rows:
                    expected[row["department"]] += row["quantity"] * row["unit_cents"]
                answer = {"totals_cents": dict(expected)}
                instruction = "Return JSON totals_cents mapping each present department to quantity*unit_cents summed over its rows. All values are integer cents."
            elif category == "duplicate_invoices":
                rows = [{"invoice_id": f"INV-{i:03}", "amount_cents": rng.randint(100, 99999)} for i in range(8)]
                duplicates = rng.sample(rows, 3)
                answer = {"duplicate_ids": sorted(r["invoice_id"] for r in duplicates),
                          "unique_total_cents": sum(r["amount_cents"] for r in rows)}
                rows += [dict(r) for r in duplicates]
                rng.shuffle(rows)
                instruction = "Return JSON duplicate_ids (sorted IDs occurring more than once) and unique_total_cents. Identical duplicate invoices count once toward the total."
            else:
                rows = [{"account": f"AC-{i:02}", "billed_cents": rng.randint(10000, 99999)} for i in range(6)]
                for row in rows:
                    row["paid_cents"] = rng.randint(0, row["billed_cents"] + 10000)
                answer = {"balance_cents": {r["account"]: r["billed_cents"] - r["paid_cents"] for r in rows}}
                instruction = "Return JSON balance_cents mapping each account to billed_cents minus paid_cents. Retain negative balances for overpayments."
            task = {"task_id": tid, "category": category, "instruction": instruction,
                    "input_rows": rows, "data_class": "public_synthetic_demonstration"}
            task["task_sha256"] = object_hash(task)
            tasks.append(task)
            answers[tid] = answer
    destination.mkdir(parents=True)
    (destination / "tasks.jsonl").write_text("".join(json.dumps(t, sort_keys=True) + "\n" for t in tasks), encoding="utf-8")
    (destination / "oracle_answers.json").write_text(json.dumps(answers, indent=2) + "\n", encoding="utf-8")
    systems = {"systems": [{"system_id": "replace_with_actual_system_id", "model_snapshot": "unknown",
                           "endpoint": "unknown", "reasoning_effort": "unknown", "harness": "manual_json_artifact_submission",
                           "fallback_policy": "none_declared", "resource_budget": "declare_token_time_and_spend_caps_before_runs",
                           "repeated_attempts": 3, "evaluation_date": "unknown", "data_class": "configuration_template_not_a_model_run"}]}
    (destination / "systems_template.json").write_text(json.dumps(systems, indent=2) + "\n", encoding="utf-8")
    paths = ["tasks.jsonl", "oracle_answers.json"]
    (destination / "manifest.json").write_text(json.dumps({"seed": seed, "task_count": len(tasks),
            "sha256": {p: digest(destination / p) for p in paths},
            "qualification": "Public synthetic evaluator fixtures; expert task review and private holdouts are still required for an original model study."}, indent=2) + "\n", encoding="utf-8")
    return tasks, answers


def equal_artifact(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(equal_artifact(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(equal_artifact(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, int):
        return type(actual) is int and actual == expected
    return type(actual) is type(expected) and actual == expected


def grade(destination, responses, systems, attempts=3):
    destination = Path(destination)
    verify_manifest(destination, destination / "manifest.json")
    tasks = {t["task_id"]: t for t in map(json.loads, (destination / "tasks.jsonl").read_text().splitlines())}
    answers = json.loads((destination / "oracle_answers.json").read_text())
    registry = {}
    for system in systems:
        sid = system.get("system_id")
        required = ("model_snapshot", "endpoint", "reasoning_effort", "harness", "fallback_policy", "resource_budget", "evaluation_date", "data_class")
        if not sid or sid in registry or any(not system.get(k) for k in required):
            raise ValueError("Unique systems with explicit run configuration fields are required")
        registry[sid] = system
    if not registry or type(attempts) is not int or attempts < 1:
        raise ValueError("At least one system and a positive number of attempts are required")
    submitted = {}
    for row in responses:
        sid, tid, attempt = row["system_id"], row["task_id"], row["attempt"]
        if sid not in registry or tid not in tasks or type(attempt) is not int or not 1 <= attempt <= attempts:
            raise ValueError("Unknown system/task or attempt outside the registered budget")
        key = sid, tid, attempt
        if key in submitted:
            raise ValueError("Duplicate response attempt")
        if row.get("task_sha256") != tasks[tid]["task_sha256"]:
            raise ValueError("Response task hash mismatch")
        for metric in ("elapsed_seconds", "cost_usd"):
            value = row.get(metric)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
                raise ValueError("Recorded time and cost must be nonnegative finite numbers or null")
        submitted[key] = row
    records = []
    for sid in registry:
        for tid, task in tasks.items():
            for attempt in range(1, attempts + 1):
                row = submitted.get((sid, tid, attempt))
                correct = bool(row and equal_artifact(row.get("artifact"), answers[tid]))
                records.append({"system_id": sid, "task_id": tid, "category": task["category"], "attempt": attempt,
                                "status": "missing_submission" if row is None else "correct" if correct else "incorrect_artifact",
                                "correct": correct, "elapsed_seconds": row.get("elapsed_seconds") if row else None,
                                "cost_usd": row.get("cost_usd") if row else None})
    summaries = []
    for sid, system in registry.items():
        for category in sorted({t["category"] for t in tasks.values()}):
            rows = [r for r in records if r["system_id"] == sid and r["category"] == category]
            summaries.append({"system_id": sid, "category": category, "attempts": len(rows),
                              "correct": sum(r["correct"] for r in rows), "missing": sum(r["status"] == "missing_submission" for r in rows),
                              "accuracy": sum(r["correct"] for r in rows) / len(rows), "data_class": system["data_class"]})
    return {"qualification": "Public synthetic tasks. Oracle demonstrations validate the evaluator and are never AI capability results. Repeated attempts are clustered by task, not independent tasks.",
            "systems": systems, "summaries": summaries, "attempt_records": records,
            "paired_attempts": [{"task_id": tid, "attempt": attempt,
                                 "correct_by_system": {sid: next(r["correct"] for r in records if r["system_id"] == sid and r["task_id"] == tid and r["attempt"] == attempt) for sid in registry}}
                                for tid in tasks for attempt in range(1, attempts + 1)]}
