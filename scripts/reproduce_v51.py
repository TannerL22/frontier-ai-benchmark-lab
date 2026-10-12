#!/usr/bin/env python3
"""Versioned 8-model AA release batch. DOES NOT overwrite frozen v4.2/v4.4 results."""
from pathlib import Path
import sys,json,csv
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from frontierlab.core import Evidence,METHODS

def main():
    ev=Evidence(ROOT/'data'/'v5_1')
    result={'version':'v5.1','as_of':'2026-10-12','mode':'best available (not equal compute)',
            'models':list(ev.models),'benchmark_rows':len(ev.rows),'evaluator_count':len(ev.evaluators),
            'distinct_families':len(ev.families),'aa_evaluation_count_new_models':10,
            'scores_by_method':{method:ev.index(ev.all_fit(method)) for method in METHODS},
            'evidence_coverage':{},'limitations':['New-model scores currently come only from Artificial Analysis; no independent evaluator diversity for Meta variants',
            'Re-estimated scores across eight models; not directly comparable with previous index releases',
            'Different models/harnesses/reasoning efforts. No equal compute or paired task-level uncertainty.',
            'AA composite Intelligence Index and Coding Agents Index excluded from scoring']}
    for i,m in enumerate(ev.models):
        present=[r for r in ev.rows if r.scores[i] is not None]
        result['evidence_coverage'][m]={'benchmark_rows':len(present),'fraction_rows':len(present)/len(ev.rows),
                                      'evaluators':sorted({r.evaluator for r in present})}
    out=ROOT/'outputs';out.mkdir(exist_ok=True)
    (out/'v5_1_preview_results.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'v5_1_rankings.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['method','rank','model','score','observed_benchmark_rows','distinct_evaluators'])
        for method,values in result['scores_by_method'].items():
            for rank,(model,score) in enumerate(sorted(values.items(),key=lambda p:-p[1]),1):
                cov=result['evidence_coverage'][model]
                w.writerow([method,rank,model,round(score,5),cov['benchmark_rows'],len(cov['evaluators'])])
    print('v5.1: 8 models, 57 benchmark rows, 20 independent AA scores added')
    for method,values in result['scores_by_method'].items():
        print('\n'+method)
        for m,v in sorted(values.items(),key=lambda p:-p[1]):print(' %-21s %.3f  %d rows'%(m,v,result['evidence_coverage'][m]['benchmark_rows']))
if __name__=='__main__':main()
