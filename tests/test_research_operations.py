"""Source-version and preparation gates; no real model or future outcomes."""
from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
import shutil
import tempfile
import subprocess
import pytest

from frontierlab.core import Evidence
from frontierlab.pilot_ops import prepare_holdout, independent_answers, verify_review, grade_controlled
from frontierlab.prospective_ops import score_registered
from frontierlab.study import seal, score_future

ROOT = Path(__file__).resolve().parents[1]


def test_v53_four_revisions_and_explicit_historical_gap():
    before, after = Evidence(ROOT / "data/v5_2"), Evidence(ROOT / "data/v5_3")
    changed = [(a["benchmark_id"], a["model_name"], float(a["score"]), float(b["score"]))
               for a, b in zip(before.score_records, after.score_records) if float(a["score"]) != float(b["score"])]
    assert changed == [("B006", "GPT-6 Astra", 1570, 1571), ("B006", "GPT-6.1 Sol", 1557, 1561),
                       ("B007", "GPT-6 Astra", 1574, 1572), ("B007", "GPT-6.1 Sol", 1592, 1593)]
    statuses = after.catalog.status_counts()
    assert sum(statuses.values()) == 306 and statuses["inherited_not_rechecked"] == 1
    assert statuses["derived_from_rounded_components"] == 5
    historical = after.catalog.details("B062", "GPT-6 Astra")
    assert historical["score"] == 1440 and "cannot corroborate" in historical["source_review_qualification"]
    assert before.rows[0].denominator == after.rows[0].denominator


def test_source_review_covers_all_inherited_records_without_changing_time_population():
    review = json.loads((ROOT / "reviews/source_review_2026_10_13.json").read_text())
    assert review["summary"]["inherited_reviewed"] == 153
    assert review["summary"]["inherited_numbers_matching"] == 148
    assert review["summary"]["inherited_different_dated_population"] == 1
    rows = {(r["benchmark_id"], r["model_id"]): r for r in review["observations"]}
    assert len(rows) == len(review["observations"])
    assert rows["B062", "gpt-6-astra"]["stored_population_date"] == "2026-10-08"


def test_private_preparation_passes_a_separate_oracle_and_blocks_unreviewed_runs(tmp_path):
    workspace = tmp_path / "holdout"
    manifest = prepare_holdout(workspace, per_category=2)
    tasks = [json.loads(line) for line in (workspace / "tasks.jsonl").read_text().splitlines()]
    answers = json.loads((workspace / "oracle_answers.json").read_text())
    assert manifest["task_count"] == 6 and manifest["independent_oracle_checks"] == 6
    for task in tasks:
        assert independent_answers(task) == answers[task["task_id"]]
        reordered = copy.deepcopy(task)
        reordered["input_rows"].reverse()
        assert independent_answers(reordered) == answers[task["task_id"]]
    with pytest.raises(ValueError, match="review is incomplete"):
        verify_review(workspace)
    with pytest.raises(ValueError, match="review is incomplete"):
        grade_controlled(workspace, [], [], {"execution_enabled": False})
    review = json.loads((workspace / "review.json").read_text())
    review.update(reviewed_at=datetime.now(timezone.utc).isoformat(), overall_task_validity_accepted=True)
    for row in review["items"]:
        row["decision"] = "approve"
    # Synthetic attestation solely inside a temporary test fixture.
    (workspace / "review.json").write_text(json.dumps(review))
    verify_review(workspace)
    with pytest.raises(ValueError, match="disabled"):
        grade_controlled(workspace, [], [], {"execution_enabled": False})
    with pytest.raises(ValueError, match="no paid model"):
        grade_controlled(workspace, [], [], {"execution_enabled": True, "max_paid_spend_usd": 1})
    review["task_sha256"] = "tampered"
    (workspace / "review.json").write_text(json.dumps(review))
    with pytest.raises(ValueError, match="digest mismatch"):
        verify_review(workspace)


@pytest.fixture
def registration_fixture(tmp_path, monkeypatch):
    root = tmp_path / "study_root"
    root.mkdir()
    # Seal real fixed forecasts while placing the test bundle in an unused location.
    bundle = tmp_path / "registered"
    registration = seal(ROOT, bundle)
    start = datetime.fromisoformat(registration["sealed_at"]) + timedelta(seconds=1)
    publication = {"bundle_path": str(bundle), "public_registered_at": start.isoformat(),
                   "collection_ends_at": (start + timedelta(days=180)).isoformat(), "independent_reviewer_id": "fixture_reviewer"}
    monkeypatch.setattr("frontierlab.prospective_ops.verify_publication", lambda root, publication: registration)
    mids = registration["model_ids"][:2]
    row = {"benchmark_id": "future-fixture-ops", "family_id": "fresh-fixture-family", "genealogy_id": "fresh-fixture-ancestry",
           "domain": "Coding", "direction": "higher", "scores": {mids[0]: 10, mids[1]: 20},
           "published_at": (start + timedelta(hours=1)).isoformat(), "acquired_at": (start + timedelta(hours=2)).isoformat(),
           "reviewed_at": (start + timedelta(hours=3)).isoformat(), "reviewer_id": "fixture_reviewer", "prior_exposure": False,
           "review_accepted": True, "review_reason": "Synthetic fixture, not a collected outcome", "source_url": "https://example.org/fixture",
           "system_records": {mid: {key: "synthetic_fixture" for key in ("model_snapshot", "endpoint", "reasoning_effort", "harness", "fallback_policy", "resource_budget", "evaluation_date")} for mid in mids}}
    return publication, row, start + timedelta(days=1)


def test_registered_cutoff_is_later_than_local_seal_and_retains_proposals(registration_fixture):
    publication, row, now = registration_fixture
    publication["registration_url"] = "https://example.org/synthetic_registration"
    before_public = copy.deepcopy(row)
    before_public["published_at"] = publication["public_registered_at"]
    needs_review = copy.deepcopy(row)
    needs_review["reviewer_id"] = "not_the_designated_reviewer"
    report = score_registered(ROOT, publication, [before_public, needs_review, row, 123], now=now)
    assert report["proposal_count"] == 4 and report["accepted_outcome_count"] == 1
    assert "registered future-outcome window" in report["acquisition_ledger"][0]["reason"]
    assert "designated reviewer" in report["acquisition_ledger"][1]["reason"]
    assert report["acquisition_ledger"][3]["status"] == "retained_not_scored"


def test_registered_window_and_future_review_are_not_silently_accepted(registration_fixture):
    publication, row, now = registration_fixture
    publication["registration_url"] = "https://example.org/synthetic_registration"
    outside = copy.deepcopy(row)
    outside["published_at"] = (now + timedelta(days=200)).isoformat()
    future_review = copy.deepcopy(row)
    future_review["reviewed_at"] = (now + timedelta(days=1)).isoformat()
    report = score_registered(ROOT, publication, [outside, future_review], now=now)
    assert report["accepted_outcome_count"] == 0
    assert all(r["status"] == "retained_not_scored" for r in report["acquisition_ledger"])


def test_private_review_ui_cannot_accept_an_unreviewed_dataset(tmp_path, monkeypatch):
    workspace = tmp_path / "private_pilot/artifact_private_v1"
    prepare_holdout(workspace, per_category=1)
    app_path = tmp_path / "pilot_review_app.py"
    shutil.copyfile(ROOT / "pilot_review_app.py", app_path)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(app_path), default_timeout=30).run()
    assert not app.exception
    next(b for b in app.button if b.label == "Record my overall review").click().run()
    assert not app.exception and app.error
    review = json.loads((workspace / "review.json").read_text())
    assert review["overall_task_validity_accepted"] is False
    assert all(r["decision"] == "not_reviewed" for r in review["items"])


def test_public_registry_keeps_frozen_inputs_after_ui_changes(tmp_path):
    root = tmp_path / "registered_root"
    shutil.copytree(ROOT / "data/v5_2", root / "data/v5_2")
    shutil.copytree(ROOT / "src/frontierlab", root / "src/frontierlab", ignore=shutil.ignore_patterns("__pycache__"))
    for relative in ("studies/prospective_v1/protocol.json", "scripts/prospective_study.py"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    bundle = root / "registered"
    registration = seal(root, bundle)
    for args in (["init"], ["add", "."], ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.org", "commit", "-m", "Synthetic registered inputs"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    start = datetime.fromisoformat(registration["sealed_at"]) + timedelta(seconds=1)
    publication = {"status": "publicly_registered_awaiting_future_outcomes",
                   "registration_url": "https://github.com/TannerL22/frontier-ai-benchmark-lab/issues/5",
                   "public_registered_at": start.isoformat(), "collection_ends_at": (start + timedelta(days=180)).isoformat(),
                   "bundle_path": "registered", "frozen_input_commit": commit,
                   "forecast_sha256": registration["forecast_sha256"], "independent_reviewer_id": "fixture_reviewer"}
    mids = registration["model_ids"][:2]
    row = {"benchmark_id": "future-fixture", "family_id": "fresh-fixture", "genealogy_id": "fresh-fixture-ancestry",
           "domain": "Coding", "direction": "higher", "scores": {mids[0]: 10, mids[1]: 20},
           "published_at": (start + timedelta(hours=1)).isoformat(), "acquired_at": (start + timedelta(hours=2)).isoformat(),
           "reviewed_at": (start + timedelta(hours=3)).isoformat(), "reviewer_id": "fixture_reviewer", "prior_exposure": False,
           "review_accepted": True, "review_reason": "Synthetic test fixture only", "source_url": "https://example.org/fixture",
           "system_records": {mid: {key: "fixture" for key in ("model_snapshot", "endpoint", "reasoning_effort", "harness", "fallback_policy", "resource_budget", "evaluation_date")} for mid in mids}}
    expected = score_future(root, bundle, [row])
    ui_file = root / "src/frontierlab/presentation.py"
    ui_file.write_text(ui_file.read_text(encoding="utf-8") + "\n# Synthetic UI revision\n", encoding="utf-8")
    report = score_registered(root, publication, [row], now=start + timedelta(days=1))
    assert report["accepted_outcome_count"] == 1
    assert report["summaries"] == expected["summaries"]
    assert report["predictions"] == expected["predictions"]
    assert "Synthetic UI revision" in ui_file.read_text(encoding="utf-8")
    engine = root / "src/frontierlab/study.py"
    original_engine = engine.read_bytes()
    engine.write_bytes(original_engine + b"\n# Synthetic engine revision\n")
    with pytest.raises(ValueError, match="integrity mismatch"):
        score_registered(root, publication, [row], now=start + timedelta(days=1))
    engine.write_bytes(original_engine)
    # A current UI revision is permitted; a changed sealed forecast still fails.
    with (bundle / "forecasts.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="integrity mismatch"):
        score_registered(root, publication, [row], now=start + timedelta(days=1))
