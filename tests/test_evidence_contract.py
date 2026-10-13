import csv
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from frontierlab.core import Evidence
from frontierlab.catalog import Catalog
from frontierlab.analysis import PAIR_BASELINES, validation_records
from frontierlab.integrity import digest, verify_manifest

ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, records, fields=None):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def mutate_csv(path, transform):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    transformed = transform(rows)
    fields = list(dict.fromkeys(fields + [key for row in transformed for key in row]))
    write_csv(path, transformed, fields)


@pytest.fixture
def tiny_release(tmp_path):
    config = {"baseline_models": ["A", "B", "C", "D"], "domain_weights": {"Coding": 1},
              "display_anchor": "A", "scale_factor": 20}
    (tmp_path / "config.json").write_text(json.dumps(config))
    write_csv(tmp_path / "models.csv", [{"model_name": name} for name in config["baseline_models"]])
    write_csv(tmp_path / "candidate_scores.csv", [], ["model_name"])
    write_csv(tmp_path / "external_indices.csv", [], ["primary_index_eligible"])
    benchmark = {"benchmark_name": "Synthetic", "evaluator": "Fixture", "domain": "Coding",
                 "unit": "pct", "configuration": "Known synthetic conditions", "scale_floor": "5",
                 "source_url": "https://example.org/fixture", "provenance": "Synthetic test, not real evidence",
                 "included": "1", "overlap_notes": ""}
    write_csv(tmp_path / "benchmarks.csv", [dict(benchmark, benchmark_id="B1", family_id="F1"),
                                          dict(benchmark, benchmark_id="B2", family_id="F2")])
    write_csv(tmp_path / "scores.csv", [{"benchmark_id": bid, "model_name": model, "score": str(value),
                                        "verified_source_url": "https://example.org/fixture", "evidence_status": "synthetic"}
                                       for bid, model, value in [("B1", "A", 10), ("B1", "B", 15), ("B2", "C", 20), ("B2", "D", 30)]])
    return tmp_path


@pytest.mark.parametrize("kind,expected", [
    ("orphan", "Unknown benchmark"), ("percentage", "Invalid pct"),
    ("nonfinite_score", "Invalid pct"), ("nonfinite_floor", "Invalid scale floor"),
    ("duplicate_model", "unique identities"), ("unregistered", "registered models"),
    ("duplicate_benchmark", "unique"), ("bad_url", "provenance"),
])
def test_rejects_semantically_invalid_inputs(tiny_release, kind, expected):
    if kind == "duplicate_model":
        cfg = json.loads((tiny_release / "config.json").read_text())
        cfg["baseline_models"].append("A")
        (tiny_release / "config.json").write_text(json.dumps(cfg))
    elif kind == "unregistered":
        mutate_csv(tiny_release / "models.csv", lambda rows: rows[:-1])
    elif kind == "duplicate_benchmark":
        mutate_csv(tiny_release / "benchmarks.csv", lambda rows: rows + [rows[0]])
    elif kind == "nonfinite_floor":
        mutate_csv(tiny_release / "benchmarks.csv", lambda rows: [dict(r, scale_floor="nan") for r in rows])
    else:
        fields = {"orphan": {"benchmark_id": "B999"}, "percentage": {"score": "130"},
                  "nonfinite_score": {"score": "inf"}, "bad_url": {"verified_source_url": "javascript:alert(1)"}}
        mutate_csv(tiny_release / "scores.csv", lambda rows: [dict(rows[0], **fields[kind])] + rows[1:])
    with pytest.raises(ValueError, match=expected):
        Evidence(tiny_release)


def test_disconnected_components_are_not_silently_aligned(tiny_release):
    evidence = Evidence(tiny_release)
    assert evidence.all_fit("Equal families") is None
    predictions = evidence.pair_predictions(range(2), "Equal families")
    assert predictions[0, 1] == pytest.approx(1)
    assert predictions[2, 3] == pytest.approx(2)
    assert predictions[0, 2] is None
    records = evidence.cv_pairs("family")
    summary = evidence.macro_accuracy(records, "family", "Equal families")
    assert summary["attempted_pair_count"] == 2 and summary["abstained_pair_count"] == 2
    assert summary["fold_count"] == 0 and summary["attempted_fold_count"] == 2
    assert summary["macro"] is None


def test_known_connected_solution_and_lower_direction(tiny_release):
    cfg = json.loads((tiny_release / "config.json").read_text())
    cfg["baseline_models"] = ["A", "B", "C"]
    (tiny_release / "config.json").write_text(json.dumps(cfg))
    mutate_csv(tiny_release / "scores.csv", lambda rows: rows[:2] + [dict(rows[2], model_name="B", score="5"), dict(rows[3], model_name="C", score="10")])
    evidence = Evidence(tiny_release)
    np.testing.assert_allclose(evidence.all_fit("Equal families"), [0, 1, 2], atol=1e-12)
    mutate_csv(tiny_release / "benchmarks.csv", lambda rows: [dict(r, direction="lower") for r in rows])
    evidence = Evidence(tiny_release)
    np.testing.assert_allclose(evidence.all_fit("Equal families"), [0, -1, -2], atol=1e-12)


def test_excluded_benchmarks_need_an_explicit_reason(tiny_release):
    mutate_csv(tiny_release / "benchmarks.csv", lambda rows: [dict(rows[0], included="0")] + rows[1:])
    with pytest.raises(ValueError, match="requires a reason"):
        Evidence(tiny_release)


def test_actual_fold_training_membership(tiny_release, monkeypatch):
    evidence = Evidence(tiny_release)
    calls = []
    original = evidence.pair_predictions
    def capture(train, method):
        calls.append(set(train))
        return original(train, method)
    monkeypatch.setattr(evidence, "pair_predictions", capture)
    evidence.cv_pairs("family")
    assert calls[:3] == [{1}] * 3
    assert calls[3:] == [{0}] * 3


def test_fixed_reference_does_not_follow_roster_scores(tiny_release):
    cfg = json.loads((tiny_release / "config.json").read_text())
    cfg["normalization_reference"] = "normalizers.csv"
    (tiny_release / "config.json").write_text(json.dumps(cfg))
    write_csv(tiny_release / "normalizers.csv", [{"benchmark_id": bid, "denominator": "8"} for bid in ["B1", "B2"]])
    evidence = Evidence(tiny_release)
    mutate_csv(tiny_release / "scores.csv", lambda rows: [dict(rows[0], score="0")] + rows[1:])
    changed = Evidence(tiny_release)
    assert [r.denominator for r in evidence.rows] == [r.denominator for r in changed.rows] == [8, 8]


def test_v52_catalog_corrections_and_excluded_alternative():
    evidence = Evidence(ROOT / "data" / "v5_2")
    catalog = evidence.catalog
    assert len(evidence.score_records) == 306 and len(catalog.observations) == 307
    assert len(catalog.missingness) == 150
    for model, value in [("Claude Fable 5.1", 50.9), ("GPT-6.1 Sol", 50.2)]:
        detail = catalog.details("B036", model)
        assert detail["score"] == value and detail["system"]["reasoning_effort"] == "medium"
    assert catalog.details("B032", "Claude Opus 5.5")["score"] == 13.93
    alternate = [o for o in catalog.observations if not o["included"]]
    assert len(alternate) == 1 and alternate[0]["score"] == 17.29
    assert "different observational population" in alternate[0]["inclusion_reason"]


def test_catalog_is_enforced_by_loader(tmp_path):
    target = tmp_path / "release"
    shutil.copytree(ROOT / "data" / "v5_2", target)
    mutate_csv(target / "scores.csv", lambda rows: [dict(rows[0], score="1700")] + rows[1:])
    with pytest.raises(ValueError, match="catalog observations disagree"):
        Evidence(target)


def test_evaluator_holdout_counts_abstentions_and_keeps_valid_component():
    evidence = Evidence(ROOT / "data" / "v5_1")
    records = evidence.cv_pairs("evaluator")
    summary = evidence.macro_accuracy(records, "evaluator", "Equal families")
    assert summary["attempted_pair_count"] == 709
    assert summary["pair_count"] == 586 and summary["abstained_pair_count"] == 123
    aa = next(fold for fold in summary["folds"] if fold["fold"] == "AA")
    assert aa["predicted"] == 138 and aa["abstained"] == 123
    assert all(r["Equal families"] is None for r in records if r["fold"] == "AA" and "Muse" in (r["model_a"] + r["model_b"]))


def test_pair_baseline_abstains_when_domain_has_no_shared_training(tiny_release):
    evidence = Evidence(tiny_release)
    records = validation_records(evidence, "family")
    for method in PAIR_BASELINES[:2]:
        summary = evidence.macro_accuracy(records, "family", method)
        assert summary["abstained_pair_count"] == 2
    assert evidence.macro_accuracy(records, "family", PAIR_BASELINES[2])["macro"] == .5


def test_canonical_manifest_and_newline_equivalence(tmp_path):
    lf, crlf = tmp_path / "lf.txt", tmp_path / "crlf.txt"
    lf.write_bytes(b"one\ntwo\n")
    crlf.write_bytes(b"one\r\ntwo\r\n")
    assert digest(lf) == digest(crlf)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sha256": {"lf.txt": digest(lf)}}))
    verify_manifest(tmp_path, manifest)
    lf.write_text("changed")
    with pytest.raises(ValueError, match="integrity mismatch"):
        verify_manifest(tmp_path, manifest)
