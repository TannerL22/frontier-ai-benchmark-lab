"""Historical out-of-fold validation and nested pairwise probability calibration.

Note: historical folds are NOT future prospective tests, and model pairs within
one benchmark are correlated. Aggregate over benchmark families, not raw pairs.
"""
from collections import defaultdict
import math
import numpy as np
from scipy.optimize import minimize_scalar
from .core import METHODS

def sigmoid(v):return 1/(1+np.exp(-np.clip(v,-30,30)))

def nested_calibration(evidence, records=None):
    """Double-withhold benchmark-family data from model fitting AND slope calibration.
    Returns family-macro Brier and log losses. Replicates v4.4 methodology.
    """
    groups=evidence.groups('family')
    all_ix=set(range(len(evidence.rows)))
    records=[]
    for outer,outer_ids in groups.items():
        outer_set=set(outer_ids)
        outer_fit={m:evidence.fit(sorted(all_ix-outer_set),m) for m in METHODS}
        for method in METHODS:
            cal=[]
            for inner,inner_ids in groups.items():
                if inner==outer:continue
                tr=sorted(all_ix-outer_set-set(inner_ids))
                th=evidence.fit(tr,method)
                if th is None:continue
                family_cases=[]
                for i in inner_ids:
                    for a,b,_,norm in evidence.rows[i].pair_data():
                        if abs(norm)>1e-12:family_cases.append((float(th[b]-th[a]),int(norm>0)))
                if family_cases:
                    weight=1/len(family_cases)
                    cal.extend((x,y,weight) for x,y in family_cases)
            if not cal:slope=1.0
            else:
                xx=np.array([x for x,_,_ in cal]);yy=np.array([y for _,y,_ in cal]);ww=np.array([w for _,_,w in cal]);ww/=ww.sum()
                def loss(k):
                    p=np.clip(sigmoid(k*xx),1e-9,1-1e-9)
                    return -float(np.sum(ww*(yy*np.log(p)+(1-yy)*np.log(1-p))))+.002*(k-1)**2
                slope=float(minimize_scalar(loss,bounds=(0,10),method='bounded',options={'xatol':.01}).x)
            th=outer_fit[method]
            if th is None:continue
            for i in outer_ids:
                for a,b,_,norm in evidence.rows[i].pair_data():
                    if abs(norm)<=1e-12:continue
                    p=float(sigmoid(slope*(th[b]-th[a])))
                    y=int(norm>0)
                    records.append({'method':method,'family':outer,'model_a':evidence.models[a],
                                    'model_b':evidence.models[b],'p_b_wins':p,'observed_b_wins':y,
                                    'brier':(p-y)**2,'logloss':-math.log(max(1e-10,p if y else 1-p)),
                                    'calibration_slope':slope})
    summary=[]
    for method in METHODS:
        group=defaultdict(list)
        for r in records:
            if r['method']==method:group[r['family']].append(r)
        summary.append({'method':method,'families':len(group),'pairs':sum(len(v) for v in group.values()),
                        'macro_brier':float(np.mean([np.mean([r['brier'] for r in v]) for v in group.values()])),
                        'macro_logloss':float(np.mean([np.mean([r['logloss'] for r in v]) for v in group.values()]))})
    return summary,records
