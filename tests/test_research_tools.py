"""Synthetic checks of study integrity and evaluator failure handling, not model results."""
from datetime import timedelta
from pathlib import Path
import copy
import json
import pytest
from frontierlab.integrity import digest
from frontierlab.study import seal, verify, score_future, timestamp
from frontierlab.pilot import prepare, grade, equal_artifact

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def study_bundle(tmp_path):
    destination = tmp_path / "registered"
    registration = seal(ROOT, destination)
    return destination, registration


def outcome(registration):
    model_ids = registration["model_ids"][:2]
    return {"benchmark_id": "future-fixture", "family_id": "new-fixture-family", "genealogy_id": "new-fixture-ancestry",
            "domain": "Coding", "direction": "higher", "scores": {model_ids[0]: 10, model_ids[1]: 20},
            "published_at": (timestamp(registration["sealed_at"]) + timedelta(days=1)).isoformat(),
            "source_url": "https://example.org/synthetic-fixture", "review_accepted": True,
            "review_reason": "Synthetic testing only, no future research outcome acquired",
            "system_records": {mid: {key: "explicit_synthetic_fixture" for key in (
                "model_snapshot", "endpoint", "reasoning_effort", "harness", "fallback_policy", "resource_budget", "evaluation_date")} for mid in model_ids}}


def test_seal_refuses_overwrite_and_detects_tampering(study_bundle):
    destination, registration = study_bundle
    assert verify(ROOT, destination)["forecast_count"] == 1372
    with pytest.raises(ValueError, match="overwrite"):
        seal(ROOT, destination)
    with (destination / "forecasts.jsonl").open("a") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="integrity mismatch"):
        verify(ROOT, destination)


@pytest.mark.parametrize("change,reason", [
    ({"published_at": "2020-01-01T00:00:00Z"}, "predates"),
    ({"family_id": "USE_OLD"}, "Previously seen"),
    ({"review_accepted": False}, "eligibility review"),
    ({"scores": {"new-unregistered-model": 10}}, "registered roster"),
    ({"system_records": {}}, "system metadata"),
    ({"scores": "bad"}, "registered roster"),
])
def test_ineligible_future_outcomes_remain_in_report(study_bundle, change, reason):
    destination, registration = study_bundle
    row = outcome(registration)
    if change.get("family_id") == "USE_OLD":
        change = {"family_id": registration["seen_families"][0]}
    row.update(change)
    result = score_future(ROOT, destination, [row])
    assert not result["predictions"]
    assert reason in result["rejected_outcomes"][0]["reason"]


def test_future_score_retains_duplicate_and_tie_counts(study_bundle):
    destination, registration = study_bundle
    row = outcome(registration)
    tied = copy.deepcopy(row)
    tied["benchmark_id"] = "future-tie-fixture"
    tied["scores"] = {mid: 10 for mid in tied["scores"]}
    result = score_future(ROOT, destination, [row, row, tied])
    assert len(result["rejected_outcomes"]) == 1
    assert result["accepted_outcome_count"] == 2 and result["observed_tied_pair_count"] == 1
    random = next(s for s in result["summaries"] if s["method"] == "Random direction reference")
    assert random["family_macro_accuracy_abstention_half"] == .5 and random["family_macro_brier"] == .25


def pilot_system():
    return {"system_id": "fixture", **{key: "synthetic_fixture" for key in (
        "model_snapshot", "endpoint", "reasoning_effort", "harness", "fallback_policy", "resource_budget", "evaluation_date", "data_class")}}


def test_pilot_incorrect_and_missing_attempts_are_retained(tmp_path):
    destination = tmp_path / "pilot"
    tasks, answers = prepare(destination)
    assert len(tasks) == 12
    task = tasks[0]
    responses = [{"system_id": "fixture", "task_id": task["task_id"], "task_sha256": task["task_sha256"],
                  "attempt": 1, "artifact": answers[task["task_id"]]},
                 {"system_id": "fixture", "task_id": task["task_id"], "task_sha256": task["task_sha256"],
                  "attempt": 2, "artifact": {"totals_cents": {"wrong_department": 0}}}]
    result = grade(destination, responses, [pilot_system()])
    assert len(result["attempt_records"]) == 36
    assert sum(r["correct"] for r in result["attempt_records"]) == 1
    assert sum(r["status"] == "missing_submission" for r in result["attempt_records"]) == 34
    assert len(result["paired_attempts"]) == 36
    with pytest.raises(ValueError, match="Duplicate response"):
        grade(destination, responses + responses[:1], [pilot_system()])
    responses[0]["task_sha256"] = "wrong"
    with pytest.raises(ValueError, match="hash mismatch"):
        grade(destination, responses, [pilot_system()])


def test_artifact_types_and_negative_balances():
    assert equal_artifact({"balance_cents": {"A": -100}}, {"balance_cents": {"A": -100}})
    assert not equal_artifact(True, 1)
    assert not equal_artifact(100.0, 100)
    assert not equal_artifact({"a": 1, "extra": 2}, {"a": 1})
    assert not equal_artifact(["B", "A"], ["A", "B"])


def test_public_pilot_generation_is_seeded_and_tamper_evident(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    prepare(first)
    prepare(second)
    assert digest(first / "tasks.jsonl") == digest(second / "tasks.jsonl")
    with pytest.raises(ValueError, match="overwrite"):
        prepare(first)
    (first / "oracle_answers.json").write_text("{}")
    with pytest.raises(ValueError, match="integrity mismatch"):
        grade(first, [], [pilot_system()])
