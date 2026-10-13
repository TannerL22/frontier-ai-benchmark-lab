"""Validated release loading and the historically reproducible graph estimator.

The estimator is an exploratory portfolio summary, not an intelligence measure.
Historical formulas remain unchanged; disconnected validation pairs abstain.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import isfinite, sqrt
from pathlib import Path
from statistics import pstdev
from urllib.parse import urlparse
import csv
import json

import numpy as np

METHODS = ("Equal families", "Equal domains", "Super-Aggregate v4.2")
METRIC_BOUNDS = {"pct": (0, 100), "elo": (None, None), "index": (-100, 100)}


def valid_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def csv_records(path: Path, required=()):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(required).issubset(fields):
            raise ValueError(f"Invalid columns in {path.name}; required: {required}")
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV row: {path.name}:{line}")
            yield row


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
    direction: str = "higher"
    genealogy: str = ""

    def pair_data(self):
        present = [(i, value) for i, value in enumerate(self.scores) if value is not None]
        sign = 1 if self.direction == "higher" else -1
        for (i, a), (j, b) in combinations(present, 2):
            raw = sign * (b - a) / self.denominator
            yield i, j, float(np.clip(raw, -2, 2)), float(raw)


class Evidence:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.config = json.loads((self.data_dir / "config.json").read_text(encoding="utf-8"))
        roster = self.config["baseline_models"]
        if not isinstance(roster, list) or any(not isinstance(name, str) or not name.strip() for name in roster):
            raise ValueError("Model roster must contain nonempty string identities")
        self.models = tuple(roster)
        if len(self.models) < 2 or len(set(self.models)) != len(self.models):
            raise ValueError("Model roster must contain at least two unique identities")
        self.domain_weights = self.config["domain_weights"]
        if not isinstance(self.domain_weights, dict) or not self.domain_weights or any(
            not isinstance(w, (int, float)) or isinstance(w, bool) or not isfinite(w) or w < 0 for w in self.domain_weights.values()
        ) or sum(self.domain_weights.values()) <= 0:
            raise ValueError("Domain weights must be finite, nonnegative and have positive mass")
        self.anchor = self.config["display_anchor"]
        self.scale = float(self.config["scale_factor"])
        if self.anchor not in self.models or not isfinite(self.scale) or self.scale <= 0:
            raise ValueError("Invalid display anchor or scale")
        self.model_registry = list(self.csv_rows("models.csv", ("model_name",)))
        registered = [r["model_name"] for r in self.model_registry]
        if len(registered) != len(set(registered)) or not set(self.models).issubset(registered):
            raise ValueError("Roster must reference unique registered models")
        self.candidates = list(self.csv_rows("candidate_scores.csv"))
        self.external = list(self.csv_rows("external_indices.csv"))
        metadata = list(self.csv_rows("benchmarks.csv", (
            "benchmark_id", "benchmark_name", "evaluator", "domain", "family_id", "unit",
            "configuration", "scale_floor", "source_url", "provenance", "included", "overlap_notes",
        )))
        ids = [b["benchmark_id"] for b in metadata]
        if any(not value for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("Benchmark IDs must be nonempty and unique")
        by_id = {b["benchmark_id"]: b for b in metadata}
        reference = {}
        reference_file = self.config.get("normalization_reference")
        if reference_file:
            reference_path = (self.data_dir / reference_file).resolve()
            if not reference_path.is_relative_to(self.data_dir.resolve()):
                raise ValueError("Normalization reference escapes release directory")
            for record in csv_records(reference_path, ("benchmark_id", "denominator")):
                bid = record["benchmark_id"]
                value = float(record["denominator"])
                if bid not in by_id or bid in reference or not isfinite(value) or value <= 0:
                    raise ValueError("Invalid normalization reference")
                reference[bid] = value
        rawscores = defaultdict(dict)
        self.score_records = list(self.csv_rows("scores.csv", (
            "benchmark_id", "model_name", "score", "verified_source_url", "evidence_status",
        )))
        for score in self.score_records:
            bid, model = score["benchmark_id"], score["model_name"]
            if bid not in by_id:
                raise ValueError(f"Unknown benchmark ID in scores: {bid}")
            if model not in self.models:
                raise ValueError(f"Score outside release roster: {model}")
            if model in rawscores[bid]:
                raise ValueError(f"Duplicate model score: {(bid, model)}")
            unit = by_id[bid]["unit"]
            if unit not in METRIC_BOUNDS:
                raise ValueError(f"Unsupported metric unit: {unit}")
            value = float(score["score"])
            low, high = METRIC_BOUNDS[unit]
            if not isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
                raise ValueError(f"Invalid {unit} score for {(bid, model)}: {value}")
            if not valid_url(score["verified_source_url"]) or not score["evidence_status"]:
                raise ValueError(f"Missing observation provenance: {(bid, model)}")
            rawscores[bid][model] = value
        self.rows = []
        self.excluded_benchmarks = []
        for benchmark in metadata:
            bid = benchmark["benchmark_id"]
            if benchmark["included"] not in {"0", "1"}:
                raise ValueError(f"Invalid inclusion flag: {bid}")
            if benchmark["included"] == "0":
                if not benchmark.get("exclusion_reason"):
                    raise ValueError(f"Excluded benchmark requires a reason: {bid}")
                self.excluded_benchmarks.append(benchmark)
                continue
            if any(not benchmark[field] for field in ("benchmark_name", "evaluator", "domain", "family_id")):
                raise ValueError(f"Incomplete benchmark identity: {bid}")
            if benchmark["domain"] not in self.domain_weights:
                raise ValueError(f"Unknown capability domain: {benchmark['domain']}")
            values = tuple(rawscores[bid].get(model) for model in self.models)
            present = [value for value in values if value is not None]
            if len(present) < 2:
                raise ValueError(f"Benchmark {bid} lacks a model pair")
            floor = float(benchmark["scale_floor"])
            direction = benchmark.get("direction", "higher")
            if not isfinite(floor) or floor <= 0 or direction not in {"higher", "lower"}:
                raise ValueError(f"Invalid scale floor or direction: {bid}")
            if not valid_url(benchmark["source_url"]):
                raise ValueError(f"Invalid benchmark source: {bid}")
            if reference_file and (bid not in reference or reference[bid] < floor):
                raise ValueError(f"Missing or below-floor normalization reference: {bid}")
            self.rows.append(Benchmark(
                bid, benchmark["benchmark_name"], benchmark["evaluator"], benchmark["domain"],
                benchmark["family_id"], benchmark["unit"], benchmark["configuration"], floor,
                benchmark["source_url"], benchmark["provenance"], benchmark["overlap_notes"],
                values, reference[bid] if reference_file else max(floor, pstdev(present)), direction,
                benchmark.get("genealogy_id", benchmark["family_id"]),
            ))
        if not self.rows:
            raise ValueError("A release requires included evidence")
        self.families = sorted({b.family for b in self.rows})
        self.evaluators = sorted({b.evaluator for b in self.rows})
        counts = {"models": len(self.models), "benchmarks": len(self.rows), "scores": len(self.score_records)}
        for field, expected in self.config.get("expected_counts", {}).items():
            if field not in counts or counts[field] != expected:
                raise ValueError(f"Release count mismatch for {field}: expected {expected}, got {counts.get(field)}")
        self.catalog = None
        if self.config.get("catalog_required"):
            from .catalog import Catalog
            self.catalog = Catalog(self)

    def csv_rows(self, name, required=()):
        yield from csv_records(self.data_dir / name, required)

    def grouped(self, train):
        groups = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for ix in train:
            row = self.rows[ix]
            groups[row.domain][row.evaluator][row.family].append(ix)
        return groups

    def weights(self, train, method):
        train = list(train)
        if not train:
            return {}
        groups = self.grouped(train)
        out = defaultdict(float)
        if method == "Equal families":
            families = defaultdict(list)
            for ix in train:
                families[self.rows[ix].family].append(ix)
            for members in families.values():
                for ix in members:
                    out[ix] = 1 / (len(families) * len(members))
            return dict(out)
        if method == "Equal domains":
            for domain in groups:
                families = defaultdict(list)
                for evaluator, values in groups[domain].items():
                    for family, ids in values.items():
                        families[family].extend(ids)
                for ids in families.values():
                    for ix in ids:
                        out[ix] = 1 / (len(groups) * len(families) * len(ids))
            return dict(out)
        if method != "Super-Aggregate v4.2":
            raise ValueError(method)
        active = [domain for domain in groups if self.domain_weights.get(domain, 0) > 0]
        mass = sum(self.domain_weights[domain] for domain in active)
        if not mass:
            raise ValueError("No positive-weight domain remains in this selection")
        max_pairs = len(self.models) * (len(self.models) - 1) / 2
        for domain in active:
            evaluator_groups = groups[domain]
            strengths = {}
            for evaluator, families in evaluator_groups.items():
                coverage = []
                for family, ids in families.items():
                    coverage.append(float(np.mean([
                        sum(x is not None for x in self.rows[ix].scores)
                        * (sum(x is not None for x in self.rows[ix].scores) - 1) / 2 / max_pairs
                        for ix in ids
                    ])))
                strength = len(families) / (len(families) + 2.0) * sqrt(float(np.mean(coverage)))
                if evaluator == "Arena" and domain == "Knowledge":
                    strength *= 0.5
                strengths[evaluator] = strength
            total = sum(strengths.values())
            for evaluator, families in evaluator_groups.items():
                for family, ids in families.items():
                    for ix in ids:
                        out[ix] = self.domain_weights[domain] / mass * (strengths[evaluator] / total) / len(families) / len(ids)
        if not np.isclose(sum(out.values()), 1.0, atol=1e-10):
            raise AssertionError("Weights fail to sum to one")
        return dict(out)

    def _system(self, train, method):
        n = len(self.models)
        laplacian, rhs = np.zeros((n, n)), np.zeros(n)
        for ix, weight in self.weights(train, method).items():
            pair_weight = weight / (n * (n - 1) / 2)
            for i, j, clipped, raw in self.rows[ix].pair_data():
                laplacian[i, i] += pair_weight
                laplacian[j, j] += pair_weight
                laplacian[i, j] -= pair_weight
                laplacian[j, i] -= pair_weight
                rhs[i] -= pair_weight * clipped
                rhs[j] += pair_weight * clipped
        return laplacian, rhs

    def fit(self, train, method):
        train = list(train)
        if not train:
            return None
        laplacian, rhs = self._system(train, method)
        if np.linalg.matrix_rank(laplacian[1:, 1:], tol=1e-11) < len(self.models) - 1:
            return None
        theta = np.zeros(len(self.models))
        theta[1:] = np.linalg.solve(laplacian[1:, 1:], rhs[1:])
        return theta

    def pair_predictions(self, train, method):
        """Only compare nodes within a connected component; never align components."""
        train = list(train)
        fit = self.fit(train, method)
        if fit is not None:
            return {(i, j): float(fit[j] - fit[i]) for i, j in combinations(range(len(self.models)), 2)}
        laplacian, rhs = self._system(train, method)
        remaining = set(range(len(self.models)))
        predictions = {(i, j): None for i, j in combinations(sorted(remaining), 2)}
        while remaining:
            component, pending = set(), [min(remaining)]
            while pending:
                node = pending.pop()
                if node in component:
                    continue
                component.add(node)
                pending.extend(i for i in remaining if laplacian[node, i] < 0 and i not in component)
            remaining -= component
            nodes = sorted(component)
            if len(nodes) < 2:
                continue
            block = laplacian[np.ix_(nodes[1:], nodes[1:])]
            if np.linalg.matrix_rank(block, tol=1e-11) < len(nodes) - 1:
                continue
            values = np.r_[0, np.linalg.solve(block, rhs[nodes[1:]])]
            for a, b in combinations(range(len(nodes)), 2):
                predictions[nodes[a], nodes[b]] = float(values[b] - values[a])
        return predictions

    def index(self, fit):
        if fit is None:
            return None
        reference = fit[self.models.index(self.anchor)]
        return {model: float(100 + self.scale * (fit[i] - reference)) for i, model in enumerate(self.models)}

    def all_fit(self, method):
        return self.fit(range(len(self.rows)), method)

    def groups(self, mode):
        if mode not in {"family", "evaluator", "domain", "genealogy"}:
            raise ValueError(mode)
        groups = defaultdict(list)
        for ix, row in enumerate(self.rows):
            groups[getattr(row, mode) or row.family].append(ix)
        return dict(groups)

    def folds(self, mode):
        for label, held in self.groups(mode).items():
            excluded = set(held)
            yield label, [ix for ix in range(len(self.rows)) if ix not in excluded], held

    def cv_pairs(self, mode):
        records = []
        for fold, kept, held in self.folds(mode):
            predictions = {method: self.pair_predictions(kept, method) for method in METHODS}
            for ix in held:
                row = self.rows[ix]
                for i, j, clipped, raw in row.pair_data():
                    if abs(raw) < 1e-12:
                        continue
                    record = {
                        "fold_type": mode, "fold": fold, "family": row.family, "evaluator": row.evaluator,
                        "domain": row.domain, "benchmark_id": row.id, "benchmark": row.name,
                        "model_a": self.models[i], "model_b": self.models[j],
                        "observed_margin_norm": raw, "observed_b_wins": int(raw > 0), "source": row.source,
                    }
                    for method in METHODS:
                        value = predictions[method][i, j]
                        record[method] = value
                        record[method + " abstention"] = "different_connected_components" if value is None else ""
                    records.append(record)
        return records

    def macro_accuracy(self, records, mode, method, threshold=0):
        groups, attempted, reasons = defaultdict(list), Counter(), Counter()
        excluded = 0
        for record in records:
            if abs(record["observed_margin_norm"]) <= threshold:
                excluded += 1
                continue
            attempted[record["fold"]] += 1
            value = record[method]
            if value is None:
                reasons[record.get(method + " abstention") or "unavailable_prediction"] += 1
                continue
            margin = value * record["observed_margin_norm"]
            groups[record["fold"]].append(1 if margin > 1e-12 else 0.5 if abs(value) < 1e-12 else 0)
        means = [np.mean(values) for values in groups.values()]
        predicted = sum(len(values) for values in groups.values())
        total = sum(attempted.values())
        return {
            "macro": float(np.mean(means)) if means else None,
            "micro": float(np.mean([x for values in groups.values() for x in values])) if means else None,
            "fold_count": len(groups), "pair_count": predicted,
            "attempted_fold_count": len(attempted), "attempted_pair_count": total,
            "abstained_pair_count": total - predicted, "prediction_coverage": predicted / total if total else None,
            "excluded_near_tie_pair_count": excluded, "abstention_reasons": dict(reasons),
            "folds": [{"fold": fold, "attempted": count, "predicted": len(groups[fold]),
                       "abstained": count - len(groups[fold]),
                       "accuracy": float(np.mean(groups[fold])) if groups[fold] else None}
                      for fold, count in attempted.items()],
        }

