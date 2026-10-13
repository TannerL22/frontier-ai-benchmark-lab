"""Seal fixed-roster forecasts and score explicitly reviewed future outcomes."""
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
import json
import math

from .analysis import PAIR_BASELINES, pair_vote
from .core import Evidence, METHODS, valid_url
from .integrity import digest, verify_manifest

SOURCE_BASELINE = "AA pair direction vote"


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Study timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def seal(root, destination):
    root, destination = Path(root), Path(destination)
    if destination.exists():
        raise ValueError("Refusing to overwrite a sealed study; use a new study ID")
    evidence = Evidence(root / "data" / "v5_2")
    protocol = json.loads((root / "studies/prospective_v1/protocol.json").read_text())
    train = list(range(len(evidence.rows)))
    graph = {method: evidence.pair_predictions(train, method) for method in METHODS}
    model_ids = {r["model_name"]: mid for mid, r in evidence.catalog.models.items()}
    records = []
    for domain in evidence.domain_weights:
        for a, b in combinations(range(len(evidence.models)), 2):
            values = {method: graph[method][a, b] for method in METHODS}
            values[PAIR_BASELINES[0]] = pair_vote(evidence, train, a, b)
            values[PAIR_BASELINES[1]] = pair_vote(evidence, train, a, b, domain)
            values[PAIR_BASELINES[2]] = 0.0
            values[SOURCE_BASELINE] = pair_vote(evidence, [i for i in train if evidence.rows[i].evaluator == "AA"], a, b)
            for method, value in values.items():
                probability = .5 if value is None else (
                    1 / (1 + math.exp(-value)) if method in METHODS else (value + 1) / 2)
                records.append({"domain": domain, "model_a": model_ids[evidence.models[a]],
                                "model_b": model_ids[evidence.models[b]], "method": method,
                                "margin": value, "probability_b_wins": probability,
                                "abstention": "no_identifiable_training_comparison" if value is None else ""})
    destination.mkdir(parents=True)
    (destination / "forecasts.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")
    inputs = list((root / "data/v5_2").glob("*")) + list((root / "src/frontierlab").glob("*.py"))
    inputs += [root / "studies/prospective_v1/protocol.json", root / "scripts/prospective_study.py"]
    registration = {
        "status": "locally_sealed_draft_requires_public_registration_before_outcome_collection",
        "sealed_at": datetime.now(timezone.utc).isoformat(), "protocol": protocol,
        "input_sha256": {p.relative_to(root).as_posix(): digest(p) for p in sorted(inputs) if p.is_file()},
        "forecast_sha256": digest(destination / "forecasts.jsonl"),
        "model_ids": list(model_ids.values()), "domains": list(evidence.domain_weights),
        "seen_families": evidence.families, "seen_genealogies": sorted({r.genealogy for r in evidence.rows}),
        "seen_benchmarks": [r.id for r in evidence.rows], "forecast_count": len(records),
        "qualification": "A local digest establishes content integrity, not independent proof of registration time. Publish this bundle before collecting eligible outcomes.",
    }
    (destination / "registration.json").write_text(json.dumps(registration, indent=2) + "\n", encoding="utf-8")
    (destination / "seal.json").write_text(json.dumps({"sha256": {
        "registration.json": digest(destination / "registration.json"),
        "forecasts.jsonl": digest(destination / "forecasts.jsonl"),
    }}, indent=2) + "\n", encoding="utf-8")
    return registration


def verify(root, destination):
    destination = Path(destination)
    verify_manifest(destination, destination / "seal.json")
    registration = json.loads((destination / "registration.json").read_text())
    verify_manifest(Path(root), {"sha256": registration["input_sha256"]})
    if digest(destination / "forecasts.jsonl") != registration["forecast_sha256"]:
        raise ValueError("Forecast integrity mismatch")
    return registration


def score_future(root, destination, outcomes):
    registration = verify(root, destination)
    forecasts = [json.loads(line) for line in (Path(destination) / "forecasts.jsonl").read_text().splitlines()]
    prediction = defaultdict(list)
    for record in forecasts:
        prediction[record["domain"], record["model_a"], record["model_b"]].append(record)
    results, rejected, seen = [], [], set()
    accepted, ties = 0, 0
    for row_number, outcome in enumerate(outcomes, 1):
        try:
            bid, family, genealogy, domain = [outcome[key] for key in ("benchmark_id", "family_id", "genealogy_id", "domain")]
            if not all(isinstance(v, str) and v.strip() for v in (bid, family, genealogy, domain)):
                raise ValueError("Empty outcome identity")
            if bid in seen or bid in registration["seen_benchmarks"]:
                raise ValueError("Duplicate or previously seen benchmark")
            seen.add(bid)
            if family in registration["seen_families"] or genealogy in registration["seen_genealogies"]:
                raise ValueError("Previously seen family or ancestry; not a new-family outcome")
            if domain not in registration["domains"] or outcome["direction"] not in {"higher", "lower"}:
                raise ValueError("Unknown domain or direction")
            if timestamp(outcome["published_at"]) <= timestamp(registration["sealed_at"]):
                raise ValueError("Outcome predates registration")
            if not valid_url(outcome["source_url"]) or outcome["review_accepted"] is not True or not outcome["review_reason"]:
                raise ValueError("Source and explicit eligibility review are required")
            values, systems = outcome["scores"], outcome["system_records"]
            if len(values) < 2 or not set(values).issubset(registration["model_ids"]):
                raise ValueError("At least two scores from the registered roster are required")
            for mid, value in values.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Scores must be finite numbers")
                if mid not in systems or any(not systems[mid].get(key) for key in (
                        "model_snapshot", "endpoint", "reasoning_effort", "harness", "fallback_policy", "resource_budget", "evaluation_date")):
                    raise ValueError("Each outcome requires explicit system metadata, including unknowns")
            accepted += 1
            for a, b in combinations(registration["model_ids"], 2):
                if a not in values or b not in values:
                    continue
                margin = (values[b] - values[a]) * (1 if outcome["direction"] == "higher" else -1)
                if margin == 0:
                    ties += 1
                    continue
                for pred in prediction[domain, a, b]:
                    value = pred["margin"]
                    accuracy = .5 if value is None or value == 0 else float(value * margin > 0)
                    results.append({**pred, "family_id": family, "benchmark_id": bid,
                                    "observed_b_wins": int(margin > 0), "accuracy_abstention_half": accuracy,
                                    "brier": (pred["probability_b_wins"] - int(margin > 0)) ** 2})
        except (KeyError, TypeError, ValueError) as error:
            rejected.append({"row": row_number, "benchmark_id": outcome.get("benchmark_id"), "reason": str(error)})
    summaries = []
    for method in dict.fromkeys(r["method"] for r in forecasts):
        groups = defaultdict(list)
        rows = [r for r in results if r["method"] == method]
        for row in rows:
            groups[row["family_id"]].append(row)
        def macro(field):
            return sum(sum(r[field] for r in g) / len(g) for g in groups.values()) / len(groups) if groups else None
        predicted = [r for r in rows if r["margin"] is not None]
        summaries.append({"method": method, "family_count": len(groups), "attempted": len(rows),
                          "predicted": len(predicted), "abstained": len(rows) - len(predicted),
                          "family_macro_accuracy_abstention_half": macro("accuracy_abstention_half"),
                          "family_macro_brier": macro("brier"),
                          "conditional_pair_accuracy": sum(r["accuracy_abstention_half"] for r in predicted) / len(predicted) if predicted else None})
    model_counts = [{"method": method, "model_id": mid,
                     "attempted": sum(r["method"] == method and mid in (r["model_a"], r["model_b"]) for r in results),
                     "abstained": sum(r["method"] == method and r["margin"] is None and mid in (r["model_a"], r["model_b"]) for r in results)}
                    for method in dict.fromkeys(r["method"] for r in forecasts) for mid in registration["model_ids"]]
    return {"status": "future_outcomes_scored" if results else "no_eligible_non_tied_pairs",
            "accepted_outcome_count": accepted, "observed_tied_pair_count": ties, "model_counts": model_counts,
            "summaries": summaries, "rejected_outcomes": rejected, "predictions": results,
            "qualification": "Clustered by registered family. No confidence intervals from correlated model pairs. Selection and publication biases remain possible."}
