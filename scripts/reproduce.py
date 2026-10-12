#!/usr/bin/env python3
"""Recompute rankings and historical cross-validation from CSV/JSON only."""
import argparse, json, csv, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from frontierlab.core import Evidence,METHODS
from frontierlab.validation import nested_calibration

def dump_csv(filename,rows):
    if not rows:return
    with filename.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--calibration',action='store_true',help='Run the computationally expensive nested 56-family calibration')
    args=ap.parse_args()
    ev=Evidence(ROOT/'data')
    fits={m:ev.all_fit(m) for m in METHODS}
    scores={m:ev.index(fits[m]) for m in METHODS}
    validation=[]; pairs=[]
    for typ in ('family','evaluator','domain'):
        r=ev.cv_pairs(typ);pairs.extend(r)
        for method in METHODS:
            for threshold in (0,0.10,0.25):
                validation.append(dict(fold_type=typ,method=method,margin_threshold=threshold,**ev.macro_accuracy(r,typ,method,threshold)))
    result={'version':'v5.0-milestone1','frozen_training_data':'v4.2','models':ev.models,
            'included_benchmark_rows':len(ev.rows),'distinct_benchmark_families':len(ev.families),
            'evaluators':len(ev.evaluators),'baseline_index_by_method':scores,'cross_validation':validation,
            'external_composites_excluded':True,'candidate_models_excluded':[r['model_name'] for r in ev.model_registry if r['status']!='baseline_v4_2'],
            'notes':['No equal-compute claim','Historical cross-validation; not prospective validation','Rounded Artificial Analysis composites are external comparators, never added as underlying scores']}
    if args.calibration:
        result['nested_calibration'],cals=nested_calibration(ev)
        dump_csv(ROOT/'outputs'/'calibrated_predictions.csv',cals)
    out=ROOT/'outputs';out.mkdir(exist_ok=True)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    dump_csv(out/'cross_validation_predictions.csv',pairs)
    print(f"Regenerated {len(ev.rows)} benchmark rows, {len(ev.families)} families, {len(pairs)} CV pair predictions")
    for m,sc in sorted(scores['Super-Aggregate v4.2'].items(),key=lambda p:-p[1]): print(f'{m:24} {sc:.4f}')
    print('Results:',out/'results.json')
if __name__=='__main__':main()
