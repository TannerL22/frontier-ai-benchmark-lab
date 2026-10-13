"""Descriptive coverage, conditional pair votes and aggregation sensitivity."""
from collections import Counter, defaultdict
from dataclasses import replace
import copy

import numpy as np

from .core import METHODS

PAIR_BASELINES = ("Pair direction vote", "Same-domain pair vote", "Random direction reference")


def coverage(evidence, train=None):
    domains = list(evidence.domain_weights)
    selected = evidence.rows if train is None else [evidence.rows[i] for i in train]
    results = []
    for i, model in enumerate(evidence.models):
        present = [b for b in selected if b.scores[i] is not None]
        counts = Counter(b.domain for b in present)
        evaluators = sorted({b.evaluator for b in present})
        results.append({
            "Model": model, "Recorded results": len(present), "Evaluators": len(evaluators),
            "Source coverage": ", ".join(evaluators),
            "Missing domains": ", ".join(d for d in domains if not counts[d]) or "None in this portfolio",
            "Scope": "Single-evaluator evidence" if len(evaluators) == 1 else "Selected multi-evaluator evidence",
            **{d: counts[d] for d in domains},
        })
    return results


def selected_rows(evidence, domains=None, evaluators=None, include_provisional=True):
    domains = set(evidence.domain_weights if domains is None else domains)
    evaluators = set(evidence.evaluators if evaluators is None else evaluators)
    return [i for i, b in enumerate(evidence.rows) if b.domain in domains and b.evaluator in evaluators
            and (include_provisional or b.id not in {"B010", "B013"})]


def pair_vote(evidence, train, a, b, domain=None):
    ids = [i for i in train if domain is None or evidence.rows[i].domain == domain]
    weights = evidence.weights(ids, "Equal families")
    votes, observed_mass = 0.0, 0.0
    for ix, weight in weights.items():
        row = evidence.rows[ix]
        if row.scores[a] is None or row.scores[b] is None:
            continue
        direction = (row.scores[b] - row.scores[a]) * (1 if row.direction == "higher" else -1)
        votes += weight * np.sign(direction)
        observed_mass += weight
    return float(votes / observed_mass) if observed_mass else None


def validation_records(evidence, mode):
    records = evidence.cv_pairs(mode)
    training = {fold: kept for fold, kept, held in evidence.folds(mode)}
    for record in records:
        a, b = evidence.models.index(record["model_a"]), evidence.models.index(record["model_b"])
        for method, domain in ((PAIR_BASELINES[0], None), (PAIR_BASELINES[1], record["domain"])):
            value = pair_vote(evidence, training[record["fold"]], a, b, domain)
            record[method] = value
            record[method + " abstention"] = "no_shared_training_evidence" if value is None else ""
        record[PAIR_BASELINES[2]] = 0.0
        record[PAIR_BASELINES[2] + " abstention"] = ""
    return records


def contributions(evidence, train, method):
    possible = len(evidence.models) * (len(evidence.models) - 1) / 2
    result = []
    for ix, nominal in evidence.weights(train, method).items():
        row = evidence.rows[ix]
        count = sum(value is not None for value in row.scores)
        result.append({"Benchmark": row.name, "Evaluator": row.evaluator, "Domain": row.domain,
                       "Family": row.family, "Nominal weight": nominal,
                       "Observed comparison mass": nominal * count * (count - 1) / 2 / possible,
                       "Normalizer": row.denominator, "Floor": row.floor})
    return result


def deletion_sensitivity(evidence, method, mode="evaluator", train=None):
    results = []
    selection = set(range(len(evidence.rows)) if train is None else train)
    for label, kept, held in evidence.folds(mode):
        if not selection.intersection(held):
            continue
        scores = evidence.index(evidence.fit([i for i in kept if i in selection], method))
        if scores is None:
            results.append({"Removed group": label, "Model": "Whole roster",
                            "Relative difference": None, "Status": "Disconnected; global summary unavailable"})
        else:
            for model, value in scores.items():
                results.append({"Removed group": label, "Model": model,
                                "Relative difference": value - 100, "Status": "Conditional experiment"})
    return results


def genealogy_evidence(evidence):
    """Alternative taxonomy for sensitivity only; not proof of task overlap."""
    clone = copy.copy(evidence)
    clone.rows = [replace(b, family=b.genealogy or b.family) for b in evidence.rows]
    return clone
