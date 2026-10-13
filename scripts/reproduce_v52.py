"""Export evidence coverage and explicitly conditional v5.2 diagnostics."""
import json
from pathlib import Path
from frontierlab.core import Evidence, METHODS
from frontierlab.analysis import (PAIR_BASELINES, coverage, contributions, deletion_sensitivity,
                                  genealogy_evidence, validation_records)
from frontierlab.presentation import csv_export

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = Evidence(ROOT / "data/v5_2")
    output = ROOT / "outputs/v5_2"
    output.mkdir(parents=True, exist_ok=True)
    validation, predictions, model_counts = [], [], []
    for mode in ("family", "evaluator", "domain", "genealogy"):
        records = validation_records(evidence, mode)
        predictions.extend(records)
        for method in METHODS + PAIR_BASELINES:
            for threshold in (0, .10, .25):
                validation.append({"holdout": mode, "method": method, "threshold": threshold,
                                   **evidence.macro_accuracy(records, mode, method, threshold)})
            for model in evidence.models:
                rows = [r for r in records if model in (r["model_a"], r["model_b"])]
                model_counts.append({"holdout": mode, "method": method, "model": model, "attempted": len(rows),
                                     "predicted": sum(r[method] is not None for r in rows),
                                     "abstained": sum(r[method] is None for r in rows)})
    result = {"version": evidence.config["version"], "scope": "Conditional experiments; not a universal ranking",
              "coverage": coverage(evidence), "evidence_status": evidence.catalog.status_counts(),
              "experimental_full_portfolio": {m: evidence.index(evidence.all_fit(m)) for m in METHODS},
              "broader_genealogy_experiment": {m: genealogy_evidence(evidence).index(genealogy_evidence(evidence).all_fit(m)) for m in METHODS},
              "cross_validation": validation, "abstention_by_model": model_counts,
              "qualification": "Historical holdouts of selected identities. Deletion ranges are sensitivity, not uncertainty intervals; pair counts are correlated."}
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    files = {"coverage.csv": coverage(evidence), "holdout_predictions.csv": predictions,
             "abstention_by_model.csv": model_counts}
    for method in METHODS:
        name = method.lower().replace(" ", "_").replace(".", "_")
        files[name + "_contributions.csv"] = contributions(evidence, range(len(evidence.rows)), method)
        for mode in ("evaluator", "family"):
            files[name + "_remove_" + mode + ".csv"] = deletion_sensitivity(evidence, method, mode)
    for filename, records in files.items():
        (output / filename).write_text(csv_export(records), encoding="utf-8")
    print(f"Exported {len(predictions)} attempted holdout comparisons with explicit abstentions")


if __name__ == "__main__":
    main()
