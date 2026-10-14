from dataclasses import replace
from pathlib import Path
import copy

import pytest

from frontierlab.core import Evidence, METHODS
from frontierlab.explorer import product_evidence, broad_cohort, standings, robustness, comparison, domain_standings, release_changes

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def expanded():
    return Evidence(ROOT / "data/v5_4")


def test_expansion_preserves_prior_observations_and_rulers(expanded):
    old = Evidence(ROOT / "data/v5_3")
    assert (len(expanded.rows),len(expanded.families),len(expanded.evaluators),len(expanded.score_records)) == (61,59,10,326)
    assert expanded.rows[:len(old.rows)] == old.rows
    assert expanded.score_records[:len(old.score_records)] == old.score_records
    assert expanded.catalog.observations[:len(old.catalog.observations)] == old.catalog.observations


def test_frontiercode_two_executions_share_one_family_weight(expanded):
    rows = {r.id:i for i,r in enumerate(expanded.rows)}
    weights = expanded.weights(range(len(expanded.rows)),"Equal families")
    assert expanded.rows[rows["B036"]].family == expanded.rows[rows["B064"]].family
    assert weights[rows["B036"]] + weights[rows["B064"]] == pytest.approx(1/59)


def test_eap_masking_does_not_erase_other_models_or_relabel_public_runs(expanded):
    primary = product_evidence(expanded)
    complete = product_evidence(expanded,True)
    index = expanded.models.index("Gemini 4 Argon")
    for bid in ("B065","B066"):
        row = next(r for r in primary.rows if r.id == bid)
        assert row.scores[index] is None
        assert row.scores[0] is not None
        assert next(r for r in complete.rows if r.id == bid).scores[index] is not None
        record = expanded.catalog.details(bid,"Gemini 4 Argon")
        assert "EAP" in record["system"]["model_snapshot"]
    assert next(r for r in primary.rows if r.id == "B064").scores[index] == 42.6
    assert not {"B010","B013"} & {r.id for r in primary.rows}
    assert {"B010","B013"} <= {r.id for r in complete.rows}


def test_no_identity_substitutions_and_original_metric_intervals(expanded):
    argon = expanded.models.index("Gemini 4 Argon")
    muse_full = expanded.models.index("Muse Wonder Full")
    assert next(r for r in expanded.rows if r.id == "B063").scores[argon] is None
    assert all(r.scores[muse_full] is None for r in expanded.rows if r.id in {"B063","B064","B065","B066"})
    sonnet = expanded.catalog.details("B063","Claude Sonnet 5.5")
    assert sonnet["uncertainty"]["value"] == [1160,1228]
    assert "preference Elo" in sonnet["uncertainty"]["qualification"]


@pytest.mark.parametrize("method",METHODS)
def test_updated_primary_comparison_and_removal_conclusions(expanded,method):
    view = product_evidence(expanded)
    names = broad_cohort(view)
    assert len(names) == 6 and not any("Muse" in n for n in names)
    table = standings(view,names,method)
    assert table[0]["Model"] == "Claude Opus 5.5"
    checks = robustness(view,names,method)
    assert (checks["first"],checks["scenarios"],checks["disconnected"],checks["rank_range"]) == (9,10,0,[1,2])
    removed_aa = standings(view,names,method,[i for i,r in enumerate(view.rows) if r.evaluator != "AA"])
    assert removed_aa[0]["Model"] != table[0]["Model"]


def test_disconnected_models_never_get_a_joint_rank(expanded):
    view = product_evidence(expanded)
    no_aa = [i for i,r in enumerate(view.rows) if r.evaluator != "AA"]
    assert standings(view,view.models,"Equal families",no_aa) == []
    assert standings(view,view.models,ids=[]) == []
    assert comparison(view,view.models[0],view.models[0]) == []
    assert not any(r["Model"] == "Gemini 4 Argon" for r in domain_standings(view,"Multimodal"))


def test_pair_margins_respect_lower_is_better(expanded):
    view = copy.copy(expanded)
    view.rows = [replace(expanded.rows[0],direction="lower")]
    a,b = view.models[:2]
    row = comparison(view,a,b)[0]
    assert row["Winner"] == b
    assert row["Margin"] < 0


def test_release_changes_use_matched_cohort_ranks_and_not_index_deltas(expanded):
    before = product_evidence(Evidence(ROOT / "data/v5_3"))
    current = product_evidence(expanded)
    changes = release_changes(before,current,broad_cohort(current))
    assert changes[0]["Previous"] == changes[0]["Current"] == 1
    assert changes[0]["Added_results"] == 4
    assert all(r["Movement"] == r["Previous"]-r["Current"] for r in changes)
    assert not any("Index" in r for r in changes)
