"""Rebuild the reviewable v5.2 migration from frozen inputs and the audit ledger.

No remote page is fetched. Corroboration records are auditor transcriptions, not
immutable original HTML captures. Unknown run metadata stays explicitly unknown.
"""
from pathlib import Path
import csv
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frontierlab.core import Evidence


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, records, fields=None):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_lines(path, values):
    path.write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values), encoding="utf-8")


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def system_details(bid, name):
    effort, harness, fallback = "unknown", "unknown", "unknown"
    if bid in {f"B{i:03d}" for i in range(6, 16)}:
        effort = "high" if name == "Gemini 4 Argon" else "max"
        if name.startswith("Claude"):
            fallback = "Default Fallback label reported by AA; exact policy not reconstructed"
    if bid == "B036":
        effort = {"Claude Opus 5.5": "medium", "GPT-6 Astra": "max", "Claude Sonnet 5.5": "xhigh",
                  "Claude Fable 5.1": "medium", "GPT-6.1 Sol": "medium"}.get(name, "unknown")
        harness = "Claude Code" if name.startswith("Claude") else "Codex"
    if bid == "B032":
        effort = "high" if name in {"Claude Opus 5.5", "Gemini 4 Argon"} else "max"
    if bid == "B062":
        effort = "high" if name in {"Claude Opus 5.5", "Gemini 4 Argon"} else "xhigh" if name == "Claude Sonnet 5.5" else "max"
    if bid == "B050":
        effort = "high" if name == "Claude Opus 5.5" else "max"
    if bid == "B035":
        harness = "Terminus-2"
        effort = "high" if name == "Gemini 4 Argon" else "max"
    if bid in {"B034", "B037", "B060"}:
        effort = "xhigh" if bid == "B060" and name == "GPT-6 Astra" else "max"
    if bid == "B033":
        effort = "high" if name == "Gemini 4 Argon" else "max"
    if bid == "B041":
        effort = "xhigh" if name == "Claude Opus 5.5" else "max" if name.startswith("GPT") else "unknown"
    if bid == "B053":
        harness = "Claude Code" if name.startswith("Claude") else "Codex" if name.startswith("GPT") else "Google computer-use agent / Antigravity CLI"
    return effort, harness, fallback


def main():
    target = ROOT / "data" / "v5_2"
    target.mkdir(exist_ok=True)
    old = ROOT / "data" / "v5_1"
    ledger = read_csv(ROOT / "snapshots" / "source_corroboration_2026_10_12.csv")
    corroborated = {(r["benchmark_id"], r["model"]): r for r in ledger}
    scores = read_csv(old / "scores.csv")
    for name, value in (("Claude Fable 5.1", 50.9), ("GPT-6.1 Sol", 50.2)):
        scores.append({"benchmark_id": "B036", "model_name": name, "score": str(value),
                       "verified_source_url": "https://cognition.com/frontiercode",
                       "evidence_status": "numeric_corroborated_2026_10_12"})
    write_csv(target / "scores.csv", scores)
    benchmarks = read_csv(old / "benchmarks.csv")
    genealogy = {"B007": "gdp-related", "B012": "gdp-related", "B055": "gdp-related",
                 "B009": "terminal-related", "B031": "terminal-related", "B059": "terminal-related"}
    definitions = {
        "B006": "Combined rubric, analytical-quality and presentation Elo",
        "B007": "Published pairwise work-product preference Elo",
        "B014": "AA-Omniscience reliability index; -100 to 100, not percentage accuracy",
        "B032": "User-confirmed success in observational live sessions; populations may differ",
        "B033": "Pass@1 across three 80-task occupational groups",
        "B035": "Pass@1 across two 100-task SWE categories",
        "B036": "FrontierCode 1.1 Main weighted rubric Score; NOT the separate pass-rate column",
        "B040": "Remote Labor Index automation rate",
        "B041": "Pass@1 averaged over three attempts per task; source reports task-cluster intervals",
        "B053": "Mean progress across six games; one trial per cell, speed/harness included",
        "B054": "Observed progress in one KSP campaign; not a sampling confidence interval",
        "B061": "Task-weighted pass@1 across 507 tasks and 20 trials per task",
        "B062": "Blind human preference Elo; different effort settings, provisional Argon",
    }
    for row in benchmarks:
        bid = row["benchmark_id"]
        row.update(direction="higher", genealogy_id=genealogy.get(bid, row["family_id"]),
                   genealogy_note="Broader ancestry sensitivity assumption; disjoint tasks are not proven duplicate" if bid in genealogy else "No broader relationship reviewed",
                   metric_definition=definitions.get(bid, "Published evaluator score; see source for exact metric and aggregation"),
                   quality_status="publisher_under_review" if bid in {"B010", "B013"} else "recorded_with_limitations",
                   exclusion_reason="", benchmark_creator="unknown", execution_operator="unknown",
                   publishing_organisation=row["evaluator"], task_set_version="see_reported_configuration",
                   judge_version="unknown")
        if bid == "B036":
            row["configuration"] = "FrontierCode 1.1 Main: Opus medium / Claude Code; Astra max / Codex; Sonnet xhigh / Claude Code; Fable medium / Claude Code; Sol medium / Codex"
            row["provenance"] = "Five published Main Score cells numerically corroborated 2026-10-12; exact endpoint/run dates unknown"
    write_csv(target / "benchmarks.csv", benchmarks)
    for name in ("models.csv", "candidate_scores.csv", "external_indices.csv"):
        (target / name).write_text((old / name).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    config = json.loads((old / "config.json").read_text())
    config.update(version="v5.2-evidence-2026-10-13", as_of="2026-10-13", evidence_cutoff="2026-10-12",
                  release_status="reviewable_draft", catalog_required=True, expected_counts={"models": 8, "benchmarks": 57, "scores": 306},
                  normalization_reference="normalization_reference.csv",
                  note="Frozen reported configurations with two omitted FrontierCode cells restored. No current-best-system claim. Fixed v4.2 normalizers are an experimental reference, not capability or uncertainty units.")
    write_json(target / "config.json", config)
    baseline = Evidence(ROOT / "data")
    write_csv(target / "normalization_reference.csv", [{"benchmark_id": b.id, "denominator": repr(b.denominator),
                "reference_release": "v4.2", "reference_rule": "max(floor, population SD of frozen six-model scores)"} for b in baseline.rows])
    identities = []
    for row in read_csv(old / "models.csv"):
        identities.append({"model_id": slug(row["model_name"]), "model_name": row["model_name"],
                           "developer": row["developer"], "provider_snapshot_id": "unknown",
                           "released_on": row["released_on"] or "unknown",
                           "identity_qualification": "Canonical display identity; exact evaluated provider snapshot not reconstructed"})
    write_csv(target / "model_identities.csv", identities)
    model_ids = {r["model_name"]: r["model_id"] for r in identities}
    source_records, systems, observations = [], [], []
    law = "https://www.mercor.com/apex/apex-agents-leaderboard/corporate-lawyer-agent/"
    consulting = "https://www.mercor.com/apex/apex-agents-leaderboard/management-consultant-agent/"
    banking = "https://www.mercor.com/apex/apex-agents-leaderboard/investment-banking-analyst-agent/"
    integration = "https://www.mercor.com/apex/apex-swe-leaderboard/integration-swe/"
    observability = "https://www.mercor.com/apex/apex-swe-leaderboard/observability-swe/"
    derived = {("B033", "GPT-6 Astra"): ([73.4, 64.7, 55.9], [law, consulting, banking], 80),
               ("B033", "GPT-6.1 Sol"): ([63.4, 58.4, 58.1], [law, consulting, banking], 80),
               ("B035", "GPT-6 Astra"): ([62, 38], [integration, observability], 100),
               ("B035", "GPT-6.1 Sol"): ([61.5, 32.3], [integration, observability], 100),
               ("B035", "Gemini 4 Argon"): ([71.3, 27.3], [integration, observability], 100)}
    metadata = {r["benchmark_id"]: r for r in benchmarks}
    for row in scores:
        bid, name = row["benchmark_id"], row["model_name"]
        mid = model_ids[name]
        oid = bid.lower() + "-" + mid
        verification = corroborated.get((bid, name))
        status = "numeric_corroborated" if verification else "inherited_not_rechecked"
        if bid in {"B010", "B013"}:
            status = "provisional_numeric_corroborated" if verification else "provisional_inherited"
        if (bid, name) in derived:
            status = "derived_from_rounded_components"
        capture = {"benchmark_id": bid, "model_name": name, "score": float(row["score"])}
        source_records.append({"source_id": "source-" + oid,
            "url": row["verified_source_url"], "corroboration_urls": verification["source_url"].split(" | ") if verification else [],
            "observed_on": "2026-10-12" if verification else "unknown",
            "publication_date": "unknown", "capture_type": "auditor_transcription" if verification else "inherited_link",
            "transcribed_values": capture if verification else {},
            "transcription_sha256": hashlib.sha256(json.dumps(capture, sort_keys=True).encode()).hexdigest() if verification else "",
            "qualification": "Digest covers this curated numeric transcription, NOT original webpage bytes; frozen run identity/comparability is not certified"})
        effort, harness, fallback = system_details(bid, name)
        systems.append({"system_id": "system-" + oid, "model_id": mid, "benchmark_id": bid,
                        "model_snapshot": "unknown", "endpoint": "unknown", "reasoning_effort": effort,
                        "harness": harness, "fallback_policy": fallback, "resource_budget": "unknown",
                        "evaluation_date": "unknown", "configuration_status": "partially_documented" if effort != "unknown" or harness != "unknown" else "unknown",
                        "reported_configuration": metadata[bid]["configuration"], "tool_configuration": "unknown",
                        "retry_policy": "unknown", "harness_version": "unknown"})
        observation = {"observation_id": "observation-" + oid, "benchmark_id": bid, "model_id": mid,
                       "system_id": "system-" + oid, "source_id": "source-" + oid, "original_run_id": "unknown",
                       "score": float(row["score"]), "included": True, "evidence_status": status,
                       "sample_count": "unknown", "trial_count": "unknown", "judge_version": "unknown",
                       "inclusion_reason": "Frozen reported configuration carried forward for descriptive evidence; exact run metadata gaps retained" if bid != "B036" else "Same FrontierCode 1.1 Main metric and named system; restore previously omitted published cell",
                       "uncertainty": {"type": "not_captured", "value": None,
                                       "qualification": "No paired task-level uncertainty reconstructed; source intervals may have different interpretations"}}
        if (bid, name) in derived:
            values, urls, task_count = derived[bid, name]
            observation["derivation"] = {"formula": "task-count weighted mean", "rounding": "Inputs published to 0.1 percentage point; extra result digits are not measurement precision",
                "components": [{"score": value, "task_count": task_count, "source_url": url} for value, url in zip(values, urls)]}
        observations.append(observation)
    alt = "b032-claude-opus-5-5-max-alternative"
    base_system = next(r for r in systems if r["system_id"] == "system-b032-claude-opus-5-5")
    systems.append(dict(base_system, system_id="system-" + alt, reasoning_effort="max", reported_configuration="Opus Max on observational Agent Arena sessions"))
    capture = {"benchmark_id": "B032", "model_name": "Claude Opus 5.5 (Max)", "score": 17.29}
    source_records.append({"source_id": "source-" + alt, "url": "https://canary.arena.ai/leaderboard/agent",
        "corroboration_urls": ["https://canary.arena.ai/leaderboard/agent"], "observed_on": "2026-10-12",
        "publication_date": "2026-10-08", "capture_type": "auditor_transcription", "transcribed_values": capture,
        "transcription_sha256": hashlib.sha256(json.dumps(capture, sort_keys=True).encode()).hexdigest(),
        "qualification": "Curated numeric transcription; different live-session population from recorded High result"})
    observations.append({"observation_id": "observation-" + alt, "benchmark_id": "B032", "model_id": "claude-opus-5-5",
        "system_id": "system-" + alt, "source_id": "source-" + alt, "original_run_id": "unknown", "score": 17.29,
        "included": False, "evidence_status": "alternative_configuration",
        "sample_count": "unknown", "trial_count": "unknown", "judge_version": "unknown",
        "inclusion_reason": "Keep historical High configuration explicitly; Max belongs to a different observational population and is not a silent best-score substitution",
        "uncertainty": {"type": "reported_plus_minus", "value": 6.02, "qualification": "Source interval interpretation not reconstructed; not paired with High sessions"}})
    write_csv(target / "systems.csv", systems)
    write_lines(target / "sources.jsonl", source_records)
    write_lines(target / "observations.jsonl", observations)
    included = {(r["benchmark_id"], r["model_name"]) for r in scores}
    missing = [{"benchmark_id": b["benchmark_id"], "model_id": mid, "reason": "unknown_not_recorded_in_this_release",
                "qualification": "No score entered; untested, unavailable and excluded are not inferred from a blank cell"}
               for b in benchmarks for name, mid in model_ids.items() if (b["benchmark_id"], name) not in included]
    write_csv(target / "missingness.csv", missing)
    write_json(target / "decisions.json", [
        {"id": "D001", "date": "2026-10-13", "decision": "Restore Fable 5.1 and GPT-6.1 Sol FrontierCode Main Scores (50.9 and 50.2)", "basis": "Independent audit's original Cognition table transcription", "review_status": "Proposed release; review in pull request"},
        {"id": "D002", "date": "2026-10-13", "decision": "Retain Opus High 13.93; disclose Max 17.29 as excluded alternative", "basis": "Different observational session populations; frozen-system scope replaces best-available wording", "review_status": "Proposed release; review in pull request"},
        {"id": "D003", "date": "2026-10-13", "decision": "Fix experimental normalizers to v4.2 reference", "basis": "Prevent roster changes from redefining the ruler; does not make index a capability measure or scores comparable across releases", "review_status": "Declared experimental convention"},
        {"id": "D004", "date": "2026-10-13", "decision": "Expose provisional tasks and broader genealogy sensitivity", "basis": "AA labels SciCode/CritPt under review; ancestry grouping is a sensitivity assumption", "review_status": "Does not establish task duplication"},
    ])
    write_json(target / "release.json", {"id": "v5.2", "status": "reviewable_draft", "created_on": "2026-10-13",
        "evidence_cutoff": "2026-10-12", "scope": "Selected, frozen reported system configurations; descriptive evidence portfolio",
        "included_observations": 306, "excluded_alternatives": 1, "numerically_corroborated_in_audit": 153,
        "not_individually_rechecked_in_audit": 153, "exact_run_metadata": "incomplete",
        "original_webpage_archives": "not captured; source records distinguish transcriptions from inherited links",
        "historical_data": "data/ and data/v5_1/ are unchanged"})
    print("Built v5.2: 306 included observations, 1 excluded alternative, 150 explicit missing cells")


if __name__ == "__main__":
    main()
