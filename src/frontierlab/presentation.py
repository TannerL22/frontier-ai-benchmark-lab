"""Small presentation adapters: no second calculation engine."""
from io import StringIO
import csv


def csv_export(rows):
    if not rows:
        return ""
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def system_record(evidence, benchmark, model):
    if evidence.catalog:
        return evidence.catalog.details(benchmark.id, model)
    return {"evidence_status": "historical_record_not_individually_rechecked_here",
            "original_run_id": "unknown", "inclusion_reason": "Frozen historical evidence",
            "system": {"reasoning_effort": "unknown", "harness": "unknown", "fallback_policy": "unknown",
                       "model_snapshot": "unknown", "endpoint": "unknown", "resource_budget": "unknown",
                       "evaluation_date": "unknown", "reported_configuration": benchmark.config},
            "source": {"url": benchmark.source, "observed_on": "unknown", "capture_type": "inherited_link",
                       "qualification": benchmark.provenance},
            "uncertainty": {"type": "not_captured", "qualification": "Historical source uncertainty not reconstructed"}}
