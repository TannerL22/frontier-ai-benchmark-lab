import json
from pathlib import Path
from frontierlab.core import Evidence
from frontierlab.validation import nested_calibration
import pytest

@pytest.mark.slow
def test_nested_probability_calibration_reproduces_v44():
    root=Path(__file__).resolve().parents[1]
    ev=Evidence(root/'data')
    actual,_=nested_calibration(ev)
    reference=json.loads((root/'snapshots'/'v4_4_reference.json').read_text())
    for item in actual:
        expected=next(x for x in reference['nested_probability_calibration'] if x['method']==item['method'])
        assert item['macro_brier']==pytest.approx(expected['macro_brier'],abs=1e-9)
        assert item['macro_logloss']==pytest.approx(expected['macro_logloss'],abs=1e-9)
