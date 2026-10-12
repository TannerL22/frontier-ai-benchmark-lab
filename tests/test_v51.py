import csv,json
from pathlib import Path
import numpy as np
import pytest
from frontierlab.core import Evidence,METHODS
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'/'v5_1'

def test_release_counts_and_original_identity():
    e=Evidence(D)
    assert len(e.models)==8 and len(e.rows)==57 and len(e.evaluators)==9
    for model in ('Muse Wonder Full','Muse Wonder'):
        j=e.models.index(model)
        present=[r for r in e.rows if r.scores[j] is not None]
        assert len(present)==10
        assert {r.evaluator for r in present}=={'AA'}
        assert len({r.family for r in present})==10
        assert all(r.id in {f'B{i:03d}' for i in range(6,16)} for r in present)
    assert all('intelligence index' not in r.name.lower() for r in e.rows)

def test_exact_score_vector_and_unit():
    e=Evidence(D)
    expected={'Muse Wonder Full':[1729,1857,71,57,63,54,33,33,30,84],
              'Muse Wonder':[1659,1770,68,52,60,50,31,28,25,81]}
    lookup={r.id:r for r in e.rows}
    for model,values in expected.items():
        idx=e.models.index(model)
        assert [lookup[f'B{i:03d}'].scores[idx] for i in range(6,16)]==values
        assert lookup['B014'].unit=='index'  # AA-Omniscience is an index, NOT % accuracy

def test_frozen_legacy_is_unmodified():
    baseline=Evidence(ROOT/'data')
    assert len(baseline.models)==6 and len(baseline.rows)==57
    saved=json.loads((ROOT/'snapshots'/'v4_2_reference.json').read_text())
    got=baseline.index(baseline.all_fit('Super-Aggregate v4.2'))
    for m in baseline.models:assert got[m]==pytest.approx(saved['full_index'][m],abs=1e-8)

def test_joint_methods_connected_and_finite():
    e=Evidence(D)
    for meth in METHODS:
        fit=e.all_fit(meth)
        assert fit is not None and np.isfinite(fit).all()
        s=e.index(fit)
        assert len(s)==8 and s['Claude Opus 5.5']==pytest.approx(100.0)

def test_no_new_duplicates_or_vendor_scores():
    with (D/'scores.csv').open() as f:rows=list(csv.DictReader(f))
    keys=[(r['benchmark_id'],r['model_name']) for r in rows]
    assert len(keys)==len(set(keys))==304
    for r in rows:
        if r['model_name'].startswith('Muse Wonder'):
            assert 'artificialanalysis.ai' in r['verified_source_url']
            assert r['evidence_status'].startswith('independent_original_AA')
import pytest
