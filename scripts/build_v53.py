"""Version the follow-up source review without changing frozen forecast inputs."""
import csv
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def json_file(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    old, target = ROOT / "data/v5_2", ROOT / "data/v5_3"
    if target.exists():
        raise ValueError("Refusing to overwrite a versioned source-review release")
    shutil.copytree(old, target)
    review = json.loads((ROOT / "reviews/source_review_2026_10_13.json").read_text())
    checked = {(r["benchmark_id"], r["model_id"]): r for r in review["observations"]}
    artifacts = {r["source_id"]: r for r in review["sources"]}
    observations = [json.loads(line) for line in (target / "observations.jsonl").read_text().splitlines()]
    sources = {r["source_id"]: r for r in map(json.loads, (target / "sources.jsonl").read_text().splitlines())}
    corrections = []
    for obs in observations:
        result = checked.get((obs["benchmark_id"], obs["model_id"]))
        if not obs["included"] or not result:
            continue
        obs["source_review_id"] = review["review_id"]
        if result["result"] == "different_dated_population":
            obs["source_review_qualification"] = result["qualification"]
            continue
        artifact = artifacts[result["source_id"]]
        if obs["score"] != result["score"]:
            corrections.append({"benchmark_id": obs["benchmark_id"], "model_id": obs["model_id"],
                                "previous": obs["score"], "current": result["score"], "source_url": artifact["url"],
                                "interpretation": "Current-source revision; prior transcription error versus later source update is unestablished"})
            obs["previous_release_score"] = obs["score"]
            obs["score"] = result["score"]
            obs["inclusion_reason"] = "Dated follow-up source result in v5.3; v5.2 and registered forecasts retain their original inputs"
        obs["evidence_status"] = "provisional_numeric_corroborated" if obs["benchmark_id"] in {"B010", "B013"} else "numeric_corroborated"
        source = sources[obs["source_id"]]
        source.update(url=artifact["url"], corroboration_urls=[artifact["url"]], observed_on="2026-10-13",
                      capture_type="auditor_transcription", retrieval_timestamp=artifact["retrieved_at"],
                      observation_locator=result["locator"], capture_representation=artifact["capture_type"],
                      capture_representation_sha256=artifact["capture_sha256"],
                      original_html_sha256="not_captured", source_review_id=review["review_id"],
                      qualification="Curated numeric transcription with source-reader or visible-table capture digest. Full reader captures are local; this is not original HTML or exact run verification.")
        source["transcribed_values"] = {"benchmark_id": obs["benchmark_id"],
                                       "model_name": source["transcribed_values"].get("model_name") or obs["model_id"],
                                       "score": obs["score"]}
        source["transcription_sha256"] = hashlib.sha256(json.dumps(source["transcribed_values"], sort_keys=True).encode()).hexdigest()
        if result.get("reported_plus_minus") is not None:
            ksp = obs["benchmark_id"] == "B054"
            obs["uncertainty"] = {"type": "reported_display_zero_uninterpreted" if ksp else "publisher_reported_SEM",
                                  "value": result["reported_plus_minus"], "source_url": artifact["url"],
                                  "methodology_url": "https://www.vals.ai/methodology",
                                  "sampling_unit": "not established for this particular run",
                                  "qualification": "KSP campaign/progress proxy: a displayed zero is not a confidence interval" if ksp else
                                  "Vals describes task-level or run-level SEM by study design; this is not paired model uncertainty or deployment variability"}
    (target / "observations.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in observations), encoding="utf-8")
    (target / "sources.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sources.values()), encoding="utf-8")
    identities = {r["model_id"]: r["model_name"] for r in csv.DictReader((target / "model_identities.csv").open())}
    scores = list(csv.DictReader((target / "scores.csv").open()))
    included = {(o["benchmark_id"], identities[o["model_id"]]): o for o in observations if o["included"]}
    for row in scores:
        obs = included[row["benchmark_id"], row["model_name"]]
        row.update(score=str(obs["score"]), evidence_status=obs["evidence_status"], verified_source_url=sources[obs["source_id"]]["url"])
    write_csv(target / "scores.csv", scores)
    systems = list(csv.DictReader((target / "systems.csv").open()))
    for system in systems:
        result = checked.get((system["benchmark_id"], system["model_id"]))
        if result and result["result"] != "different_dated_population":
            artifact = artifacts[result["source_id"]]
            system["source_review_id"] = review["review_id"]
            system["publisher_profile_defaults"] = json.dumps(artifact.get("reported_profile_defaults", {}), sort_keys=True)
            system["profile_defaults_scope"] = "Default profile settings; individual benchmark applicability is not certified"
            if system["model_id"] == "claude-opus-5-5" and result["source_id"] == "vals_opus":
                system["fallback_policy"] = "Vals reports refusal fallbacks to Opus 5 and Opus 4.8; benchmark-specific treatment varies; exact run version unknown"
    write_csv(target / "systems.csv", systems)
    config = json.loads((target / "config.json").read_text())
    config.update(version="v5.3-source-review-2026-10-13", release_status="tested_source_review", as_of="2026-10-13",
                  evidence_cutoff="2026-10-13", note="All 153 inherited observations investigated: 148 matching numbers, four AA revisions, one uncorroborated historical Arena population. No exact-run or equal-budget certification. Frozen forecasts continue to use v5.2.")
    json_file(target / "config.json", config)
    decisions = json.loads((target / "decisions.json").read_text())
    decisions.append({"id": "D005", "date": "2026-10-13", "decision": "Apply four dated AA Elo revisions in a new release",
                      "basis": corrections, "review_status": "Internal primary-source numeric check; project owner authorized publication"})
    decisions.append({"id": "D006", "date": "2026-10-13", "decision": "Retain Astra Arena Oct 8 value as individually uncorroborated",
                      "basis": "The Oct 13 leaderboard reports 1442 for another dated population; it cannot verify the stored Oct 8 value 1440", "review_status": "Explicit unresolved historical-source gap"})
    json_file(target / "decisions.json", decisions)
    json_file(target / "release.json", {"id": "v5.3", "status": "tested_source_review", "created_on": "2026-10-13",
              "evidence_cutoff": "2026-10-13", "scope": "Selected reported systems; dated source review, not verified equal-compute runs",
              "included_observations": 306, "excluded_alternatives": 1, "inherited_observations_investigated": 153,
              "numeric_corroborations_including_reconstructions": 305, "historical_population_not_corroborated": 1,
              "score_revisions": corrections, "exact_run_metadata": "incomplete", "independent_human_review": "pending owner task/eligibility review",
              "frozen_forecast_inputs": "data/v5_2 unchanged; the four revisions are not supplied to registered estimators"})
    print("Built v5.3: four AA revisions, 305 numeric corroborations/reconstructions, one explicit historical population gap")


if __name__ == "__main__":
    main()
