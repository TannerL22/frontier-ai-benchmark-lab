import json
from pathlib import Path
import numpy as np
import pytest
from frontierlab.core import Evidence,METHODS
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def evidence():return Evidence(ROOT/'data')
def test_frozen_counts(evidence):
    assert len(evidence.rows)==57
    assert len(evidence.families)==56
    assert len(evidence.evaluators)==9
    assert len(evidence.models)==6
    assert len(evidence.model_registry)==8

def test_no_composite_leakage(evidence):
    assert all('intelligence index' not in b.name.lower() for b in evidence.rows)
    assert all(r['primary_index_eligible']=='0' for r in evidence.external)
    assert all(r['model_name'] not in evidence.models for r in evidence.candidates)

def test_frozen_joint_estimator_identical(evidence):
    ref=json.loads((ROOT/'snapshots'/'v4_2_reference.json').read_text())
    fitted=evidence.all_fit('Super-Aggregate v4.2')
    expected=np.array([ref['joint_theta'][m] for m in evidence.models])
    assert np.max(np.abs(fitted-expected))<1e-9
    scores=evidence.index(fitted)
    for model in evidence.models:assert scores[model]==pytest.approx(ref['full_index'][model],abs=1e-8)

@pytest.mark.parametrize('method',METHODS)
def test_weights_total_one(evidence,method):
    assert sum(evidence.weights(range(len(evidence.rows)),method).values())==pytest.approx(1.0)

@pytest.mark.parametrize('typ,expected_pairs', [('family',586),('evaluator',586),('domain',586)])
def test_no_leakage_cv_and_counts(evidence,typ,expected_pairs):
    pairs=evidence.cv_pairs(typ)
    assert len(pairs)==expected_pairs
    for r in pairs:
        assert r['observed_margin_norm']!=0
        assert r['fold']==r[typ]

def test_historical_validation_match(evidence):
    ref=json.loads((ROOT/'snapshots'/'v4_4_reference.json').read_text())
    for mode in ('family','evaluator','domain'):
        records=evidence.cv_pairs(mode)
        for method in METHODS:
            got=evidence.macro_accuracy(records,mode,method,0)
            expected=next(x for x in ref['cross_validation_summary'] if x['fold_type']==mode and x['method']==method and x['margin_threshold']==0)
            assert got['macro']==pytest.approx(expected['macro'],abs=1e-9)
            assert got['pair_count']==expected['pair_count']

def test_candidate_evidence_does_not_change_frozen_baseline(evidence):
    assert {r['model_name'] for r in evidence.model_registry if r['status']=='pending_original_scores'}=={'Muse Wonder Full','Muse Wonder'}
    assert evidence.index(evidence.all_fit('Super-Aggregate v4.2'))['Claude Opus 5.5']==pytest.approx(100)
