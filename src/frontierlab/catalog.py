"""Run-level evidence records with explicit unknowns and source qualifications."""
from collections import Counter
from datetime import date
from pathlib import Path
import json
import math
import hashlib

from .core import Evidence, METRIC_BOUNDS, csv_records, valid_url

STATUSES = {
    "numeric_corroborated", "inherited_not_rechecked", "derived_from_rounded_components",
    "provisional_numeric_corroborated", "provisional_inherited", "alternative_configuration",
}


def json_lines(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def unique(records, key):
    result = {}
    for record in records:
        identifier = record.get(key)
        if not identifier or identifier in result:
            raise ValueError(f"Missing or duplicate {key}: {identifier}")
        result[identifier] = record
    return result


class Catalog:
    def __init__(self, evidence: Evidence):
        self.evidence = evidence
        root = evidence.data_dir
        self.models = unique(list(csv_records(root / "model_identities.csv")), "model_id")
        self.systems = unique(list(csv_records(root / "systems.csv")), "system_id")
        self.sources = unique(json_lines(root / "sources.jsonl"), "source_id")
        self.observations = json_lines(root / "observations.jsonl")
        unique(self.observations, "observation_id")
        self.missingness = list(csv_records(root / "missingness.csv"))
        self.decisions = json.loads((root / "decisions.json").read_text(encoding="utf-8"))
        self.by_pair = {}
        names = [r["model_name"] for r in self.models.values()]
        if len(names) != len(set(names)) or set(names) != set(evidence.models):
            raise ValueError("Catalog model identities must match the calculation roster")
        benchmarks = {b.id: b for b in evidence.rows}
        for system in self.systems.values():
            if system["model_id"] not in self.models or system["benchmark_id"] not in benchmarks:
                raise ValueError(f"Unknown system reference: {system['system_id']}")
            for field in ("model_snapshot", "endpoint", "reasoning_effort", "harness", "fallback_policy", "resource_budget", "evaluation_date"):
                if not system.get(field):
                    raise ValueError(f"System field must be explicit, including unknown: {field}")
        for source in self.sources.values():
            if not valid_url(source["url"]):
                raise ValueError("Invalid source URL")
            if source["capture_type"] not in {"auditor_transcription", "inherited_link"}:
                raise ValueError("Unsupported source capture type")
            if source["observed_on"] != "unknown":
                date.fromisoformat(source["observed_on"])
            if source["capture_type"] == "auditor_transcription":
                if not source.get("transcription_sha256") or not source.get("transcribed_values"):
                    raise ValueError("A transcription requires its captured values and digest")
                actual = hashlib.sha256(json.dumps(source["transcribed_values"], sort_keys=True).encode()).hexdigest()
                if actual != source["transcription_sha256"]:
                    raise ValueError("Source transcription digest mismatch")
        for observation in self.observations:
            bid, mid, sid = observation["benchmark_id"], observation["model_id"], observation["system_id"]
            if bid not in benchmarks or mid not in self.models or sid not in self.systems:
                raise ValueError(f"Unknown observation reference: {observation['observation_id']}")
            if self.systems[sid]["model_id"] != mid or self.systems[sid]["benchmark_id"] != bid:
                raise ValueError("Observation and system identities disagree")
            if observation["source_id"] not in self.sources or observation["evidence_status"] not in STATUSES:
                raise ValueError("Unknown source or evidence status")
            source = self.sources[observation["source_id"]]
            if source["capture_type"] == "auditor_transcription":
                capture = source["transcribed_values"]
                if capture["benchmark_id"] != bid or capture["score"] != observation["score"]:
                    raise ValueError("Source transcription and observation disagree")
            for field in ("sample_count", "trial_count", "judge_version", "original_run_id"):
                if field not in observation or observation[field] in (None, ""):
                    raise ValueError(f"Observation field must be explicit: {field}")
            if not isinstance(observation["included"], bool) or not observation["inclusion_reason"]:
                raise ValueError("An inclusion decision and reason are required")
            value = observation["score"]
            low, high = METRIC_BOUNDS[benchmarks[bid].unit]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
                raise ValueError("Invalid observation score")
            if observation["evidence_status"] == "derived_from_rounded_components":
                components = observation.get("derivation", {}).get("components", [])
                if not components or any(not valid_url(c["source_url"]) or type(c["task_count"]) is not int or c["task_count"] <= 0
                                         or isinstance(c["score"], bool) or not math.isfinite(c["score"]) for c in components):
                    raise ValueError("Derived results require source-linked weighted components")
                derived = sum(c["score"] * c["task_count"] for c in components) / sum(c["task_count"] for c in components)
                if not math.isclose(value, derived, abs_tol=2e-6):
                    raise ValueError("Derived score disagrees with its components")
            if observation["included"]:
                key = bid, self.models[mid]["model_name"]
                if key in self.by_pair:
                    raise ValueError(f"Multiple included observations for {key}")
                self.by_pair[key] = observation
        engine = {(r["benchmark_id"], r["model_name"]): float(r["score"]) for r in evidence.score_records}
        if set(engine) != set(self.by_pair) or any(engine[k] != self.by_pair[k]["score"] for k in engine):
            raise ValueError("Calculation inputs and included catalog observations disagree")
        expected_missing = {(b.id, name) for b in evidence.rows for name in evidence.models} - set(engine)
        recorded_missing = set()
        for row in self.missingness:
            if row["model_id"] not in self.models or not row["reason"]:
                raise ValueError("Invalid missing-evidence reason")
            key = row["benchmark_id"], self.models[row["model_id"]]["model_name"]
            if key in recorded_missing:
                raise ValueError("Duplicate missing-evidence record")
            recorded_missing.add(key)
        if recorded_missing != expected_missing:
            raise ValueError("Every absent evidence cell requires exactly one reason")

    def details(self, benchmark_id, model_name):
        observation = self.by_pair.get((benchmark_id, model_name))
        if observation is None:
            return None
        return {
            **observation, "system": self.systems[observation["system_id"]],
            "source": self.sources[observation["source_id"]],
        }

    def status_counts(self):
        return dict(Counter(o["evidence_status"] for o in self.observations if o["included"]))
