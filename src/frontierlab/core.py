"""Single scoring engine for v4.2-frozen evidence and three comparable methods.

No Excel dependency. The six-model baseline remains fixed until source observations for
new models are comparable. One observation is a benchmark-run/model score, NOT a
composite index. Pair differences are capped; each source's missing pairs get zero
weight rather than an enhanced weight.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import isfinite, sqrt
from pathlib import Path
from statistics import pstdev
import csv, json
import numpy as np

METHODS = ('Equal families', 'Equal domains', 'Super-Aggregate v4.2')

@dataclass(frozen=True)
class Benchmark:
    id: str
    name: str
    evaluator: str
    domain: str
    family: str
    unit: str
    config: str
    floor: float
    source: str
    provenance: str
    overlap_notes: str
    scores: tuple[float | None, ...]
    denominator: float

    def pair_data(self):
        present = [(i, v) for i,v in enumerate(self.scores) if v is not None]
        for (i, a),(j,b) in combinations(present,2):
            raw = (b-a)/self.denominator
            yield i,j, float(np.clip(raw,-2,2)), float(raw)

class Evidence:
    def __init__(self, data_dir: Path):
        self.data_dir=Path(data_dir)
        cfg=json.loads((self.data_dir/'config.json').read_text(encoding='utf-8'))
        self.models=tuple(cfg['baseline_models'])
        self.domain_weights=cfg['domain_weights']
        self.anchor=cfg['display_anchor']
        self.scale=float(cfg['scale_factor'])
        self.model_registry=list(self.csv_rows('models.csv'))
        self.candidates=list(self.csv_rows('candidate_scores.csv'))
        self.external=list(self.csv_rows('external_indices.csv'))
        rawscores=defaultdict(dict)
        for s in self.csv_rows('scores.csv'):
            if s['model_name'] not in self.models:
                raise ValueError('Candidate score in frozen training data — requires versioned promotion')
            key=(s['benchmark_id'],s['model_name'])
            if s['model_name'] in rawscores[s['benchmark_id']]:
                raise ValueError(f'Duplicate model score: {key}')
            rawscores[s['benchmark_id']][s['model_name']]=float(s['score'])
        self.rows=[]
        seen=set()
        for b in self.csv_rows('benchmarks.csv'):
            if b['benchmark_id'] in seen:raise ValueError('Duplicate benchmark ID')
            seen.add(b['benchmark_id'])
            if int(b['included'])!=1:continue
            vals=tuple(rawscores[b['benchmark_id']].get(m) for m in self.models)
            v=[x for x in vals if x is not None]
            if len(v)<2: raise ValueError(f"Benchmark {b['benchmark_name']} lacks a model pair")
            floor=float(b['scale_floor'])
            if floor<=0 or not all(isfinite(x) for x in v):raise ValueError(f"Bad scores or scale floor: {b['benchmark_id']}")
            denom=max(floor,pstdev(v))
            if not b['source_url']:raise ValueError(f"No source: {b['benchmark_id']}")
            self.rows.append(Benchmark(b['benchmark_id'],b['benchmark_name'],b['evaluator'],b['domain'],b['family_id'],b['unit'],b['configuration'],floor,b['source_url'],b['provenance'],b['overlap_notes'],vals,denom))
        if len(self.rows)!=57:raise ValueError('Frozen v4.2 dataset should have 57 included rows')
        self.families=sorted(set(b.family for b in self.rows))
        self.evaluators=sorted(set(b.evaluator for b in self.rows))

    def csv_rows(self,name):
        with (self.data_dir/name).open(newline='',encoding='utf-8') as f:
            yield from csv.DictReader(f)

    def grouped(self,train):
        g=defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
        for ix in train:
            b=self.rows[ix]
            g[b.domain][b.evaluator][b.family].append(ix)
        return g

    def weights(self, train, method):
        train=list(train)
        if not train:return {}
        group=self.grouped(train)
        out=defaultdict(float)
        if method=='Equal families':
            f=defaultdict(list)
            for ix in train:f[self.rows[ix].family].append(ix)
            for members in f.values():
                for ix in members:out[ix]=1/(len(f)*len(members))
            return dict(out)
        if method=='Equal domains':
            for domain in group:
                f=defaultdict(list)
                for ev,fs in group[domain].items():
                    for fam,ids in fs.items():f[fam].extend(ids)
                for ids in f.values():
                    for ix in ids:out[ix]=1/(len(group)*len(f)*len(ids))
            return dict(out)
        if method!='Super-Aggregate v4.2':raise ValueError(method)
        active=[d for d in group if self.domain_weights.get(d,0)>0]
        mass=sum(self.domain_weights[d] for d in active)
        n=len(self.models)
        max_pairs=n*(n-1)/2
        for d in active:
            ev_group=group[d]; strengths={}
            for ev,fs in ev_group.items():
                coverage=[]
                for fam,ids in fs.items():
                    coverage.append(float(np.mean([sum(x is not None for x in self.rows[ix].scores)*(sum(x is not None for x in self.rows[ix].scores)-1)/2/max_pairs for ix in ids])))
                strength=(len(fs)/(len(fs)+2.0))*sqrt(float(np.mean(coverage)))
                if ev=='Arena' and d=='Knowledge':strength*=0.5
                strengths[ev]=strength
            total=sum(strengths.values())
            for ev,fs in ev_group.items():
                for fam,ids in fs.items():
                    for ix in ids:
                        out[ix]=self.domain_weights[d]/mass*(strengths[ev]/total)/len(fs)/len(ids)
        if not np.isclose(sum(out.values()),1.0,atol=1e-10):raise AssertionError('Weights fail to sum to 1')
        return dict(out)

    def fit(self,train,method):
        train=list(train)
        if not train:return None
        n=len(self.models)
        lap=np.zeros((n,n));rhs=np.zeros(n)
        for ix,w in self.weights(train,method).items():
            # Sparse-pair method allocates potential pair weight evenly; missing pairs are not upweighted.
            ww=w/(n*(n-1)/2)
            for i,j,clipped,raw in self.rows[ix].pair_data():
                lap[i,i]+=ww;lap[j,j]+=ww;lap[i,j]-=ww;lap[j,i]-=ww
                rhs[i]-=ww*clipped;rhs[j]+=ww*clipped
        if np.linalg.matrix_rank(lap[1:,1:],tol=1e-11)<n-1:return None
        theta=np.zeros(n)
        theta[1:]=np.linalg.solve(lap[1:,1:],rhs[1:])
        return theta

    def index(self,fit):
        if fit is None:return None
        reference=fit[self.models.index(self.anchor)]
        return {m:float(100+self.scale*(fit[i]-reference)) for i,m in enumerate(self.models)}

    def all_fit(self,method):
        return self.fit(range(len(self.rows)),method)

    def groups(self,mode):
        grouped=defaultdict(list)
        if mode not in ('family','evaluator','domain'):raise ValueError(mode)
        for ix,row in enumerate(self.rows):grouped[getattr(row,mode)].append(ix)
        return dict(grouped)

    def cv_pairs(self,mode):
        """Out-of-fold predictions; source benchmark families are grouped together."""
        results=[]
        for fold, held in self.groups(mode).items():
            drop=set(held)
            kept=[ix for ix in range(len(self.rows)) if ix not in drop]
            fits={method:self.fit(kept,method) for method in METHODS}
            for ix in held:
                row=self.rows[ix]
                for i,j,clipped,raw in row.pair_data():
                    if abs(raw)<1e-12:continue
                    rec={'fold_type':mode,'fold':fold,'family':row.family,'evaluator':row.evaluator,'domain':row.domain,
                         'benchmark_id':row.id,'benchmark':row.name,'model_a':self.models[i], 'model_b':self.models[j],
                         'observed_margin_norm':raw,'observed_b_wins':int(raw>0),'source':row.source}
                    for method in METHODS:
                        rec[method]=None if fits[method] is None else float(fits[method][j]-fits[method][i])
                    results.append(rec)
        return results

    def macro_accuracy(self,recs,mode,method,threshold=0):
        groups=defaultdict(list)
        for r in recs:
            v=r[method]
            if v is None or abs(r['observed_margin_norm'])<=threshold:continue
            d=v*r['observed_margin_norm']
            correct=1 if d>1e-12 else 0.5 if abs(v)<1e-12 else 0
            groups[r['fold']].append(correct)
        vals=[np.mean(v) for v in groups.values()]
        return {'macro':float(np.mean(vals)) if vals else None,'micro':float(np.mean([x for group in groups.values() for x in group])) if vals else None,'fold_count':len(groups),'pair_count':sum(len(v) for v in groups.values())}
