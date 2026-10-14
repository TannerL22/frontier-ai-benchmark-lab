"""Product comparisons with explicit cohorts and preserved experimental scales.

All fits use the historical engine. Display filters never redefine the cohort.
Removal scenarios are robustness checks, not confidence probabilities.
"""
import copy
from dataclasses import replace

from .core import METHODS


def product_evidence(evidence, include_provisional=False):
    view = copy.copy(evidence)
    view.rows = []
    for row in evidence.rows:
        if not include_provisional and row.id in {"B010", "B013"}:
            continue
        scores = list(row.scores)
        if evidence.catalog and not include_provisional:
            for i,name in enumerate(evidence.models):
                record = evidence.catalog.by_pair.get((row.id, name))
                if record and record["evidence_status"].startswith("provisional"):
                    scores[i] = None
        view.rows.append(replace(row, scores=tuple(scores)))
    return view


def support(evidence, model, ids=None):
    selected = list(range(len(evidence.rows))) if ids is None else list(ids)
    pos = evidence.models.index(model)
    rows = [evidence.rows[i] for i in selected if evidence.rows[i].scores[pos] is not None]
    return dict(results=len(rows), families=len({r.family for r in rows}), evaluators=len({r.evaluator for r in rows}), domains=len({r.domain for r in rows}))


def broad_cohort(evidence):
    """Declared reporting threshold, independent of model score or rank."""
    return tuple(m for m in evidence.models if (s := support(evidence,m))["results"] >= 20 and s["evaluators"] >= 3 and s["domains"] >= 6)


def cohort_evidence(evidence, names):
    view = copy.copy(evidence)
    view.models = tuple(names)
    positions = [evidence.models.index(n) for n in names]
    view.rows = [replace(row, scores=tuple(row.scores[i] for i in positions)) for row in evidence.rows]
    view.anchor = evidence.anchor if evidence.anchor in names else names[0] if names else ""
    return view


def standings(evidence, names, method=METHODS[0], ids=None):
    if len(names) < 2:
        return []
    view = cohort_evidence(evidence,names)
    ids = list(range(len(view.rows))) if ids is None else list(ids)
    values = view.index(view.fit(ids,method))
    if values is None:
        return []
    ordered = sorted(values, key=lambda m:(-values[m],m))
    return [dict(Model=m, Rank=1 + sum(v > values[m] + 1e-10 for v in values.values()), Index=values[m], **support(evidence,m,ids)) for m in ordered]


def domain_standings(evidence, domain, method=METHODS[0]):
    ids = [i for i,r in enumerate(evidence.rows) if r.domain == domain]
    names = [m for m in broad_cohort(evidence) if support(evidence,m,ids)["results"] > 0]
    return standings(evidence,names,method,ids)


def robustness(evidence, names, method=METHODS[0], grouping="evaluator"):
    baseline = standings(evidence,names,method)
    if not baseline:
        return dict(scenarios=0, connected=0, first=0, rank_range=None, leader=None)
    leader = baseline[0]["Model"]
    groups = sorted({getattr(r,grouping) for r in evidence.rows})
    ranks, disconnected = [],0
    for group in groups:
        ids = [i for i,r in enumerate(evidence.rows) if getattr(r,grouping) != group]
        table = standings(evidence,names,method,ids)
        if not table:
            disconnected += 1
        else:
            ranks.append(next(r["Rank"] for r in table if r["Model"] == leader))
    return dict(scenarios=len(groups), connected=len(ranks), disconnected=disconnected, first=sum(r == 1 for r in ranks),
                rank_range=[min(ranks),max(ranks)] if ranks else None, leader=leader)


def comparison(evidence, a, b):
    if a == b:
        return []
    ai,bi = evidence.models.index(a),evidence.models.index(b)
    rows = []
    for row in evidence.rows:
        av,bv = row.scores[ai],row.scores[bi]
        if av is None or bv is None:
            continue
        delta = (av-bv) * (1 if row.direction == "higher" else -1)
        rows.append(dict(Benchmark=row.name, Domain=row.domain, Evaluator=row.evaluator, Family=row.family,
                         A=av, B=bv, Winner=a if delta > 0 else b if delta < 0 else "Tie", Margin=delta / row.denominator, Source=row.source))
    return rows


def release_changes(previous, current, names, method=METHODS[0]):
    """Compare ordinal ranks with a matched cohort; never subtract release indices."""
    before = {r["Model"]:r for r in standings(previous,names,method)}
    after = standings(current,names,method)
    if not before or not after:
        return []
    return [dict(Model=r["Model"], Previous=before[r["Model"]]["Rank"], Current=r["Rank"],
                 Movement=before[r["Model"]]["Rank"]-r["Rank"], Added_results=r["results"]-before[r["Model"]]["results"]) for r in after]
